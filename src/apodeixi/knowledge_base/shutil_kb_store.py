import os                                               as _os
import shutil                                           as _shutil
import yaml                                             as _yaml

from apodeixi.knowledge_base.isolation_kb_store         import Isolation_KBStore_Impl
from apodeixi.knowledge_base.knowledge_base_util        import ManifestUtils
from apodeixi.util.a6i_error                            import ApodeixiError
from apodeixi.util.path_utils                           import PathUtils

class Shutil_KBStore_Impl(Isolation_KBStore_Impl):
    '''
    File-system-based implementation of the KnowledgeBaseStore where environment synchronization is done
    via the "shutil" module, i.e., via file system operations that copy entire folders across environments.
    
    The entire knowledge base is held under a two root folders
    (one for postings and one for all derived data, including manifests)
    and follows a structure based on filing schemes of the KB_ProcessingRules.

    Implements failover for reads by re-trying in parent environment, if one exists and if such failover policy
    is stipulated in the current environment's configuration.

    @param kb_rootdir A string, corresponding to the absolute path in the local machine
                            corresponding to the KnowledgeBase.
    @param clientURL A string, corresponding to the absolute path to a root folder in a collaboration
                            drive system (such as SharePoint) in which end-users will collaborate to create
                            the Excel spreadsheets that will be eventually posted to the KnowledgeBase. This
                            shared drive is also the location to which the KnowledgeBase will save
                            generated forms or reports requested by end-users. This is a "root folder" in that
                            the structure below will be assumed to follow the filing structure of the
                            KnowledgeBase for postings.
    '''
    def __init__(self, parent_trace, kb_rootdir, clientURL):

        super().__init__(parent_trace, kb_rootdir, clientURL)

    def beginTransaction(self, parent_trace):
        '''
        Starts an isolation state in which all subsequent I/O is done in an isolation area
        dedicated to this transaction, and not applied back to the store's persistent area until the
        transaction is committed..
        '''
        return super().beginTransaction(parent_trace)

    def commitTransaction(self, parent_trace):
        '''
        Finalizes a transaction previously started by beginTransaction, by cascading any I/O previously done in
        the transaction's isolation area to the store's persistent area.
        '''
        env, parent_env             = self._validate_transaction_end_of_life(parent_trace)

        src_postings_root           = env.postingsURL(parent_trace)
        dst_postings_root           = parent_env.postingsURL(parent_trace)

        src_manifests_root          = env.manifestsURL(parent_trace)
        dst_manifests_root          = parent_env.manifestsURL(parent_trace)

        src_clientURL_root          = env.clientURL(parent_trace)
        dst_clientURL_root          = parent_env.clientURL(parent_trace)

        # If the parent environment is also a transactional envinronment, we will have to record in it
        # the events so that when the parent is committed, those events are cascaded to the parent's parent.
        # But it may also be that the parent is not transactional, which is why the `parent_events`
        # variable may be None and why we need to be checking for that all the time.
        parent_name                 = parent_env.name(parent_trace)
        if parent_name in self._transaction_events_dict.keys():
            parent_events           = self._transaction_events_dict[parent_name]
        else:
            parent_events           = None

        # **GOTCHA** 
        # 
        # Don't call pop()! We want to see the "last transaction's" environment, but not yet remove
        # the last transaction (so peek, not pop). The reason is that if any of the subsequent code in this commit() method
        # raises an exception, it will cause a subsequent problem for the abortTransaction method,
        # since abortTransaction will look for the "last transaction" and will not find it (or will)
        # find the wrong one) if we have poped. So use the [-1] notation to peek (not pop!) the last
        # transaction. Later, just before exiting this method, do the pop()
        ending_env                  = self._transactions_stack[-1]
        events                      = self._transaction_events_dict[ending_env.name(parent_trace)]

        for relative_path in events.posting_writes():
            from_path               = src_postings_root + "/" + relative_path
            to_path                 = dst_postings_root + "/" + relative_path
            to_dir                  = _os.path.dirname(to_path)
            PathUtils().create_path_if_needed(parent_trace, to_dir)
            PathUtils().copy_file(parent_trace, from_path, to_dir)

            if parent_events != None:
                parent_events.remember_posting_write(relative_path)

        for relative_path in events.manifest_writes():
            from_path               = src_manifests_root + "/" + relative_path
            to_path                 = dst_manifests_root + "/" + relative_path
            to_dir                  = _os.path.dirname(to_path)
            PathUtils().create_path_if_needed(parent_trace, to_dir)
            PathUtils().copy_file(parent_trace, from_path, to_dir)

            if parent_events != None:
                parent_events.remember_manifest_write(relative_path)

        for relative_path in events.clientURL_writes():
            from_path               = src_clientURL_root + "/" + relative_path
            to_path                 = dst_clientURL_root + "/" + relative_path
            # Normally clientURL is the same across environments (except mostly in test situations),
            # so to prevent the copy operation from raising an exception make sure we only attempt to copy
            # the file when the two paths are different
            if not _os.path.samefile(from_path, to_path):
            #if from_path != to_path: 
                to_dir                  = _os.path.dirname(to_path)
                PathUtils().create_path_if_needed(parent_trace, to_dir)
                PathUtils().copy_file(parent_trace, from_path, to_dir)

                if parent_events != None:
                    parent_events.remember_clientURL_write(relative_path)

        for relative_path in events.posting_deletes():
            to_path                 = dst_postings_root + "/" + relative_path
            if 0 == PathUtils().remove_file_if_exists(parent_trace, to_path):
                if parent_events != None:
                    parent_events.remember_posting_delete(relative_path)

        for relative_path in events.manifest_deletes():
            to_path                 = dst_manifests_root + "/" + relative_path
            if 0 == PathUtils().remove_file_if_exists(parent_trace, to_path):
                if parent_events != None:
                    parent_events.remember_manifest_deletes(relative_path)

        for relative_path in events.clientURL_deletes():
            to_path                 = dst_clientURL_root + "/" + relative_path
            if 0 == PathUtils().remove_file_if_exists(parent_trace, to_path):
                if parent_events != None:
                    parent_events.remember_clientURL_deletes(relative_path)


        # Now remove the environment of the transaction we just committed
        self.removeEnvironment(parent_trace, env.name(parent_trace)) 
        self.activate(parent_trace, parent_env.name(parent_trace))

        # **GOTCHA** 
        # 
        # Now it is safe to pop() - it wasn't safe earlier because if any of the code in this method
        # raised an exception after having popped the last transaction in the stack, the abortTransaction
        #method woudld have failed since it wouldh't have found the last transaction to then abort it.
        ending_env                  = self._transactions_stack.pop()
        events                      = self._transaction_events_dict.pop(ending_env.name(parent_trace))

    def abortTransaction(self, parent_trace):
        '''
        Aborts a transaction previously started by beginTransaction, by deleting transaction's isolation area,
        effectively ignoring any I/O previously done during the transaction's lifetime, and leaving the
        KnowledgeBaseStore in a state such that any immediately following I/O operation would be done 
        directly to the store's persistent area.
        '''
        return super().abortTransaction(parent_trace)


    def activate(self, parent_trace, environment_name):
        '''
        Switches the store's current environment to be the one identified by the `environment_name`, unless
        no such environment exists in which case it raises an ApodeixiError
        '''
        super().activate(parent_trace, environment_name)

    def deactivate(self, parent_trace):
        '''
        Switches the store's current environment to be the base environment.
        '''
        super().deactivate(parent_trace)

    def copy_posting_across_environments(self, parent_trace, handle, from_environment, to_environment):
        '''
        Copies the posting file denoted by the `handle` in the `from_environment` to the `to_environment`
        '''
        from_path       = from_environment.postingsURL(parent_trace)    + "/" + handle.getRelativePath(parent_trace)
        to_path         = to_environment.postingsURL(parent_trace)      + "/" + handle.getRelativePath(parent_trace)
        to_dir          = _os.path.dirname(to_path)

        
        my_trace                    = parent_trace.doing("Copying a posting file",
                                        data = {"src_path":     from_path,
                                                "to_dir":       to_dir})
        if not _os.path.exists(to_dir):
            PathUtils().create_path_if_needed(parent_trace=my_trace, path=to_dir)
        PathUtils().copy_file(parent_trace, from_path, to_dir)

    def _file_not_found_error(self, ex):
        '''
        Helper method. Returns true if `ex` is an ApodeixiError triggered by a file not found
        '''
        if not type(ex) == ApodeixiError or not 'error' in ex.data.keys():
            return False
        elif "No such file or directory" in ex.data['error']:
            return True
        else:
            return False

    def loadPostingLabel(self, parent_trace, posting_label_handle):
        '''
        Loads and returns a DataFrame based on the `posting_label_handle` provided
        '''
        try:
            label_df                    = super().loadPostingLabel(parent_trace, posting_label_handle)          
        except ApodeixiError as ex:
            # Try again in parent environment if failover is configured and error is a missing file
            if self._file_not_found_error(ex) and self._failover_posting_reads_to_parent(parent_trace):
                my_trace                = parent_trace.doing("Searching in parent environment")
                # Temporarily switch to the environment in which to search
                original_env            = self.current_environment(my_trace)
                self.activate(my_trace, self.parent_environment(my_trace).name(my_trace))
                label_df                = self.loadPostingLabel(
                                                    parent_trace                = my_trace,
                                                    posting_label_handle        = posting_label_handle)
                # Now that search in parent environment is done, reset back to original environment
                self.activate(my_trace, original_env.name(my_trace))
                # Before leaving, copy the parent's data into our environment, so next time 
                # we don't have to failover again
                self.copy_posting_across_environments(  
                                                parent_trace        = my_trace, 
                                                handle              = posting_label_handle, 
                                                from_environment    = self.parent_environment(my_trace), 
                                                to_environment      = self.current_environment(my_trace))
            else:
                raise ex

        return label_df

    def loadPostingData(self, parent_trace, data_handle, config):
        '''
        Loads and returns a DataFrame based on the `posting_data_handle` provided

        @param config PostingConfig
        '''
        try:
            df                      = super().loadPostingData(parent_trace, data_handle, config)
        except ApodeixiError as ex:
            # Try again in parent environment if failover is configured and error is a missing file
            if self._file_not_found_error(ex) and self._failover_posting_reads_to_parent(parent_trace):
                my_trace                = parent_trace.doing("Searching in parent environment")
                # Temporarily switch to the environment in which to search
                original_env            = self.current_environment(my_trace)
                self.activate(my_trace, self.parent_environment(my_trace).name(my_trace))
                df                      = self.loadPostingData(
                                                    parent_trace        = my_trace,
                                                    data_handle         = data_handle,
                                                    config              = config)
                # Now that search in parent environment is done, reset back to original environment
                self.activate(my_trace, original_env.name(my_trace))
                # Before leaving, copy the parent's data into our environment, so next time 
                # we don't have to failover again
                self.copy_posting_across_environments(  
                                                parent_trace        = my_trace, 
                                                handle              = data_handle, 
                                                from_environment    = self.parent_environment(my_trace), 
                                                to_environment      = self.current_environment(my_trace))
            else:
                raise ex

        return df

    def searchPostings(self, parent_trace, posting_api, filing_coordinates_filter=None):
        '''
        Returns a list of PostingLabelHandle objects, one for each posting in the Knowledge Base that matches
        the given criteria:

        * They are all postings for the `posting_api`
        * They pass the given filters

        @param posting_api A string that identifies the type of posting represented by an Excel file. For example,
                            'milestone.modernization.a6i' is a recognized posting API and files that end with that suffix,
                            such as 'opus_milestone.modernization.a6i.xlsx' will be located by this method.
        @param filing_coordinates_filter A function that takes a FilingCoordinates instance as a parameter and returns a boolean. 
                            Any FilingCoordinates instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        '''
        ME                          = Shutil_KBStore_Impl

        if self._failover_posting_reads_to_parent(parent_trace):
            # Search in parent first, and copy anything found to the current environment

            my_trace                = parent_trace.doing("Searching in parent environment")
            # Temporarily switch to the environment in which to search
            original_env            = self.current_environment(my_trace)
            self.activate(my_trace, self.parent_environment(my_trace).name(my_trace))
            parent_handles          = self.searchPostings(
                                                parent_trace                = my_trace,
                                                posting_api                 = posting_api,
                                                filing_coordinates_filter   = filing_coordinates_filter)
            # Now that search in parent environment is done, reset back to original environment
            self.activate(my_trace, original_env.name(my_trace))

            # Populate current environment with anything found in the parent environment, but only if it is not
            # already in current environment
            my_trace                = parent_trace.doing("Copying postings from parent environment",
                                                data = {"parent environment name":  
                                                                    self.parent_environment(my_trace).name(my_trace),
                                                        "current environment name":     
                                                                    self.current_environment(my_trace).name(my_trace)})
            for handle in parent_handles:
                self.copy_posting_across_environments(  
                                                parent_trace        = my_trace, 
                                                handle              = handle, 
                                                from_environment    = self.parent_environment(my_trace), 
                                                to_environment      = self.current_environment(my_trace))

        my_trace                = parent_trace.doing("Searching in environment '" 
                                                        + str(self.current_environment(parent_trace).name(parent_trace)) 
                                                        + "'" )
        scanned_handles             = super().searchPostings(
                                                parent_trace                = my_trace, 
                                                posting_api                 = posting_api, 
                                                filing_coordinates_filter   = filing_coordinates_filter)
        return scanned_handles

    def persistManifest(self, parent_trace, manifest_dict):
        '''
        Persists manifest_dict as a yaml object and returns a ManifestHandle that uniquely identifies it.

        Will raise an ApodeixiError if version consistency is violated, i.e., can only save
        manifest_dict with version N+1 if N is the highest version existing in the KnowledgeStore, if any. 
        If no prior version of the manifests exists then the manifest_dict must have version number equal to 1.
        '''
        my_trace                        = parent_trace.doing("Checking version consistency")
        if True:
            self.checkDuplicateManifest(my_trace, manifest_dict)

            prior_manifest = self.retrievePreviousManifest(my_trace, manifest_dict)

            new_handle                  = ManifestUtils().inferHandle(my_trace, manifest_dict)
            new_version                 = new_handle.version

            # Check that if we are doing an update a prior version does exist
            if new_version > 1 and prior_manifest == None: 
                raise ApodeixiError(my_trace, "Can't persist manifest with version " + str(new_version) 
                                                + " because no prior manifest exist with version " + str(new_version - 1),
                                            data = {"manifest handle": new_handle.display(my_trace)})
            
        my_trace                        = parent_trace.doing("Persisting manifest")
        handle                          = super().persistManifest(parent_trace, manifest_dict)
        return handle

    def findLatestVersionManifest(self, parent_trace, manifest_api_name, namespace, name, kind):
        '''
        For a given manifest API, a manifest is logically identified by its name and kind properties within 
        a given namespace.
        However, there might be multiple versions of a logical manifest (versions are integers starting
        at 1, 2, 3, ..., with version increasing each time the manifest gets updated).

        This method returns a manifest and a string.
        
        The manifest is the most recent version of the manifest that is logically identified
        by the parameters.
        The 2nd returned value is the path to that manifest.

        If no such manifest exists in the KnowledgeBase store then the first returned object is None.

        Example: for file-based stores, a manifest may be stored in a filename like:

            $KB_STORE/manifests/my-corp.production/modernization.default.dec-2020.fusionopus/big-rock.2.yaml

            In this example, 
                * the namespace is "my-corp.production"
                * the name is "modernization.default.dec-2020.fusionopus"
                * the kind is "big-rock"
                * the version is 2 (an int)
                * the manifest api is embedded within the YAML file. The YAML file has a field called
                  "apiVersion" with a value like "delivery-planning.journeys.a6i.io/v1a", and the manifest api
                  is the substring without the suffix: "delivery-planning.journeys.a6i.io"

        @param manifest_api_name A string representing the Apodeixi API defining the YAML schemas for the
                    manifest kinds subsumed under such API. The search for manifests is filtered to those
                    whose YAML representation declares itself as falling under this API.
                    Example: 'delivery-planning.journeys.a6i.io'
        @param namespace A string. Represents the namespace in the KnowledgeBase store's manifests area 
                        where to look for the manifest.
        @param name A string representing the name of the manifest. Along with kind, this identifies a 
                    unique logical manifest (other than version number)
        @param kind A string representing the kind of the manifest. Along with kind, this identifies a unique 
                    logical manifest (other than version number)
        '''
        manifest, manifest_path         = super().findLatestVersionManifest(parent_trace, manifest_api_name, 
                                                                                namespace, name, kind)

        if manifest == None:
            # Not found, so normally we should return None. But before giving up, look in parent environment
            # if we have been configured to fail over the parent environment whenver we can't find something
            if self._failover_manifest_reads_to_parent(parent_trace):
                # Search in parent first, and copy anything found to the current environment

                my_trace                = parent_trace.doing("Searching in parent environment")
                # Temporarily switch to the parent environment, and try again
                original_env            = self.current_environment(my_trace)
                self.activate(my_trace, self.parent_environment(my_trace).name(my_trace))

                manifest, manifest_path = self.findLatestVersionManifest(my_trace, manifest_api_name, 
                                                                                namespace, name, kind)
                # Now that search in parent environment is done, reset back to original environment
                self.activate(my_trace, original_env.name(my_trace))

                # Populate current environment with anything found in the parent environment, but only if it is not
                # already in current environment
                if manifest != None:
                    my_trace            = parent_trace.doing("Copying manifest from parent environment",
                                                    data = {"parent environment name":  
                                                                        self.parent_environment(my_trace).name(my_trace),
                                                            "current environment name":     
                                                                        self.current_environment(my_trace).name(my_trace)})
                
                
                    from_path           = manifest_path
                    to_dir              = self.current_environment(my_trace).postingsURL(parent_trace) 

                    if not _os.path.exists(to_dir):
                        my_trace                    = parent_trace.doing("Copying a manifest file",
                                                        data = {"src_path":     from_path,
                                                                "to_dir":       to_dir})
                        PathUtils().create_path_if_needed(parent_trace=my_trace, path=to_dir)
                    PathUtils().copy_file(parent_trace, from_path, to_dir)

        return manifest, manifest_path

    def retrievePreviousManifest(self, parent_trace, manifest_dict):
        '''
        Given a manifest expressed as a dict with a certain version N, will retrieve the same manifest
        but with version N-1, and return is a dict.

        If no prior version exists, it returns None
        '''
        new_handle                  = ManifestUtils().inferHandle(parent_trace, manifest_dict)
        new_version                 = new_handle.version

        if new_version < 1: # versions should be 1, 2, 3, .. etc, not 0 or below
            raise ApodeixiError(parent_trace, "Invalid manifest with a version below 1",
                                            data = {"version given": str(new_version),
                                                    "manifest handle": new_handle.display(parent_trace)})
        # Check that if we are doing an update a prior version does exist
        prior_handle            = new_handle
        prior_handle.version    = new_version - 1
        prior_manifest, prior_manifest_path     = self.retrieveManifest(parent_trace, prior_handle)

        return prior_manifest

    def checkDuplicateManifest(self, parent_trace, manifest_dict):
        '''
        Given a manifest expressed as a dict with a certain version N, will confirm that the store
        does not already have a manifest with version N.

        If it does, this method raises an ApodeixiError

        '''
        new_handle                  = ManifestUtils().inferHandle(parent_trace, manifest_dict)
        new_version                 = new_handle.version

        if new_version < 1: # versions should be 1, 2, 3, .. etc, not 0 or below
            raise ApodeixiError(parent_trace, "Invalid manifest with a version below 1",
                                            data = {"version given": str(new_version),
                                                    "manifest handle": new_handle.display(parent_trace)})
        # Check that no manifest exists with this version
        duplicate_manifest, duplicate_manifest_path     = self.retrieveManifest(parent_trace, new_handle)
        if duplicate_manifest != None:
            raise ApodeixiError(parent_trace, "Invalid duplicate manifest: one already exists for the given version",
                                            data = {"version given": str(new_version),
                                                    "manifest handle": new_handle.display(parent_trace)})

    def retrieveManifest(self, parent_trace, manifest_handle):
        '''
        Returns a dict and a string.
        
        The dict represents the unique manifest in the store that is identified by the `manifest handle`.
        
        The string represents the full pathname for the manifest.

        If none exists, it returns (None, None). That said, before giving up and returning (None, None), 
        this method will attempt to find the manifest in the parent environment if that is what is stipulated
        in the current environment's configuration

        @param manifest_handle A ManifestHandle instance that uniquely identifies the manifest we seek to retrieve.
        '''
        manifest, manifest_path         = super().retrieveManifest(parent_trace, manifest_handle)

        if manifest == None:
            # Not found, so normally we should return None. But before giving up, look in parent environment
            # if we have been configured to fail over the parent environment whenver we can't find something
            if self._failover_manifest_reads_to_parent(parent_trace):
                # Search in parent first, and copy anything found to the current environment

                my_trace                = parent_trace.doing("Searching in parent environment")
                # Temporarily switch to the parent environment, and try again
                original_env            = self.current_environment(my_trace)
                self.activate(my_trace, self.parent_environment(my_trace).name(my_trace))

                manifest, manifest_path = self.retrieveManifest(my_trace, manifest_handle)
                # Now that search in parent environment is done, reset back to original environment
                self.activate(my_trace, original_env.name(my_trace))

                # Populate current environment with anything found in the parent environment, but only if it is not
                # already in current environment
                if manifest != None:
                    my_trace            = parent_trace.doing("Copying manifest from parent environment",
                                                    data = {"parent environment name":  
                                                                        self.parent_environment(my_trace).name(my_trace),
                                                            "current environment name":     
                                                                        self.current_environment(my_trace).name(my_trace)})
                
                
                    from_path           = manifest_path
                    to_dir              = self.current_environment(my_trace).postingsURL(parent_trace) 

                    if not _os.path.exists(to_dir):
                        my_trace                    = parent_trace.doing("Copying a manifest file",
                                                        data = {"src_path":     from_path,
                                                                "to_dir":       to_dir})
                        PathUtils().create_path_if_needed(parent_trace=my_trace, path=to_dir)
                    PathUtils().copy_file(parent_trace, from_path, to_dir)


        return manifest, manifest_path

    def archivePosting(self, parent_trace, posting_label_handle):
        '''
        Used after a posting Excel file has been processed. It moves the Excel file to a newly created folder dedicated 
        to this posting event and returns a PostingLabelHandle to identify the Excel file in this newly
        created archival folder.       
        '''
        archival_handle                     = super().archivePosting(parent_trace, posting_label_handle)
        
        return archival_handle

    def logPostEvent(self, parent_trace, controller_response):
        '''
        Used to record in the store information about a posting event that has been completed.
        '''
        log_txt                             = super().logPostEvent(parent_trace, controller_response)

        return log_txt

    def logFormRequestEvent(self, parent_trace, form_request, controller_response):
        '''
        Used to record in the store information about a request form event that has been completed.
        '''
        log_txt                             = super().logFormRequestEvent(parent_trace, form_request, controller_response)
        return log_txt

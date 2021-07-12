import os                                               as _os
import shutil                                           as _shutil
import yaml                                             as _yaml

from apodeixi.knowledge_base.isolation_kb_store         import Isolation_KnowledgeBaseStore
from apodeixi.util.a6i_error                            import ApodeixiError
from apodeixi.util.path_utils                           import PathUtils

class File_KnowledgeBaseStore(Isolation_KnowledgeBaseStore):
    '''
    File-system-based implementation of the KnowledgeBaseStore. The entire knowledge base is held under a two root folders
    (one for postings and one for all derived data, including manifests)
    and follows a structure based on filing schemes of the KB_ProcessingRules.

    Implements failover for reads by re-trying in parent environment, if one exists and if such failover policy
    is stipulated in the current environment's configuration.
    '''
    def __init__(self, postings_rootdir, manifests_roodir):
        super().__init__(postings_rootdir, manifests_roodir)

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
        dst_manifests_root           = parent_env.manifestsURL(parent_trace)

        ending_env                  = self._transactions_stack.pop()
        events                      = self._transaction_events_dict.pop(ending_env.name(parent_trace))

        # If the parent environment is also a transactional envinronment, we will have to record in it
        # the events so that when the parent is committed, those events are cascaded to the parent's parent.
        # But it may also be that the parent is not transactional, which is why the `parent_events`
        # variable may be None and why we need to be checking for that all the time.
        parent_name                 = parent_env.name(parent_trace)
        if parent_name in self._transaction_events_dict.keys():
            parent_events           = self._transaction_events_dict[parent_name]
        else:
            parent_events           = None

        for relative_path in events.posting_writes():
            from_path               = src_postings_root + "/" + relative_path
            to_path                 = dst_postings_root + "/" + relative_path
            to_dir                  = _os.path.dirname(to_path)
            PathUtils().create_path_if_needed(parent_trace, to_dir)
            _shutil.copy2(src = from_path, dst = to_dir)
            if parent_events != None:
                parent_events.remember_posting_write(relative_path)

        for relative_path in events.manifest_writes():
            from_path               = src_manifests_root + "/" + relative_path
            to_path                 = dst_manifests_root + "/" + relative_path
            to_dir                  = _os.path.dirname(to_path)
            PathUtils().create_path_if_needed(parent_trace, to_dir)
            _shutil.copy2(src = from_path, dst = to_dir)
            if parent_events != None:
                parent_events.remember_manifest_write(relative_path)

        for relative_path in events.posting_deletes():
            to_path                 = dst_postings_root + "/" + relative_path
            if _os.path.isfile(to_path):
                _os.remove(to_path)
                if parent_events != None:
                    parent_events.remember_posting_delete(relative_path)

        for relative_path in events.manifest_deletes():
            to_path                 = dst_manifests_root + "/" + relative_path
            if _os.path.isfile(to_path):
                _os.remove(to_path)
                if parent_events != None:
                    parent_events.remember_manifest_deletes(relative_path)

        # Now remove the environment of the transaction we just committed
        self.removeEnvironment(parent_trace, env.name(parent_trace)) 
        self.activate(parent_trace, parent_env.name(parent_trace))

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
        _shutil.copy2(src = from_path, dst = to_dir)

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
            if self._file_not_found_error(ex) and self._failover_reads_to_parent(parent_trace):
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
            if self._file_not_found_error(ex) and self._failover_reads_to_parent(parent_trace):
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

    def searchPostings(self, parent_trace, posting_api, filing_coordinates_filter=None, posting_version_filter=None):
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
        @param posting_version_filter A function that takes a PostingVersion instance as a parameter and returns a boolean. 
                            Any PostingVersion instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.n.
        '''
        ME                          = File_KnowledgeBaseStore

        if self._failover_reads_to_parent(parent_trace):
            # Search in parent first, and copy anything found to the current environment

            my_trace                = parent_trace.doing("Searching in parent environment")
            # Temporarily switch to the environment in which to search
            original_env            = self.current_environment(my_trace)
            self.activate(my_trace, self.parent_environment(my_trace).name(my_trace))
            parent_handles          = self.searchPostings(
                                                parent_trace                = my_trace,
                                                posting_api                 = posting_api,
                                                filing_coordinates_filter   = filing_coordinates_filter,
                                                posting_version_filter      = posting_version_filter)
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
                                                        + str(self.current_environment(parent_trace)) + "'" )
        scanned_handles             = super().searchPostings(
                                                parent_trace                = my_trace, 
                                                posting_api                 = posting_api, 
                                                filing_coordinates_filter   = filing_coordinates_filter, 
                                                posting_version_filter      = posting_version_filter)
        return scanned_handles

    def persistManifest(self, parent_trace, manifest_dict):
        '''
        Persists manifest_dict as a yaml object and returns a ManifestHandle that uniquely identifies it.
        '''
        handle              = super().persistManifest(parent_trace, manifest_dict)
        return handle

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
            if self._failover_reads_to_parent(parent_trace):
                # Search in parent first, and copy anything found to the current environment

                my_trace                = parent_trace.doing("Searching in parent environment")
                # Temporarily switch to the parent environment, and try again
                original_env            = self.current_environment(my_trace)
                self.activate(my_trace, self.parent_environment(my_trace).name(my_trace))

                manifest, manifest_path = self.retrieveManifest(parent_trace, manifest_handle)
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
                    _shutil.copy2(src = from_path, dst = to_dir)


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

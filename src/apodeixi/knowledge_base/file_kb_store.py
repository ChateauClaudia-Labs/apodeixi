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

    def _copy_posting(self, parent_trace, from_handle, to_environment, overwrite=False):
        src_path                        = from_handle.getFullPath(parent_trace)

        to_handle                       = from_handle.copy(parent_trace)
        to_handle.kb_postings_url       = self.current_environment(parent_trace).postingsURL(parent_trace)
        to_path                         = to_handle.getFullPath(parent_trace)
        to_dir                          = _os.path.dirname(to_path)

        if not _os.path.exists(to_path) or overwrite == True:
            my_trace                    = parent_trace.doing("Copying a posting file",
                                            data = {"src_path":     src_path,
                                                    "to_dir":       to_dir})
            PathUtils().create_path_if_needed(parent_trace=my_trace, path=to_dir)
            _shutil.copy2(src = src_path, dst = to_dir)

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
                self._copy_posting(my_trace,    from_handle         = handle, 
                                                to_environment      = self.current_environment(my_trace),
                                                overwrite           = False)

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
                self._copy_posting(my_trace,    from_handle         = manifest_handle, 
                                                to_environment      = self.current_environment(my_trace),
                                                overwrite           = False)

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
        archival_list                       = controller_response.archivedPostings()
        if len(archival_list) != 1:
            raise ApodeixiError(parent_trace, "Can't log post event because it lacks a unique archival record",
                                                    data = {"Nb of archivals for this posting": str(len(archival_list))})
        original_handle, archival_handle    = archival_list[0]

        archival_path                       = archival_handle.getFullPath(parent_trace)
        log_folder                          = _os.path.dirname(archival_path)

        env_config                          = self.current_environment(parent_trace).config(parent_trace)
        path_mask                           = env_config.path_mask

        log_txt                             = ""
        for handle in controller_response.createdManifests():
            log_txt                         += "\nCREATED MANIFEST:        " + handle.display(parent_trace) + "\n"

        for handle in controller_response.updatedManifests():
            log_txt                         += "\nUPDATED MANIFEST:        " + handle.display(parent_trace) + "\n"

        for handle in controller_response.deletedManifests():
            log_txt                         += "\nDELETED MANIFEST:        " + handle.display(parent_trace) + "\n"

        for handle1, handle2 in controller_response.archivedPostings():
            log_txt                         += "\nARCHIVED POSTING FROM:   " + handle1.display(parent_trace, path_mask)
            log_txt                         += "\n             TO:         " + handle2.display(parent_trace, path_mask) + "\n"

        for form_request in controller_response.optionalForms():
            log_txt                         += "\nPUBLISHED OPTIONAL FORM: " + form_request.display(parent_trace) + "\n"

        for form_request in controller_response.mandatoryForms():
            log_txt                         += "\nPUBLISHED MANDATORY FORM: " + form_request.display(parent_trace) + "\n"


        LOG_FILENAME                        = "POST_EVENT_LOG.txt"
        try:
            with open(log_folder + "/" + LOG_FILENAME, 'w') as file:
                file.write(str(log_txt))

        except Exception as ex:
            raise ApodeixiError(parent_trace, "Encountered problem saving log for post event",
                                    data = {"Exception found": str(ex)})

        return log_txt

    def logFormRequestEvent(self, parent_trace, form_request, controller_response):
        '''
        Used to record in the store information about a request form event that has been completed.
        '''
        log_txt                             = super().logFormRequestEvent(parent_trace, form_request, controller_response)
        return log_txt

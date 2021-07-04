import os                                               as _os
import shutil                                           as _shutil
import yaml                                             as _yaml

from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore
from apodeixi.knowledge_base.kb_environment             import File_KB_Environment, KB_Environment_Config
from apodeixi.knowledge_base.filing_coordinates         import JourneysFilingCoordinates, \
                                                                InitiativesFilingCoordinates, \
                                                                ArchiveFilingCoordinates
from apodeixi.knowledge_base.knowledge_base_util        import ManifestHandle, ManifestUtils
from apodeixi.util.path_utils                           import PathUtils
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

class File_KnowledgeBaseStore(KnowledgeBaseStore):
    '''
    File-system-based implementation of the KnowledgeBaseStore. The entire knowledge base is held under a two root folders
    (one for postings and one for all derived data, including manifests)
    and follows a structure based on filing schemes of the KB_ProcessingRules.
    '''
    def __init__(self, postings_rootdir, manifests_roodir):
        super().__init__()

        _BASE_ENVIRONMENT           = '_BASE_ENVIRONMENT'
        root_trace                  = FunctionalTrace(None).doing("Creating KB's store's base environment")
        env_config                  = KB_Environment_Config(
                                            root_trace, 
                                            read_misses_policy  = KB_Environment_Config.FAILOVER_READS_TO_PARENT,
                                            use_timestamps      = True)
        self._base_env              = File_KB_Environment(parent_trace            = root_trace, 
                                                                    name                    = _BASE_ENVIRONMENT, 
                                                                    store                   = self, 
                                                                    parent_environment      = None,
                                                                    config                  = env_config,
                                                                    postings_rootdir        = postings_rootdir,
                                                                    manifests_roodir        = manifests_roodir)  
          
        self._current_env           = self._base_env

        self.filing_rules           = { #List of associations of posting API => FilingCoordinate class to use for such posting API
            'big-rocks.journeys.a6i':                               JourneysFilingCoordinates,
            'milestone.journeys.a6i':                               JourneysFilingCoordinates,
            'capability-hierarchy.bdd.kernel.a6i':                  None, # TODO
            'workstream.initiatives.a6i':                           InitiativesFilingCoordinates,
            'charter.initiatives.a6i':                              InitiativesFilingCoordinates, 
            
        }

    def _failover_reads_to_parent(self, parent_trace):
        '''
        Returns a boolean to determine if parent environment should be used to retrieve data that is not
        present in the current environment.

        It is used by the I/O read services of the store whenever a read operation results in a "miss": if the
        current environment lacks the data in question, the I/O read service will search in the parent 
        environment and, if it finds it, will copy it to the current environment. 
        '''
        if self._current_env._parent_environment == None: # Can't failover to a non-existent parent
            return False
        if self._current_env._config.read_misses_policy == KB_Environment_Config.FAILOVER_READS_TO_PARENT:
            return True
        else:
            return False

    def supported_apis(self, parent_trace):
        '''
        Returns a list of the posting APIs that this KnowledgeStore knows about.
        '''
        return list(self.filing_rules.keys())

    def getFilingClass(self, parent_trace, posting_api):
        '''
        Returns a class object, derived from FilingCoordinates, that this store uses to structure postings for 
        the giving posting api
        '''
        if not posting_api in self.supported_apis(parent_trace):
            raise ApodeixiError(parent_trace, "Posting API '" + str(posting_api) + "' is not supported.")
        klass                           = self.filing_rules[posting_api]
        return klass

    def getPostingsURL(self, parent_trace):
        '''
        Returns a string that can be used to locate the postings area in the Knowledge Base store's current environment
        '''   
        current_kb_env_url              = self._current_env.postingsURL(parent_trace)
        return current_kb_env_url

    def current_environment(self, parent_trace):
        return self._current_env

    def parent_environment(self, parent_trace):
        return self._current_env._parent_environment

    def base_environment(self, parent_trace):
        return self._base_env

    def removeEnvironment(self, parent_trace, name):
        '''
        Removes the environment with the given name, if one exists, in which case returns 0.
        If no such environment exists then it returns -1.
        '''
        ME                          = File_KB_Environment

        root_dir                    = _os.path.dirname(self.base_environment(parent_trace).manifestsURL(parent_trace))
        envs_dir                    = root_dir + "/" + ME.ENVS_FOLDER
        PathUtils().create_path_if_needed(parent_trace, envs_dir)

        self._validate_environment_name(parent_trace    = parent_trace, name = name)

        sub_env_name                = name.strip()
        dir_to_remove               = envs_dir + "/" + sub_env_name
        try:
            if _os.path.isdir(dir_to_remove):
                _shutil.rmtree(dir_to_remove)
            else:
                return -1
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Encountered a problem deleting environment",
                                data = {"environment name": name, "exception": ex})
        
    def _validate_environment_name(self, parent_trace, name):
        my_trace                    = parent_trace.doing("Checking environment's name is a str")
        if not type(name) == str:
            raise ApodeixiError(my_trace, "Can't create an environment with a name that is not a string",
                                        data = {'name': str(name), 'type(name)': str(type(name))})

        my_trace                    = parent_trace.doing("Checking environment's name not blank")
        env_name                = name.strip()
        if len(env_name) == 0:
            raise ApodeixiError(my_trace, "Can't create a sub environment with a name that is blank",
                                        data = {'sub_env_name': str(env_name)})


    def activate(self, parent_trace, environment_name):
        '''
        Switches the store's current environment to be the one identified by the `environment_name`, unless
        no such environment exists in which case it raises an ApodeixiError
        '''
        if environment_name == self._base_env.name(parent_trace):
            next_env                    = self._base_env
        else:
            next_env                    = self._current_env.findSubEnvironment(parent_trace, environment_name)
        
        if next_env != None:
            self._current_env           = next_env
        else:
            raise ApodeixiError(parent_trace, "Can't activiate an environment that does not exist",
                                                    data = {"environment_name": str(environment_name)})

    def deactivate(self, parent_trace):
        '''
        Switches the store's current environment to be the base environment.
        '''
        self._current_env               = self._base_env

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
                                                my_trace,
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

        # TODO - Implement logic to filter by posting version. Until such time, abort if user needs such filtering
        if posting_version_filter != None:
            raise ApodeixiError(parent_trace, "Apologies, but filtering postings by version is not yet implemented in "
                                                + "File_KnowledgeBaseStore. Aborting the effort to searchPostings.")


        my_trace                    = parent_trace.doing("Scanning existing filing coordinates",
                                                data = {"environment":  
                                                        self.current_environment(parent_trace).name(parent_trace)})
        if True:
            scanned_handles         = []
            for currentdir, dirs, files in _os.walk(self.current_environment(my_trace).postingsURL(my_trace)):
                #for subdir in dirs:
                for a_file in files:
                    if a_file.startswith("~"):
                        continue # Skip such files, they are temporary Excel locks
                    loop_trace          = my_trace.doing("Scanning directory", data = {'currentdir': currentdir, 'file': a_file})
                    try:
                        handle      = self.buildPostingHandle(  parent_trace        = loop_trace,
                                                                excel_posting_path  = _os.path.join(currentdir, a_file))
                    except ApodeixiError as ex:
                        continue # This just means that this directory had nothing matching the posting API
                    if handle.posting_api != posting_api:
                        continue # Don't count this handle, since it for the wrong posting_api
                    if filing_coordinates_filter == None or filing_coordinates_filter(handle.filing_coords): # Passed the filter, if any
                        scanned_handles.append(handle)

        return scanned_handles

    def persistManifest(self, parent_trace, manifest_dict):
        '''
        Persists manifest_dict as a yaml object and returns a ManifestHandle that uniquely identifies it.
        '''
        ME                  = File_KnowledgeBaseStore
        kind                = manifest_dict['kind']
        name                = manifest_dict['metadata']['name']
        namespace           = manifest_dict['metadata']['namespace']
        suffix              = ''

        version             = ManifestUtils().get_manifest_version(parent_trace, manifest_dict)
        if version != None and len(str(version).strip()) > 0:
            suffix = '.' + str(version)
        manifest_dir        = self._current_env.manifestsURL(parent_trace) + "/" + namespace  + "/" + name
        PathUtils().create_path_if_needed(parent_trace=parent_trace, path=manifest_dir)
        manifest_file       = kind + suffix + ".yaml"
        my_trace            = parent_trace.doing("Persisting manifest", 
                                                    data = {    'manifests_dir': manifest_dir, 
                                                                'manifest_file': manifest_file},
                                                    origination = {
                                                                'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})
        if True:
            with open(manifest_dir + "/" + manifest_file, 'w') as file:
                _yaml.dump(manifest_dict, file)
            
            handle          = ManifestHandle.inferHandle(my_trace, manifest_dict)
            return handle

    def retrieveManifest(self, parent_trace, manifest_handle):
        '''
        Returns a dict and a string.
        
        The dict represents the unique manifest in the store that is identified by the `manifest handle`.
        
        The string represents the full pathname for the manifest.

        If none exists, it returns None. That said, before giving up and returning None, based on the environment
        configuration this method will attempt to find the manifest in the parent environment.

        @param manifest_handle A ManifestHandle instance that uniquely identifies the manifest we seek to retrieve.
        '''
        matching_manifests      = [] # List of dictionaries, one per manifest
        matching_filenames      = [] # List of filename strings. Will be 1-1 lined up with matching_manifests

        folder                  = self._current_env.manifestsURL(parent_trace) + '/' \
                                        + manifest_handle.namespace + '/' + manifest_handle.name

        manifests, filenames    = self._getMatchingManifests(   parent_trace    = parent_trace, 
                                                                folder          = folder, 
                                                                manifest_handle = manifest_handle)
        matching_manifests.extend(manifests)
        matching_filenames.extend(filenames)
        
        if len(matching_filenames) > 1:
            raise ApodeixiError(parent_trace, "Found multiple manifests for given handle",
                                                data = {'manifest_handle': str(manifest_handle),
                                                        'matching files':   str(matching_filenames)},
                                                origination = {
                                                        'concrete class': str(self.__class__.__name__), 
                                                        'signaled_from': __file__})
        if len(matching_filenames) == 0:
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
                self._copy_posting(my_trace,    from_handle         = handle, 
                                                to_environment      = self.current_environment(my_trace),
                                                overwrite           = False)
            else:
                return None
        # By now we know there is exaclty one match - that must be the manifest we are after

        manifest_path                   = folder + "/" + matching_filenames[0]
        return matching_manifests[0], manifest_path


    def _getMatchingManifests(self, parent_trace, folder, manifest_handle):
        '''
        Returns two lists of the same length:

        * A list of dictionaries, one per manifest that matches the given manifest handle
        * A list of filenames, which is where each of those manifests was retrieved from

        The search is done over the space of objects in the store that lie "at or below the folder", where
        the notion of "folder" depends on the concrete store class. For filesystem-based stores, "folder" would
        literally be a directory of some filesystem mount.

        @param folder A string scoping a subset of the store
        @param manifest_handle A ManifestHandle instance that (should) uniquely identify a single manifest in the store
        '''
        matching_manifests = [] # List of dictionaries, one per manifest
        matching_filenames = [] # List of filename strings. Will be 1-1 lined up with matching_manifests

        # Two areas where to search for manifests: input area, and output area. First the input area
        for filename in self._getFilenames(parent_trace, folder):
            my_trace            = parent_trace.doing("Loading manifest from file",
                                                        data = {'filename':         filename,
                                                                'folder':           folder},
                                                        origination = {
                                                                'concrete class':   str(self.__class__.__name__), 
                                                                'signaled_from':    __file__})
            with open(folder + '/' + filename, 'r') as file:
                manifest_dict   = _yaml.load(file, Loader=_yaml.FullLoader)
            #manifest_dict       = _yaml.load(filename, Loader=_yaml.FullLoader)
            inferred_handle     = ManifestHandle.inferHandle(my_trace, manifest_dict)
            if inferred_handle == manifest_handle:
                matching_filenames.append(filename)
                matching_manifests.append(manifest_dict)

        return matching_manifests, matching_filenames

    def _getFilenames(self, parent_trace, folder):
        '''
        Helper method that looks at all files in the given folder that end in the given suffix and returns their filenames

        The suffix might be ".yaml" to retrieve manifests, or even "_<version>.yaml" for versioned manifests
        '''
        matches = [filename for filename in _os.listdir(folder) if filename.endswith(".yaml")]

        return matches

    def archivePosting(self, parent_trace, posting_label_handle):
        '''
        Used after a posting Excel file has been processed. It moves the Excel file to a newly created folder dedicated 
        to this posting event and returns a FilingCoordinates object to identify that folder.       
        '''
        submitted_posting_path              = posting_label_handle.getFullPath(parent_trace)
        submitted_posting_coords            = posting_label_handle.filing_coords
        filename                            = posting_label_handle.excel_filename

        env_config                          = self.current_environment(parent_trace).config(parent_trace)
        archival_folder_coords              = ArchiveFilingCoordinates(
                                                            parent_trace            = parent_trace, 
                                                            posting_label_handle    = posting_label_handle,
                                                            use_timestamps          = env_config.use_timestamps)

        archival_folder_path_tokens         = archival_folder_coords.path_tokens(parent_trace)
        archival_folder_path                = posting_label_handle.kb_postings_url +  '/' + '/'.join(archival_folder_path_tokens)

        PathUtils().create_path_if_needed(parent_trace, archival_folder_path)

        if PathUtils().is_parent(           parent_trace                = parent_trace,
                                            parent_dir                  = self.getPostingsURL(parent_trace), 
                                            path                        = submitted_posting_path):
            # In this case the posting was submitted in the current environment, so move it
            _os.rename(src = submitted_posting_path, dst = archival_folder_path + "/" + filename)
        else:
            # In this case the posting was submitted from outside the current environment, so archive it but don't move it
            _shutil.copy2(src = submitted_posting_path, dst = archival_folder_path)
        
        return archival_folder_coords



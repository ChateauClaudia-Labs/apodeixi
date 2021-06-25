import os                                               as _os
import yaml                                             as _yaml

from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore
from apodeixi.knowledge_base.filing_coordinates         import JourneysFilingCoordinates, InitiativesFilingCoordinates
from apodeixi.knowledge_base.knowledge_base_util        import ManifestHandle, ManifestUtils
from apodeixi.util.path_utils                           import PathUtils
from apodeixi.util.a6i_error                            import ApodeixiError

class File_KnowledgeBaseStore(KnowledgeBaseStore):
    '''
    File-system-based implementation of the KnowledgeBaseStore. The entire knowledge base is held under a two root folders
    (one for postings and one for all derived data, including manifests)
    and follows a structure based on filing schemes of the KB_ProcessingRules.
    '''
    def __init__(self, postings_rootdir, derived_data_rootdir):
        super().__init__()

        self.postings_rootdir       = postings_rootdir
        self.derived_data_rootdir   = derived_data_rootdir

        self.filing_rules           = { #List of associations of posting API => FilingCoordinate class to use for such posting API
            'big-rocks.journeys.a6i':                               JourneysFilingCoordinates,
            #'modernization-milestone.delivery-planning.journeys.a6i':       JourneysFilingCoordinates,
            'capability-hierarchy.bdd.kernel.a6i':                          None, # TODO
            'milestone.journeys.a6i':                                       JourneysFilingCoordinates,
            'workstream.initiatives.a6i':                                   InitiativesFilingCoordinates,
            'charter.initiatives.a6i':                                      InitiativesFilingCoordinates, 
            
        }

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

    def getStoreURL(self, parent_trace):
        '''
        Returns a string that can be used to locate this Knowledge Base store
        '''
        kb_store_url                    = self.postings_rootdir    
        return kb_store_url


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
        # TODO - Implement logic to filter by posting version. Until such time, abort if user needs such filtering
        if posting_version_filter != None:
            raise ApodeixiError(parent_trace, "Apologies, but filtering postings by version is not yet implemented in "
                                                + "File_KnowledgeBaseStore. Aborting the effort to searchPostings.")

        my_trace                    = parent_trace.doing("Scanning existing filing coordinates")
        if True:
            scanned_handles         = []
            for currentdir, dirs, files in _os.walk(self.postings_rootdir):
                #for subdir in dirs:
                for a_file in files:
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
        manifest_dir        = self.derived_data_rootdir + "/" + namespace  + "/" + name
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
        Returns a dict representing the unique manifest in the store that is identified by the `manifest handle`.
        If none exists, it returns None.

        @param manifest_handle A ManifestHandle instance that uniquely identifies the manifest we seek to retrieve.
        '''
        matching_manifests      = [] # List of dictionaries, one per manifest
        matching_filenames      = [] # List of filename strings. Will be 1-1 lined up with matching_manifests

        folder                  = self.derived_data_rootdir + '/' + manifest_handle.namespace + '/' + manifest_handle.name

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
            return None
        # By now we know there is exaclty one match - that must be the manifest we are after
        return matching_manifests[0]

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




import os                                               as _os
import yaml                                             as _yaml
from pathlib                                            import Path

from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore
from apodeixi.knowledge_base.filing_coordinates         import JourneysFilingCoordinates, InitiativesFilingCoordinates
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
            'delivery-planning.journeys.a6i':       JourneysFilingCoordinates,
            'milestone.journeys.a6i':               JourneysFilingCoordinates,
            'milestones.initiative.a6i':            InitiativesFilingCoordinates,
            'charter.initiative.a6i':               InitiativesFilingCoordinates

        }

    def discoverPostingURL(self, parent_trace, excel_posting_path, sheet="Sheet1"):
        ME                          = File_KnowledgeBaseStore
        
        if not _os.path.isfile(excel_posting_path):
            raise ApodeixiError(parent_trace, "File does not exist",
                                                data = {    'excel_posting_path': excel_posting_path})

        # Check if file exists to begin with
        excel_posting_path_tokens       = _os.path.split(excel_posting_path)
        posting_filename                = excel_posting_path_tokens[1]
        posting_dir                     = excel_posting_path_tokens[0]
        
        # Check that posting is for a supported posting API
        my_trace                        = parent_trace.doing("Inferring api from posting's filename")
        posting_api                     = self.infer_posting_api(my_trace, posting_filename)

        # Check if the posting is in the Knowledge Base to start with. 
        my_trace                        = parent_trace.doing("Checking that posting belongs to Knowledge Base")
        if not posting_dir.startswith(self.postings_rootdir):
            raise ApodeixiError(my_trace, "Can't post a file not in the Knowledge Base's folder structure",
                                                data =  {   'excel_posting_path':           excel_posting_path,
                                                            'knowledge base root directory':    self.postings_rootdir})
        posting_relative_path           = excel_posting_path.split(self.postings_rootdir)[1]

        path_tokens                     = ME._tokenizePath( parent_trace    = parent_trace,
                                                            relative_path   = posting_relative_path)[:-1] # Discard last token, which is filename
        # Check thath the relative path of the posting within the Knowledge Base corresponds to the filing structure
        # for that API
        filing_coords                   = self.filing_rules[posting_api]()
        my_trace                        = parent_trace.doing("Validating that posting is in the right folder structure "
                                                                + "within the Knowledge Base")
        built_filing_coords             = filing_coords.build(parent_trace = my_trace, path_tokens = path_tokens)
        if built_filing_coords == None:
            raise ApodeixiError(my_trace, "Posting is not in the right folder within the Knowledge Base for this kind of API",
                                            data = {'posting relative path tokens':         path_tokens,
                                                    'posting api':                          posting_api,
                                                    'relative path expected by api':        filing_coords.expected_tokens(my_trace)})

        my_trace                        = parent_trace.doing("Done validating; constructing URL")
        parsed_tokens                   = built_filing_coords.path_tokens(my_trace)

        url         = self.postings_rootdir  +  '/' + '/'.join(parsed_tokens) + '/' + posting_filename + ':' + sheet
        return url

    def persistManifest(self, parent_trace, manifest_dict, version = None):
        '''
        Persists manifest_dict as a yaml object
        '''
        ME                  = File_KnowledgeBaseStore
        kind                = manifest_dict['kind']
        name                = manifest_dict['metadata']['name']
        namespace           = manifest_dict['metadata']['namespace']
        suffix              = ''
        if version != None:
            suffix = '_' + version
        manifest_dir        = self.derived_data_rootdir + "/" + namespace  + "/" + name
        ME._create_path_if_needed(parent_trace=parent_trace, path=manifest_dir)
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

    def retrieveManifest(self, parent_trace, manifest_handle, version = None):
        '''
        Retrieve all yaml manifests, and then filter the ones that are matching the handle
        '''
        matching_manifests      = [] # List of dictionaries, one per manifest
        matching_filenames      = [] # List of filename strings. Will be 1-1 lined up with matching_manifests

        folder                  = self.derived_data_rootdir + '/' + manifest_handle.namespace + '/' + manifest_handle.name

        suffix                  = manifest_handle.kind
        if version != None:
            suffix              += '_' + version
        suffix                  += '.yaml'
        manifests, filenames    = self._getMatchingManifests(   parent_trace    = parent_trace, 
                                                                folder          = folder, 
                                                                manifest_handle = manifest_handle, 
                                                                suffix          = suffix)
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

    def supported_apis(self, parent_trace, manifest_handle=None, version = None):
        '''
        Abstract method. Returns a list of the posting APIs that this KnowledgeStore knows about.
        '''
        return list(self.filing_rules.keys())

    def locatePostings(self, parent_trace, posting_api, filing_coordinates_filter=None, posting_version_filter=None):
        '''
        @param posting_api A string that identifies the type of posting represented by an Excel file. For example,
                            'milestone.modernization.a6i' is a recognized posting API and files that end with that suffix,
                            such as 'opus_milestione.modernization.a6i.xlsx' will be located by this method.
        @param filing_coordinates_filter A function that takes a FilingCoordinates instance as a parameter and returns a boolean. 
                            Any FilingCoordinates instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        @param posting_version An instance of a posting version.
        '''
        ME                          = File_KnowledgeBaseStore
        # TODO - Implement logic to filter by posting version. Until such time, abort if user needs such filtering
        if posting_version_filter != None:
            raise ApodeixiError(parent_trace, "Apologies, but filtering postings by version is not yet implemented in "
                                                + "File_KnowledgeBaseStore. Aborting the effort to locatePostings.")

        my_trace                    = parent_trace.doing("Scanning existing filing coordinates")
        if True:
            scanned_coords              = []
            supported_apis              = list(self.filing_rules.keys())
            if not posting_api in supported_apis:
                raise ApodeixiError(my_trace, "Knowledge Base does not accept this kind of posting API",
                                                data = {    "posting_api":      str(posting_api),
                                                            "supported apis":   str(supported_apis)})
            filing_class                = self.filing_rules[posting_api]
            for currentdir, dirs, files in _os.walk(self.postings_rootdir):
                for subdir in dirs:
                    loop_trace          = my_trace.doing("Tokenzing  path", data = {'currentdir': currentdir, 'subdir': subdir})
                    path_tokens         = ME._tokenizePath( parent_trace    = loop_trace,
                                                            relative_path   = _os.path.join(currentdir, subdir).split(self.postings_rootdir)[1]) 
                    filing_coords       = filing_class().build(parent_trace = loop_trace, path_tokens = path_tokens)
                    if filing_coords    != None:
                        if filing_coordinates_filter == None or filing_coordinates_filter(filing_coords): # Passed the filter, if any
                            scanned_coords.append(filing_coords)

        my_trace                    = parent_trace.doing("Collecting matching files for scanned coordinates")
        if True:
            result                  = {}
            for coords in scanned_coords:
                files               = self._findMatchingFiles(my_trace, coords, posting_api)
                result[coords]      = files

        return result

    def _findMatchingFiles(self, parent_trace, filing_coordinates, posting_api):
        path_tokens                 = filing_coordinates.path_tokens(parent_trace)
        full_path                   = self.postings_rootdir + "/" + "/".join(path_tokens)

        result                      = []
        for file in _os.listdir(full_path): # This picks up both directories and files
            d = _os.path.join(full_path, file)
            if not _os.path.isdir(d) and file.endswith(posting_api + ".xlsx"):
                result.append(file)
        return result
 
    def _tokenizePath(parent_trace, relative_path):
        '''
        Helper method suggested in  https://stackoverflow.com/questions/3167154/how-to-split-a-dos-path-into-its-components-in-python.
        It tokenizes relative paths to make it easier to construct FilingCoordinates from them
        For example, given a relative path like

                \FY 22\LIQ\MTP

        it returns a list

                ['FY 22', 'LIQ', 'MTP']
        '''
        folders             = []
        SPURIOUS_FOLDERS    = ["\\", "/"] # This might be added in Windows by some _os / split manipulations. If so, ignore it
        LIMIT               = 1000 # Maximum path length to handle. As a precaution to avoid infinte loops
        idx                 = 0
        path                = relative_path
        while idx < LIMIT: # This could have been "while True", but placed a limit out of caution
            path, folder = _os.path.split(path)

            if folder   != "": 
                folders.append(folder)
            elif path   != "":
                folders.append(path)
                break
            idx             += 1

        folders.reverse()
        if folders[0] in SPURIOUS_FOLDERS:
            folders         = folders[1:]
        return folders

    def _create_path_if_needed(parent_trace, path):
        '''
        Helper method to create a directory if it does not alreay exist
        '''
        Path(path).mkdir(parents=True, exist_ok=True)

class PostingVersion():
    '''
    Helper class to represent different versions of the same posting
    '''
    def __init__(self, version_nb = 0):
        self.version_nb         = version_nb
        return
    
    def nextVersion(self, posting_version):
        return PostingVersion(posting_version.version_nb + 1)


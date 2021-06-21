import os                                           as _os
import yaml                                         as _yaml

from apodeixi.util.a6i_error                        import ApodeixiError

from apodeixi.knowledge_base.knowledge_base_store   import KnowledgeBaseStore
from apodeixi.knowledge_base.knowledge_base_util    import ManifestHandle, ManifestUtils, PostingLabelHandle

class UnitTest_KnowledgeBaseStore(KnowledgeBaseStore):
    '''
    Very simple store used for unit testing purposes. It assumes no segregation of postings or manifests based on functional
    fields such as scenarios, scoring cycles, products, etc.
    Instead, there are four (not necessarily distinct) folders for reading / writing  of postings / manifests.
    '''
    def __init__(self, test_case_name, 
                        input_manifests_dir, input_postings_dir, output_manifests_dir, output_postings_dir):
        super().__init__()

        self.test_case_name                 = test_case_name
        self.input_manifests_dir            = input_manifests_dir
        self.input_postings_dir             = input_postings_dir
        self.output_manifests_dir           = output_manifests_dir
        self.output_postings_dir            = output_postings_dir

    def supported_apis(self, parent_trace, manifest_handle=None, version = None):
        '''
        Returns a list of the posting APIs that this KnowledgeStore knows about.
        '''
        supported_apis                      = [ 'delivery-planning.journeys.a6i', '_INPUT', # Need spurious api "_INPUT" for unit tests
                                                ]
        return supported_apis

    def buildPostingHandle(self, parent_trace, excel_posting_path, sheet="Posting Label", excel_range="B2:C100"):
        '''
        Returns an Apodeixi Excel URL for the posting label embedded within the Excel spreadsheet that resides in the path provided.
        '''
        posting_handle      = PostingLabelHandle(   parent_trace        = parent_trace, 
                                                    excel_filename      = excel_posting_path, 
                                                    excel_sheet         = sheet, 
                                                    excel_range         = excel_range)

        filename                        = _os.path.split(excel_posting_path)[1]
        url                             = self.input_postings_dir  +  '/' + filename + ':' + sheet
        posting_handle.url              = url
        posting_handle.excel_path       = self.input_postings_dir

        my_trace                        = parent_trace.doing("Inferring api from posting's filename")
        posting_handle.posting_api      = None
        supported_apis                  = self.supported_apis(parent_trace=parent_trace)
        for api in supported_apis:
            if filename.endswith(api + ".xlsx"):
                posting_handle.posting_api             = api
                break
        if posting_handle.posting_api == None:
            raise ApodeixiError(parent_trace, "Filename is not for a supported API",
                                            data = {    'filename':             filename,
                                                        'supported apis':       str(supported_apis)})


        
        return posting_handle



    def persistManifest(self, parent_trace, manifest_dict):
        '''
        Persists manifest_dict as a yaml object and returns a ManifestHandle that uniquely identifies it.
        '''
        kind                = manifest_dict['kind']
        suffix              = ''

        version             = ManifestUtils().get_manifest_version(parent_trace, manifest_dict)
        if version != None and len(str(version).strip()) > 0:
            suffix = '.' + str(version)
        manifest_file       = self.test_case_name + "." + kind + suffix + ".yaml"
        my_trace            = parent_trace.doing("Persisting manifest", 
                                                    data = {    'manifests_dir': self.output_manifests_dir, 
                                                                'manifest_file': manifest_file},
                                                    origination = {
                                                                'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})
        if True:
            with open(self.output_manifests_dir + '/' + manifest_file, 'w') as file:
                _yaml.dump(manifest_dict, file)
            handle          = ManifestHandle.inferHandle(my_trace, manifest_dict)
            return handle

    def retrieveManifest(self, parent_trace, manifest_handle):
        '''
        Returns a dict representing the unique manifest in the store that is identified by the `manifest handle`.
        If none exists, it returns None.

        @param manifest_handle A ManifestHandle instance that uniquely identifies the manifest we seek to retrieve.
        '''
        matching_manifests = [] # List of dictionaries, one per manifest
        matching_filenames = [] # List of filename strings. Will be 1-1 lined up with matching_manifests


        input_manifests, input_filenames    = self._getMatchingManifests(   parent_trace    = parent_trace, 
                                                                            folder          = self.input_manifests_dir, 
                                                                            manifest_handle = manifest_handle)
        output_manifests, output_filenames  = self._getMatchingManifests(   parent_trace    = parent_trace, 
                                                                            folder          = self.output_manifests_dir, 
                                                                            manifest_handle = manifest_handle)
        matching_manifests.extend(input_manifests)
        matching_manifests.extend(output_manifests)
        matching_filenames.extend(input_filenames)
        matching_filenames.extend(output_filenames)
        
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
        @param suffix A string representing a valid "file extension" type used for manifests, where the logical
                        notion of "file extension" is up to each concrete store class to define. For filesystem-based
                        stores, the suffix string is literally a file extension in the filesystem, such as ".yaml"
                        for stores that persist manifests as yaml files.
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
        Helper method that looks at all files in the given folder that end in the given suffix and returns their filenames if
        they comply with the store's file naming conventions for manifests
        '''
        # Exclude files named "*EXPECTED.yaml" because logically they are not part of the store.
        # Ditto for files named "*OUTPUT.yaml". 
        # The store only has files named "*.<version nb>.yaml". Other files may sit in the same folder because the
        # test harness produces them, but they are not logically part of the store
        matches = [filename for filename in _os.listdir(folder) if filename.endswith(".yaml")]
        matches = [filename for filename in matches if not filename.endswith("EXPECTED.yaml")]
        matches = [filename for filename in matches if not filename.endswith("OUTPUT.yaml")]
        return matches
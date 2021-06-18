import os                                           as _os
import yaml                                         as _yaml

from apodeixi.util.a6i_error                        import ApodeixiError

from apodeixi.knowledge_base.knowledge_base_store   import KnowledgeBaseStore
from apodeixi.knowledge_base.knowledge_base_util    import ManifestHandle

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
        Abstract method. Returns a list of the posting APIs that this KnowledgeStore knows about.
        '''
        supported_apis                      = [ 'delivery-planning.journeys.a6i',
                                                ]
        return supported_apis

    def discoverPostingURL(self, parent_trace, excel_posting_path, sheet="Posting Label"):
        '''
        Returns an Apodeixi Excel URL for the posting label embedded within the Excel spreadsheet that resides in the path provided.
        '''
        filename    = _os.path.split(excel_posting_path)[1]
        url         = self.input_postings_dir  +  '/' + filename + ':' + sheet
        return url


    def persistManifest(self, parent_trace, manifest_dict, version = None):
        '''
        Persists manifest_dict as a yaml object
        '''
        kind                = manifest_dict['kind']
        suffix              = ''
        if version != None:
            suffix = '_' + version
        manifest_file       = self.test_case_name + "_" + kind + suffix + ".yaml"
        my_trace            = parent_trace.doing("Persisting manifest", 
                                                    data = {    'manifests_dir': self.output_manifests_dir, 
                                                                'manifest_file': manifest_file},
                                                    origination = {
                                                                'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})
        if True:
            with open(self.output_manifests_dir + '/' + manifest_file, 'w') as file:
                _yaml.dump(manifest_dict, file)

    def retrieveManifest(self, parent_trace, manifest_handle, version = None):
        '''
        Retrieve all yaml manifests, and then filter the ones that are matching the handle
        '''
        matching_manifests = [] # List of dictionaries, one per manifest
        matching_filenames = [] # List of filename strings. Will be 1-1 lined up with matching_manifests

        suffix                  = ''
        if version != None:
            suffix              += '_' + version
        suffix                  += '.yaml'

        input_manifests, input_filenames    = self._getMatchingManifests(   parent_trace    = parent_trace, 
                                                                            folder          = self.input_manifests_dir, 
                                                                            manifest_handle = manifest_handle, 
                                                                            suffix          = suffix)
        output_manifests, output_filenames  = self._getMatchingManifests(   parent_trace    = parent_trace, 
                                                                            folder          = self.output_manifests_dir, 
                                                                            manifest_handle = manifest_handle, 
                                                                            suffix          = suffix)
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
import os                                           as _os
import yaml                                         as _yaml

from apodeixi.util.a6i_error                        import ApodeixiError

from apodeixi.knowledge_base.knowledge_base_store   import KnowledgeBaseStore

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

    def discoverPostingURL(self, parent_trace, excel_posting_path, sheet="Sheet1"):
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
                                                                'manifest_file': manifest_file})
        if True:
            with open(self.output_manifests_dir + '/' + manifest_file, 'w') as file:
                _yaml.dump(manifest_dict, file)
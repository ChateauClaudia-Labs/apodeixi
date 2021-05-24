import sys                                              as _sys

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.testing_framework.mock_kb_store           import UnitTest_KnowledgeBaseStore
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase, KB_ProcessingRules
from apodeixi.knowledge_base.knowledge_base_store       import File_KnowledgeBaseStore

class Test_KnowledgeBase(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    '''
    TODO
    def test_posting_with_file_store(self):
        POSTING_TYPE            = KB_ProcessingRules.POSTING_BIG_ROCKS
        return
    '''

    def test_posting_with_mock_store(self):

        MANIFEST_FILE_PREFIX    = 'posting_with_mock_store'
        POSTING_TYPE            = KB_ProcessingRules.POSTING_BIG_ROCKS

        STORE                   = UnitTest_KnowledgeBaseStore(  test_case_name          = MANIFEST_FILE_PREFIX,
                                                                input_manifests_dir     = self.input_data, 
                                                                input_postings_dir      = self.input_data, 
                                                                output_manifests_dir    = self.output_data, 
                                                                output_postings_dir     = self.output_data)
        
        self._posting_testing_skeleton( store           = STORE, 
                                        posting_type    = POSTING_TYPE, 
                                        test_case_name  = MANIFEST_FILE_PREFIX)

    def _posting_testing_skeleton(self, store, posting_type, test_case_name):

        EXCEL_FILE              = test_case_name + '_INPUT.xlsx' 

        all_manifests_dicts     = []

        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Posting excel file", 
                                                                                data={  'excel_file'    : EXCEL_FILE,
                                                                                        'signaled_from' : __file__,
                                                                                        'concrete class': str(self.__class__.__name__)})

            kbase               = KnowledgeBase(store)

            response            = kbase.post(   parent_trace                = root_trace, 
                                                path_of_file_being_posted   = EXCEL_FILE, 
                                                posting_type                = posting_type,
                                                version                     = "OUTPUT")

            NB_MANIFESTS_EXPECTED   = 3
            if len(response.createdHandles()) != NB_MANIFESTS_EXPECTED:
                raise ApodeixiError(root_trace, 'Expected ' + str(NB_MANIFESTS_EXPECTED) + ' manifests, but found ' 
                                    + str(len(all_manifests_dicts)))

            # Retrieve the manifests created
            manifest_dict           = {}
            for handle in response.createdHandles():
                loop_trace          = root_trace.doing("Retrieving manifest for handle " + str(handle),
                                                        data = {    'concrete class': str(self.__class__.__name__), 
                                                                    'signaled_from': __file__})
                manifest_dict       = store.retrieveManifest(loop_trace, handle, version = "OUTPUT")
                self._compare_to_expected_yaml(manifest_dict, test_case_name + "_" + handle.kind)

        except ApodeixiError as ex:
            print(ex.trace_message())                                                                                        

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_KnowledgeBase()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='posting_with_mock_store':
            T.test_posting_with_mock_store()
        if what_to_do=='posting_with_file_store':
            T.test_posting_with_file_store()

    main(_sys.argv)
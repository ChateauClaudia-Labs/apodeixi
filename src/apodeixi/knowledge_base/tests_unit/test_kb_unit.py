import sys                                              as _sys

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.testing_framework.mock_kb_store           import UnitTest_KnowledgeBaseStore
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase

from apodeixi.util.apodeixi_config              import ApodeixiConfig

class Test_KnowledgeBase_Unit(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_posting_with_mock_store(self):

        MANIFEST_FILE_PREFIX    = 'posting_with_mock_store'

        STORE                   = UnitTest_KnowledgeBaseStore(  test_case_name          = MANIFEST_FILE_PREFIX,
                                                                input_manifests_dir     = self.input_data, 
                                                                input_postings_dir      = self.input_data, 
                                                                output_manifests_dir    = self.output_data, 
                                                                output_postings_dir     = self.output_data)

        EXCEL_FILE                      = MANIFEST_FILE_PREFIX + '_big-rocks.journeys.a6i.xlsx' 
        
        self._posting_testing_skeleton( store           = STORE, 
                                        test_case_name  = MANIFEST_FILE_PREFIX,
                                        excel_file      = EXCEL_FILE)


    def _posting_testing_skeleton(self, store, test_case_name, excel_file):

        all_manifests_dicts                     = []

        try:
            root_trace                          = FunctionalTrace(parent_trace=None).doing("Posting excel file", 
                                                                                data={  'excel_file'    : excel_file},
                                                                                origination = {
                                                                                        'signaled_from' : __file__,
                                                                                        'concrete class': str(self.__class__.__name__)})

            kbase                               = KnowledgeBase(root_trace, store)

            response, log_txt                   = kbase.postByFile( parent_trace                = root_trace, 
                                                                    path_of_file_being_posted   = excel_file,
                                                                    excel_sheet                 = "Sheet1")

            NB_MANIFESTS_EXPECTED               = 3
            if len(response.createdManifests()) != NB_MANIFESTS_EXPECTED:
                raise ApodeixiError(root_trace, 'Expected ' + str(NB_MANIFESTS_EXPECTED) + ' manifests, but found ' 
                                    + str(len(all_manifests_dicts)))

            # Retrieve the manifests created
            manifest_dict                       = {}
            for handle in response.createdManifests():
                loop_trace                      = root_trace.doing("Retrieving manifest for handle " + str(handle),
                                                        origination = {    
                                                                    'concrete class': str(self.__class__.__name__), 
                                                                    'signaled_from': __file__})
                manifest_dict, manifest_path    = store.retrieveManifest(loop_trace, handle)
                self._compare_to_expected_yaml(manifest_dict, test_case_name + "." + handle.kind)

            return
        except ApodeixiError as ex:
            print(ex.trace_message())                  

        # If we get this far, the tests failed since we should have returned within the try statement. 
        # So hardcode an informative failure.
        self.assertTrue("Shouldn't have gotten to this line" == 0)                                                                      

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_KnowledgeBase_Unit()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='posting_with_mock_store':
            T.test_posting_with_mock_store()

    main(_sys.argv)
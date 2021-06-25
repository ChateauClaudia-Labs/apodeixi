import sys                                              as _sys

from apodeixi.testing_framework.a6i_integration_test    import ApodeixiIntegrationTest
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase

class Test_KnowledgeBase_Integration(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()

    def test_big_rocks_posting(self):

        TEST_CASE                       = 'big_rocks_posting'

        EXCEL_FILE                      = self.postings_folder + "/journeys/Dec 2020/FusionOpus/Default/" \
                                            + 'OPUS_big-rocks.journeys.a6i.xlsx' 

        self._posting_testing_skeleton( store           = self.store, 
                                        test_case_name  = TEST_CASE,
                                        excel_file      = EXCEL_FILE)

    def _posting_testing_skeleton(self, store, test_case_name, excel_file):

        all_manifests_dicts     = []

        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Posting excel file", 
                                                                                data={  'excel_file'    : excel_file},
                                                                                origination = {
                                                                                        'signaled_from' : __file__,
                                                                                        'concrete class': str(self.__class__.__name__)})

            kbase               = KnowledgeBase(root_trace, store)

            response            = kbase.post(   parent_trace                = root_trace, 
                                                path_of_file_being_posted   = excel_file, 
                                                excel_sheet                 = "Sheet1")

            NB_MANIFESTS_EXPECTED   = 3
            if len(response.createdHandles()) != NB_MANIFESTS_EXPECTED:
                raise ApodeixiError(root_trace, 'Expected ' + str(NB_MANIFESTS_EXPECTED) + ' manifests, but found ' 
                                    + str(len(all_manifests_dicts)))

            # Retrieve the manifests created
            manifest_dict           = {}
            for handle in response.createdHandles():
                loop_trace          = root_trace.doing("Retrieving manifest for handle " + str(handle),
                                                        origination = {    
                                                                    'concrete class': str(self.__class__.__name__), 
                                                                    'signaled_from': __file__})
                manifest_dict       = store.retrieveManifest(loop_trace, handle)
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
        T = Test_KnowledgeBase_Integration()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='big_rocks_posting':
            T.test_big_rocks_posting()

    main(_sys.argv)
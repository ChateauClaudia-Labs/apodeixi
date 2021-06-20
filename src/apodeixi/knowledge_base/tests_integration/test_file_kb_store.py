import sys                                              as _sys

from apodeixi.testing_framework.a6i_integration_test    import ApodeixiIntegrationTest
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils                     import DictionaryFormatter 

from apodeixi.knowledge_base.file_kb_store              import File_KnowledgeBaseStore

class Test_File_KnowledgeBaseStore(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()
        
        root_trace                      = FunctionalTrace(None).doing("Loading Apodeixi configuration",
                                                                        origination = {'signaled_from': __file__})
        self.products                   = self.config.getProducts(root_trace)

    def test_locate_milestone_postings(self):
        POSTING_API                     = 'milestone.journeys.a6i'
        TEST_NAME                       = 'test_locate_milestone_postings'
        self._locate_product_postings(POSTING_API, TEST_NAME)

    def test_locate_marathon_postings(self):
        POSTING_API                     = 'delivery-planning.journeys.a6i'
        TEST_NAME                       = 'test_locate_marathon_postings'
        self._locate_product_postings(POSTING_API, TEST_NAME)

    def _locate_product_postings(self, posting_api, test_name):
        coords_txt                          = ''
        try:
            root_trace                      = FunctionalTrace(None).doing("Testing File Knowledge Base::locate product postings")

            def _coords_filter(coords):
                return coords.scoringCycle == "FY 22" and coords.scenario == "MTP"

            coords_dict                     = self.store.locatePostings(    parent_trace                = root_trace, 
                                                                            posting_api                 = posting_api, 
                                                                            filing_coordinates_filter   = _coords_filter, 
                                                                            posting_version_filter      = None)

            stringified_coords_dict         = {}    # Keys in coords_dict are objects, need to turn them into strings to print test output
            for coords in coords_dict.keys():
                stringified_coords_dict[format(coords, '')] = coords_dict[coords]
            coords_txt                      = "--------------------- Products with a filing structure in the KnowledgeBase\n\n"
            coords_txt                      += DictionaryFormatter().dict_2_nice(   parent_trace   = root_trace,
                                                                                    a_dict          = stringified_coords_dict, 
                                                                                    flatten=True)
            
            products_in_kb                  = [coords.product for coords in coords_dict.keys()]

            # These are legitimate products in the Apodeixi config but with no filing structure in the Knowledge Base
            missing                         = [format(prod_info) for prod_info in self.products if not prod_info.short_name in products_in_kb]

            # This is the dual gap: products with filing structure in the Knowledge Base but not appearing as legitimate in the Apodeixi config
            illegitimate                    = [prod for prod in products_in_kb if not prod in [prod_info.short_name for prod_info in self.products]]

            coords_txt                      += "\n\n--------------------- Products lacking a filing structure in the KnowledgeBase\n\n"
            coords_txt                      += "\n".join(missing)

            coords_txt                      += "\n\n--------------------- 'Illegitimate' products: \n" \
                                                + "\tthey are missing in the Apodeixi config but appear in the KnowledgeBase\n\n"
            coords_txt                      += "\n".join(illegitimate)

        except ApodeixiError as ex:
            print(ex.trace_message()) 

        self._compare_to_expected_txt(  output_txt      = coords_txt, 
                                        test_case_name  = test_name, 
                                        save_output_txt = True)

    def test_locate_initiative_milestone_postings(self):
        POSTING_API                     = 'workstream.initiatives.a6i'
        TEST_NAME                       = 'test_locate_initiative_milestone_postings'
        self._locate_workstream_postings(POSTING_API, TEST_NAME)

    def _locate_workstream_postings(self, posting_api, test_name):
        
        coords_txt                          = ''
        try:
            root_trace                      = FunctionalTrace(None).doing("Testing File Knowledge Base::locate postings")
            kb                              = File_KnowledgeBaseStore(  postings_rootdir       = self.postings_folder,
                                                                        derived_data_rootdir    = None)

            def _coords_filter(coords):
                return coords.scoringCycle == "FY 22" # and coords.scenario == "MTP"

            coords_dict                     = kb.locatePostings(    parent_trace                = root_trace, 
                                                                    posting_api                 = posting_api, 
                                                                    filing_coordinates_filter   = _coords_filter, 
                                                                    posting_version_filter      = None)

            stringified_coords_dict         = {}    # Keys in coords_dict are objects, need to turn them into strings to print test output
            for coords in coords_dict.keys():
                stringified_coords_dict[format(coords, '')] = coords_dict[coords]
            coords_txt                      = "--------------------- Workstreams with a filing structure in the KnowledgeBase\n\n"
            coords_txt                      += DictionaryFormatter().dict_2_nice(   parent_trace   = root_trace,
                                                                                    a_dict          = stringified_coords_dict, 
                                                                                    flatten=True)

        except ApodeixiError as ex:
            print(ex.trace_message()) 

        self._compare_to_expected_txt(  output_txt      = coords_txt, 
                                        test_case_name  = test_name, 
                                        save_output_txt = True)



if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_File_KnowledgeBaseStore()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='locate_milestone_postings':
            T.test_locate_milestone_postings()
        elif what_to_do=='locate_marathon_postings':
            T.test_locate_marathon_postings()
        elif what_to_do=='locate_initiative_milestone_postings':
            T.test_locate_initiative_milestone_postings()

    main(_sys.argv)
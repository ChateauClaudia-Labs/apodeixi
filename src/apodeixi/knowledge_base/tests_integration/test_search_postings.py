import sys                                              as _sys

from apodeixi.testing_framework.a6i_integration_test    import ApodeixiIntegrationTest, ShutilStoreTestStack
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils                     import DictionaryFormatter 

class Test_SearchPostings(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()
        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Selecting stack for test case")
        self.selectStack(root_trace) 
        
        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Retrieving product list from config",
                                                                        origination = {'signaled_from': __file__})
        self.products                   = ["LIQ", "CCB", "FCC", "FCM", "TI", "ESS", "GPP", "FCQ", "LPR", "MBTLOS",
                                            "MBTPOS", "MLZ", "PHX", "KON", "OPI", "RISK", "SUM"]

    def selectStack(self, parent_trace):
        '''
        Called as part of setting up each integration test case. It chooses and provisions the stack that should
        be used by this test case.
        '''
        self._stack                 = ShutilStoreTestStack(parent_trace, self.a6i_config)

    def test_locate_milestone_postings(self):
        POSTING_API                     = 'milestone.journeys.a6i'
        TEST_NAME                       = 'test_locate_milestone_postings'
        self.setScenario("search_milestone_postings")
        self.selectTestDataLocation()
        self._locate_product_postings(POSTING_API, TEST_NAME)

    def test_locate_big_rocks_postings(self):
        POSTING_API                     = 'big-rocks.journeys.a6i'
        TEST_NAME                       = 'test_locate_big_rocks_postings'
        self.setScenario("search_big_rocks_postings")
        self.selectTestDataLocation()
        self._locate_product_postings(POSTING_API, TEST_NAME)

    def _locate_product_postings(self, posting_api, test_name):
        coords_txt                          = ''

        root_trace                          = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing File Knowledge Base::locate product postings")
        
        try:

            def _coords_filter(coords):
                return coords.scoringCycle == "FY 22" and coords.scenario == "MTP"

            scanned_handles                  = self.stack().store().searchPostings(    parent_trace                = root_trace,
                                                                            posting_api                 = posting_api, 
                                                                            filing_coordinates_filter   = _coords_filter)

            # To ensure that regression test output is deterministic across Windows and Linux/Containers, sort the scanned 
            # handles before going further
            scanned_handles             = sorted(scanned_handles, key=lambda handle: format(handle.filing_coords) + handle.excel_filename)

            stringified_coords_dict         = {}    # Keys in coords_dict are objects, need to turn them into strings to print test output
            idx = 1
            for handle in scanned_handles:
                stringified_coords_dict[str(idx) + "." + format(handle.filing_coords, '')] = handle.excel_filename
                idx +=1
            coords_txt                      = "--------------------- Products with a posting in the KnowledgeBase filing structure\n\n"
            coords_txt                      += DictionaryFormatter().dict_2_nice(   parent_trace   = root_trace,
                                                                                    a_dict          = stringified_coords_dict, 
                                                                                    flatten=True)
            
            products_in_kb                  = [handle.filing_coords.product for handle in scanned_handles]

            # These are legitimate products in the Apodeixi config but with no filing structure in the Knowledge Base
            missing                         = [prod for prod in self.products if not prod in products_in_kb]

            # This is the dual gap: products with filing structure in the Knowledge Base but not appearing as legitimate in the Apodeixi config
            illegitimate                    = [prod for prod in products_in_kb if not prod in self.products]

            coords_txt                      += "\n\n--------------------- Products lacking postings in the KnowledgeBase filing structure\n\n"
            coords_txt                      += "\n".join(missing)

            coords_txt                      += "\n\n--------------------- 'Illegitimate' products: \n" \
                                                + "\tthey are missing in the Apodeixi config but appear in the KnowledgeBase\n\n"
            coords_txt                      += "\n".join(illegitimate)

        except ApodeixiError as ex:
            print(ex.trace_message()) 
            self.assertTrue(1==2)

        self._compare_to_expected_txt(  parent_trace        = root_trace,
                                        output_txt          = coords_txt, 
                                        test_output_name    = test_name, 
                                        save_output_txt     = True)

    def test_locate_initiative_milestone_postings(self):
        POSTING_API                     = 'workstream.initiatives.a6i'
        TEST_NAME                       = 'test_locate_initiative_milestone_postings'
        self.setScenario("search_workstream_postings")
        self.selectTestDataLocation()
        self._locate_workstream_postings(POSTING_API, TEST_NAME)

    def _locate_workstream_postings(self, posting_api, test_name):
        
        coords_txt                      = ''
        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing File Knowledge Base::locate postings")
        try:
            

            def _coords_filter(coords):
                return coords.scoringCycle == "FY 22" # and coords.scenario == "MTP"

            scanned_handles             = self.stack().store().searchPostings(    parent_trace                = root_trace, 
                                                                    posting_api                 = posting_api, 
                                                                    filing_coordinates_filter   = _coords_filter)

            # To ensure that regression test output is deterministic across Windows and Linux/Containers, sort the scanned 
            # handles before going further
            scanned_handles             = sorted(scanned_handles, key=lambda handle: format(handle.filing_coords) + handle.excel_filename)

            stringified_coords_dict     = {}    # Keys in coords_dict are objects, need to turn them into strings to print test output

            idx = 1
            for handle in scanned_handles:
                stringified_coords_dict[str(idx) + "." + format(handle.filing_coords, '')] = handle.excel_filename
                idx +=1

            coords_txt                  = "--------------------- Workstreams with a filing structure in the KnowledgeBase\n\n"
            coords_txt                  += DictionaryFormatter().dict_2_nice(   parent_trace   = root_trace,
                                                                                    a_dict          = stringified_coords_dict, 
                                                                                    flatten=True)

        except ApodeixiError as ex:
            print(ex.trace_message())
            self.assertTrue(1==2)
            

        self._compare_to_expected_txt(  parent_trace        = root_trace,
                                        output_txt          = coords_txt, 
                                        test_output_name    = test_name, 
                                        save_output_txt     = True)



if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_SearchPostings()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='locate_milestone_postings':
            T.test_locate_milestone_postings()
        elif what_to_do=='locate_big_rocks_postings':
            T.test_locate_big_rocks_postings()
        elif what_to_do=='locate_initiative_milestone_postings':
            T.test_locate_initiative_milestone_postings()

    main(_sys.argv)
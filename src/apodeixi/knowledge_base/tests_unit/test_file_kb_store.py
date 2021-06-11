import sys                                      as _sys

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils             import DictionaryFormatter 

from apodeixi.knowledge_base.file_kb_store      import File_KnowledgeBaseStore

from apodeixi.util.apodeixi_config              import ApodeixiConfig

class Test_File_KnowledgeBaseStore(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()
        
        root_trace                      = FunctionalTrace(None).doing("Loading EA Journeys configuration",
                                                                        origination = {'signaled_from': __file__})
        config                          = ApodeixiConfig(root_trace)
        self.postings_folder            = config.get_KB_PostingsRootFolder(root_trace)
        self.products                   = config.getProducts(root_trace)

    def test_locate_milestone_postings(self):
        POSTING_API                     = 'milestone.modernization.ea'
        TEST_NAME                       = 'test_locate_milestone_postings'
        self._locate_postings(POSTING_API, TEST_NAME)

    def test_locate_marathon_postings(self):
        POSTING_API                     = 'marathon-investment.modernization.ea'
        TEST_NAME                       = 'test_locate_marathon_postings'
        self._locate_postings(POSTING_API, TEST_NAME)

    def _locate_postings(self, posting_api, test_name):
        

        root_trace                      = FunctionalTrace(None).doing("Testing File Knowledge Base::locate postings")
        kb                              = File_KnowledgeBaseStore(  postings_rootdir       = self.postings_folder,
                                                                    derived_data_rootdir    = None)

        def _coords_filter(coords):
            return coords.scoringCycle == "FY 22" and coords.scenario == "MTP"

        coords_dict                     = kb.locatePostings(    parent_trace                = root_trace, 
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

        # These are legitimate products in the EA Journeys config but with no filing structure in the Knowledge Base
        missing                         = [format(prod_info) for prod_info in self.products if not prod_info.short_name in products_in_kb]

        # This is the dual gap: products with filing structure in the Knowledge Base but not appearing as legitimate in the EA Journeys config
        illegitimate                    = [prod for prod in products_in_kb if not prod in [prod_info.short_name for prod_info in self.products]]

        coords_txt                      += "\n\n--------------------- Products lacking a filing structure in the KnowledgeBase\n\n"
        coords_txt                      += "\n".join(missing)

        coords_txt                      += "\n\n--------------------- 'Illegitimate' products: \n" \
                                            + "\tthey are missing in the EA Journeys config but appear in the KnowledgeBase\n\n"
        coords_txt                      += "\n".join(illegitimate)

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

    main(_sys.argv)
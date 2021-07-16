import sys                                              as _sys

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.testing_framework.mock_kb_store           import UnitTest_KnowledgeBaseStore
from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.knowledge_base.knowledge_base_util        import ManifestUtils
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.controllers.journeys.delivery_planning    import big_rocks 

class Test_BigRocksEstimate(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_simple_burnout(self):
        '''
        Tests the "internal logic" of a controller: the _buildAllManifests method, using a simple mock KnowledgeBaseStore
        suitable for unit tests.
        '''

        EXCEL_FILE              = 'simple_burnout_INPUT.xlsx' 
        SHEET                   = 'simple burnout'

        MANIFEST_FILE_PREFIX    = 'simple_burnout'

        STORE_IMPL              = UnitTest_KnowledgeBaseStore(  test_case_name          = MANIFEST_FILE_PREFIX,
                                                                input_manifests_dir     = self.input_data, 
                                                                input_postings_dir      = self.input_data, 
                                                                output_manifests_dir    = self.output_data, 
                                                                output_postings_dir     = self.output_data)
        root_trace              = FunctionalTrace(parent_trace=None).doing("Discovering URL", data={'path'  : EXCEL_FILE,
                                                                                                    'sheet' : SHEET})

        STORE                   = KnowledgeBaseStore(root_trace, STORE_IMPL)                                                                                           
        posting_handle          = STORE.buildPostingHandle(root_trace, EXCEL_FILE, sheet=SHEET, excel_range="B2:C100")

        MANIFESTS_DIR           = self.output_data
        EXPLANATIONS_OUTPUT     = 'simple_burnout_explanations_OUTPUT.yaml'
        EXPLANATIONS_EXPECTED   = 'simple_burnout_explanations_EXPECTED.yaml'
        all_manifests_dicts     = []

        PL                      = big_rocks.BigRocksEstimate_Controller._MyPostingLabel # Abbreviation for readability purposes

        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Generating Big Rocks (simple burnout)")

            controller          = big_rocks.BigRocksEstimate_Controller(root_trace, STORE)
            all_manifests_dict, label,   = controller._buildAllManifests(root_trace, posting_handle)

            NB_MANIFESTS_EXPECTED   = 3
            if len(all_manifests_dict.keys()) != NB_MANIFESTS_EXPECTED:
                raise ApodeixiError(root_trace, 'Expected ' + str(NB_MANIFESTS_EXPECTED) + ' manifests, but found ' 
                                    + str(len(all_manifests_dicts)))

            
            for manifest_nb in all_manifests_dict.keys():
                manifest_dict     = all_manifests_dict[manifest_nb]

                STORE.persistManifest(root_trace, manifest_dict)

            # Make explanations readable by creating a pretty 
            explanations_nice   = DictionaryFormatter().dict_2_nice(    parent_trace    = root_trace,
                                                                        a_dict          = controller.show_your_work.as_dict(root_trace), 
                                                                        flatten=True, 
                                                                        delimeter="::")
            with open(MANIFESTS_DIR + '/'  + EXPLANATIONS_OUTPUT, 'w') as file:
                file            .write(explanations_nice)

        except ApodeixiError as ex:
            print(ex.trace_message())                                                                                        

        self.assertTrue(len(all_manifests_dict) == NB_MANIFESTS_EXPECTED)
        for manifest_nb in all_manifests_dict.keys():
            manifest_dict   = all_manifests_dict[manifest_nb]
            kind            = manifest_dict['kind']
            self._compare_to_expected_yaml(root_trace, manifest_dict, MANIFEST_FILE_PREFIX + "." + kind)
        with open(MANIFESTS_DIR + '/'  + EXPLANATIONS_EXPECTED, 'r') as file:
                expected_explain        = file.read()
        self.assertEqual(explanations_nice,    expected_explain)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_BigRocksEstimate()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='simple_burnout':
            T.test_simple_burnout()
        T.tearDown()

    main(_sys.argv)
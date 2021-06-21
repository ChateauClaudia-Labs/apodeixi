import sys                                              as _sys

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.testing_framework.mock_kb_store           import UnitTest_KnowledgeBaseStore
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.knowledge_base.knowledge_base_util        import ManifestUtils
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.controllers.initiatives.workstream        import Workstream_Controller 

class Test_Workstream(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_workstream_controller(self):
        '''
        Tests the "internal logic" of a controller: the _buildAllManifests method, using a simple mock KnowledgeBaseStore
        suitable for unit tests.
        '''

        EXCEL_FILE              = 'workstream_controller_INPUT.xlsx' 
        #SHEET                   = 'simple burnout'
        #CTX_RANGE               = 'b2:c20'

        MANIFEST_FILE_PREFIX    = 'workstream_controller'

        STORE                   = UnitTest_KnowledgeBaseStore(  test_case_name          = MANIFEST_FILE_PREFIX,
                                                                input_manifests_dir     = self.input_data, 
                                                                input_postings_dir      = self.input_data, 
                                                                output_manifests_dir    = self.output_data, 
                                                                output_postings_dir     = self.output_data)

        root_trace              = FunctionalTrace(parent_trace=None).doing("Discovering URL", data={'path'  : EXCEL_FILE,
                                                                                                    })
                                                                                                    #'sheet' : SHEET})
        url                     = STORE.discoverPostingURL(root_trace, EXCEL_FILE) #, sheet=SHEET)


        MANIFESTS_DIR           = self.output_data
        EXPLANATIONS_OUTPUT     = 'workstream_controller_explanations_OUTPUT.yaml'
        EXPLANATIONS_EXPECTED   = 'workstream_controller_explanations_EXPECTED.yaml'
        all_manifests_dicts     = []

        PL                      = Workstream_Controller._MyPostingLabel # Abbreviation for readability purposes

        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Generating workstream", data={'url'  : url})

            controller          = Workstream_Controller(root_trace, STORE)
            all_manifests_dict, label,   = controller._buildAllManifests(root_trace, url)#, CTX_RANGE)

            NB_MANIFESTS_EXPECTED   = 2
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
            self._compare_to_expected_yaml(manifest_dict, MANIFEST_FILE_PREFIX + "." + kind)
        with open(MANIFESTS_DIR + '/'  + EXPLANATIONS_EXPECTED, 'r') as file:
                expected_explain        = file.read()
        self.assertEqual(explanations_nice,    expected_explain)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_Workstream()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='workstream_controller':
            T.test_workstream_controller()
        T.tearDown()

    main(_sys.argv)
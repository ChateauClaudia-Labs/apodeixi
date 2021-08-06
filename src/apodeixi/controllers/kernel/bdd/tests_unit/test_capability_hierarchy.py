import sys                                              as _sys

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.testing_framework.mock_kb_store           import UnitTest_KnowledgeBaseStore
from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.knowledge_base.knowledge_base_util        import ManifestUtils
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.controllers.kernel.bdd                    import capability_hierarchy             as ctrl

class Test_CapabilityHierarchy(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_feature_injection(self):

        EXCEL_FILE              = 'feature_injection_INPUT.xlsx' 
        SHEET                   = 'Feature Injection'

        MANIFEST_FILE_PREFIX    = 'feature_injection'

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
        EXPLANATIONS_OUTPUT     = 'feature_injection_explanations_OUTPUT.yaml'
        EXPLANATIONS_EXPECTED   = 'feature_injection_explanations_EXPECTED.yaml'
        manifest_dict             = {}

        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Generating BDD scaffolding") 

            controller          = ctrl.CapabilityHierarchy_Controller(root_trace, STORE, a6i_config = self.a6i_config)
            all_manifests_dict, label,   = controller._buildAllManifests(   parent_trace            = root_trace, 
                                                                            posting_label_handle    = posting_handle)

            if len(all_manifests_dict) != 1:
                raise ApodeixiError(root_trace, 'Expected one manifest, but found ' + str(len(all_manifests_dict)))

            manifest_dict         = all_manifests_dict[0]

            STORE.persistManifest(root_trace, manifest_dict)

            # Make explanations readable by creating a pretty 
            explanations_dict   = controller.show_your_work.as_dict(root_trace) | controller.link_table.as_dict(root_trace)
            explanations_nice   = DictionaryFormatter().dict_2_nice(    parent_trace    = root_trace,
                                                                        a_dict          = explanations_dict, 
                                                                        flatten=True, 
                                                                        delimeter="::")
            with open(MANIFESTS_DIR + '/'  + EXPLANATIONS_OUTPUT, 'w') as file:
                file            .write(explanations_nice)

        except ApodeixiError as ex:
            print(ex.trace_message())  

        with open(MANIFESTS_DIR + '/'  + EXPLANATIONS_EXPECTED, 'r') as file:
                expected_explain        = file.read()
        self._compare_to_expected_yaml(root_trace, manifest_dict, 'feature_injection', save_output_dict = True)
        self.assertEqual(explanations_nice,    expected_explain)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_CapabilityHierarchy()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='a6i_feature_injection':
            T.test_feature_injection()


    main(_sys.argv)
import sys                              as _sys

from apodeixi.util.a6i_unit_test        import ApodeixiUnitTest
from apodeixi.util.a6i_error            import ApodeixiError, FunctionalTrace

from apodeixi.controllers.kernel.bdd    import capability_hierarchy             as ctrl

class Test_CapabilityHierarchy(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_feature_injection(self):

        EXCEL_FILE          = 'feature_injection_INPUT.xlsx' 
        SHEET               = 'Feature Injection'
        CTX_RANGE           = 'b2:c100'

        url                 = self.input_data  +  '/' + EXCEL_FILE + ':' + SHEET

        MANIFEST_FILE       = 'feature_injection_OUTPUT.yaml'
        MANIFESTS_DIR       = self.output_data
        result_dict         = {}
        try:
            root_trace      = FunctionalTrace(parent_trace=None).doing("Generating BDD scaffolding", data={'url'  : url})

            controller      = ctrl.CapabilityHierarchy_Controller(root_trace)
            all_manifests_dicts, label  = controller._buildAllManifests(root_trace, url, CTX_RANGE) 

            if len(all_manifests_dicts) != 1:
                raise ApodeixiError(root_trace, 'Expected one manifest, but found ' + str(len(all_manifests_dicts)))

            result_dict     = all_manifests_dicts[0]
            controller._saveManifest(root_trace, result_dict, MANIFESTS_DIR, MANIFEST_FILE)

        except ApodeixiError as ex:
            print(ex.trace_message())                                                                                        

        self._compare_to_expected_yaml(result_dict, 'feature_injection')

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_CapabilityHierarchy()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='a6i_feature_injection':
            T.test_feature_injection()


    main(_sys.argv)
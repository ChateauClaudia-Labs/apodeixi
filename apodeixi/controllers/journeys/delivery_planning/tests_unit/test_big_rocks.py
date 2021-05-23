import sys                                              as _sys

from apodeixi.util.a6i_unit_test                        import ApodeixiUnitTest
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.controllers.journeys.delivery_planning    import big_rocks 

class Test_BigRocksEstimate(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_simple_burnout(self):

        EXCEL_FILE              = 'simple_burnout_INPUT.xlsx' 
        SHEET                   = 'simple burnout'
        CTX_RANGE               = 'b2:c20'

        url                     = self.input_data  +  '/' + EXCEL_FILE + ':' + SHEET

        MANIFEST_FILE_PREFIX    = 'simple_burnout'
        MANIFESTS_DIR           = self.output_data
        EXPLANATIONS_OUTPUT     = 'simple_burnout_explanations_OUTPUT.yaml'
        EXPLANATIONS_EXPECTED   = 'simple_burnout_explanations_EXPECTED.yaml'
        all_manifests_dicts     = []

        PL                      = big_rocks.BigRocksEstimate_Controller._MyPostingLabel # Abbreviation for readability purposes

        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Generating Big Rocks (simple burnout)", data={'url'  : url})

            controller          = big_rocks.BigRocksEstimate_Controller(root_trace)
            all_manifests_dict, label,   = controller._buildAllManifests(root_trace, url, CTX_RANGE)

            NB_MANIFESTS_EXPECTED   = 3
            if len(all_manifests_dict.keys()) != NB_MANIFESTS_EXPECTED:
                raise ApodeixiError(root_trace, 'Expected ' + str(NB_MANIFESTS_EXPECTED) + ' manifests, but found ' 
                                    + str(len(all_manifests_dicts)))

            
            for manifest_nb in all_manifests_dict.keys():
                manifest_dict     = all_manifests_dict[manifest_nb]
                kind            = manifest_dict['kind']
                manifest_file   = MANIFEST_FILE_PREFIX + "_" + kind + "_OUTPUT.yaml"
                controller._saveManifest(root_trace, manifest_dict, MANIFESTS_DIR, manifest_file)

            # Make explanations readable by creating a pretty 
            explanations_nice   = self.dict_2_nice(controller.show_your_work.worklog, flatten=True)
            with open(MANIFESTS_DIR + '/'  + EXPLANATIONS_OUTPUT, 'w') as file:
                file            .write(explanations_nice)

        except ApodeixiError as ex:
            print(ex.trace_message())                                                                                        

        self.assertTrue(len(all_manifests_dict) == 3)
        for manifest_nb in all_manifests_dict.keys():
            manifest_dict   = all_manifests_dict[manifest_nb]
            kind            = manifest_dict['kind']
            self._compare_to_expected_yaml(manifest_dict, MANIFEST_FILE_PREFIX + "_" + kind)
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


    main(_sys.argv)
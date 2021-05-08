import sys as _sys
#import datetime
#import pandas as pd
#import yaml as _yaml

from apodeixi.controllers.kernel.bdd import bdd_scaffolding_controller as ctrl
from apodeixi.util.ApodeixiUnitTest import *
from apodeixi.util.ApodeixiError    import *

class Test_BDD_Scaffolding(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_feature_injection(self):

        EXCEL_FILE          = 'feature_injection_INPUT.xlsx' #capability-hierarchy.kernel.a6i.xlsx'
        SHEET               = 'Feature Injection'
        CTX_RANGE           = 'b2:c100'

        url                 = self.input_data  +  '/' + EXCEL_FILE + ':' + SHEET

        MANIFEST_FILE       = 'feature_injection_OUTPUT.yaml'
        #manifest_file       = EXCEL_FILE.replace('xlsx', 'yaml')
        MANIFESTS_DIR       = self.output_data

        result_dict         = ctrl._genScaffoldingManifest(url, CTX_RANGE, MANIFESTS_DIR, MANIFEST_FILE)

        self._compare_to_expected_yaml(result_dict, 'feature_injection')

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_BDD_Scaffolding()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='a6i_feature_injection':
            T.test_a6i_feature_injection()


    main(_sys.argv)
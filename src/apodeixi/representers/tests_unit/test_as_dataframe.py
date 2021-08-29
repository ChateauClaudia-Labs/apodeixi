import sys                              as _sys
import pandas                           as _pd

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.controllers.util.manifest_api             import ManifestAPIVersion
from apodeixi.util.a6i_error            import ApodeixiError, FunctionalTrace
from apodeixi.util.dataframe_utils      import DataFrameComparator

from apodeixi.representers              import AsDataframe_Representer

class Test_AsDataframe_Representer(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_yaml_2_sparse_dataframe(self):

        MANIFEST_FILE       = 'yaml_2_dataframe_INPUT.yaml' # Input file common across multiple tests
        MANIFESTS_FOLDER    = self.input_data
        OUTPUT_FOLDER       = self.output_data
        OUTPUT_FILE         = 'yaml_2_sparse_dataframe_OUTPUT.csv'
        df                  = None
        subtree             = None
        root_trace   = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing yam_2_df")
        try:
            rep          = AsDataframe_Representer()
            df, subtree  = rep.yaml_2_df(root_trace, MANIFESTS_FOLDER, MANIFEST_FILE, 'scaffolding.jobs-to-be-done',
                                            sparse=True, abbreviate_uids=True)
            # Save DataFrame in case the assertion below fails, so that we can do a visual comparison of OUTPUT vs EXPECTED csv files
            df.to_csv(OUTPUT_FOLDER + '/' + OUTPUT_FILE)
        except ApodeixiError as ex:
            print(ex.trace_message())
            self.assertTrue(1==2)                                                                                        

        self.assertEqual(subtree,       self._expected_subtree())

        self._compare_to_expected_df(   root_trace, 
                                        output_df           = df, 
                                        test_output_name    = "yaml_2_sparse_dataframe", 
                                        columns_to_ignore   = [], 
                                        id_column           = None)

    def test_yaml_2_full_dataframe(self):

        MANIFEST_FILE       = 'yaml_2_dataframe_INPUT.yaml' # Input file common across multiple tests
        MANIFESTS_FOLDER    = self.input_data
        OUTPUT_FOLDER       = self.output_data
        OUTPUT_FILE         = 'yaml_2_full_dataframe_OUTPUT.csv'
        df                  = None
        subtree             = None
        root_trace   = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing yam_2_full_df")
        try:
            rep          = AsDataframe_Representer()
            df, subtree  = rep.yaml_2_df(root_trace, MANIFESTS_FOLDER, MANIFEST_FILE, 'scaffolding.jobs-to-be-done',
                                                sparse=False, abbreviate_uids=True)
            # Save DataFrame in case the assertion below fails, so that we can do a visual comparison of OUTPUT vs EXPECTED csv files
            df.to_csv(OUTPUT_FOLDER + '/' + OUTPUT_FILE)
        except ApodeixiError as ex:
            print(ex.trace_message())
            self.assertTrue(1==2)                                                                                        

        self.assertEqual(subtree,       self._expected_subtree())

        self._compare_to_expected_df(   root_trace, 
                                        output_df           = df, 
                                        test_output_name    = "yaml_2_full_dataframe", 
                                        columns_to_ignore   = [], 
                                        id_column           = None)


    def _expected_subtree(self):
        return {ManifestAPIVersion.API_VERSION:   'kernel.a6i.io/v1dev',
                'kind':         'ProjectScaffolding',
                'metadata':     {   'labels':       {'organization': 'ChateauClaudia Labs', 'project': 'Apodeixi'},
                                    'name':         'bdd-tests.apodeixi',
                                    'namespace':    'chateauclaudia-labs.production'},
                'scaffolding':  {'entity_type': 'Jobs to be done', 'recordedBy': 'alejandro@chateauclaudia-labs.com'}}


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_AsDataframe_Representer()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='yaml_2_sparse_dataframe':
            T.test_yaml_2_sparse_dataframe()


    main(_sys.argv)
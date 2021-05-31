import sys                              as _sys
import pandas                           as _pd

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.util.a6i_error            import ApodeixiError, FunctionalTrace

from apodeixi.representers              import AsDataframe_Representer

class Test_AsDataframe_Representer(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_yaml_2_dataframe(self):

        MANIFEST_FILE       = 'yaml_2_dataframe_INPUT.yaml'
        MANIFESTS_FOLDER    = self.input_data
        OUTPUT_FOLDER       = self.output_data
        OUTPUT_FILE         = 'yaml_2_dataframe_OUTPUT.csv'
        df                  = None
        subtree             = None
        try:
            rep          = AsDataframe_Representer()
            root_trace   = FunctionalTrace(parent_trace=None).doing("Testing yam_2_df")
            df, subtree  = rep.yaml_2_df(root_trace, MANIFESTS_FOLDER, MANIFEST_FILE, 'scaffolding.jobs-to-be-done')
            # Save DataFrame in case the assertion below fails, so that we can do a visual comparison of OUTPUT vs EXPECTED csv files
            df.to_csv(OUTPUT_FOLDER + '/' + OUTPUT_FILE)
        except ApodeixiError as ex:
            print(ex.trace_message())                                                                                        

        self.assertEqual(subtree,       self._expected_subtree())
        self.assertTrue(df.             equals(self._expected_df()))


    def _expected_subtree(self):
        return {'apiVersion':   'kernel.a6i.io/v1dev',
                'kind':         'ProjectScaffolding',
                'metadata':     {   'labels':       {'organization': 'ChateauClaudia Labs', 'project': 'Apodeixi'},
                                    'name':         'bdd-tests.apodeixi',
                                    'namespace':    'chateauclaudia-labs.production'},
                'scaffolding':  {'entity_type': 'Jobs to be done', 'recordedBy': 'alejandro@chateauclaudia-labs.com'}}

    def _expected_df(self):
        FOLDER              = self.output_data
        FILE                = 'yaml_2_dataframe_EXPECTED.csv'
        saved_df            = _pd.read_csv(FOLDER + '/' + FILE)
        saved_df            = saved_df.fillna('')
        saved_df            = saved_df.drop(['Unnamed: 0'], axis=1)
        return saved_df


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_AsDataframe_Representer()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='yaml_2_dataframe':
            T.test_yaml_2_dataframe()


    main(_sys.argv)
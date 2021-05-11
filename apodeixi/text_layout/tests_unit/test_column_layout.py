import sys                              as _sys
import pandas                           as _pd

from apodeixi.util.a6i_unit_test        import ApodeixiUnitTest
from apodeixi.util.a6i_error            import ApodeixiError, FunctionalTrace

from apodeixi.text_layout.column_layout import ColumnWidthCalculator

class Test_ColumnWidthCalculator(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_sparse_layout(self):

        INPUT_FOLDER            = self.input_data
        INPUT_FILE              = 'test_sparse_layout_INPUT.csv'
        OUTPUT_FOLDER           = self.output_data
        OUTPUT_FILE             = 'test_sparse_layout_OUTPUT.csv'
        EXPECTED_FILE           = 'test_sparse_layout_EXPECTED.csv'

        OUTPUT_EXPLAIN_FILE     = 'test_sparse_layout_explain_OUTPUT.txt'
        EXPECTED_EXPLAIN_FILE   = 'test_sparse_layout_explain_EXPECTED.txt'

        try:

            data_df             = _pd.read_csv(INPUT_FOLDER + '/' + INPUT_FILE)
            data_df             = data_df.fillna('')
            data_df             = data_df.drop(['Unnamed: 0'], axis=1)

            calc                = ColumnWidthCalculator(data_df=data_df, viewport_width=50, viewport_height=40, max_word_length=20)
            output_df           = calc.calc()
            output_explain      = '\n'.join(calc.explanations)
            # Save DataFrame and explain in case the assertion below fails, so that we can do 
            # a visual comparison of OUTPUT vs EXPECTED csv files
            output_df.to_csv(OUTPUT_FOLDER + '/' + OUTPUT_FILE)
            with open(OUTPUT_FOLDER + '/'  + OUTPUT_EXPLAIN_FILE, 'w') as file:
                file            .write(output_explain)

            # Load the output we just saved, which we'll use for regression comparison since in Pandas the act of loading will
            # slightly change formats and we want to apply the same such changes as were applied to the expected output,
            # to avoid frivolous differences that don't deserve to cause this test to fail
            loaded_output_df    = _pd.read_csv(OUTPUT_FOLDER + '/' + OUTPUT_FILE)
            loaded_output_df    = loaded_output_df.fillna('')
            loaded_output_df    = loaded_output_df.drop(['Unnamed: 0'], axis=1)

            # Now load the expected output
            expected_df         = _pd.read_csv(OUTPUT_FOLDER + '/' + EXPECTED_FILE)
            expected_df         = expected_df.fillna('')
            expected_df         = expected_df.drop(['Unnamed: 0'], axis=1)

            

            with open(OUTPUT_FOLDER + '/'  + EXPECTED_EXPLAIN_FILE, 'r') as file:
                expected_explain     = file.read()

        except ApodeixiError as ex:
            print(ex.trace_message()) 

        self.assertTrue(loaded_output_df.equals(expected_df))
        self.assertEqual(output_explain, expected_explain)
        

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_ColumnWidthCalculator()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='sparse_layout':
            T.test_small_text()


    main(_sys.argv)
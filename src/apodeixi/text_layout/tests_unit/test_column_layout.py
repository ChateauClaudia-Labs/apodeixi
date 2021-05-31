import sys                              as _sys
import pandas                           as _pd

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.util.formatting_utils     import DictionaryFormatter
from apodeixi.util.a6i_error            import ApodeixiError, FunctionalTrace

from apodeixi.text_layout.column_layout import ColumnWidthCalculator

class Test_ColumnWidthCalculator(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_sparse_layout(self):

        self._shell_test_case('test_sparse_layout', viewport_width=50, viewport_height=40, max_word_length=20)

    def test_thick_layout(self):

        self._shell_test_case('test_thick_layout', viewport_width=100, viewport_height=40, max_word_length=20)

    def _shell_test_case(self, name, viewport_width, viewport_height, max_word_length):

        INPUT_FOLDER            = self.input_data
        INPUT_FILE              = name + '_INPUT.csv'
        OUTPUT_FOLDER           = self.output_data
        OUTPUT_FILE             = name + '_OUTPUT.csv'
        EXPECTED_FILE           = name + '_EXPECTED.csv'

        OUTPUT_EXPLAIN_FILE     = name + '_explain_OUTPUT.txt'
        EXPECTED_EXPLAIN_FILE   = name + '_explain_EXPECTED.txt'

        OUTPUT_RESULTS_FILE     = name + '_results_OUTPUT.txt'
        EXPECTED_RESULTS_FILE   = name + '_results_EXPECTED.txt'

        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Testing computation of column widths")

            data_df             = self.load_csv(INPUT_FOLDER + '/' + INPUT_FILE)

            calc                = ColumnWidthCalculator(    data_df             = data_df, 
                                                            viewport_width      = viewport_width, 
                                                            viewport_height     = viewport_height, 
                                                            max_word_length     = max_word_length)
            result_dict         = calc.calc(root_trace)
            output_df           = calc.analysis_df
            output_explain      = '\n'.join(calc.explanations)
            # Save DataFrame, explain and results in case the assertion below fails, so that we can do 
            # a visual comparison of OUTPUT vs EXPECTED csv files
            output_df.to_csv(OUTPUT_FOLDER + '/' + OUTPUT_FILE)
            with open(OUTPUT_FOLDER + '/'  + OUTPUT_EXPLAIN_FILE, 'w') as file:
                file            .write(output_explain)
            # Make results readable by creating a pretty 
            result_nice         = DictionaryFormatter().dict_2_nice(result_dict)
            with open(OUTPUT_FOLDER + '/'  + OUTPUT_RESULTS_FILE, 'w') as file:
                file            .write(result_nice)

            # Load the output we just saved, which we'll use for regression comparison since in Pandas the act of loading will
            # slightly change formats and we want to apply the same such changes as were applied to the expected output,
            # to avoid frivolous differences that don't deserve to cause this test to fail
            loaded_output_df    = self.load_csv(OUTPUT_FOLDER + '/' + OUTPUT_FILE)


            # Now load the expected output
            expected_df         = self.load_csv(OUTPUT_FOLDER + '/' + EXPECTED_FILE)
           
            with open(OUTPUT_FOLDER + '/'  + EXPECTED_EXPLAIN_FILE, 'r') as file:
                expected_explain        = file.read()
            with open(OUTPUT_FOLDER + '/'  + EXPECTED_RESULTS_FILE, 'r') as file:
                expected_result     = file.read()

        except ApodeixiError as ex:
            print(ex.trace_message()) 

        self.assertTrue(loaded_output_df.equals(expected_df))
        self.assertEqual(output_explain,    expected_explain)
        self.assertEqual(result_nice,       expected_result)
        

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_ColumnWidthCalculator()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='sparse_layout':
            T.test_small_text()


    main(_sys.argv)
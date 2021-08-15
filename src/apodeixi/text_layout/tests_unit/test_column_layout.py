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

        INPUT_FOLDER                = self.input_data
        INPUT_FILE                  = name + '_INPUT.csv'
        OUTPUT_FOLDER               = self.output_data
        OUTPUT_FILE                 = name + '_OUTPUT.csv'
        EXPECTED_FOLDER             = self.expected_data
        EXPECTED_FILE               = name + '_EXPECTED.csv'

        OUTPUT_COMPARISON_FILE      = name + '_comparison_OUTPUT.txt'
        EXPECTED_COMPARISON_FILE    = name + '_comparison_EXPECTED.txt'

        OUTPUT_EXPLAIN_FILE         = name + '_explain_OUTPUT.txt'
        EXPECTED_EXPLAIN_FILE       = name + '_explain_EXPECTED.txt'

        OUTPUT_RESULTS_FILE         = name + '_results_OUTPUT.txt'
        EXPECTED_RESULTS_FILE       = name + '_results_EXPECTED.txt'

        try:
            root_trace          = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing computation of column widths")

            data_df             = self.load_csv(root_trace, INPUT_FOLDER + '/' + INPUT_FILE)

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
            result_nice         = DictionaryFormatter().dict_2_nice(parent_trace = root_trace, a_dict = result_dict)
            with open(OUTPUT_FOLDER + '/'  + OUTPUT_RESULTS_FILE, 'w') as file:
                file            .write(result_nice)

            # Load the output we just saved, which we'll use for regression comparison since in Pandas the act of loading will
            # slightly change formats and we want to apply the same such changes as were applied to the expected output,
            # to avoid frivolous differences that don't deserve to cause this test to fail
            loaded_output_df    = self.load_csv(root_trace, OUTPUT_FOLDER + '/' + OUTPUT_FILE)


            # Now load the expected output. 
            expected_df         = self.load_csv(root_trace, EXPECTED_FOLDER + '/' + EXPECTED_FILE)

            check, comparison_dict = self._compare_dataframes(  df1         = loaded_output_df, 
                                                                df1_name    = "output",
                                                                df2         = expected_df, 
                                                                df2_name    = "expected")

            df_comparison_nice              = DictionaryFormatter().dict_2_nice(parent_trace    = root_trace, 
                                                                                a_dict          = comparison_dict, 
                                                                                flatten=True)
            with open(OUTPUT_FOLDER + '/' + OUTPUT_COMPARISON_FILE, 'w') as file:
                file            .write(df_comparison_nice)

            with open(EXPECTED_FOLDER + '/' + EXPECTED_COMPARISON_FILE, 'r') as file:
                expected_df_comparison  = file.read()           
            with open(EXPECTED_FOLDER + '/' + EXPECTED_EXPLAIN_FILE, 'r') as file:
                expected_explain        = file.read()
            with open(EXPECTED_FOLDER + '/' + EXPECTED_RESULTS_FILE, 'r') as file:
                expected_result     = file.read()

        except ApodeixiError as ex:
            print(ex.trace_message()) 

        self.assertEqual(df_comparison_nice,       expected_df_comparison)
        self.assertTrue(check)
        self.assertEqual(output_explain,    expected_explain)
        self.assertEqual(result_nice,       expected_result)

    def _compare_dataframes(self, df1, df2, df1_name, df2_name):
        '''
        Helper method used in lieu of dataframe.equals, which fails for spurious reasons.
        Under this method's policy, two dataframes are equal if they have the same columns, indices, and are
        point-wise equal.

        Method returns two things: a boolean result of the comparison, and a dictionary to pin point where there are
        differences, if any
        '''
        # Prepare an explanation of where the dataframes differ, if they do differ. This visibility helps with debugging
        comparison_dict                                 = {}
        cols_1                                          = set(df1.columns)
        cols_2                                          = set(df2.columns)

        # Ensure determinism with sort
        common_cols                                     = list(cols_1.intersection(cols_2))
        common_cols.sort() 
        missing_in_1                                    = list(cols_2.difference(cols_1))
        missing_in_1.sort()
        missing_in_2                                    = list(cols_1.difference(cols_2))
        missing_in_2.sort()

        comparison_dict[df1_name + ' shape']            = str(df1.shape)
        comparison_dict[df2_name + ' shape']            = str(df2.shape)
        if len(missing_in_1) > 0:
            comparison_dict[df1_name + ' missing columns']  = '\n'.join(missing_in_1)
        if len(missing_in_2) > 0:
            comparison_dict[df2_name + ' missing columns']  = '\n'.join(missing_in_2)

        # Initialize true until profen false
        check                                           = True

        if not df1.index.equals(df2.index): 
            check                                       = False
        else: # Compare element by element for the common_cols
            cell_dict                                   = {}
            for row in df1.iterrows():
                row1_nb                                 = row[0]
                row1_data                               = row[1]
                for col in common_cols: # use common_cols that is a deterministic list
                    val1                                = row1_data[col]
                    val2                                = df2.iloc[row1_nb][col]
                    if val1 != val2:
                        check                           = False
                        coords                          = col + '.row' + str(row1_nb)
                        cell_dict[coords]               = "values differ"
                        cell_dict[coords + '.' + df1_name]    = str(val1)
                        cell_dict[coords + '.' + df2_name]    = str(val2)
            comparison_dict['elt-by-elt comparison']   = cell_dict

            if check:
                comparison_dict['Result of elt-by-elt comparison'] = "Everything matches"

        return check, comparison_dict
    

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_ColumnWidthCalculator()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='sparse_layout':
            T.test_small_text()


    main(_sys.argv)
import sys                                          as _sys
import os                                           as _os
import unittest                                     as _unittest

from apodeixi.testing_framework.a6i_unit_test       import ApodeixiUnitTest
from apodeixi.util.a6i_error                        import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils                 import DictionaryFormatter, NotebookUtils
from apodeixi.util.dictionary_utils                 import DictionaryUtils 

from apodeixi.util.dataframe_utils                  import DataFrameComparator 

SMOKE_TESTS_ONLY                                    = _os.environ.get('SMOKE_TESTS_ONLY')

class Test_DataFrameComparator(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_compare_dataframes(self):
        root_trace                      = FunctionalTrace(None).doing("Testing DataFrame Comparison")
        try:
            INPUT_FOLDER                    = self.input_data
            OUTPUT_FOLDER                   = self.output_data
            TEST_SCENARIO                   = 'test_compare_dataframes'

            my_trace                        = root_trace.doing("Loading and comparing the dataframes")

            df1                             = self.load_csv(my_trace, INPUT_FOLDER + '/' + TEST_SCENARIO + '_df1_INPUT.csv')
            df2                             = self.load_csv(my_trace, INPUT_FOLDER + '/' + TEST_SCENARIO + '_df2_INPUT.csv')

            comparator                      = DataFrameComparator(  df1                 = df1,
                                                                    df2                 = df2, 
                                                                    df1_name            = "df1", 
                                                                    df2_name            = "df2", 
                                                                    id_column           = 'Diario')

            check, comparison_dict          = comparator.compare(my_trace)

            my_trace                        = root_trace.doing("Formatting comparison text")

            output_txt                      = ''
            for key in comparison_dict:
                output_txt                  += "\n\n-------------------- " + str(key) + ' ----------------------\n'
                val                         = comparison_dict[key]
                if type(val) == dict:
                    for sub_key in val.keys():
                        output_txt          += str(sub_key) + ":\n"
                        subval              = val[sub_key]
                        if type(subval) == dict:
                            subval_txt      = DictionaryFormatter().dict_2_nice(    parent_trace    = my_trace,
                                                                                    a_dict          = subval, 
                                                                                    flatten         = True)
                        else:
                            subval_txt      = str(subval)
                        output_txt          += "" + subval_txt + "\n"

                else:
                    output_txt              += str(val)

            self._compare_to_expected_txt(  parent_trace        = my_trace,
                                            output_txt          = output_txt, 
                                            test_case_name      = TEST_SCENARIO + '_comparison', 
                                            save_output_txt=True)


            self.assertTrue(check==False) # The comparison should result in the two DataFrames being different

        except ApodeixiError as ex:
            print(ex.trace_message())

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_DataFrameComparator()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='compare_dataframes':
            T.test_compare_dataframes()
        T.tearDown()
        
    main(_sys.argv)
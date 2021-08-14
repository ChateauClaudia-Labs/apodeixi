import sys                                          as _sys
import os                                           as _os
import unittest                                     as _unittest

from apodeixi.testing_framework.a6i_unit_test       import ApodeixiUnitTest
from apodeixi.util.a6i_error                        import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils                 import DictionaryFormatter, NotebookUtils
from apodeixi.util.dictionary_utils                 import DictionaryUtils 

from apodeixi.util.list_utils              			import ListMerger

class Test_ListMerger(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_merge_lists(self):
        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing List Merger")
        try:
            INPUT_FOLDER                    = self.input_data
            OUTPUT_FOLDER                   = self.output_data
            TEST_SCENARIO                   = 'test_merge_lists'
            OUTPUT_FILE                     = TEST_SCENARIO + '_OUTPUT.txt'
            EXPECTED_FILE                   = TEST_SCENARIO + '_EXPECTED.txt'



            list1                           = [ 1000,           3000,   4000,   5000,                   8000,   9000]
            list2                           = [ 1000,   2000,   3000,   4000,   5000,   6000,   7000,           9000]

            my_trace                        = root_trace.doing("Merging lists")

            merger                          = ListMerger(   parent_trace        = my_trace,
                                                            list1               = list1,
                                                            list2               = list2, 
                                                            list1_name          = "left", 
                                                            list2_name          = "right")

            merged_list                     = merger.merge(my_trace)

            my_trace                        = root_trace.doing("Comparing merge list to expected output")

            output_txt                      = '============ List1 ================\n' + str(list1)
            output_txt                      += '\n\n============ List2 ================\n' + str(list2)
            output_txt                      += '\n\n============ Merged Result ================\n' + merger.format_results(my_trace)

            '''
            output_txt                      = '\n'.join(['\t\t'.join(["Element: " + str(e[0]), 
                                                                    "LEFT" if e[1] else "    ", 
                                                                    "RIGHT" if e[2] else "     "]) for e in merged_list])
            '''

            self._compare_to_expected_txt(  parent_trace        = my_trace,
                                            output_txt          = output_txt,
                                            test_output_name    = TEST_SCENARIO, 
                                            save_output_txt     = True)

        except ApodeixiError as ex:
            print(ex.trace_message())

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_ListMerger()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='merge_lists':
            T.test_merge_lists()
        T.tearDown()
        
    main(_sys.argv)
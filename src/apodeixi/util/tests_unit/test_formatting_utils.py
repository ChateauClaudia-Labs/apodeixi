import sys                                          as _sys
import os                                           as _os
import unittest                                     as _unittest

from apodeixi.testing_framework.a6i_unit_test       import ApodeixiUnitTest
from apodeixi.util.a6i_error                        import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils                 import NotebookUtils
from apodeixi.util.dictionary_utils                 import DictionaryUtils 
from apodeixi.util.path_utils                       import PathUtils

SMOKE_TESTS_ONLY                                    = _os.environ.get('SMOKE_TESTS_ONLY')

class Test_NotebookUtils(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    @_unittest.skipIf(SMOKE_TESTS_ONLY != None, "Skip long-running routines")
    def test_notebook_run(self):
        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing Notebook execution")
        try:
            INPUT_FOLDER                    = self.input_data
            OUTPUT_FOLDER                   = self.output_data
            EXPECTED_FOLDER                 = self.expected_data
            TEST_SCENARIO                   = 'test_notebook_run' 

            PathUtils().create_path_if_needed(root_trace, OUTPUT_FOLDER + "/notebooks/")
            nb_utils                        = NotebookUtils(    src_folder              = INPUT_FOLDER, 
                                                                src_filename            = TEST_SCENARIO + "_INPUT.ipynb", 
                                                                destination_folder      = OUTPUT_FOLDER + "/notebooks/", 
                                                                destination_filename    = TEST_SCENARIO + "_executed_notebook.ipynb")

            my_trace                        = root_trace.doing("Running notebook")
            result_dict                     = nb_utils.run(my_trace)

            # Remove a path with timestamps since it changes all the time
            my_trace                        = root_trace.doing("Removing path with timestamps")
            hide_timestamps                 = lambda x: '<Timestamps removed in test output>'
            cleaned_dict                    = DictionaryUtils().replace_path(   parent_trace            = my_trace, 
                                                                                root_dict               = result_dict, 
                                                                                root_dict_name          = 'nb_utils_run_result_dict', 
                                                                                path_list               = ['cells', '*', 'metadata', 'execution','*'], 
                                                                                replacement_lambda      = hide_timestamps)
            my_trace                        = root_trace.doing("Hiding user_folders printed as output")
            def _hide_user_folders(val):
                folder_hints                = ['apodeixi\\util', 'apodeixi\\\\util']
                result                      = val
                for hint in folder_hints:
                    if hint in val: # val is a path, keep only what comes after 'src/apodeixi'.
                        result              = '<Root directory hidden in test output>' + hint + val.split(hint)[1]
                        return result
                return result
            cleaned_dict                    = DictionaryUtils().replace_path(   parent_trace            = my_trace, 
                                                                                root_dict               = cleaned_dict, 
                                                                                root_dict_name          = 'aha_configurer_result_dict', 
                                                                                path_list               = ['cells', '*', 'outputs', '*','data', 'text/plain'], 
                                                                                replacement_lambda      = _hide_user_folders)

            self._compare_to_expected_yaml( parent_trace        = my_trace,
                                            output_dict         = cleaned_dict, 
                                            test_output_name    = TEST_SCENARIO, 
                                            save_output_dict    = True)
        except ApodeixiError as ex:
            print(ex.trace_message())
            self.assertTrue(1==2)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_NotebookUtils()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=="notebook_run":
            T.test_notebook_run()
        T.tearDown()
        
    main(_sys.argv)
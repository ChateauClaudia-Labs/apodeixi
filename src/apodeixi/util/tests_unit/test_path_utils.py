import sys                                          as _sys
import os                                           as _os
import unittest                                     as _unittest

from apodeixi.testing_framework.a6i_unit_test       import ApodeixiUnitTest
from apodeixi.util.a6i_error                        import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils                 import DictionaryFormatter, NotebookUtils
from apodeixi.util.dictionary_utils                 import DictionaryUtils 

from apodeixi.util.path_utils              			import PathUtils

class Test_PathUtils(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_path_utils(self):
        root_trace                      = FunctionalTrace(None).doing("Testing Path Utils")
        try:
            INPUT_FOLDER                    = self.input_data
            OUTPUT_FOLDER                   = self.output_data
            TEST_SCENARIO                   = 'test_path_utils'
            OUTPUT_FILE                     = TEST_SCENARIO + '_OUTPUT.txt'
            EXPECTED_FILE                   = TEST_SCENARIO + '_EXPECTED.txt'



            list1                           = [ 1000,           3000,   4000,   5000,                   8000,   9000]
            list2                           = [ 1000,   2000,   3000,   4000,   5000,   6000,   7000,           9000]

            root_dir, parent_dir            = _os.path.split(self.input_data)

            rel_real_file                   = parent_dir + '/' + TEST_SCENARIO + '_INPUT.txt'
            real_file                       = root_dir + '/' + rel_real_file

            rel_fake_file                   = parent_dir + '/' + TEST_SCENARIO +  '_NOT_REAL.foo'
            fake_file                       = root_dir + '/' + rel_fake_file

            leaf                            = "my_file.txt"
            non_leaf                        = "secrets/my_file.txt"

            bad_path                        = "/august/marzo/time.txt"

            # Test is_leaf
            my_trace                        = root_trace.doing("Testing is_leaf")
            output_txt                      = '============ Testing is_leaf ================\n'

            val                             = PathUtils().is_leaf(my_trace, leaf)
            output_txt                      += "\nis_leaf(" + leaf + ")\t\t= " + str(val)

            val                             = PathUtils().is_leaf(my_trace, non_leaf)
            output_txt                      += "\n\nis_leaf(" + non_leaf + ")\t\t= " + str(val)

            # Test is_parent
            my_trace                        = root_trace.doing("Testing is_parent")
            output_txt                      += '\n\n============ Testing is_parent ================\n'

            val                             = PathUtils().is_parent(my_trace, parent_dir = root_dir, path = real_file)
            output_txt                      += "\nis_parent(" + "< ... >" \
                                                + ", < ... >/" + rel_real_file + ") = " + str(val)

            val                             = PathUtils().is_parent(my_trace, parent_dir = root_dir, path = bad_path)
            output_txt                      += "\n\nis_parent(" + "< ... >, " + bad_path + ") = " + str(val)

            # Test relativize
            my_trace                        = root_trace.doing("Testing relativize")
            output_txt                      += '\n\n============ Testing is_parent ================\n'

            val                             = PathUtils().relativize(my_trace, root_dir = root_dir, full_path = real_file)
            output_txt                      += "\nrelativize(" + "< ... >" \
                                                + ", < ... >/" + rel_real_file + ") = \n\t\t" + str(val)            

            try:
                val                             = PathUtils().relativize(my_trace, root_dir = root_dir, full_path = fake_file)
            except ApodeixiError as ex:
                val                         = str(ex)
            output_txt                      += "\n\nrelativize(" + "< ... >" \
                                                + ", < ... >/" + rel_fake_file + ") = \n\t\t" + str(val)  

            # Test tokenize_path
            my_trace                        = root_trace.doing("Testing tokenize_path")
            output_txt                      += '\n\n============ Testing tokenize_path ================\n'

            relative_path                   = "/visions\\ideas\\problems/corrections"
            val                             = PathUtils().tokenizePath(my_trace, relative_path)
            output_txt                      += "\ntokenizePath(" + relative_path + ") = \n\t\t" + str(val)
                                                
            absolute_path                   = "C:/visions\\ideas\\problems/corrections"
            val                             = PathUtils().tokenizePath(my_trace, absolute_path)
            output_txt                      += "\n\ntokenizePath(" + absolute_path + ") = \n\t\t" + str(val)

            self._compare_to_expected_txt(  parent_trace        = my_trace,
                                            output_txt          = output_txt,
                                            test_output_name    = TEST_SCENARIO, 
                                            save_output_txt     = True)

        except ApodeixiError as ex:
            print(ex.trace_message())
            self.assertTrue(1==2)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_PathUtils()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='path_utils':
            T.test_path_utils()
        T.tearDown()
        
    main(_sys.argv)
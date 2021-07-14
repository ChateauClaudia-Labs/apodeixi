import sys                                          as _sys
import os                                           as _os

from apodeixi.testing_framework.a6i_unit_test       import ApodeixiUnitTest
from apodeixi.util.a6i_error                        import ApodeixiError, FunctionalTrace

from apodeixi.util.path_utils              			import FolderHierarchy

class Test_FolderHierarchy(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_create(self):
        root_trace                      = FunctionalTrace(None).doing("Testing Creation of FolderHierarhcy")
        try:
            INPUT_FOLDER                    = self.input_data
            OUTPUT_FOLDER                   = self.output_data
            TEST_SCENARIO                   = 'test_create'
            OUTPUT_FILE                     = TEST_SCENARIO + '_OUTPUT.txt'
            EXPECTED_FILE                   = TEST_SCENARIO + '_EXPECTED.txt'

            ROOT_DIR                        = _os.path.dirname(_os.path.dirname(INPUT_FOLDER))

            def filter(filename):
                return not filename.endswith(".pyc")

            hierarchy                       = FolderHierarchy.build(parent_trace        = root_trace, 
                                                                    rootdir             = ROOT_DIR, 
                                                                    filter              = filter,
                                                                    include_timestamps  = False)

            self._compare_to_expected_yaml( parent_trace        = root_trace,
                                            output_dict         = hierarchy.to_dict(),
                                            test_case_name      = TEST_SCENARIO, 
                                            save_output_dict    = True)

        except ApodeixiError as ex:
            print(ex.trace_message())
            self.assertTrue(1==2)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_FolderHierarchy()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='create':
            T.test_create()
        T.tearDown()
        
    main(_sys.argv)
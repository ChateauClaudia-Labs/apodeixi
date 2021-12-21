import sys                                          as _sys
import warnings

from apodeixi.testing_framework.a6i_unit_test       import ApodeixiUnitTest
from apodeixi.util.a6i_error                        import ApodeixiError, FunctionalTrace

from apodeixi.util.warning_utils                    import WarningUtils

class Test_WarningUtils(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_warning_utils(self):
        root_trace                          = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing Warning Utils")
        try:
            TEST_SCENARIO                   = 'test_warning_utils'

            my_trace                        = root_trace.doing("Testing a fake warning")

            with warnings.catch_warnings(record=True) as w:
                WarningUtils().turn_traceback_on(my_trace, warnings_list=w)
                    
                warnings.warn("Test warning for Warning Utils", DeprecationWarning)

                WarningUtils().handle_warnings(my_trace, warning_list=w)

                # The handling of the warning should raise an exception, so we should not get here
                self.assertTrue(1==2)

        except ApodeixiError as ex:
            output_txt                      = ex.trace_message()
            self._compare_to_expected_txt(  parent_trace        = my_trace,
                                            output_txt          = output_txt,
                                            test_output_name    = TEST_SCENARIO, 
                                            save_output_txt     = True)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_WarningUtils()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=="warning_utils":
            T.test_warning_utils()
        T.tearDown()
        
    main(_sys.argv)
import sys                                      as _sys

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils             import DictionaryFormatter
from apodeixi.util.dictionary_utils             import DictionaryUtils

from apodeixi.util.apodeixi_config              import ApodeixiConfig 

class Test_ApodeixiConfig(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_a6i_config(self):
        try:
            root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing loading for Apodeixi Config")
            config                          = ApodeixiConfig(root_trace)

            # To ensure determistic output, mask parent part of any path that is mentioned in the configuration before 
            # displaying it in regression putput
            #
            clean_dict                      = DictionaryUtils().apply_lambda(       parent_trace    = root_trace, 
                                                                                    root_dict       = config.config_dict, 
                                                                                    root_dict_name  = "Apodeixi config", 
                                                                                    lambda_function = self._path_mask)

            config_txt                      = DictionaryFormatter().dict_2_nice(    parent_trace    = root_trace,
                                                                                    a_dict          = clean_dict, 
                                                                                    flatten         = True)

            self._compare_to_expected_txt(  parent_trace        = root_trace,
                                            output_txt          = config_txt, 
                                            test_output_name    = 'test_a6i_config', 
                                            save_output_txt     = True)
        except ApodeixiError as ex:
            print(ex.trace_message())
            self.assertTrue(1==2)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_ApodeixiConfig()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='a6i_config':
            T.test_a6i_config()
        T.tearDown()
        
    main(_sys.argv)
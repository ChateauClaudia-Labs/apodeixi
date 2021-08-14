import sys                                      as _sys

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils             import DictionaryFormatter

from apodeixi.util.apodeixi_config              import ApodeixiConfig 

class Test_ApodeixiConfig(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_a6i_config(self):
        try:
            root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing loading for Apodeixi Config")
            config                          = ApodeixiConfig(root_trace)

            config_txt                      = DictionaryFormatter().dict_2_nice(    parent_trace    = root_trace,
                                                                                    a_dict          = config.config_dict, 
                                                                                    flatten         = True)

            self._compare_to_expected_txt(  parent_trace        = root_trace,
                                            output_txt          = config_txt, 
                                            test_output_name    = 'test_a6i_config', 
                                            save_output_txt     = True)
        except ApodeixiError as ex:
            print(ex.trace_message())

    def test_get_products(self):
        try:
            root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing getProducts for Apodeixi Config")
            config                          = ApodeixiConfig(root_trace)

            products                        = config.getProducts(root_trace)
            #output_txt                      = "\n".join([format(prod_info, '') for prod_info in products])
            output_txt                      = ''
            for prod in products:
                output_txt                  += "\n===============================================\n"
                output_txt                  += DictionaryFormatter().dict_2_nice(   parent_trace    = root_trace,
                                                                                    a_dict          = prod, 
                                                                                    flatten         = True)

            self._compare_to_expected_txt(  parent_trace        = root_trace,
                                            output_txt          = output_txt, 
                                            test_output_name    = 'test_get_products', 
                                            save_output_txt     = True)
        except ApodeixiError as ex:
            print(ex.trace_message())

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_ApodeixiConfig()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='a6i_config':
            T.test_a6i_config()
        elif what_to_do=='get_products':
            T.test_get_products()
        T.tearDown()
        
    main(_sys.argv)
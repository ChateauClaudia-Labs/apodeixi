import sys                                                                              as _sys

from apodeixi.util.a6i_error                                                            import FunctionalTrace

from apodeixi.cli.tests_integration.cli_test_skeleton                                   import CLI_Test_Skeleton
from apodeixi.controllers.admin.static_data.tests_integration.cli_static_data_script    import CLI_StaticData_Script

class Test_StaticData_CLI(CLI_Test_Skeleton):
       
    def test_cli_subproducts(self):
        self.setScenario("cli.subproducts")
        self.setCurrentTestName('subprods')
        self.selectTestDataLocation()

        _s                              = CLI_StaticData_Script
        cli_arguments_dict              = {
            _s.STATIC_DATA_v1_FILE:             "v1.products.static-data.admin.a6i.xlsx",
            _s.STATIC_DATA_v2_FILE:             "v2.products.static-data.admin.a6i.xlsx",
            _s.STATIC_DATA_API:                 "products.static-data.admin.a6i",
            _s.REL_PATH_IN_EXT_COLLABORATION:   "admin/static-data",
            _s.NAMESPACE:                       "my-corp.production",
        }

        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName()) 

        SANDBOX_FUNC                    = None  
        script                          = CLI_StaticData_Script(myTest = self)     
        script.run_script(root_trace, SANDBOX_FUNC, cli_arguments_dict)


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_StaticData_CLI()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='cli_subproducts':
            T.test_cli_subproducts()

    main(_sys.argv)
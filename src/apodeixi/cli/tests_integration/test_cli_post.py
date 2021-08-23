from os import PathLike
import sys                                              as _sys


from apodeixi.testing_framework.a6i_integration_test    import ApodeixiIntegrationTest, ShutilStoreTestStack
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace


from apodeixi.cli.cli_utils                             import CLI_Utils
from apodeixi.cli.tests_integration.cli_test_skeleton   import CLI_Test_Skeleton

class Test_CLI_Post(CLI_Test_Skeleton):

    def test_cli_post_dry_run(self):
        ME                              = Test_CLI_Post
        self.setScenario("cli.post_by_file")
        self.setCurrentTestName('post_dr')
        self.selectTestDataLocation()

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName())        
        
        #POSTING_FILENAME               = self.currentTestName() + ".products.static-data.admin.a6i.xlsx" 

        PATH_OF                     = self.fullpath_of
        MASK_SANDBOX                = CLI_Utils().mask_sandbox_lambda(root_trace)

        COMMANDS                    = [
                                        ['post', '--dry-run', '--timestamp', "_CLI__1", 
                                            PATH_OF("products.static-data.admin.a6i.xlsx")],
                                        ['post', '--sandbox', self.get_sandbox, '--timestamp', "_CLI__2",
                                            PATH_OF("scoring-cycles.static-data.admin.a6i.xlsx")],
                                        ['post', '--sandbox', self.get_sandbox, '--timestamp', "_CLI__3",
                                            PATH_OF("pbf_opus.original.OPUS_big-rocks.journeys.a6i.xlsx")],
                                        ['get', 'products']
                                    ]

        self.skeleton_test( parent_trace                = root_trace,
                            cli_command_list            = COMMANDS,
                            output_cleanining_lambda    = MASK_SANDBOX)
                                                                       

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_CLI_Post()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='cli_post_dry_run':
            T.test_cli_post_dry_run()

    main(_sys.argv)
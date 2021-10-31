import sys                                              as _sys
import os                                               as _os

from apodeixi.util.a6i_error                            import FunctionalTrace
from apodeixi.util.path_utils                           import PathUtils

from apodeixi.cli.tests_integration.cli_test_skeleton   import CLI_Test_Skeleton
from apodeixi.cli.cli_utils                             import CLI_Utils

class Test_CLI_Diff(CLI_Test_Skeleton):
      
    def test_cli_diff_basic(self):
        '''
        Tests diff functionality between the lastest version of a manifest and its prior version
        '''
        self.setScenario("cli.basic_diff")
        self.setCurrentTestName('basic_diff')
        self.selectTestDataLocation()

        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName()) 

        PRODUCTS_FILE                   = 'products.static-data.admin.a6i.xlsx'
        SCORING_CYCLES_FILE             = 'scoring-cycles.static-data.admin.a6i.xlsx'
        BIG_ROCKS_FILE_V1               = 'v1.big-rocks.journeys.a6i.xlsx'
        BIG_ROCKS_FILE_V2               = 'v2.big-rocks.journeys.a6i.xlsx'
        MANIFEST_API                    = 'delivery-planning.journeys.a6i.io'
        KIND                            = 'big-rock'
        NAMESPACE                       = 'cicloquimica.production'
        NAME                            = 'modernization.fy-22.astrea.official'

        #STATIC_DATA_WORKING_DIR         = "admin/static-data"
        #PRODUCT_WORKING_DIR             = "journeys/FY 22/Astrea/Official"

        _path_of                        = self.fullpath_of

        MASK_COMBINED                   = CLI_Utils().combined_mask(root_trace, self.a6i_config)
                  
        # This will fool the CLI to treat our provisioned environment for this test as if it were the base environment
        self.overwrite_test_context(root_trace) # Overwrites self.a6i_config , the store, the test_db, etc.

        my_trace                        = root_trace.doing("Running commands")

        COMMANDS                        = [
                                            ['post',        '--timestamp', "_CLI__1", 
                                                            _path_of(PRODUCTS_FILE)],
                                            ['post',        '--timestamp', "_CLI__2", 
                                                            _path_of(SCORING_CYCLES_FILE)],
                                            ['post',            '--timestamp', "_CLI__3", 
                                                            _path_of(BIG_ROCKS_FILE_V1)],
                                            ['post',            '--timestamp', "_CLI__4", 
                                                            _path_of(BIG_ROCKS_FILE_V2)],
                                            ['diff',        MANIFEST_API,   KIND,   NAMESPACE,  NAME]
                                        ]

        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.ONLY_AT_END)



if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_CLI_Diff()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='cli_diff_basic':
            T.test_cli_diff_basic()

    main(_sys.argv)
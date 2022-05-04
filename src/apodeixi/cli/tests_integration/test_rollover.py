import sys                                              as _sys
import os                                               as _os

from apodeixi.util.a6i_error                            import FunctionalTrace
from apodeixi.util.path_utils                           import PathUtils

from apodeixi.cli.tests_integration.cli_test_skeleton   import CLI_Test_Skeleton
from apodeixi.cli.cli_utils                             import CLI_Utils

class Test_Rollover(CLI_Test_Skeleton):
      
    def test_cli_rollover_basic(self):
        '''
        Tests rollover functionality when traversing fiscal years: if there is no previous manifest for FY 23 but one
        exists from FY 22, then trying to retrieve the latest manifest in FY 23 will result in the latest one from FY 22,
        as opposed to a template-based default.
        '''
        self.setScenario("cli.rollover_basic")
        self.setCurrentTestName('rollover_basic')
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

        # Aiming to try 
        #               apo get form big-rocks.journeys.a6i cicloquimica.production modernization
        #
        # in directory for FY23:
        #                           collaboration_area/journeys/FY 23/Astrea/Official
        #
        # when FY 23 directory is empty but FY 22 directory has data

        COMMANDS                        = [
                                            ['post',        '--timestamp', "_CLI__1", 
                                                            _path_of(PRODUCTS_FILE)],
                                            ['post',        '--timestamp', "_CLI__2", 
                                                            _path_of(SCORING_CYCLES_FILE)],
                                            ['post',            '--timestamp', "_CLI__3", 
                                                            _path_of(BIG_ROCKS_FILE_V1)],
                                            ['post',            '--timestamp', "_CLI__4", 
                                                            _path_of(BIG_ROCKS_FILE_V2)],
                                            ['get',        'form', POSTING_API,  NAMESPACE,  NAME]
                                        ]

        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.ONLY_AT_END)



if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_Rollover()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='rollover_basic':
            T.test_cli_diff_basic()

    main(_sys.argv)
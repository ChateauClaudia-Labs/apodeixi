import sys                                              as _sys
import os                                               as _os

from apodeixi.util.a6i_error                            import FunctionalTrace, ApodeixiError
from apodeixi.util.path_utils                           import PathUtils

from apodeixi.cli.tests_integration.cli_test_skeleton   import CLI_Test_Skeleton
from apodeixi.cli.cli_utils                             import CLI_Utils

class Test_ForeignKeyIntegrity(CLI_Test_Skeleton):

        
    def test_milestones_referenced_big_rock_version(self):
        '''
        Tests that integrity checks exist to prevent posting a milestones manifest if it references a
        version of the big rocks that is not the latest.
        '''
        try:
            self.setScenario("foreign_key.milestones_big_rock_version")
            self.setCurrentTestName('fkey.ml_2_br')
            self.selectTestDataLocation()

            root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                                .doing("Running " + self.currentTestName()) 


            PRODUCT_FILE                    = "products.static-data.admin.a6i.xlsx"
            SCORING_CYCLE_FILE              = "scoring-cycles.static-data.admin.a6i.xlsx"
            BIG_ROCKS_v1_FILE               = "opus.v1.big-rocks.journeys.a6i.xlsx"
            BIG_ROCKS_v2_FILE               = "opus.v2.big-rocks.journeys.a6i.xlsx"
            MILESTONES_FILE                 = "opus.v1.milestone.journeys.a6i.xlsx"
            BIG_ROCKS_API                   = "big-rocks.journeys.a6i"
            MILESTONES_API                  = "milestone.journeys.a6i"
            NAMESPACE                       = "my-corp.production"
            SUB_NAMESPACE                   = "modernization"
            REL_PATH_IN_EXT_COLLABORATION   = "journeys/Dec 2020/FusionOpus/Default"


            _path_of                        = self.fullpath_of

            MASK_COMBINED                   = CLI_Utils().combined_mask(root_trace, self.a6i_config)

            # This will fool the CLI to treat our provisioned environment for this test as if it were the base environment
            self.overwrite_test_context(root_trace) # Overwrites self.a6i_config , the store, the test_db, etc.

            # For this test, we need to switch the working directory for click
            my_trace                        = root_trace.doing("Running with working directory in the collaboration area")
            store                           = self.stack().store()

            clientURL                       = store.base_environment(my_trace).clientURL(my_trace)
            working_area                    = clientURL + "/" + REL_PATH_IN_EXT_COLLABORATION
            PathUtils().create_path_if_needed(my_trace, working_area)
            _os.chdir(working_area)

            COMMANDS                        = [
                ['post',        '--timestamp', "_CLI__1", _path_of(PRODUCT_FILE)],
                ['post',        '--timestamp', "_CLI__2", _path_of(SCORING_CYCLE_FILE)],
                ['post',        '--timestamp', "_CLI__3", _path_of(BIG_ROCKS_v1_FILE)],                 # v1 of big-rocks
                ['get', 'form', '--timestamp', "_CLI__4", MILESTONES_API,   NAMESPACE, SUB_NAMESPACE],  # milestones -> big-rocks v1
                ['get', 'form', '--timestamp', "_CLI__5", BIG_ROCKS_API,    NAMESPACE, SUB_NAMESPACE], 
                ['post',        '--timestamp', "_CLI__6", _path_of(BIG_ROCKS_v2_FILE)],                 # v2 of big-rocks
                ['get', 'assertions'],
                ['post',        '--timestamp', "_CLI__7", _path_of(MILESTONES_FILE)],                   # Should trigger an error

            ]   
        
            self.skeleton_test(  parent_trace                       = my_trace,
                                        cli_command_list            = COMMANDS,
                                        output_cleanining_lambda    = MASK_COMBINED,
                                        when_to_check_environment   = CLI_Test_Skeleton.NEVER)
        except ApodeixiError as ex:
            print(ex.trace_message())
            self.assertTrue(1==2)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_ForeignKeyIntegrity()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=="milestones_referenced_big_rock_version":
            T.test_milestones_referenced_big_rock_version()

    main(_sys.argv)
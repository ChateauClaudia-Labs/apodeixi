import sys                                                              as _sys

from apodeixi.util.a6i_error                                            import FunctionalTrace

from apodeixi.cli.tests_integration.cli_test_skeleton                   import CLI_Test_Skeleton
from apodeixi.controllers.journeys.delivery_planning.tests_integration.cli_bigrocks_and_milestones_script \
                                                                        import CLI_BigRocks_and_Milestones_Script

class Test_BigRocks_and_Milestones_CLI(CLI_Test_Skeleton):

    _s                              = CLI_BigRocks_and_Milestones_Script

    cli_arguments_dict              = {
        _s.PRODUCT_FILE:                    "products.static-data.admin.a6i.xlsx",
        _s.SCORING_CYCLE_FILE:              "scoring-cycles.static-data.admin.a6i.xlsx",
        _s.BIG_ROCKS_v1_FILE:               "v1.big-rocks.journeys.a6i.xlsx",
        _s.BIG_ROCKS_v2_FILE:               "v2.big-rocks.journeys.a6i.xlsx",
        _s.BIG_ROCKS_API:                   "big-rocks.journeys.a6i",
        _s.BIG_MILESTONES_v1_FILE:          "v1.milestone.journeys.a6i.xlsx",
        _s.BIG_MILESTONES_v2_FILE:          "v2.milestone.journeys.a6i.xlsx",
        _s.BIG_MILESTONES_API:              "milestone.journeys.a6i",
        _s.REL_PATH_IN_EXT_COLLABORATION:   "journeys/March 2021/TurboTax/IOT Experiment",
        _s.NAMESPACE:                       "intuit.innovations",
        _s.SUB_NAMESPACE:                   "Experimental"
    }
       
    def test_cli_bigrocks_and_milestones(self):
        '''
        Exercises two capabilities: 1) subproduct functionality and 2) foreign key constraints
        '''
        ME                              = Test_BigRocks_and_Milestones_CLI
        self.setScenario("cli.bigrocks_&_milestones")
        self.setCurrentTestName('cli.br_ml')
        self.selectTestDataLocation()

        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName()) 

        SANDBOX_FUNC                    = None  
        script                          = CLI_BigRocks_and_Milestones_Script(myTest = self)     
        script.run_script(root_trace, SANDBOX_FUNC, ME.cli_arguments_dict)


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_BigRocks_and_Milestones_CLI()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='cli_bigrocks_and_milestones':
            T.test_cli_bigrocks_and_milestones()

    main(_sys.argv)
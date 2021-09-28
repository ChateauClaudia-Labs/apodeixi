import sys                                              as _sys

from apodeixi.util.a6i_error                            import FunctionalTrace

from apodeixi.cli.tests_integration.cli_test_skeleton   import CLI_Test_Skeleton
from apodeixi.cli.tests_integration.cli_basic_script    import CLI_Basic_Script

class Test_CLI_Post(CLI_Test_Skeleton):

    _s                              = CLI_Basic_Script
    cli_arguments_dict              = {
        _s.PRODUCT_FILE:                    "products.static-data.admin.a6i.xlsx",
        _s.SCORING_CYCLE_FILE:              "scoring-cycles.static-data.admin.a6i.xlsx",
        _s.BIG_ROCKS_v1_FILE:               "pbf_opus.original.OPUS_big-rocks.journeys.a6i.xlsx",
        _s.BIG_ROCKS_v2_FILE:               "pbf_opus.update.big-rocks.journeys.a6i.xlsx",
        _s.BIG_ROCKS_API:                   "big-rocks.journeys.a6i",
        _s.BIG_MILESTONES_v1_FILE:          "pbf_opus.v1.milestone.journeys.a6i.xlsx",
        _s.BIG_MILESTONES_v2_FILE:          "pbf_opus.v2.milestone.journeys.a6i.xlsx",
        _s.BIG_MILESTONES_API:              "milestone.journeys.a6i",
        _s.REL_PATH_IN_EXT_COLLABORATION:   "journeys/Dec 2020/FusionOpus/Default",
        _s.NAMESPACE:                       "my-corp.production",
        _s.SUB_NAMESPACE:                   "modernization"
    }
        
    def test_cli_post_dry_run(self):
        ME                              = Test_CLI_Post
        self.setScenario("cli.post_dry_run")
        self.setCurrentTestName('post_dry')
        self.selectTestDataLocation()

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName()) 

        SANDBOX_FUNC                = self.get_sandbox  
        script                      = CLI_Basic_Script(myTest = self)     
        script.run_script(root_trace, SANDBOX_FUNC, ME.cli_arguments_dict)

    def test_cli_post_live_run(self):
        ME                              = Test_CLI_Post
        self.setScenario("cli.post_live_run")
        self.setCurrentTestName('post_live')
        self.selectTestDataLocation()

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName()) 

        SANDBOX_FUNC                = None  # This ensures it is a live run, by setting sandbox to None 
        script                      = CLI_Basic_Script(myTest = self)  
        script.run_script(root_trace, SANDBOX_FUNC, ME.cli_arguments_dict)

                    


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_CLI_Post()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='cli_post_dry_run':
            T.test_cli_post_dry_run()

    main(_sys.argv)
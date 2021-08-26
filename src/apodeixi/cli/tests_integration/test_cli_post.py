import os                                               as _os
import sys                                              as _sys
from apodeixi.cli.apo_cli import namespaces

from apodeixi.knowledge_base.kb_environment             import File_KBEnv_Impl
from apodeixi.util.a6i_error                            import FunctionalTrace

from apodeixi.cli.cli_utils                             import CLI_Utils
from apodeixi.cli.tests_integration.cli_test_skeleton   import CLI_Test_Skeleton
from apodeixi.util.path_utils import PathUtils

class Test_CLI_Post(CLI_Test_Skeleton):

    def test_cli_post_dry_run(self):
        ME                              = Test_CLI_Post
        self.setScenario("cli.post_dry_run")
        self.setCurrentTestName('post_dry')
        self.selectTestDataLocation()

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName()) 

        SANDBOX_FUNC                = self.get_sandbox       
        self.run_script(root_trace, SANDBOX_FUNC)

    def test_cli_post_live_run(self):
        ME                              = Test_CLI_Post
        self.setScenario("cli.post_live_run")
        self.setCurrentTestName('post_live')
        self.selectTestDataLocation()

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName()) 

        SANDBOX_FUNC                = None  # This ensures it is a live run, by setting sandbox to None  
        self.run_script(root_trace, SANDBOX_FUNC)

    def run_script(self, parent_trace, SANDBOX_FUNC):

        PATH_OF                     = self.fullpath_of

        MASK_COMBINED               = CLI_Utils().combined_mask(parent_trace, self.a6i_config)

        # This will fool the CLI to treat our provisioned environment for this test as if it were the base environment
        self.overwrite_test_context(parent_trace) # Overwrites self.a6i_config , the store, the test_db, etc.
        

        if SANDBOX_FUNC != None:
            DRY_RUN_OPTION          = '--dry-run'
            ENVIROMENT_OPTION       = '--environment'
            ENV_CHOICE              = SANDBOX_FUNC
        else: # Case for life runs
            DRY_RUN_OPTION          = None
            ENVIROMENT_OPTION       = None
            ENV_CHOICE              = None

        COMMANDS                    = [
                                        ['post',                    DRY_RUN_OPTION,                 '--timestamp', "_CLI__1", 
                                            PATH_OF("products.static-data.admin.a6i.xlsx")],
                                        ['post',                    ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__2",
                                            PATH_OF("scoring-cycles.static-data.admin.a6i.xlsx")],
                                        ['post',                    ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__3",
                                            PATH_OF("pbf_opus.original.OPUS_big-rocks.journeys.a6i.xlsx")],
                                        ['get', 'products',         ENVIROMENT_OPTION, ENV_CHOICE],
                                        ['get', 'scoring-cycles',   ENVIROMENT_OPTION, ENV_CHOICE],
                                        ['get', 'namespaces'],
                                        #['get', 'environments'], # Can't test- environment count non-deterministic
                                        ['get', 'apis'],
                                    ]

        self.skeleton_test( parent_trace                = parent_trace,
                            cli_command_list            = COMMANDS,
                            output_cleanining_lambda    = MASK_COMBINED) #MASK_SANDBOX)

        # For the next test, we need to switch the working directory for click
        my_trace                    = parent_trace.doing("Running with working directory in the collaboration area")
        store                       = self.stack().store()

        if self.sandbox != None:
            root_dir                    = _os.path.dirname(store.base_environment(my_trace).manifestsURL(my_trace))
            envs_dir                    = root_dir + "/" + File_KBEnv_Impl.ENVS_FOLDER

            _os.chdir(envs_dir + "/" + self.sandbox + "/external-collaboration/journeys/Dec 2020/FusionOpus/Default")
        else:
            clientURL                   = store.base_environment(my_trace).clientURL(my_trace)
            _os.chdir(clientURL + "/" + "/journeys/Dec 2020/FusionOpus/Default")

        NAMESPACE                   = "my-corp.production"
        SUB_NAMESPACE               = "modernization"

        COMMANDS_2                    = [
                                        ['get', 'form',                 ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__4", 
                                            "big-rocks.journeys.a6i", NAMESPACE, SUB_NAMESPACE],
                                        ['post',                        ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__5", 
                                            PATH_OF("pbf_opus.update.big-rocks.journeys.a6i.xlsx")],
                                        ['get', 'form',                 ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__6", 
                                            "milestone.journeys.a6i", NAMESPACE, SUB_NAMESPACE],
                                        ['post',                        ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__7", 
                                            PATH_OF("pbf_opus.v1.milestone.journeys.a6i.xlsx")],
                                        ['get', 'form',                 ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__8", 
                                            "milestone.journeys.a6i", NAMESPACE, SUB_NAMESPACE],
                                        ['post',                        ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__9", 
                                            PATH_OF("pbf_opus.v2.milestone.journeys.a6i.xlsx")],
                                        ['get', 'form',                 ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__10", 
                                            "milestone.journeys.a6i", NAMESPACE, SUB_NAMESPACE],
                                        ['get', 'assertions',           ENVIROMENT_OPTION, ENV_CHOICE]
                                    
                                    ]

        self.skeleton_test( parent_trace                = parent_trace,
                            cli_command_list            = COMMANDS_2,
                            output_cleanining_lambda    = MASK_COMBINED) #MASK_SANDBOX)
                                                                       


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_CLI_Post()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='cli_post_dry_run':
            T.test_cli_post_dry_run()

    main(_sys.argv)
import os                                               as _os

from apodeixi.knowledge_base.kb_environment             import File_KBEnv_Impl

from apodeixi.cli.cli_utils                             import CLI_Utils

class CLI_Basic_Script():

    def __init__(self, myTest):
        '''
        Helper class to encapsulate a sequence of CLI operations that collectively exercise CLI logic to post,
        get forms, and get system information

        @param myTest An object whose class derives from CLI_Test_Skeleton
        '''
        self.myTest                 = myTest

    PRODUCT_FILE                    = "PRODUCT_FILE"
    SCORING_CYCLE_FILE              = "SCORING_CYCLE_FILE"
    BIG_ROCKS_v1_FILE               = "BIG_ROCKS_v1_FILE"
    BIG_ROCKS_v2_FILE               = "BIG_ROCKS_v2_FILE"
    BIG_ROCKS_API                   = "BIG_ROCKS_API"
    BIG_MILESTONES_v1_FILE          = "BIG_MILESTONES_v1_FILE"
    BIG_MILESTONES_v2_FILE          = "BIG_MILESTONES_v2_FILE"
    BIG_MILESTONES_API              = "BIG_MILESTONES_API"



    def run_script(self, parent_trace, SANDBOX_FUNC):

        PATH_OF                     = self.myTest.fullpath_of

        MASK_COMBINED               = CLI_Utils().combined_mask(parent_trace, self.myTest.a6i_config)

        _s                          = CLI_Basic_Script
        cli_arguments_dict              = {
            _s.PRODUCT_FILE:               "products.static-data.admin.a6i.xlsx",
            _s.SCORING_CYCLE_FILE:         "scoring-cycles.static-data.admin.a6i.xlsx",
            _s.BIG_ROCKS_v1_FILE:          "pbf_opus.original.OPUS_big-rocks.journeys.a6i.xlsx",
            _s.BIG_ROCKS_v2_FILE:          "pbf_opus.update.big-rocks.journeys.a6i.xlsx",
            _s.BIG_ROCKS_API:              "big-rocks.journeys.a6i",
            _s.BIG_MILESTONES_v1_FILE:     "pbf_opus.v1.milestone.journeys.a6i.xlsx",
            _s.BIG_MILESTONES_v2_FILE:     "pbf_opus.v2.milestone.journeys.a6i.xlsx",
            _s.BIG_MILESTONES_API :        "milestone.journeys.a6i",
        }
        _args                        = cli_arguments_dict

        # This will fool the CLI to treat our provisioned environment for this test as if it were the base environment
        self.myTest.overwrite_test_context(parent_trace) # Overwrites self.a6i_config , the store, the test_db, etc.
        

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
                                            PATH_OF(_args[_s.PRODUCT_FILE])],
                                        ['post',                    ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__2",
                                            PATH_OF(_args[_s.SCORING_CYCLE_FILE])],
                                        ['post',                    ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__3",
                                            PATH_OF(_args[_s.BIG_ROCKS_v1_FILE])],
                                        ['get', 'products',         ENVIROMENT_OPTION, ENV_CHOICE],
                                        ['get', 'scoring-cycles',   ENVIROMENT_OPTION, ENV_CHOICE],
                                        ['get', 'namespaces'],
                                        #['get', 'environments'], # Can't test- environment count non-deterministic
                                        ['get', 'apis'],
                                    ]

        self.myTest.skeleton_test(  parent_trace                = parent_trace,
                                    cli_command_list            = COMMANDS,
                                    output_cleanining_lambda    = MASK_COMBINED)

        # For the next test, we need to switch the working directory for click
        my_trace                    = parent_trace.doing("Running with working directory in the collaboration area")
        store                       = self.myTest.stack().store()

        if self.myTest.sandbox != None:
            root_dir                    = _os.path.dirname(store.base_environment(my_trace).manifestsURL(my_trace))
            envs_dir                    = root_dir + "/" + File_KBEnv_Impl.ENVS_FOLDER

            _os.chdir(envs_dir + "/" + self.myTest.sandbox + "/external-collaboration/journeys/Dec 2020/FusionOpus/Default")
        else:
            clientURL                   = store.base_environment(my_trace).clientURL(my_trace)
            _os.chdir(clientURL + "/" + "/journeys/Dec 2020/FusionOpus/Default")

        NAMESPACE                   = "my-corp.production"
        SUB_NAMESPACE               = "modernization"

        COMMANDS_2                    = [
                                        ['get', 'form',                 ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__4", 
                                            _args[_s.BIG_ROCKS_API], NAMESPACE, SUB_NAMESPACE],
                                        ['post',                        ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__5", 
                                            PATH_OF(_args[_s.BIG_ROCKS_v2_FILE])],
                                        ['get', 'form',                 ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__6", 
                                            _args[_s.BIG_MILESTONES_API], NAMESPACE, SUB_NAMESPACE],
                                        ['post',                        ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__7", 
                                            PATH_OF(_args[_s.BIG_MILESTONES_v1_FILE])],
                                        ['get', 'form',                 ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__8", 
                                            _args[_s.BIG_MILESTONES_API], NAMESPACE, SUB_NAMESPACE],
                                        ['post',                        ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__9", 
                                            PATH_OF(_args[_s.BIG_MILESTONES_v2_FILE)],
                                        ['get', 'form',                 ENVIROMENT_OPTION, ENV_CHOICE,  '--timestamp', "_CLI__10", 
                                            _args[_s.BIG_MILESTONES_API], NAMESPACE, SUB_NAMESPACE],
                                        ['get', 'assertions',           ENVIROMENT_OPTION, ENV_CHOICE]
                                    
                                    ]

        self.myTest.skeleton_test(  parent_trace                = parent_trace,
                                    cli_command_list            = COMMANDS_2,
                                    output_cleanining_lambda    = MASK_COMBINED)
                                                   
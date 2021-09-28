import os                                               as _os

from apodeixi.knowledge_base.kb_environment             import File_KBEnv_Impl

from apodeixi.cli.cli_utils                             import CLI_Utils

from apodeixi.util.path_utils                           import PathUtils

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
    REL_PATH_IN_EXT_COLLABORATION   = "REL_PATH_IN_EXT_COLLABORATION"
    NAMESPACE                       = "NAMESPACE",
    SUB_NAMESPACE                   = "SUB_NAMESPACE"


    def run_script(self, parent_trace, SANDBOX_FUNC, cli_arguments_dict):

        _path_of                     = self.myTest.fullpath_of

        MASK_COMBINED               = CLI_Utils().combined_mask(parent_trace, self.myTest.a6i_config)

        _s                          = CLI_Basic_Script
        _args                       = cli_arguments_dict

        # This will fool the CLI to treat our provisioned environment for this test as if it were the base environment
        self.myTest.overwrite_test_context(parent_trace) # Overwrites self.a6i_config , the store, the test_db, etc.
        

        if SANDBOX_FUNC != None:
            __dry_run               = '--dry-run'
            __environment           = '--environment'
            ENV_CHOICE              = SANDBOX_FUNC
        else: # Case for life runs
            __dry_run               = None
            __environment           = None
            ENV_CHOICE              = None

        COMMANDS                    = [
                                        ['post',                    __dry_run,                 '--timestamp', "_CLI__1", 
                                            _path_of(_args[_s.PRODUCT_FILE])],
                                        ['post',                    __environment, ENV_CHOICE,  '--timestamp', "_CLI__2",
                                            _path_of(_args[_s.SCORING_CYCLE_FILE])],
                                        ['post',                    __environment, ENV_CHOICE,  '--timestamp', "_CLI__3",
                                            _path_of(_args[_s.BIG_ROCKS_v1_FILE])],
                                        ['get', 'products',         __environment, ENV_CHOICE],
                                        ['get', 'scoring-cycles',   __environment, ENV_CHOICE],
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

            working_dir                 = envs_dir + "/" + self.myTest.sandbox + "/external-collaboration/" \
                                            + _args[_s.REL_PATH_IN_EXT_COLLABORATION]
        else:
            clientURL                   = store.base_environment(my_trace).clientURL(my_trace)
            working_dir                 = clientURL + "/" + _args[_s.REL_PATH_IN_EXT_COLLABORATION]

        PathUtils().create_path_if_needed(parent_trace, working_dir)
        _os.chdir(working_dir)

        COMMANDS_2                    = [
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__4", 
                                            _args[_s.BIG_ROCKS_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        ['post',                        __environment, ENV_CHOICE,  '--timestamp', "_CLI__5", 
                                            _path_of(_args[_s.BIG_ROCKS_v2_FILE])],
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__6", 
                                            _args[_s.BIG_MILESTONES_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        ['post',                        __environment, ENV_CHOICE,  '--timestamp', "_CLI__7", 
                                            _path_of(_args[_s.BIG_MILESTONES_v1_FILE])],
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__8", 
                                            _args[_s.BIG_MILESTONES_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        ['post',                        __environment, ENV_CHOICE,  '--timestamp', "_CLI__9", 
                                            _path_of(_args[_s.BIG_MILESTONES_v2_FILE])],
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__10", 
                                            _args[_s.BIG_MILESTONES_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        ['get', 'assertions',           __environment, ENV_CHOICE]
                                    
                                    ]

        self.myTest.skeleton_test(  parent_trace                = parent_trace,
                                    cli_command_list            = COMMANDS_2,
                                    output_cleanining_lambda    = MASK_COMBINED)
                                                   
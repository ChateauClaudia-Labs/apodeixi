import os                                               as _os

from apodeixi.knowledge_base.kb_environment             import File_KBEnv_Impl

from apodeixi.cli.cli_utils                             import CLI_Utils
from apodeixi.cli.tests_integration.cli_test_skeleton   import CLI_Test_Skeleton

from apodeixi.util.path_utils                           import PathUtils

class CLI_BigRocks_and_Milestones_Script():

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

        _s                          = CLI_BigRocks_and_Milestones_Script
        _args                       = cli_arguments_dict

        # This will fool the CLI to treat our provisioned environment for this test as if it were the base environment
        self.myTest.overwrite_test_context(parent_trace) # Overwrites self.a6i_config , the store, the test_db, etc.
        
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

        if SANDBOX_FUNC != None:
            __dry_run               = '--dry-run'
            __environment           = '--environment'
            ENV_CHOICE              = SANDBOX_FUNC
        else: # Case for life runs
            __dry_run               = None
            __environment           = None
            ENV_CHOICE              = None

        COMMANDS_1                  = [
                                        # Initialize static data
                                        ['post',                    __dry_run,                 '--timestamp', "_CLI__1", 
                                            _path_of(_args[_s.PRODUCT_FILE])],
                                        ['post',                    __environment, ENV_CHOICE,  '--timestamp', "_CLI__2",
                                            _path_of(_args[_s.SCORING_CYCLE_FILE])],
                                        # Create big rocks v1
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__3", 
                                            _args[_s.BIG_ROCKS_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        ['post',                    __environment, ENV_CHOICE,  '--timestamp', "_CLI__4",
                                            _path_of(_args[_s.BIG_ROCKS_v1_FILE])],
                                        # Create milestones v1
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__5", 
                                            _args[_s.BIG_MILESTONES_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        ['post',                        __environment, ENV_CHOICE,  '--timestamp', "_CLI__6", 
                                            _path_of(_args[_s.BIG_MILESTONES_v1_FILE])],

        ]

        self.myTest.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_1,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.NEVER)

        # Check that manifest is as expected
        NAME                    = "experimental.march-2021.turbotax.iot-experiment"
        NAMESPACE               = "intuit.innovations"
        self.myTest.check_manifest(my_trace, 'delivery-planning.journeys.a6i.io', NAMESPACE, NAME, 'big-rock')
        self.myTest.check_manifest(my_trace, 'delivery-planning.journeys.a6i.io', NAMESPACE, NAME, 'big-rock-estimate')
        self.myTest.check_manifest(my_trace, 'delivery-planning.journeys.a6i.io', NAMESPACE, NAME, 'modernization-milestone')

        COMMANDS_2                  = [
                                        # First try to update big rocks v2 - should fail due to foreign key constraints
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__7", 
                                            _args[_s.BIG_ROCKS_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        ['post',                        __environment, ENV_CHOICE,  '--timestamp', "_CLI__8", 
                                            _path_of(_args[_s.BIG_ROCKS_v2_FILE])],
                                        # Update milestones v2 - should remove the reference that caused big rocks v2 to fail
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__9", 
                                            _args[_s.BIG_MILESTONES_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        ['post',                        __environment, ENV_CHOICE,  '--timestamp', "_CLI__10", 
                                            _path_of(_args[_s.BIG_MILESTONES_v2_FILE])],
                                        # Second try to update big rocks v2 - should work now that user removed references in
                                        # milestones v2 to the rocks that were removed in v2
                                        ['post',                        __environment, ENV_CHOICE,  '--timestamp', "_CLI__11", 
                                            _path_of(_args[_s.BIG_ROCKS_v2_FILE])],
        ]

        self.myTest.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_2,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.NEVER)

        # Check that manifest is as expected
        self.myTest.check_manifest(my_trace, 'delivery-planning.journeys.a6i.io', NAMESPACE, NAME, 'big-rock')
        self.myTest.check_manifest(my_trace, 'delivery-planning.journeys.a6i.io', NAMESPACE, NAME, 'big-rock-estimate')
        self.myTest.check_manifest(my_trace, 'delivery-planning.journeys.a6i.io', NAMESPACE, NAME, 'modernization-milestone')

        COMMANDS_3                  = [
                                        # Get final forms
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__12", 
                                            _args[_s.BIG_ROCKS_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__13", 
                                            _args[_s.BIG_MILESTONES_API], _args[_s.NAMESPACE], _args[_s.SUB_NAMESPACE]],
                                        # Summarize assertions created
                                        ['get', 'assertions',           __environment, ENV_CHOICE]
                                    
                                    ]

        self.myTest.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_3,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.ONLY_AT_END)
                                                   
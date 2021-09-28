import os                                               as _os

from apodeixi.knowledge_base.kb_environment             import File_KBEnv_Impl

from apodeixi.cli.tests_integration.cli_test_skeleton   import CLI_Test_Skeleton
from apodeixi.cli.cli_utils                             import CLI_Utils

from apodeixi.util.path_utils                           import PathUtils

class CLI_StaticData_Script():

    def __init__(self, myTest):
        '''
        Helper class to encapsulate a sequence of CLI operations that collectively exercise CLI logic to post,
        get forms, and get system information for static data

        @param myTest An object whose class derives from CLI_Test_Skeleton
        '''
        self.myTest                 = myTest

    STATIC_DATA_v1_FILE             = "STATIC_DATA_v1_FILE"
    STATIC_DATA_v2_FILE             = "STATIC_DATA_v2_FILE"
    STATIC_DATA_API                 = "STATIC_DATA_API"


    REL_PATH_IN_EXT_COLLABORATION   = "REL_PATH_IN_EXT_COLLABORATION"
    NAMESPACE                       = "NAMESPACE",

    def run_script(self, parent_trace, SANDBOX_FUNC, cli_arguments_dict):

        _path_of                     = self.myTest.fullpath_of

        MASK_COMBINED               = CLI_Utils().combined_mask(parent_trace, self.myTest.a6i_config)

        _s                          = CLI_StaticData_Script
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
        COMMANDS                    = [
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__1", 
                                            _args[_s.STATIC_DATA_API], _args[_s.NAMESPACE]],            
                                        ['post',                    __dry_run,                      '--timestamp', "_CLI__2", 
                                            _path_of(_args[_s.STATIC_DATA_v1_FILE])],
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__3", 
                                            _args[_s.STATIC_DATA_API], _args[_s.NAMESPACE]], 
                                        ['post',                    __environment, ENV_CHOICE,      '--timestamp', "_CLI__4",
                                            _path_of(_args[_s.STATIC_DATA_v2_FILE])],
                                        ['get', 'form',                 __environment, ENV_CHOICE,  '--timestamp', "_CLI__5", 
                                            _args[_s.STATIC_DATA_API], _args[_s.NAMESPACE]], 

                                    ]

        self.myTest.skeleton_test(  parent_trace                = parent_trace,
                                    cli_command_list            = COMMANDS,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.ONLY_AT_END)





                                                   
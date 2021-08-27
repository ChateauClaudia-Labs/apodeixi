import os                                               as _os 
import yaml                                             as _yaml

from apodeixi.cli.cli_utils import CLI_Utils
from click.testing                                      import CliRunner

from apodeixi.cli.apo_cli                               import apo_cli
from apodeixi.testing_framework.a6i_integration_test    import ShutilStoreTestStack, ApodeixiIntegrationTest
from apodeixi.util.a6i_error                            import FunctionalTrace, ApodeixiError
from apodeixi.util.apodeixi_config                      import ApodeixiConfig

'''
Abstract class intended as parent for concrete test cases test the Apodeixi CLI
'''
class CLI_Test_Skeleton(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()

        # CLI scenario tests are "realistic", so for them we want to enforce referential integrity.
        self.a6i_config.enforce_referential_integrity   = True

        # CLI tests differ from other integration tests in that we don't care (or can) deterministically
        # predict the size of log files.
        # Reason:
        # CLI tests don't mask contents of log files, so when we display environments, the number of bytes
        # appearing in test output for such files becomes dependent on the loation of the test DB.
        # Upshot:
        # So to ensure determinism, for CLI tests overwrite the parent's value.
        self.ignore_log_files_byte_size                 = True

        self.sandbox               = None # Will be set in self.skeleton_test

        self.provisioned_env_name = None # This will be set in self.skeleton_test the first time it is caleld

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Selecting stack for test case")
        
        # Commented as now it should happen after overwrite_a6i_config_director  .. self.selectStack(root_trace) 

    def overwrite_test_context(self, parent_trace):
        '''
        This is a "trick" method needed so that CLI invocations run in the environment isolated for this test case (or
        its children), as opposed to on the base environment.

        It accomplishes this by "fooling" the CLI into thinking that "base environment" is actually the environment
        isolated for this test case.

        It does so by overwriting the value of the APODEIXI_CONFIG_DIRECTORY environment variable
        but what is tricky is:

        * By the time this method is called, this class no longer needs the APODEIXI_CONFIG_DIRECTORY environment
          variable, since it was used in super().setUp() to initialize self.a6i_config and other properties, and
          that is as it should be. 

        * Therefore, the modification in this method to APODEIXI_CONFIG_DIRECTORY is not going to impact this
          test object. Instead, it will impact other objects that use it. There is no such object in Apodeixi itself,
          but there is one in the CLI: the KB_Session class.

        * The intent is then for the KB_Session class to initialize it's notion of self.a6i_config differently, so
          that it is "fooled" into thinking that the "base environment" is this test cases's isolated environment.

        * Each time the CLI is invoked, it constructs a KB_Session to initialiaze the KnowledgeBaseStore. Thus
          the CLI will be using a store pointing to this test case's isolated environment. This is different than
          for non-CLI tests, for whom the store points to the test knowledge base common to the Apodeixi test suite.
        '''
        # Before changing context, create the environment for this test, which will later become the 
        # "fake base environment" when we switch context. But this uses the "original" store, so must be done
        # before we switch context, so we must select the stack here (and later we re-select it when
        # switching context)
        self.selectStack(parent_trace)
        self.provisionIsolatedEnvironment(parent_trace)

        # Remember original config before it is overwritten when we change context
        original_a6i_config                         = self.a6i_config

        # In case it is ever needed, remember this tests suite's value for the environment variable
        self.config_directory_for_this_test_object  = _os.environ.get('APODEIXI_CONFIG_DIRECTORY')

        # OK, we start the context switch here.
        # For this test case, we want the CLI to use a config file that is in the input folder
        _os.environ['APODEIXI_CONFIG_DIRECTORY']    = self.input_data + "/" + self.scenario() 

        # Now overwrite parent's notion of self.a6i_config and of the self.test_config_dict
        self.a6i_config                             = ApodeixiConfig(parent_trace)
        self.selectStack(parent_trace)          # Re-creates the store for this test with the "fake" base environment

        # Set again the location of the test directory as per the original a6i config. We need it to mask non-deterministic
        # paths
        self.a6i_config.test_db_dir                 = original_a6i_config.test_db_dir


        # Lastly, we need to 

        # Next time an environment is provisioned for this test, use this overwritten config for the name of the folder           
        with open(self.input_data + "/" + self.scenario() + '/test_config.yaml', 'r', encoding="utf8") as file:
            self.test_config_dict                   = _yaml.load(file, Loader=_yaml.FullLoader)

    def selectStack(self, parent_trace):
        '''
        Called as part of setting up each integration test case. It chooses and provisions the stack that should
        be used by this test case.
        '''
        self._stack                 = ShutilStoreTestStack(parent_trace, self.a6i_config)

    def get_sandbox(self):
        return self.sandbox

    def next_cli_output(self, description=None):
        '''
        Returns a string that can be used as the output name for test output consisting of what the
        Apodeixi CLI outputs to the end user
        '''
        return self.next_output_name(output_type="cli_output", description=description)

    def fullpath_of(self, posting_filename):
        '''
        Returns a string, corresponding to the full path from which `posting_filename` is expected
        to be found
        '''
        return self.input_data + "/" + self.scenario() + "/" + posting_filename

    def skeleton_test(self, parent_trace, cli_command_list, output_cleanining_lambda):

        try:
            my_trace                            = self.trace_environment(parent_trace, "Isolating test case")
            if self.provisioned_env_name == None:
                # This is the second time we provision the isolated environment, but now with a different context, i.e.,
                # different self.a6i_config and different self.test_config_dict than the first time we provisioned
                # an isolated environment, which was in self.setUp. See comments there. The environment provisioned
                # here is a child of the one configured in self.setUp, and is fo
                self.provisionIsolatedEnvironment(my_trace)
                self.check_environment_contents(my_trace)
                self.provisioned_env_name       = self.stack().store().current_environment(my_trace).name(my_trace)
            else:
                self.stack().store().activate(my_trace, self.provisioned_env_name)

            my_trace                            = self.trace_environment(parent_trace, "Invoking " 
                                                                                    + str(len(cli_command_list)) 
                                                                                    + " commands")
            if True:
                runner = CliRunner()
                for raw_command_argv in cli_command_list:
                    # The raw_command_arv might include some lambdas that need to be evaluated not in order to
                    # determine the real argv to pass to the CLI. The reason there might be lambdas is that some
                    # parameters for some commands can only be determined after earlier commands are run, so they
                    # aren't known when the command list was defined, and only now that we have run prior commands
                    # can it be determined.
                    # Example: 
                    #       The sandbox to use, if flag "--sandbox" is on. That can only be known after 
                    # self.sandbox is set, which happens when the first command runs.
                    def _unraw_param(param):
                        if callable(param):
                            return param()
                        else:
                            return param

                    # Note: two operations are being done here:
                    # 
                    # 1) Replacing a "delayed parameter": a parameter that couldn't be given when the caller's code was
                    #   written, but can at runtime, so the "delayed parameter" is a callable that, if called, would return
                    #   the actual parameter to use. Example: the sandbox parameter, which is determined in the first
                    #   post of the script and must be passed to all subsequent post commands so they continue the work
                    #   in a common sandbox.
                    # 2) Filtering out nulls. That is a trick to enable the caller, for example, to use the same script
                    #   for both dry runs and live runs. All the caller has to do is set the "--sandbox <sandbox>" to a
                    #   value when using the script with a sandbox, and to None when doing it live.
                    command_argv                = [_unraw_param(param) for param in raw_command_argv if param != None]


                    loop_trace                  = self.trace_environment(my_trace, 
                                                                            "Executing '" + " ".join(command_argv) + "'")
                    result                      = runner.invoke(apo_cli, command_argv)
                    assert result.exit_code == 0

                    sandbox                     = CLI_Utils().infer_sandbox_name(loop_trace, result.output)
                    if sandbox != None:
                        # We only overwrite self.sandbox if this particular command chose a sandbox. Otherwise
                        # we retain whatever self.sandbox was set by prior commands. This is important since some commands
                        # don't have a --sandbox option (Example: get namespaces), but that does not mean that
                        # our intention is to switch out of the sandbox and into the parent environment.
                        self.sandbox            = sandbox

                    command_flags               = [token for token in command_argv if token.startswith("--")]
                    if command_argv[0] in ["post"]:
                        argv_without_arguments      = command_argv[:1]
                    elif command_argv[0] in ["get"]:
                        argv_without_arguments      = command_argv[:2]
                    else:
                        raise ApodeixiError(my_trace, "Command not recognized: '" + str(command_argv[0]) + "'")

                    argv_without_arguments.extend(command_flags) # Like post --dry-run

                    # Once we are done building it, command_without_flag_params will be something like 
                    # 
                    #   => post --dry-run products.static-data.admin.a6i.xlsx
                    #
                    # or
                    # 
                    #   => post --sandbox products.static-data.admin.a6i.xlsx
                    #
                    # hence it will be suitable for inclusion in deterministic output. For example, we remove
                    # timestamp-sensitive sandbox names (if any) and also the full path for the posted file.
                    command_without_flag_params = " ".join(argv_without_arguments)
                    if command_argv[0] in ["post"] or command_argv[:2] in [["get", "form"]]: 
                        # These are commands with a unique argument. Other commands lack it
                        path_posted                 = command_argv[-1]
                        unique_argument             = _os.path.split(path_posted)[1]
                        command_without_flag_params += " " + unique_argument 

                    output_to_display           = "=> " + command_without_flag_params + "\n\n"
                    
                    if output_cleanining_lambda==None:
                        output_to_display       += result.output
                    else:
                        output_to_display       += output_cleanining_lambda(result.output)

                    self.check_cli_output(  parent_trace        = loop_trace, 
                                            cli_output          = output_to_display, 
                                            cli_command         = " ".join(argv_without_arguments) # Like post --dry-run
                                            )
                    if self.sandbox != None:
                        # In this case, the CLI is not running in this test's provisioned environment, but in
                        # a subenvironment that the CLI itself created (the sandbox), a child of the base environment.
                        # Since we want to display the contents of the environment in which the CLI ran, 
                        # we need to temporarily switch from our test environment to the sandbox, and then revert
                        # 
                        provisioned_env_name    = self.stack().store().current_environment(loop_trace).name(loop_trace)
                        self.stack().store().activate(loop_trace, self.sandbox)
                        self.check_environment_contents(loop_trace)
                        # Now restore environment to what we are using in the test
                        self.stack().store().activate(loop_trace, provisioned_env_name)
                    else:
                        # In this case, the CLI is running in this store's base environment, so temporarily switch
                        # to the base environment by deactivating the current "Test Runner" environment
                        provisioned_env_name    = self.stack().store().current_environment(loop_trace).name(loop_trace)
                        self.stack().store().deactivate(loop_trace) # This puts us in the base environment
                        self.check_environment_contents(loop_trace)
                        # Now restore environment to what we are using in the test
                        self.stack().store().activate(loop_trace, provisioned_env_name)

            my_trace                = self.trace_environment(parent_trace, "Deactivating environment")
            self.stack().store().deactivate(my_trace)

        except ApodeixiError as ex:
            print(ex.trace_message()) 
            self.assertTrue(1==2)

    def check_cli_output(self, parent_trace, cli_output, cli_command):
        self._compare_to_expected_txt(  parent_trace        = parent_trace,
                                        output_txt          = cli_output,
                                        test_output_name    = self.next_cli_output(cli_command), 
                                        save_output_txt     = True)
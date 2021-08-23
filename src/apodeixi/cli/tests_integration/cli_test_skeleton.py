import os                                               as _os 

from apodeixi.cli.cli_utils import CLI_Utils
from click.testing                                      import CliRunner

from apodeixi.cli.apo_cli                               import apo_cli
from apodeixi.testing_framework.a6i_integration_test    import ShutilStoreTestStack, ApodeixiIntegrationTest
from apodeixi.util.a6i_error                            import FunctionalTrace, ApodeixiError

'''
Abstract class intended as parent for concrete test cases test the Apodeixi CLI
'''
class CLI_Test_Skeleton(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()

        # CLI scenario tests are "realistic", so for them we want to enforce referential integrity.
        self.a6i_config.enforce_referential_integrity = True

        self.sandbox               = None # Will be set in self.skeleton_test

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Selecting stack for test case")
        self.selectStack(root_trace) 

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
            self.provisionIsolatedEnvironment(my_trace)
            self.check_environment_contents(my_trace)

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
                    command_argv                = [_unraw_param(param) for param in raw_command_argv]

                    loop_trace                  = self.trace_environment(my_trace, 
                                                                            "Executing '" + " ".join(command_argv) + "'")
                    result                      = runner.invoke(apo_cli, command_argv)
                    assert result.exit_code == 0

                    self.sandbox                = CLI_Utils().infer_sandbox_name(loop_trace, result.output)

                    command_flags               = [token for token in command_argv if token.startswith("--")]
                    argv_without_arguments      = command_argv[:1]
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
                    path_posted                 = command_argv[-1]
                    filename_posted             = _os.path.split(path_posted)[1]
                    command_without_flag_params += " " + filename_posted 

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
                        provisioned_env_name    = self.stack().store().current_environment(loop_trace).name(loop_trace)
                        self.stack().store().activate(loop_trace, self.sandbox)
                        self.check_environment_contents(loop_trace)
                        # Now restore environment to what we are using in the test
                        self.stack().store().activate(loop_trace, provisioned_env_name)
                    else:
                        # In this case, the CLI is running in this test's provisioned environment, so display that
                        self.check_environment_contents(loop_trace)

            my_trace                = self.trace_environment(parent_trace, "Deactivating environment")
            self.stack().store().deactivate(my_trace)
            self.check_environment_contents(my_trace) 

        except ApodeixiError as ex:
            print(ex.trace_message()) 
            self.assertTrue(1==2)

    def check_cli_output(self, parent_trace, cli_output, cli_command):
        self._compare_to_expected_txt(  parent_trace        = parent_trace,
                                        output_txt          = cli_output,
                                        test_output_name    = self.next_cli_output(cli_command), 
                                        save_output_txt     = True)
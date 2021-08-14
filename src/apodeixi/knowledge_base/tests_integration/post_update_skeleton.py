import sys                                                              as _sys

from apodeixi.testing_framework.a6i_integration_test                    import ShutilStoreTestStack, ApodeixiIntegrationTest
from apodeixi.util.a6i_error                                            import ApodeixiError, FunctionalTrace

from apodeixi.controllers.util.skeleton_controller                      import SkeletonController

from apodeixi.knowledge_base.tests_integration.post_update_flow_script  import Post_and_Update_Script

'''
Abstract class intended as parent for concrete test cases that use the `Post_and_Update_Script` on a particular
posting API
'''
class Post_and_Update_Skeleton(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()

        # Flow scenario tests are "realistic", so for them we want to enforce referential integrity.
        self.a6i_config.enforce_referential_integrity = True

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Selecting stack for test case")
        self.selectStack(root_trace) 

    def selectStack(self, parent_trace):
        '''
        Called as part of setting up each integration test case. It chooses and provisions the stack that should
        be used by this test case.
        '''
        self._stack                 = ShutilStoreTestStack(parent_trace, self.a6i_config)


    def run_script(self, scenario, test_name, excel_relative_path, excel_file, excel_sheet, 
                                nb_manifests, from_nothing, namespace, subnamespace, posting_api, setup_dependencies):

        self.setScenario(scenario)
        self.setCurrentTestName(test_name) # big rock burnout for product Opus
        self.selectTestDataLocation()

        script                      = Post_and_Update_Script(self)

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Running script for " + self.scenario())

        script._run_basic_flow( parent_trace                =root_trace,
                                from_nothing                = from_nothing,
                                namespace                   = namespace,
                                subnamespace                = subnamespace,
                                posting_api                 = posting_api,
                                excel_relative_path         = excel_relative_path,
                                excel_file                  = excel_file,
                                excel_sheet                 = excel_sheet,
                                nb_manifests_expected       = nb_manifests,
                                generated_form_worksheet    = SkeletonController.GENERATED_FORM_WORKSHEET,
                                setup_dependencies          = setup_dependencies)

    def setup_static_data(self, parent_trace):
        '''
        Sets up the static data that is generally needed by flow tests
        '''
        EXCEL_FILES                 = [ "products.static-data.admin.a6i.xlsx",
                                        "scoring-cycles.static-data.admin.a6i.xlsx"]

        my_trace                    = parent_trace.doing("Setting up static data")

        for file in EXCEL_FILES:
            loop_trace              = my_trace.doing("Posting file '" + str(file) + "'")
            posting_path                = self.getInputDataFolder(loop_trace)  + "/" + self.scenario() + "/" + file
            response, log_txt           = self.stack().kb().postByFile( parent_trace                = loop_trace, 
                                                                        path_of_file_being_posted   = posting_path, 
                                                                        excel_sheet                 = "Posting Label")

    def setup_reference_data(self, parent_trace):
        '''
        Sets up any reference data (such as other manifests) that are assumed as pre-conditions by this test. 
        '''
        if self.scenario() == "basic_posting_flows.milestones":
            EXCEL_FILE                      = "for_mls.big-rocks.journeys.a6i.xlsx"
            EXCEL_FOLDER                    = self.getInputDataFolder(parent_trace) + "/" + self.scenario()
            my_trace                        = self.trace_environment(parent_trace, "Creating big-rocks dependency")
            if True:
                clientURL                   = self.stack().store().current_environment(my_trace).clientURL(my_trace)
                posting_path                = EXCEL_FOLDER + "/" + EXCEL_FILE
                response, log_txt           = self.stack().kb().postByFile( parent_trace                = my_trace, 
                                                                            path_of_file_being_posted   = posting_path, 
                                                                            excel_sheet                 = "Posting Label")
                self.check_environment_contents(parent_trace = my_trace )           
        else:
            return # No other scenarios have dependencies to pre-populate


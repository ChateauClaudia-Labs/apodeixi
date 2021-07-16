import sys                                              as _sys

from apodeixi.testing_framework.a6i_integration_test    import ApodeixiIntegrationTest, ShutilStoreTestStack
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace
from apodeixi.util.path_utils              			    import FolderHierarchy

from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase
from apodeixi.knowledge_base.kb_environment             import KB_Environment_Config

class Test_EnvironmentLIfecycle(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()
        root_trace                  = FunctionalTrace(None).doing("Selecting stack for test case")
        self.selectStack(root_trace) 

    def selectStack(self, parent_trace):
        '''
        Called as part of setting up each integration test case. It chooses and provisions the stack that should
        be used by this test case.
        '''
        self._stack                 = ShutilStoreTestStack(parent_trace, self._config)


    def test_play_in_sandbox(self):

        self.setScenario("environment_lifecycle")
        self.setCurrentTestName('play_in_sandbox')

        POSTING_FULLPATH            = self.input_data + "/" + self.currentTestName() + ".big-rocks.journeys.a6i.xlsx" 
        POSTING_LABEL_SHEET         = "Sheet1"
                    
        all_manifests_dicts         = []

        try:
            root_trace              = FunctionalTrace(parent_trace=None).doing("Running " + self.currentTestName())

            my_trace                = self.trace_environment(root_trace, "Isolating test case")
            self.provisionIsolatedEnvironment(my_trace)
            self.check_environment_contents(my_trace)

            my_trace                = self.trace_environment(root_trace, "Doing postByFile")
            response, log_txt       = self.stack().kb().postByFile( parent_trace                = my_trace, 
                                                                    path_of_file_being_posted   = POSTING_FULLPATH,
                                                                    excel_sheet                 = POSTING_LABEL_SHEET)
            self.check_environment_contents(my_trace)

            my_trace                = self.trace_environment(root_trace, "Deactivating environment")
            self.stack().store().deactivate(my_trace)
            self.check_environment_contents(my_trace) 

        except ApodeixiError as ex:
            print(ex.trace_message()) 
            self.assertTrue(1==2)
           
                                                                       

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_EnvironmentLIfecycle()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='play_in_sandbox':
            T.test_play_in_sandbox()

    main(_sys.argv)
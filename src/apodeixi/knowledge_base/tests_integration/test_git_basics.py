import sys                                              as _sys

from apodeixi.testing_framework.a6i_integration_test    import ApodeixiIntegrationTest, GITStoreTestStack
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase
from apodeixi.knowledge_base.kb_environment             import KB_Environment_Config
from apodeixi.knowledge_base.git_kb_store               import GIT_KBStore_Impl

class Test_GIT_Basics(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()
        root_trace                  = FunctionalTrace(None).doing("Selecting stack for test case")
        self.selectStack(root_trace) 

    def selectStack(self, parent_trace):
        '''
        Called as part of setting up each integration test case. It chooses and provisions the stack that should
        be used by this test case.
        '''
        self._stack                 = GITStoreTestStack(parent_trace, self.a6i_config)

    def test_persist_manifest(self):

        TEST_CASE                       = 'persist_manifest'

        ENVIRONMENT_NAME                = TEST_CASE + "_ENV"

        self.setScenario("persist_manifest")

        self.assertTrue(1 == 2) # TODO: finish the test

        #POSTING_FULLPATH                = self.input_data + "/" + TEST_CASE + "_big-rocks.journeys.a6i.xlsx" 
        #POSTING_LABEL_SHEET             = "Sheet1"
                    
        all_manifests_dicts     = []

        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Running " + TEST_CASE)


        except ApodeixiError as ex:
            print(ex.trace_message()) 
            self.assertTrue(1==2)
           

                                                                       

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_GIT_Basics()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='persist_manifest':
            T.test_create_environment()

    main(_sys.argv)
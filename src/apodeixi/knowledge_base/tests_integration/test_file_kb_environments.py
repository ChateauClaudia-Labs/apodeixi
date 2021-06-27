import sys                                              as _sys

from apodeixi.testing_framework.a6i_integration_test    import ApodeixiIntegrationTest
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase

class Test_File_KB_Environments(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()

    def test_create_environment(self):

        TEST_CASE                       = 'test_create_environment'

        ENVIRONMENT_NAME                = TEST_CASE + "_ENV"


        all_manifests_dicts     = []

        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Running " + TEST_CASE)
            
            my_trace            = root_trace.doing("Creating an enfironment", 
                                                    data={  'environment_name'    : ENVIRONMENT_NAME},
                                                    origination = { 'signaled_from' : __file__,
                                                                    'concrete class': str(self.__class__.__name__)})

            self.store.current_environment(my_trace).addSubEnvironment(my_trace, ENVIRONMENT_NAME)

            my_trace            = root_trace.doing("Activiting environment '" + ENVIRONMENT_NAME + "'")
            self.store.activate(parent_trace = my_trace, environment_name = ENVIRONMENT_NAME)

            my_trace            = root_trace.doing("Deactiviting environment '" + ENVIRONMENT_NAME + "'")
            self.store.deactivate(parent_trace = my_trace)

        except ApodeixiError as ex:
            print(ex.trace_message()) 

        # TODO - Fail until we complete the test
        self.assertTrue(1==2)                 

                                                                       

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_File_KB_Environments()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='create_environment':
            T.test_create_environment()

    main(_sys.argv)
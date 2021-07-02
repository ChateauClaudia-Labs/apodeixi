import sys                                              as _sys

from apodeixi.testing_framework.a6i_integration_test    import ApodeixiIntegrationTest
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace
from apodeixi.util.path_utils              			    import FolderHierarchy

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

            my_trace            = root_trace.doing("Removing previously created environment, if any",
                                                        data = {'environment name': ENVIRONMENT_NAME})
            stat                = self.store.removeEnvironment(parent_trace = my_trace, name = ENVIRONMENT_NAME)
            
            my_trace            = root_trace.doing("Creating an environment", 
                                                    data={  'environment_name'    : ENVIRONMENT_NAME},
                                                    origination = { 'signaled_from' : __file__,
                                                                    'concrete class': str(self.__class__.__name__)})

            self.store.current_environment(my_trace).addSubEnvironment(my_trace, ENVIRONMENT_NAME)

            my_trace            = root_trace.doing("Activiting environment '" + ENVIRONMENT_NAME + "'")
            self.store.activate(parent_trace = my_trace, environment_name = ENVIRONMENT_NAME)

            hierarchy_env       = self.store.current_environment(my_trace).folder_hierarchy(root_trace)
            # TODO: add some data to environment, maybe calling a controller on some posting

            self._compare_to_expected_yaml( output_dict         = hierarchy_env.to_dict(),
                                            test_case_name      = ENVIRONMENT_NAME, 
                                            save_output_dict    = True)
            my_trace            = root_trace.doing("Deactiviting environment '" + ENVIRONMENT_NAME + "'")
            self.store.deactivate(parent_trace = my_trace)

            hierarchy_base      = self.store.current_environment(my_trace).folder_hierarchy(root_trace)
            # TODO: ensure that we can get hierarchies for the base environment as well, not just the other ones

            self._compare_to_expected_yaml( output_dict         = hierarchy_base.to_dict(),
                                            test_case_name      = TEST_CASE + "_BASE", 
                                            save_output_dict    = True)            

        except ApodeixiError as ex:
            print(ex.trace_message()) 
            self.assertTrue(1==2)

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
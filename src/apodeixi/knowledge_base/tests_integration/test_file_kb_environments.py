import sys                                              as _sys

from apodeixi.testing_framework.a6i_integration_test    import ApodeixiIntegrationTest
from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace
from apodeixi.util.path_utils              			    import FolderHierarchy

from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase
from apodeixi.knowledge_base.kb_environment             import KB_Environment_Config

class Test_File_KB_Environments(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()

    def test_create_environment(self):

        TEST_CASE                       = 'test_create_environment'

        ENVIRONMENT_NAME                = TEST_CASE + "_ENV"

        POSTING_FULLPATH                = self.input_data + "/" + TEST_CASE + "_big-rocks.journeys.a6i.xlsx" 
        POSTING_LABEL_SHEET             = "Sheet1"
                    
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
            env_config                  = KB_Environment_Config(
                                                root_trace, 
                                                read_misses_policy  = KB_Environment_Config.FAILOVER_READS_TO_PARENT,
                                                use_timestamps      = False,
                                                path_mask           = self._path_mask)
            self.store.current_environment(my_trace).addSubEnvironment(my_trace, ENVIRONMENT_NAME, env_config,
                                                                        isolate_collab_folder = True)

            my_trace            = root_trace.doing("Activating environment '" + ENVIRONMENT_NAME + "'")
            self.store.activate(parent_trace = my_trace, environment_name = ENVIRONMENT_NAME)
            self._assert_current_environment(   parent_trace    = my_trace,
                                                snapshot_name   = ENVIRONMENT_NAME + "_Step_0")

            my_trace            = root_trace.doing("Making a posting in environment '" + ENVIRONMENT_NAME + "'")
            response, log_txt   = self.kb.postByFile(   parent_trace                = my_trace, 
                                                        path_of_file_being_posted   = POSTING_FULLPATH,
                                                        excel_sheet                 = POSTING_LABEL_SHEET)

            self._assert_current_environment(   parent_trace    = my_trace,
                                                snapshot_name   = ENVIRONMENT_NAME + "_Step_1")

            my_trace            = root_trace.doing("Deactivating environment '" + ENVIRONMENT_NAME + "'")
            self.store.deactivate(parent_trace = my_trace)

            self._assert_current_environment(   parent_trace    = my_trace,
                                                snapshot_name   = TEST_CASE + "_BASE") 

        except ApodeixiError as ex:
            print(ex.trace_message()) 
            self.assertTrue(1==2)
           

    def DEPRECATED_assert_current_environment(self, parent_trace, test_case_name):     
        '''
        Helper method to validate current environment's folder hierarchy is as expected
        '''
        hierarchy_env       = self.store.current_environment(parent_trace).folder_hierarchy(parent_trace        = parent_trace,
                                                                                            include_timestamps  = False)
        # TODO: add some data to environment, maybe calling a controller on some posting

        self._compare_to_expected_yaml( output_dict         = hierarchy_env.to_dict(),
                                        test_case_name      = test_case_name, 
                                        save_output_dict    = True)
                                                                       

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_File_KB_Environments()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='create_environment':
            T.test_create_environment()

    main(_sys.argv)
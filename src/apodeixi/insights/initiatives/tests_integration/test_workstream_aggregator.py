import sys                                                      as _sys

from apodeixi.testing_framework.a6i_integration_test            import ApodeixiIntegrationTest, ShutilStoreTestStack
from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils                             import DictionaryFormatter 

from apodeixi.knowledge_base.kb_environment                     import KB_Environment_Config
from apodeixi.insights.initiatives.workstream_aggregator        import WorkstreamAggregator

class Test_WorkstreamAggregator(ApodeixiIntegrationTest):

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

    def test_workstream_aggregator(self):

        TEST_NAME                       = 'test_workstream_aggregator'
        INITIATIVE                      = 'S1'
        ENVIRONMENT_NAME                = TEST_NAME + "_ENV"
        self.setScenario("aggregate_workstream_metrics")
        try:
            root_trace                  = FunctionalTrace(None).doing("Testing Workstream Aggregators")

            my_trace                    = root_trace.doing("Removing previously created environment, if any",
                                                        data = {'environment name': ENVIRONMENT_NAME})
            stat                        = self.stack().store().removeEnvironment(parent_trace = my_trace, name = ENVIRONMENT_NAME)

            my_trace                    = root_trace.doing("Creating a sub-environment to do postings in")
            env_config                  = KB_Environment_Config(
                                                root_trace, 
                                                read_misses_policy  = KB_Environment_Config.FAILOVER_READS_TO_PARENT,
                                                use_timestamps      = False,
                                                path_mask           = self._path_mask)
            self.stack().store().current_environment(my_trace).addSubEnvironment(my_trace, ENVIRONMENT_NAME, env_config,
                                                                            isolate_collab_area = True)
            self.stack().store().activate(parent_trace = my_trace, environment_name = ENVIRONMENT_NAME)

            my_trace                    = root_trace.doing("Running WorkstreamAggregator")
            aggregator                  = WorkstreamAggregator(         parent_trace                = my_trace,
                                                                        initiative_UID              = INITIATIVE, 
                                                                        knowledge_base              = self.stack().kb())

            result_df, errors           = aggregator.aggregateMetrics(  parent_trace                = my_trace, 
                                                                        filing_coordinates_filter   = None, 
                                                                        posting_version_filter      = None)

            explanation_txt             = "++++++++++++++++++++ Successes +++++++++++++++\n"
            if not result_df is None:
                explanation_txt         += "\nresult_df.shape = " + str(result_df.shape)


            explanation_txt             += "\n\n======================= Errors while aggregating metrics ============= "  
            error_idxs                  = list(errors.keys())
            error_idxs.sort()     
            for idx in error_idxs:
                explanation_txt              += "\n\n============= Error processinng handle #" + str(idx) + "\n"  
                explanation_txt              += errors[idx].trace_message()     

            self._compare_to_expected_txt(  parent_trace                = my_trace,
                                            output_txt                  = explanation_txt, 
                                            test_output_name            = TEST_NAME + "_explanations", 
                                            save_output_txt             = True)                                          

            self._compare_to_expected_df(   parent_trace                = my_trace,
                                            output_df                   = result_df, 
                                            test_output_name            = TEST_NAME, 
                                            columns_to_ignore           = [], 
                                            id_column                   = None)
 
        except ApodeixiError as ex:
            print(ex.trace_message()) 
            self.assertTrue(1 == 2) # Ensure that test fails
        
if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_WorkstreamAggregator()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='workstream_aggregator':
            T.test_workstream_aggregator()

    main(_sys.argv)
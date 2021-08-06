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
        self._stack                 = ShutilStoreTestStack(parent_trace, self.a6i_config)

    def test_workstream_aggregator(self):

        TEST_NAME                       = 'test_workstream_aggregator'
        INITIATIVE                      = 'S1'
        #ENVIRONMENT_NAME                = TEST_NAME + "_ENV"
        self.setScenario("aggregate_workstream_metrics")
        self.setCurrentTestName(TEST_NAME)
        self.changeResultDataLocation()

        try:
            root_trace                  = FunctionalTrace(None).doing("Testing Workstream Aggregators")

            my_trace                        = self.trace_environment(root_trace, "Isolating test case")

            # The inputs for this test are Excel postings residing in the Knowledge Base itself, so only
            # partially isolate the environment for this test, since we want to retrieve such postings.
            # So the read_misses_policy will failover on posting reads only, but *should not* failover on manifest
            # reads because version checks would prevent creating manifests (with version 1) since such exist
            # in the parent environment for historical reasons.
            self.provisionIsolatedEnvironment(my_trace, read_misses_policy = KB_Environment_Config.FAILOVER_POSTING_READS_TO_PARENT)
 
            my_trace                    = root_trace.doing("Running WorkstreamAggregator")
            aggregator                  = WorkstreamAggregator(         parent_trace                = my_trace,
                                                                        initiative_UID              = INITIATIVE, 
                                                                        knowledge_base              = self.stack().kb())

            result_df, errors           = aggregator.aggregateMetrics(  parent_trace                = my_trace, 
                                                                        filing_coordinates_filter   = None)

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
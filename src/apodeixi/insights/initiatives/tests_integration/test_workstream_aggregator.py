import sys                                                      as _sys

from apodeixi.testing_framework.a6i_integration_test            import ApodeixiIntegrationTest
from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils                             import DictionaryFormatter 

from apodeixi.insights.initiatives.workstream_aggregator        import WorkstreamAggregator

class Test_WorkstreamAggregator(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()       

    def test_workstream_aggregator(self):

        TEST_NAME                       = 'test_workstream_aggregator'
        INITIATIVE                      = 'S1'

        try:
            root_trace                  = FunctionalTrace(None).doing("Testing Workstream Aggregators")

            aggregator                  = WorkstreamAggregator(         parent_trace                = root_trace,
                                                                        initiative_UID              = INITIATIVE, 
                                                                        knowledge_base              = self.kb)

            result_df, errors           = aggregator.aggregateMetrics(  parent_trace                = root_trace, 
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

            self._compare_to_expected_txt(  output_txt                  = explanation_txt, 
                                            test_case_name              = TEST_NAME + "_explanations", 
                                            save_output_txt             = True)                                          

            self._compare_to_expected_df(   parent_trace                = root_trace,
                                            output_df                   = result_df, 
                                            test_case_name              = TEST_NAME, 
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
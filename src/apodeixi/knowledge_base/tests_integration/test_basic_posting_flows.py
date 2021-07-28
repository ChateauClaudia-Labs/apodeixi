import sys                                                              as _sys

from apodeixi.testing_framework.a6i_integration_test                    import ShutilStoreTestStack
from apodeixi.util.a6i_error                                            import ApodeixiError, FunctionalTrace

from apodeixi.controllers.journeys.delivery_planning.big_rocks          import BigRocksEstimate_Controller
from apodeixi.knowledge_base.tests_integration.flow_scenario_skeleton   import FlowScenarioSkeleton

class Test_BasicPostingFlows(FlowScenarioSkeleton):

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

    def test_big_rocks_burnout(self):

        self.setScenario("basic_posting_flows.big_rocks.burnout")
        self.setCurrentTestName('brb_opus') # big rock burnout for product Opus

        EXCEL_RELATIVE_PATH             = "journeys/Dec 2020/FusionOpus/Default"
        EXCEL_FILE                      = "OPUS_big-rocks.journeys.a6i.xlsx"
        NB_MANIFESTS_EXPECTED           = 3

        
        self._run_basic_flow(   excel_relative_path         = EXCEL_RELATIVE_PATH,
                                excel_file                  = EXCEL_FILE,
                                nb_manifests_expected       = NB_MANIFESTS_EXPECTED,
                                generated_form_worksheet    = BigRocksEstimate_Controller.GENERATED_FORM_WORKSHEET)

    def NOTREADYtest_big_rocks_explained(self):

        self.setScenario("basic_posting_flows.big_rocks.explained")
        self.setCurrentTestName('bre_ledger_pro') # big rock explained for product LedgerPro

        EXCEL_RELATIVE_PATH             = "journeys/Dec 2020/LedgerPro/OficialPlan"
        EXCEL_FILE                      = "LedgerPro.big-rocks.journeys.a6i.xlsx"
        NB_MANIFESTS_EXPECTED           = 3

        
        self._run_basic_flow(   excel_relative_path         = EXCEL_RELATIVE_PATH,
                                excel_file                  = EXCEL_FILE,
                                nb_manifests_expected       = NB_MANIFESTS_EXPECTED,
                                generated_form_worksheet    = BigRocksEstimate_Controller.GENERATED_FORM_WORKSHEET)


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_BasicPostingFlows()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='big_rocks_burnout':
            T.test_big_rocks_burnout()

    main(_sys.argv)
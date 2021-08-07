import sys                                                              as _sys

from apodeixi.testing_framework.a6i_integration_test                    import ShutilStoreTestStack
from apodeixi.util.a6i_error                                            import ApodeixiError, FunctionalTrace

from apodeixi.controllers.util.skeleton_controller                      import SkeletonController
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
        self._stack                 = ShutilStoreTestStack(parent_trace, self.a6i_config)

    def test_big_rocks_burnout(self):

        self.setScenario("basic_posting_flows.big_rocks.burnout")
        self.setCurrentTestName('brb_opus') # big rock burnout for product Opus
        self.changeResultDataLocation()

        EXCEL_RELATIVE_PATH             = "journeys/Dec 2020/FusionOpus/Default"
        EXCEL_FILE                      = "OPUS_big-rocks.journeys.a6i.xlsx"
        NB_MANIFESTS_EXPECTED           = 3

        
        self._run_basic_flow(   from_nothing                = False,
                                namespace                   = None, # Only relevant when from_nothing is True
                                subnamespace                = None, # Only relevant when from_nothing is True
                                posting_api                 = 'big-rocks.journeys.a6i',
                                excel_relative_path         = EXCEL_RELATIVE_PATH,
                                excel_file                  = EXCEL_FILE,
                                excel_sheet                 = "Sheet1",
                                nb_manifests_expected       = NB_MANIFESTS_EXPECTED,
                                generated_form_worksheet    = SkeletonController.GENERATED_FORM_WORKSHEET,
                                setup_static_data           = True)

    def test_big_rocks_explained(self):

        self.setScenario("basic_posting_flows.big_rocks.explained")
        self.setCurrentTestName('bre_ledger') # big rock explained for product LedgerPro
        self.changeResultDataLocation()

        EXCEL_RELATIVE_PATH             = "journeys/Dec 2020/LedgerPro/OfficialPlan"
        EXCEL_FILE                      = "LedgerPro.big-rocks.journeys.a6i.xlsx"
        NB_MANIFESTS_EXPECTED           = 2

        
        self._run_basic_flow(   from_nothing                = False,
                                namespace                   = None, # Only relevant when from_nothing is True
                                subnamespace                = None, # Only relevant when from_nothing is True
                                posting_api                 = 'big-rocks.journeys.a6i',
                                excel_relative_path         = EXCEL_RELATIVE_PATH,
                                excel_file                  = EXCEL_FILE,
                                excel_sheet                 = "broken explained",
                                nb_manifests_expected       = NB_MANIFESTS_EXPECTED,
                                generated_form_worksheet    = SkeletonController.GENERATED_FORM_WORKSHEET,
                                setup_static_data           = True)

    def test_milestones(self):

        self.setScenario("basic_posting_flows.milestones")
        self.setCurrentTestName('bre_ledger') # milestones for product LedgerPro
        self.changeResultDataLocation()

        EXCEL_RELATIVE_PATH             = "journeys/Dec 2020/LedgerPro/OfficialPlan"
        EXCEL_FILE                      = "LedgerPro.milestone.journeys.a6i.xlsx"
        NB_MANIFESTS_EXPECTED           = 2

        
        self._run_basic_flow(   from_nothing                = True,
                                namespace                   = 'my-corp.production',
                                subnamespace                = 'modernization',
                                posting_api                 = 'milestone.journeys.a6i',
                                excel_relative_path         = EXCEL_RELATIVE_PATH,
                                excel_file                  = EXCEL_FILE,
                                excel_sheet                 = "Posting Label",
                                nb_manifests_expected       = NB_MANIFESTS_EXPECTED,
                                generated_form_worksheet    = SkeletonController.GENERATED_FORM_WORKSHEET,
                                setup_static_data           = True)



if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_BasicPostingFlows()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='big_rocks_burnout':
            T.test_big_rocks_burnout()
        elif what_to_do=='big_rocks_explained':
            T.test_big_rocks_explained()

    main(_sys.argv)
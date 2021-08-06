import sys                                                              as _sys

from apodeixi.testing_framework.a6i_integration_test                    import ShutilStoreTestStack
from apodeixi.util.a6i_error                                            import ApodeixiError, FunctionalTrace

from apodeixi.controllers.util.skeleton_controller                      import SkeletonController
from apodeixi.knowledge_base.tests_integration.flow_scenario_skeleton   import FlowScenarioSkeleton

class Test_StaticDataFlows(FlowScenarioSkeleton):

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

    def test_products(self):

        self.setScenario("static_data_flows.products")
        self.setCurrentTestName('products') 
        self.changeResultDataLocation()

        EXCEL_RELATIVE_PATH             = "admin/static-data"
        EXCEL_FILE                      = "products.static-data.admin.a6i.xlsx"
        NB_MANIFESTS_EXPECTED           = 2
        root_trace                      = FunctionalTrace(None).doing("Retrieving organization and knowledge base areas from ApodeixiConfig")
        ORGANIZATION                    = self.a6i_config.getOrganization(root_trace)
        KNOWLEDGE_BASE_AREAS            = self.a6i_config.getKnowledgeBaseAreas(root_trace)
        NAMESPACE                       = ORGANIZATION + "." + KNOWLEDGE_BASE_AREAS[1]  #"my_corp.testing-area"
        SUBNAMESPACE                    = None
        
        self._run_basic_flow(   from_nothing                = True,
                                namespace                   = NAMESPACE,
                                subnamespace                = SUBNAMESPACE,
                                posting_api                 = 'products.static-data.admin.a6i',
                                excel_relative_path         = EXCEL_RELATIVE_PATH,
                                excel_file                  = EXCEL_FILE,
                                excel_sheet                 = "Posting Label",
                                nb_manifests_expected       = NB_MANIFESTS_EXPECTED,
                                generated_form_worksheet    = SkeletonController.GENERATED_FORM_WORKSHEET,
                                setup_static_data           = False)

    def test_scoring_cycles(self):

        self.setScenario("static_data_flows.s_c")
        self.setCurrentTestName('scoring_cycles')
        self.changeResultDataLocation() 

        EXCEL_RELATIVE_PATH             = "admin/static-data"
        EXCEL_FILE                      = "scoring-cycles.static-data.admin.a6i.xlsx"
        NB_MANIFESTS_EXPECTED           = 1
        root_trace                      = FunctionalTrace(None).doing("Retrieving organization and knowledge base areas from ApodeixiConfig")
        ORGANIZATION                    = self.a6i_config.getOrganization(root_trace)
        KNOWLEDGE_BASE_AREAS            = self.a6i_config.getKnowledgeBaseAreas(root_trace)
        NAMESPACE                       = ORGANIZATION + "." + KNOWLEDGE_BASE_AREAS[1]  #"my_corp.testing-area"
        SUBNAMESPACE                    = None
        
        self._run_basic_flow(   from_nothing                = True,
                                namespace                   = NAMESPACE,
                                subnamespace                = SUBNAMESPACE,
                                posting_api                 = 'scoring-cycles.static-data.admin.a6i',
                                excel_relative_path         = EXCEL_RELATIVE_PATH,
                                excel_file                  = EXCEL_FILE,
                                excel_sheet                 = "Posting Label",
                                nb_manifests_expected       = NB_MANIFESTS_EXPECTED,
                                generated_form_worksheet    = SkeletonController.GENERATED_FORM_WORKSHEET,
                                setup_static_data           = False)


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_StaticDataFlows()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='products':
            T.test_products()
        elif what_to_do=='scoring_cycles':
            T.test_scoring_cycles()

    main(_sys.argv)
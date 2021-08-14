import sys                                                              as _sys

from apodeixi.util.a6i_error                                            import FunctionalTrace
from apodeixi.controllers.util.skeleton_controller                      import SkeletonController
from apodeixi.knowledge_base.tests_integration.post_update_skeleton     import Post_and_Update_Skeleton

class Test_StaticDataFlows(Post_and_Update_Skeleton):

    def _select_namespace(self):
        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Retrieving organization and knowledge base areas "
                                                                        " from ApodeixiConfig")
        ORGANIZATION                    = self.a6i_config.getOrganization(root_trace)
        KNOWLEDGE_BASE_AREAS            = self.a6i_config.getKnowledgeBaseAreas(root_trace)
        NAMESPACE                       = ORGANIZATION + "." + KNOWLEDGE_BASE_AREAS[1] 
        return NAMESPACE

    def test_products(self):

        self.run_script(    scenario                    = "static_data_flows.products", 
                            test_name                   = "products", 
                            excel_relative_path         = "admin/static-data", 
                            excel_file                  = "products.static-data.admin.a6i.xlsx", 
                            excel_sheet                 = "Posting Label", 
                            nb_manifests                = 2, 
                            from_nothing                = True, 
                            namespace                   = self._select_namespace(), 
                            subnamespace                = None, 
                            posting_api                 = "products.static-data.admin.a6i", 
                            setup_dependencies          = False)


    def test_scoring_cycles(self):

        self.run_script(    scenario                    = "static_data_flows.s_c", 
                            test_name                   = "scoring_cycles", 
                            excel_relative_path         = "admin/static-data", 
                            excel_file                  = "scoring-cycles.static-data.admin.a6i.xlsx", 
                            excel_sheet                 = "Posting Label", 
                            nb_manifests                = 1, 
                            from_nothing                = True, 
                            namespace                   = self._select_namespace(), 
                            subnamespace                = None, 
                            posting_api                 = "scoring-cycles.static-data.admin.a6i", 
                            setup_dependencies          = False)


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
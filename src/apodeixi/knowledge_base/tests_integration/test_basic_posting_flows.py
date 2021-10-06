import sys                                                              as _sys

from apodeixi.controllers.util.skeleton_controller                      import SkeletonController
from apodeixi.knowledge_base.tests_integration.post_update_skeleton     import Post_and_Update_Skeleton

class Test_BasicPostingFlows(Post_and_Update_Skeleton):

    def test_big_rocks_burnout(self):

        self.run_script(    scenario                    = "basic_posting_flows.big_rocks.burnout", 
                            test_name                   = "brb_opus", 
                            excel_relative_path         = "journeys/Dec 2020/FusionOpus/Default", 
                            excel_file                  = "OPUS_big-rocks.journeys.a6i.xlsx", 
                            excel_sheet                 = "Sheet1", 
                            nb_manifests                = 3, 
                            from_nothing                = False, 
                            namespace                   = None, # Only relevant when from_nothing is True, 
                            subnamespace                = None, # Only relevant when from_nothing is True, 
                            posting_api                 = "big-rocks.journeys.a6i", 
                            setup_dependencies          = True)

    def test_big_rocks_explained(self):

        self.run_script(    scenario                    = "basic_posting_flows.big_rocks.explained", 
                            test_name                   = "bre_ledger", 
                            excel_relative_path         = "journeys/Dec 2020/LedgerPro/OfficialPlan", 
                            excel_file                  = "LedgerPro.big-rocks.journeys.a6i.xlsx", 
                            excel_sheet                 = "broken explained", 
                            nb_manifests                = 2, 
                            from_nothing                = False, 
                            namespace                   = None, # Only relevant when from_nothing is True, 
                            subnamespace                = None, # Only relevant when from_nothing is True, 
                            posting_api                 = "big-rocks.journeys.a6i", 
                            setup_dependencies          = True)
        
    def test_milestones_flows(self):

        self.run_script(    scenario                    = "basic_posting_flows.milestones", 
                            test_name                   = "ml_jackh", 
                            excel_relative_path         = "journeys/Dec 2020/Jack Henry/OfficialPlan", 
                            excel_file                  = "Jack Henry.modernization.milestone.journeys.a6i.xlsx", 
                            excel_sheet                 = "Posting Label", 
                            nb_manifests                = 1, # Not 2, since big-rock manifest will be read-only 
                            from_nothing                = True, 
                            namespace                   = "my-corp.production",
                            subnamespace                = "modernization", 
                            posting_api                 = "milestone.journeys.a6i", 
                            setup_dependencies          = True)


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
        elif what_to_do=='milestones_flows':
            T.test_milestones_flows()

    main(_sys.argv)
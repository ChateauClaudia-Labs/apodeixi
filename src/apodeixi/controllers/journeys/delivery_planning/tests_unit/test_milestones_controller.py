import sys                                                                  as _sys

from apodeixi.testing_framework.controllers.skeleton_controller_unit_test   import SkeletonControllerUnitTest
from apodeixi.util.a6i_error                                                import FunctionalTrace

from apodeixi.controllers.journeys.delivery_planning.milestones_controller  import MilestonesController 


class Test_MilestonesController(SkeletonControllerUnitTest):

    def setUp(self):
        super().setUp()

    def test_milestones(self):
        root_trace                                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing('Testing MilestoneController')
        self.impl_testcase(     parent_trace            = root_trace, 
                                test_name               = 'milestones',
                                controller_class        = MilestonesController,
                                nb_manifests_expected   = 2, 
                                excel_sheet             = 'Sheet1', 
                                ctx_range               = 'b2:c20')


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_MilestonesController()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='milestones':
            T.test_milestones()


    main(_sys.argv)
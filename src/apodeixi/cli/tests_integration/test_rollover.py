import sys                                              as _sys
import os                                               as _os

from apodeixi.util.a6i_error                            import FunctionalTrace
from apodeixi.util.path_utils                           import PathUtils

from apodeixi.cli.tests_integration.cli_test_skeleton   import CLI_Test_Skeleton
from apodeixi.cli.cli_utils                             import CLI_Utils

class Test_Rollover(CLI_Test_Skeleton):
      
    def test_cli_rollover_basic(self):
        '''
        Tests rollover functionality when traversing fiscal years: if there is no previous manifest for FY 23 but one
        exists from FY 22, then trying to retrieve the latest manifest in FY 23 will result in the latest one from FY 22,
        as opposed to a template-based default.

        This test case is basic: for a particular posting API like big rocks, confirm it we can roll over the associated
        form and manifests can be rolled over.
        '''
        self.setScenario("cli.basic_rollover")
        self.setCurrentTestName('basic_rollover')
        self.selectTestDataLocation()

        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName()) 

        PRODUCTS_FILE                   = 'products.static-data.admin.a6i.xlsx'
        SCORING_CYCLES_FILE             = 'scoring-cycles.static-data.admin.a6i.xlsx'
        BIG_ROCKS_FILE_V1               = 'v1.big-rocks.journeys.a6i.xlsx'
        BIG_ROCKS_FILE_V2               = 'v2.big-rocks.journeys.a6i.xlsx'
        BIG_ROCKS_POSTING_API           = 'big-rocks.journeys.a6i'
        BIG_ROCKS_MANIFEST_API          = "delivery-planning.journeys.a6i.io" #/v1a"
        NAMESPACE                       = 'cicloquimica.production'
        FY23_NAME                       = "modernization.fy-23.astrea.official"
        SUB_NAMESPACE                   = 'modernization'
        FY22_REL_PATH_IN_EXT_COLLAB     = "journeys/FY 22/Astrea/Official"
        FY23_REL_PATH_IN_EXT_COLLAB     = "journeys/FY 23/Astrea/Official"
        FY23_GENERATED_FORM_FILE        = "Astrea.modernization.big-rocks.journeys.a6i.xlsx"

        STATIC_DATA_WORKING_DIR         = "admin/static-data"

        _path_of                        = self.fullpath_of

        MASK_COMBINED                   = CLI_Utils().combined_mask(root_trace, self.a6i_config)
                  
        # This will fool the CLI to treat our provisioned environment for this test as if it were the base environment
        self.overwrite_test_context(root_trace) # Overwrites self.a6i_config , the store, the test_db, etc.

        store                           = self.stack().store()
        clientURL                       = store.base_environment(root_trace).clientURL(root_trace)

        # Post the static data
        my_trace                        = root_trace.doing("Running with working directory '" + STATIC_DATA_WORKING_DIR +"'")

        working_dir                     = clientURL + "/" + STATIC_DATA_WORKING_DIR

        PathUtils().create_path_if_needed(my_trace, working_dir)
        _os.chdir(working_dir)

        COMMANDS_1                      = [
                                            ['post',        '--timestamp', "_CLI__1", 
                                                            _path_of(PRODUCTS_FILE)],
                                            ['post',        '--timestamp', "_CLI__2", 
                                                            _path_of(SCORING_CYCLES_FILE)],
                                        ]

        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_1,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.NEVER)

        # Post the FY 22 big rocks
        my_trace                        = root_trace.doing("Running with working directory '" + FY22_REL_PATH_IN_EXT_COLLAB +"'")
        fy22_working_dir                = clientURL + "/" + FY22_REL_PATH_IN_EXT_COLLAB

        PathUtils().create_path_if_needed(my_trace, fy22_working_dir)
        _os.chdir(fy22_working_dir)

        COMMANDS_2                      = [
                                            ['post',            '--timestamp', "_CLI__3", 
                                                            _path_of(BIG_ROCKS_FILE_V1)],
                                            ['post',            '--timestamp', "_CLI__4", 
                                                            _path_of(BIG_ROCKS_FILE_V2)],
                                            ['get',        'form', '--timestamp', "_CLI__5",
                                                            BIG_ROCKS_POSTING_API,  NAMESPACE,  SUB_NAMESPACE]
                                        ]

        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_2,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.NEVER)

        # For the next test, we need to switch the working directory for click
        my_trace                        = root_trace.doing("Running with working directory '" + FY23_REL_PATH_IN_EXT_COLLAB +"'")


        fy23_working_dir                = clientURL + "/" + FY23_REL_PATH_IN_EXT_COLLAB

        PathUtils().create_path_if_needed(my_trace, fy23_working_dir)
        _os.chdir(fy23_working_dir)


        COMMANDS_3                      = [
                                            ['get',        'form', '--timestamp', "_CLI__6",
                                                            BIG_ROCKS_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                            ['post',        '--timestamp', "_CLI__7", 
                                                            fy23_working_dir + "/" + FY23_GENERATED_FORM_FILE],
                                        ]

        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_3,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.NEVER)

        # Check that manifest is as expected right after a first FY 23 manifest is created from a rollover
        # For example, we expect its labels to include the rollFromName field to indicate its lineage as a continuation
        # of FY 22
        
        self.check_manifest(my_trace, BIG_ROCKS_MANIFEST_API, NAMESPACE, FY23_NAME, 'big-rock')

        # Now we do a full cycle get-form + post, to see that the new lineage in FY 23 can take off as expected
        COMMANDS_4                      = [
                                            ['get',        'form', '--timestamp', "_CLI__8",
                                                            BIG_ROCKS_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                            ['post',        '--timestamp', "_CLI__9", 
                                                            fy23_working_dir + "/" + FY23_GENERATED_FORM_FILE],
                                        ]

        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_4,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.ONLY_AT_END)

        # Check that manifest is as expected right after we are no longer in a rollover situation, and are modifying
        # previous manifests in FY 23.
        # 
        # For example, it should no longer be the case that its labels include the rollFromName field, as it used to
        # be the case when we created the first FY 23 manifest, since only that first manifested needed to 
        # to indicate its lineage as a continuation of FY 22
        #
        self.check_manifest(my_trace, BIG_ROCKS_MANIFEST_API, NAMESPACE, FY23_NAME, 'big-rock')

    def test_cli_rollover_with_dependencies(self):
        '''
        Tests rollover functionality when traversing fiscal years: if there is no previous manifest for FY 23 but one
        exists from FY 22, then trying to retrieve the latest manifest in FY 23 will result in the latest one from FY 22,
        as opposed to a template-based default.

        This test case is when there are dependencies in play, with different manifests posted from different Excel
        forms, one depending on the other. We check that rollover logic still works if we first roll over the
        reference manifest and form, and later roll over the dependent one.
        
        '''
        self.setScenario("cli.dependency_rollover")
        self.setCurrentTestName('dependency_rollover')
        self.selectTestDataLocation()

        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask) \
                                            .doing("Running " + self.currentTestName()) 

        PRODUCTS_FILE                   = 'products.static-data.admin.a6i.xlsx'
        SCORING_CYCLES_FILE             = 'scoring-cycles.static-data.admin.a6i.xlsx'
        BIG_ROCKS_FILE_V1               = 'v1.big-rocks.journeys.a6i.xlsx'
        MILESTONES_FILE_V1              = 'v1.milestone.journeys.a6i.xlsx'
        BIG_ROCKS_POSTING_API           = 'big-rocks.journeys.a6i'
        BIG_ROCKS_MANIFEST_API          = "delivery-planning.journeys.a6i.io"
        MILESTONES_POSTING_API          = "milestone.journeys.a6i"
        MILESTONES_MANIFEST_API          = "delivery-planning.journeys.a6i.io" 
        NAMESPACE                       = 'cicloquimica.production'
        FY23_NAME                       = "modernization.fy-23.astrea.official"
        SUB_NAMESPACE                   = 'modernization'
        FY22_REL_PATH_IN_EXT_COLLAB     = "journeys/FY 22/Astrea/Official"
        FY23_REL_PATH_IN_EXT_COLLAB     = "journeys/FY 23/Astrea/Official"
        FY23_BIG_ROCKS_FORM_FILE        = "Astrea.modernization.big-rocks.journeys.a6i.xlsx"
        FY23_MILESTONE_FORM_FILE        = "Astrea.modernization.milestone.journeys.a6i.xlsx"

        STATIC_DATA_WORKING_DIR         = "admin/static-data"

        _path_of                        = self.fullpath_of

        MASK_COMBINED                   = CLI_Utils().combined_mask(root_trace, self.a6i_config)
                  
        # This will fool the CLI to treat our provisioned environment for this test as if it were the base environment
        self.overwrite_test_context(root_trace) # Overwrites self.a6i_config , the store, the test_db, etc.

        store                           = self.stack().store()
        clientURL                       = store.base_environment(root_trace).clientURL(root_trace)

        # Post the static data
        my_trace                        = root_trace.doing("Running with working directory '" + STATIC_DATA_WORKING_DIR +"'")

        working_dir                     = clientURL + "/" + STATIC_DATA_WORKING_DIR

        PathUtils().create_path_if_needed(my_trace, working_dir)
        _os.chdir(working_dir)

        COMMANDS_1                      = [
                                            ['post',        '--timestamp', "_CLI__1", 
                                                            _path_of(PRODUCTS_FILE)],
                                            ['post',        '--timestamp', "_CLI__2", 
                                                            _path_of(SCORING_CYCLES_FILE)],
                                        ]

        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_1,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.NEVER)

        # Post the FY 22 big rocks and milestones, and confirm all is good via get-form
        my_trace                        = root_trace.doing("Running with working directory '" + FY22_REL_PATH_IN_EXT_COLLAB +"'")
        fy22_working_dir                = clientURL + "/" + FY22_REL_PATH_IN_EXT_COLLAB

        PathUtils().create_path_if_needed(my_trace, fy22_working_dir)
        _os.chdir(fy22_working_dir)

        COMMANDS_2                      = [
                                            ['post',            '--timestamp', "_CLI__3", 
                                                            _path_of(BIG_ROCKS_FILE_V1)],
                                            ['post',            '--timestamp', "_CLI__4", 
                                                            _path_of(MILESTONES_FILE_V1)],
                                            ['get',        'form', '--timestamp', "_CLI__5",
                                                            BIG_ROCKS_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                            ['get',        'form', '--timestamp', "_CLI__6",
                                                            MILESTONES_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                        ]

        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_2,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.NEVER)

        # For the next test, we need to switch the working directory for click to FY 23
        my_trace                        = root_trace.doing("Running with working directory '" + FY23_REL_PATH_IN_EXT_COLLAB +"'")


        fy23_working_dir                = clientURL + "/" + FY23_REL_PATH_IN_EXT_COLLAB

        PathUtils().create_path_if_needed(my_trace, fy23_working_dir)
        _os.chdir(fy23_working_dir)

        # Now get form for big-rocks and milestone.
        #
        # This should cause rollover for both, and in particular in the milestone form we should see that the big-rocks
        # dependency is through a rollover name.
        #
        # Then we post the big rocks, and again get-form for both big-rocks and milestone.
        # At this point there should be no big rock rollover name in the form - only in the milestone form for referencing
        # the FY 22 milestone, but milestones should reference the FY 23 big-rocks.
        # 
        # Lastly we post and get-form the milestone, and all rollover names should now be gone. 
        # 
        COMMANDS_3                      = [
                                            ['get',        'form', '--timestamp', "_CLI__7",
                                                            BIG_ROCKS_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                            ['get',        'form', '--timestamp', "_CLI__8",
                                                            MILESTONES_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                            ['post',        '--timestamp', "_CLI__9", 
                                                            fy23_working_dir + "/" + FY23_BIG_ROCKS_FORM_FILE],
                                            ['get',        'form', '--timestamp', "_CLI__10",
                                                            BIG_ROCKS_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                            ['get',        'form', '--timestamp', "_CLI__11",
                                                            MILESTONES_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                            ['post',        '--timestamp', "_CLI__12", 
                                                            fy23_working_dir + "/" + FY23_MILESTONE_FORM_FILE],
                                            ['get',        'form', '--timestamp', "_CLI__13",
                                                            MILESTONES_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                        ]

        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_3,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.NEVER)

        # Check that manifest is as expected right after a first FY 23 manifest is created from a rollover
        # For example, we expect its labels to include the rollFromName field to indicate its lineage as a continuation
        # of FY 22
        #
        self.check_manifest(my_trace, BIG_ROCKS_MANIFEST_API, NAMESPACE, FY23_NAME, 'big-rock')
        self.check_manifest(my_trace, MILESTONES_MANIFEST_API, NAMESPACE, FY23_NAME, 'modernization-milestone')

        # Now we do a full cycle get-form + post, to see that the new lineage in FY 23 can take off as expected
        COMMANDS_4                      = [
                                            ['post',        '--timestamp', "_CLI__14", 
                                                            fy23_working_dir + "/" + FY23_BIG_ROCKS_FORM_FILE],
                                            ['get',        'form', '--timestamp', "_CLI__15",
                                                            BIG_ROCKS_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                            ['get',        'form', '--timestamp', "_CLI__16",
                                                            MILESTONES_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                            ['post',        '--timestamp', "_CLI__17", 
                                                            fy23_working_dir + "/" + FY23_MILESTONE_FORM_FILE],
                                            ['get',        'form', '--timestamp', "_CLI__18",
                                                            MILESTONES_POSTING_API,  NAMESPACE,  SUB_NAMESPACE],
                                        ]
        self.skeleton_test(  parent_trace                = my_trace,
                                    cli_command_list            = COMMANDS_4,
                                    output_cleanining_lambda    = MASK_COMBINED,
                                    when_to_check_environment   = CLI_Test_Skeleton.ONLY_AT_END)

        # Check that manifest is as expected right after we are no longer in a rollover situation, and are modifying
        # previous manifests in FY 23.
        # 
        # For example, it should no longer be the case that its labels include the rollFromName field, as it used to
        # be the case when we created the first FY 23 manifest, since only that first manifested needed to 
        # to indicate its lineage as a continuation of FY 22
        #
        self.check_manifest(my_trace, BIG_ROCKS_MANIFEST_API, NAMESPACE, FY23_NAME, 'big-rock')
        self.check_manifest(my_trace, MILESTONES_MANIFEST_API, NAMESPACE, FY23_NAME, 'modernization-milestone')
                                                   

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_Rollover()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='rollover_basic':
            T.test_cli_rollover_basic()
        elif what_to_do=='dependency_rollover':
            T.test_cli_rollover_with_dependencies()

    main(_sys.argv)
import sys                                                      as _sys
import pandas                                                   as _pd
import yaml                                                     as _yaml

from apodeixi.testing_framework.a6i_unit_test                   import ApodeixiUnitTest
from apodeixi.testing_framework.mock_kb_store                   import UnitTest_KnowledgeBaseStore
from apodeixi.knowledge_base.knowledge_base_store               import KnowledgeBaseStore
from apodeixi.testing_framework.controllers.mock_controller     import Mock_Controller
from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace
from apodeixi.util.formatting_utils                             import DictionaryFormatter

#from apodeixi.xli.breakdown_builder             import BreakdownTree, UID_Store, Interval
#from apodeixi.xli.posting_controller_utils      import PostingConfig
#from apodeixi.xli                               import UpdatePolicy

class Test_MalformedInput(ApodeixiUnitTest):
    '''
    Tests validations against mal-formed or non-canonical user input that are detected and addressed in
    the SkeletonController class, or in classes it derives work to, such as the BreakdownTree class. 
    
    Resolution of mal-formed user input may involve:

    * Raising a user-friendly error that educates the user on how to fix the mal-formed input
    * Alternatively, the software may attempt to "correct" the user error and infer the intent, and proceed from that.

    These are the user-visible validations against malformed input currently supported:
    '''
    VALIDATIONS_DICT = {  
        0: 'No malformed input',
        1: 'User creates additional columns with the same name as an entity',
        2: 'User removed or renamed an entity column for the top entity column,' 
                        + "so it no longer matches what is set as the BreakdownTree's root entity",
        3: "User removed or renamed an entity column for a secondary entity.",

        4: "User let blank the entity name in a row with data for that entity, and the software can't correct it",
        5: "User adds or re-arranges columns such that a an interval has multiple entity columns",
        6: "User puts a non-supported manifest API in posting label",
        7: "User has typo in the kinds of manifests in posting label",
        8: "User has a typo in the worksheets in the posting label",

        9: "User left blank the entity name in a row with data for that entity, and the software can 'correct it' "
            + "if what happened is that the user entered it in the previous row and then left the previous row blank "
            + "starting at some column, using the next row insted for such data. This is the first of two sub-cases:"
            + "The extra row data is in the same interval as the missing entity name",

        10: "User left blank the entity name in a row with data for that entity, and the software can 'correct it' "
            + "if what happened is that the user entered it in the previous row and then left the previous row blank "
            + "starting at some column, using the next row insted for such data. This is the second of two sub-cases:"
            + " the extra row data is for the next interval after the one with the missing entity name"
    }
    

    def setUp(self):
        super().setUp()

    def test_user_validation_0(self):  
        self._malformed_input_test_skeleton(0, expect_error=False)

    def test_user_validation_1(self):  
        self._malformed_input_test_skeleton(1, expect_error=True)

    def test_user_validation_2(self):  
        self._malformed_input_test_skeleton(2, expect_error=True)

    def test_user_validation_3(self):  
        self._malformed_input_test_skeleton(3, expect_error=True)

    def test_user_validation_4(self):  
        self._malformed_input_test_skeleton(4, expect_error=True)

    def test_user_validation_5(self):  
        self._malformed_input_test_skeleton(5, expect_error=True)

    def test_user_validation_6(self):  
        self._malformed_input_test_skeleton(6, expect_error=True)

    def test_user_validation_7(self):  
        self._malformed_input_test_skeleton(7, expect_error=True)

    def test_user_validation_8(self):  
        self._malformed_input_test_skeleton(8, expect_error=True)

    def test_user_validation_9(self):  
        self._malformed_input_test_skeleton(9, expect_error=False)

    def test_user_validation_10(self):  
        self._malformed_input_test_skeleton(10, expect_error=False)

    def _malformed_input_test_skeleton(self, test_case_nb, expect_error):
        test_case_name              = 'user_validation_' + str(test_case_nb)
        result_dict                 = None  
        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Validating mal-formed input")
        try:
            self._attempt_to_run(test_case_name, expect_error)
        except ApodeixiError as ex:
            if expect_error:
                output_txt              = "==================    This test verifies that the following user validation works:\n\n"
                output_txt              += Test_MalformedInput.VALIDATIONS_DICT[test_case_nb]
                output_txt              += "\n\n================     Below is the error message the user would get:"
                output_txt              += ex.trace_message(exclude_stack_trace=True)
                self._compare_to_expected_txt(root_trace, output_txt, test_case_name, save_output_txt=True)
                return
            else:
                print(ex.trace_message()) 
                self.assertTrue(1==2)

        if expect_error: # Shouldn't have gotten here, since an exception should have been raised before. So fail test
            self.assertTrue(1==2)

    def _attempt_to_run(self, test_case_name, expect_error):
        STORE_IMPL                      = UnitTest_KnowledgeBaseStore(  test_case_name          = test_case_name,
                                                                        input_manifests_dir     = self.input_data, 
                                                                        input_postings_dir      = self.input_data, 
                                                                        output_manifests_dir    = self.output_data, 
                                                                        output_postings_dir     = self.output_data)

        EXCEL_FILE                      = test_case_name + "_INPUT.xlsx"

        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Discovering URL", data={'path'  : EXCEL_FILE,
                                                                                                    })
        STORE                           = KnowledgeBaseStore(root_trace, STORE_IMPL)                                                                                            
        posting_handle                  = STORE.buildPostingHandle(root_trace, EXCEL_FILE,
                                                                    sheet="Posting Label", excel_range="B2:C100") 

        MANIFESTS_OUTPUT_DIR            = self.output_data
        MANIFESTS_EXPECTED_DIR          = self.expected_data
        EXPLANATIONS_OUTPUT             = test_case_name + '_explanations_OUTPUT.yaml'
        EXPLANATIONS_EXPECTED           = test_case_name + '_explanations_EXPECTED.yaml'
        all_manifests_dicts             = []

        PL                              = Mock_Controller._MyPostingLabel # Abbreviation for readability purposes

        try:
            root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Running Mock_Controller")

            controller                  = Mock_Controller(root_trace, STORE, a6i_config = self.a6i_config)
            all_manifests_dict, label   = controller._buildAllManifests(root_trace, posting_handle)

            NB_MANIFESTS_EXPECTED   = 3
            if len(all_manifests_dict.keys()) != NB_MANIFESTS_EXPECTED:
                raise ApodeixiError(root_trace, 'Expected ' + str(NB_MANIFESTS_EXPECTED) + ' manifests, but found ' 
                                    + str(len(all_manifests_dicts)))

            
            for manifest_nb in all_manifests_dict.keys():
                manifest_dict     = all_manifests_dict[manifest_nb]

                STORE.persistManifest(root_trace, manifest_dict)

            # Make explanations readable by creating a pretty 
            explanations_dict   = controller.show_your_work.as_dict(root_trace) | controller.link_table.as_dict(root_trace)
            explanations_nice   = DictionaryFormatter().dict_2_nice(    parent_trace    = root_trace,
                                                                        a_dict          = explanations_dict, 
                                                                        flatten=True, 
                                                                        delimeter="::")
            with open(MANIFESTS_OUTPUT_DIR + '/'  + EXPLANATIONS_OUTPUT, 'w') as file:
                file            .write(explanations_nice)

        except ApodeixiError as ex:
            if expect_error:
                raise ex
            else:
                print(ex.trace_message())                                                                                        

        self.assertTrue(len(all_manifests_dict) == NB_MANIFESTS_EXPECTED)
        for manifest_nb in all_manifests_dict.keys():
            manifest_dict   = all_manifests_dict[manifest_nb]
            kind            = manifest_dict['kind']
            self._compare_to_expected_yaml(root_trace, manifest_dict, test_case_name + "." + kind)
        with open(MANIFESTS_EXPECTED_DIR + '/'  + EXPLANATIONS_EXPECTED, 'r') as file:
                expected_explain        = file.read()
        self.assertEqual(explanations_nice,    expected_explain)

        

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        what_to_do = args[1]

        T = Test_MalformedInput()
        T.setUp()
        if what_to_do=='user_validation_0':
            T.test_user_validation_0()
        if what_to_do=='user_validation_1':
            T.test_user_validation_1()
        if what_to_do=='user_validation_2':
            T.test_user_validation_2()
        if what_to_do=='user_validation_3':
            T.test_user_validation_3()
        if what_to_do=='user_validation_4':
            T.test_user_validation_4()
        if what_to_do=='user_validation_5':
            T.test_user_validation_5()
        if what_to_do=='user_validation_6':
            T.test_user_validation_6()
        if what_to_do=='user_validation_7':
            T.test_user_validation_7()
        if what_to_do=='user_validation_8':
            T.test_user_validation_8()
        if what_to_do=='user_validation_9':
            T.test_user_validation_9()
        if what_to_do=='user_validation_10':
            T.test_user_validation_10()
    main(_sys.argv)
import sys                                              as _sys

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.testing_framework.mock_kb_store           import UnitTest_KnowledgeBaseStore
from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore

from apodeixi.util.formatting_utils                     import DictionaryFormatter
from apodeixi.knowledge_base.knowledge_base_util        import ManifestUtils
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

import time

class SkeletonControllerUnitTest(ApodeixiUnitTest):
    '''
    Abstract class used for commonly used testing procedures for controllers derived from 
    apodeixi.controllers.util.skeleton_controller.SkeletonController
    '''
    def setUp(self):
        super().setUp()

    def impl_testcase(self, parent_trace, test_name, controller_class, nb_manifests_expected=1, excel_sheet='Posting Label', ctx_range='b2:c1000'):

        t0                      = time.time()

        MANIFEST_FILE_PREFIX    = test_name

        EXCEL_FILE              = MANIFEST_FILE_PREFIX + '_INPUT.xlsx' 
        SHEET                   = excel_sheet
        CTX_RANGE               = ctx_range
        NB_MANIFESTS_EXPECTED   = nb_manifests_expected

        

        STORE_IMPL              = UnitTest_KnowledgeBaseStore(  test_case_name          = MANIFEST_FILE_PREFIX,
                                                                input_manifests_dir     = self.input_data, 
                                                                input_postings_dir      = self.input_data, 
                                                                output_manifests_dir    = self.output_data, 
                                                                output_postings_dir     = self.output_data)
        

        root_trace              = FunctionalTrace(parent_trace=None).doing("Discovering URL", data={'path'  : EXCEL_FILE,
                                                                                                  'sheet' : SHEET})
        STORE                   = KnowledgeBaseStore(root_trace, STORE_IMPL)
        posting_handle          = STORE.buildPostingHandle(root_trace, EXCEL_FILE, sheet=SHEET, excel_range=CTX_RANGE)

        MANIFESTS_DIR           = self.output_data
        EXPLANATIONS_OUTPUT     = MANIFEST_FILE_PREFIX + '_explanations_OUTPUT.yaml'
        EXPLANATIONS_EXPECTED   = MANIFEST_FILE_PREFIX + '_explanations_EXPECTED.yaml'
        all_manifests_dict      = []

        t100                    = time.time()
        try:
            my_trace          = parent_trace.doing("Generating manifest(s)")

            controller                  = controller_class(my_trace, STORE)
            t120                         = time.time()
            all_manifests_dict, label,   = controller._buildAllManifests(my_trace, posting_handle)

            if len(all_manifests_dict.keys()) != NB_MANIFESTS_EXPECTED:
                raise ApodeixiError(my_trace, 'Expected ' + str(NB_MANIFESTS_EXPECTED) + ' manifests, but found ' 
                                    + str(len(all_manifests_dict.keys())))

            
            t180                         = time.time()
            for manifest_nb in all_manifests_dict.keys():
                manifest_dict     = all_manifests_dict[manifest_nb]

                STORE.persistManifest(my_trace, manifest_dict)

            t200                      = time.time()
            # Make explanations readable by creating a pretty 
            explanations_nice   = DictionaryFormatter().dict_2_nice(    parent_trace    = my_trace, 
                                                                        a_dict          = controller.show_your_work.as_dict(my_trace), 
                                                                        flatten         = True, 
                                                                        delimeter       = "::")
            with open(MANIFESTS_DIR + '/'  + EXPLANATIONS_OUTPUT, 'w') as file:
                file            .write(explanations_nice)

        except ApodeixiError as ex:
            print(ex.trace_message())    

        t300                      = time.time()                                                                                    

        self.assertTrue(len(all_manifests_dict) == NB_MANIFESTS_EXPECTED)
        for manifest_nb in all_manifests_dict.keys():
            manifest_dict   = all_manifests_dict[manifest_nb]
            kind            = manifest_dict['kind']
            self._compare_to_expected_yaml(parent_trace, manifest_dict, MANIFEST_FILE_PREFIX + "." + kind)
        with open(MANIFESTS_DIR + '/'  + EXPLANATIONS_EXPECTED, 'r') as file:
                expected_explain        = file.read()
        self.assertEqual(explanations_nice,    expected_explain)

        t400                      = time.time()
        #print("************* Timing at 100: " + str(t100-t0))
        #print("************* Timing at 120: " + str(t120-t0))
        #print("************* Timing at 180: " + str(t180-t0))
        #print("************* Timing at 200: " + str(t200-t0))
        #print("************* Timing at 300: " + str(t300-t0))
        #print("************* Timing at 400: " + str(t400-t0))
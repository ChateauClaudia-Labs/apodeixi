import sys                                                      as _sys


from apodeixi.testing_framework.a6i_integration_test            import ApodeixiIntegrationTest, FileStoreTestStack
from apodeixi.util.formatting_utils                             import DictionaryFormatter
from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace

from apodeixi.controllers.journeys.delivery_planning.big_rocks  import BigRocksEstimate_Controller
from apodeixi.knowledge_base.knowledge_base                     import KnowledgeBase
from apodeixi.representers.as_excel                             import Manifest_Representer

class Test_KnowledgeBase_Integration(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()
        root_trace                  = FunctionalTrace(None).doing("Selecting stack for test case")
        self.selectStack(root_trace) 

    def selectStack(self, parent_trace):
        '''
        Called as part of setting up each integration test case. It chooses and provisions the stack that should
        be used by this test case.
        '''
        self._stack                 = FileStoreTestStack(parent_trace, self._config)

    def test_big_rocks_posting(self):

        TEST_CASE                       = 'big_rocks_posting'
         
        EXCEL_RELATIVE_PATH             = "journeys/Dec 2020/FusionOpus/Default"
        EXCEL_FILE                      = "OPUS_big-rocks.journeys.a6i.xlsx"

        self.setScenario("post_and_request_big_rocks")

        self._posting_testing_skeleton( test_case_name          = TEST_CASE,
                                        excel_relative_path     = EXCEL_RELATIVE_PATH,
                                        excel_file              = EXCEL_FILE)

    def _posting_testing_skeleton(self, test_case_name, excel_relative_path, excel_file):

        all_manifests_dicts                     = []
        ENVIRONMENT_NAME                        = test_case_name + "_ENV"
        try:
            root_trace                          = FunctionalTrace(parent_trace=None).doing("Testing post/requestForm scenario", 
                                                                                data={  'excel_file'    : excel_file},
                                                                                origination = {
                                                                                        'signaled_from' : __file__,
                                                                                        'concrete class': str(self.__class__.__name__)})

            my_trace                            = root_trace.doing("Isolating test case")
            self.provisionIsolatedEnvironment(my_trace, ENVIRONMENT_NAME)
            self._assert_current_environment(   parent_trace    = root_trace,
                                                snapshot_name   = test_case_name + "_POST_SNAPSHOT_0")

            my_trace                            = root_trace.doing("Calling 'postByFile' API")
            clientURL                           = self.stack().store().current_environment(my_trace).clientURL(my_trace)
            posting_path                        = clientURL + "/" + excel_relative_path + "/" + excel_file
            response, log_txt                   = self.stack().kb().postByFile( parent_trace                = my_trace, 
                                                                                path_of_file_being_posted   = posting_path, 
                                                                                excel_sheet                 = "Sheet1")

            NB_MANIFESTS_EXPECTED               = 3
            if len(response.createdManifests()) != NB_MANIFESTS_EXPECTED:
                raise ApodeixiError(my_trace, 'Expected ' + str(NB_MANIFESTS_EXPECTED) + ' manifests, but found ' 
                                    + str(len(all_manifests_dicts)))

            # Retrieve the manifests created
            manifest_dict                       = {}
            for handle in response.createdManifests():
                loop_trace                      = my_trace.doing("Retrieving manifest for handle " + str(handle),
                                                        origination = {    
                                                                    'concrete class': str(self.__class__.__name__), 
                                                                    'signaled_from': __file__})
                manifest_dict, manifest_path    = self.stack().store().retrieveManifest(loop_trace, handle)
                self._compare_to_expected_yaml(loop_trace, manifest_dict, test_case_name + "." + handle.kind)

            self._assert_current_environment(   parent_trace    = my_trace,
                                                snapshot_name   = test_case_name + "_POST_SNAPSHOT_1")

            # Check log is right
            self._compare_to_expected_txt(  parent_trace        = my_trace,
                                            output_txt          = log_txt,
                                            test_output_name    = test_case_name + "_LOG", 
                                            save_output_txt     = True)

            # At this point the posting seems completed successfully.
            # So as the next step, try to generate to forms suggested by the response to the posting
            my_trace                            = root_trace.doing("Calling 'requestForm' API")
            form_idx = 0
            def _regression_file(idx, purpose):
                return test_case_name + "_" + str(idx) + "_" + purpose
            for form_request in response.optionalForms() + response.mandatoryForms():
                fr_response, fr_log_txt, fr_rep                 = self.stack().kb().requestForm(  parent_trace    = root_trace, 
                                                                                        form_request    = form_request) 

                self._assert_current_environment(   parent_trace    = my_trace,
                                                    snapshot_name   = test_case_name + "_REQUEST_FORM_SNAPSHOT_" + str(form_idx))
                layout_info, pl_fmt_info, ws_fmt_info           = self._generated_form_test_output( my_trace, 
                                                                                                    form_request, 
                                                                                                    fr_response, 
                                                                                                    fr_log_txt, 
                                                                                                    fr_rep)
                self._compare_to_expected_txt(  parent_trace    = my_trace,
                                            output_txt          = fr_log_txt,
                                            test_output_name    = _regression_file(form_idx, "FORM_REQUEST_LOG"), 
                                            save_output_txt     = True) 
                self._compare_to_expected_txt(  parent_trace    = my_trace,
                                            output_txt          = layout_info,
                                            test_output_name    = _regression_file(form_idx, "LAYOUT"), 
                                            save_output_txt     = True) 
                self._compare_to_expected_txt(  parent_trace    = my_trace,
                                            output_txt          = pl_fmt_info,
                                            test_output_name    = _regression_file(form_idx, "POSTING_LABEL_FMT"), 
                                            save_output_txt     = True) 
                self._compare_to_expected_txt(  parent_trace    = my_trace,
                                            output_txt          = ws_fmt_info,
                                            test_output_name    = _regression_file(form_idx, "WORKSHEET_FMT"), 
                                            save_output_txt     = True) 
                form_idx += 1

            return
        except ApodeixiError as ex:
            print(ex.trace_message())                  

        # If we get this far, the tests failed since we should have returned within the try statement. 
        # So hardcode an informative failure.
        self.assertTrue("Shouldn't have gotten to this line" == 0)   

    def _generated_form_test_output(self, parent_trace, form_request, fr_response, fr_log_txt, fr_rep):
        '''
        Helper method that returns 3 strings with information on the generated form, so that it can be 
        validated that it matches regression output.

        It returns (in this order):

        * A string with layout information (e.g., # of columns, rows, widths, etc)
        * A string with Excel formatting information for the posting label worksheet of the generated form
        * A string with Excel formatting information for the main worksheet of the generated form
        '''
        # Check the layout for the generated form is right
        layout_output_nice                  = ""
        manifest_handles_dict               = form_request.manifestHandles(parent_trace)
        for key in manifest_handles_dict.keys():
            manifest_handle                         = manifest_handles_dict[key]
            layout_output_dict                      = {}

            layout_output_dict['layout span']       = fr_rep.span_dict[key]
            layout_output_dict['hidden columns']    = fr_rep.hidden_cols_dict[key]
            widths_dict                             = fr_rep.widths_dict_dict[key]
            layout_output_dict['column widths']     = DictionaryFormatter().dict_2_nice(parent_trace = parent_trace, 
                                                                                a_dict = widths_dict)
            layout_output_dict['total width']       = sum([widths_dict[k]['width'] for k in widths_dict.keys()])

            layout_output_nice          += "************** Layout information for Manifest '" + key + "' **********\n\n"

            layout_output_nice          += DictionaryFormatter().dict_2_nice(parent_trace = parent_trace, 
                                                                            a_dict = layout_output_dict)

        # Check the Excel formatting is right for the generated posting label
        posting_label_ws_info               = fr_rep.worksheet_info_dict[Manifest_Representer.POSTING_LABEL_SHEET]
        pl_ws_info_nice                     = self._nice_ws_info(parent_trace, posting_label_ws_info)

        # Check the Excel formatting is right for the main worksheet containing the manifests' information
        SHEET                               = BigRocksEstimate_Controller.GENERATED_FORM_WORKSHEET
        worksheet_info                      = fr_rep.worksheet_info_dict[SHEET]
        ws_info_nice                        = self._nice_ws_info(parent_trace, worksheet_info)

        return layout_output_nice, pl_ws_info_nice, ws_info_nice
                                                              

    def _nice_ws_info(self, parent_trace, worksheet_info):
        nice_format                     = ''
        nice_format += "\n======================== Column information ==========================\n"
        nice_format += DictionaryFormatter().dict_2_nice(parent_trace = parent_trace, a_dict = worksheet_info.colinfo)

        fmt_dict                        = worksheet_info.format_dict
        for row_nb in fmt_dict.keys():
            row_dict                    = fmt_dict[row_nb]
            for col_nb in row_dict.keys():
                nice_format += "\n\n================ Formats row = " + str(row_nb) + ", col = " + str(col_nb) + " ============"
                cell_fmt_dict           = row_dict[col_nb]
                nice                    = DictionaryFormatter().dict_2_nice(parent_trace = parent_trace, a_dict = cell_fmt_dict)
                nice_format += "\n" + nice
        return nice_format

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_KnowledgeBase_Integration()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='big_rocks_posting':
            T.test_big_rocks_posting()

    main(_sys.argv)
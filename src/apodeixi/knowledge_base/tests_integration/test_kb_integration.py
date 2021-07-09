import sys                                                      as _sys

from apodeixi.testing_framework.a6i_integration_test            import ApodeixiIntegrationTest
from apodeixi.util.formatting_utils                             import DictionaryFormatter
from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace

from apodeixi.controllers.journeys.delivery_planning.big_rocks  import BigRocksEstimate_Controller
from apodeixi.knowledge_base.knowledge_base                     import KnowledgeBase
from apodeixi.knowledge_base.kb_environment                     import KB_Environment_Config
from apodeixi.representers.as_excel                             import Manifest_Representer

class Test_KnowledgeBase_Integration(ApodeixiIntegrationTest):

    def setUp(self):
        super().setUp()

    def test_big_rocks_posting(self):

        TEST_CASE                       = 'big_rocks_posting'
        
        EXCEL_FILE                      = self.postings_folder + "/journeys/Dec 2020/FusionOpus/Default/" \
                                            + 'OPUS_big-rocks.journeys.a6i.xlsx' 

        self._posting_testing_skeleton( #store           = self.store, 
                                        test_case_name  = TEST_CASE,
                                        excel_file      = EXCEL_FILE)

    def _posting_testing_skeleton(self, test_case_name, excel_file): #store, test_case_name, excel_file):

        all_manifests_dicts                     = []
        ENVIRONMENT_NAME                        = test_case_name + "_ENV"
        try:
            root_trace                          = FunctionalTrace(parent_trace=None).doing("Posting excel file", 
                                                                                data={  'excel_file'    : excel_file},
                                                                                origination = {
                                                                                        'signaled_from' : __file__,
                                                                                        'concrete class': str(self.__class__.__name__)})

            #kbase                               = KnowledgeBase(root_trace, store)
            my_trace                    = root_trace.doing("Removing previously created environment, if any",
                                                        data = {'environment name': ENVIRONMENT_NAME})
            stat                        = self.store.removeEnvironment(parent_trace = my_trace, name = ENVIRONMENT_NAME)
            
            my_trace                    = root_trace.doing("Creating a sub-environment to do postings in")
            env_config                  = KB_Environment_Config(
                                                root_trace, 
                                                read_misses_policy  = KB_Environment_Config.FAILOVER_READS_TO_PARENT,
                                                use_timestamps      = False,
                                                path_mask           = self._path_mask)
            self.store.current_environment(my_trace).addSubEnvironment(my_trace, ENVIRONMENT_NAME, env_config)
            self.store.activate(parent_trace = my_trace, environment_name = ENVIRONMENT_NAME)
 
            response, log_txt                    = self.kb.postByFile(   parent_trace                = root_trace, 
                                                                        path_of_file_being_posted   = excel_file, 
                                                                        excel_sheet                 = "Sheet1")

            NB_MANIFESTS_EXPECTED               = 3
            if len(response.createdManifests()) != NB_MANIFESTS_EXPECTED:
                raise ApodeixiError(root_trace, 'Expected ' + str(NB_MANIFESTS_EXPECTED) + ' manifests, but found ' 
                                    + str(len(all_manifests_dicts)))

            # Retrieve the manifests created
            manifest_dict                       = {}
            for handle in response.createdManifests():
                loop_trace                      = root_trace.doing("Retrieving manifest for handle " + str(handle),
                                                        origination = {    
                                                                    'concrete class': str(self.__class__.__name__), 
                                                                    'signaled_from': __file__})
                manifest_dict, manifest_path    = self.store.retrieveManifest(loop_trace, handle)
                self._compare_to_expected_yaml(manifest_dict, test_case_name + "." + handle.kind)

            # Check log is right
            self._compare_to_expected_txt(  output_txt          = log_txt,
                                            test_case_name      = test_case_name + "_LOG", 
                                            save_output_txt     = True)

            # At this point the posting seems completed successfully.
            # So as the next step, try to generate to forms suggested by the response to the posting
            form_idx = 0
            def _regression_file(idx, purpose):
                return test_case_name + "_" + str(idx) + "_" + purpose
            for form_request in response.optionalForms() + response.mandatoryForms():
                fr_response, fr_log_txt, fr_rep                 = self.kb.requestForm(  parent_trace    = root_trace, 
                                                                                        form_request    = form_request) 
                layout_info, pl_fmt_info, ws_fmt_info           = self._generated_form_test_output(root_trace, 
                                                                                                    form_request, 
                                                                                                    fr_response, 
                                                                                                    fr_log_txt, 
                                                                                                    fr_rep)
                self._compare_to_expected_txt(  output_txt      = fr_log_txt,
                                            test_case_name      = _regression_file(form_idx, "FORM_REQUEST_LOG"), 
                                            save_output_txt     = True) 
                self._compare_to_expected_txt(  output_txt      = layout_info,
                                            test_case_name      = _regression_file(form_idx, "LAYOUT"), 
                                            save_output_txt     = True) 
                self._compare_to_expected_txt(  output_txt      = pl_fmt_info,
                                            test_case_name      = _regression_file(form_idx, "POSTING_LABEL_FMT"), 
                                            save_output_txt     = True) 
                self._compare_to_expected_txt(  output_txt      = ws_fmt_info,
                                            test_case_name      = _regression_file(form_idx, "WORKSHEET_FMT"), 
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
        layout_output_nice                          = ""
        for manifest_handle in form_request.manifestHandles(parent_trace):

            kind                                    = manifest_handle.kind
            layout_output_dict                      = {}

            layout_output_dict['layout span']       = fr_rep.span_dict[kind]
            widths_dict                             = fr_rep.widths_dict_dict[kind]
            layout_output_dict['column widths']     = DictionaryFormatter().dict_2_nice(parent_trace = parent_trace, 
                                                                                a_dict = widths_dict)
            layout_output_dict['total width']       = sum([widths_dict[k]['width'] for k in widths_dict.keys()])

            layout_output_nice          += "************** Layout information for Manifest '" + kind + "' **********\n\n"

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
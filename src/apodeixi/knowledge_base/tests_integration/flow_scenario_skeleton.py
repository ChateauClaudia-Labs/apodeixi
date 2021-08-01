from apodeixi.testing_framework.a6i_integration_test            import ApodeixiIntegrationTest
from apodeixi.util.formatting_utils                             import DictionaryFormatter
from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace

from apodeixi.knowledge_base.knowledge_base_util                import FormRequest
from apodeixi.representers.as_excel                             import ManfiestRepresenter


class FlowScenarioSkeleton(ApodeixiIntegrationTest):
    '''
    Abstract class.

    Used as a helper class for integration test cases involving flows of multiple KnowledgeBase API calls.
    Provides re-usable utilities for common things to check, consistent naming of regression output files,
    and skeleton test drivers that concrete classes can use to succintly define flow test scenarios.

    @param from_nothing A boolean to determine if we should request a form even before any manifest exists
                        (i.e., a "blank" form)
    @param namespace A string. Only relevant if from_nothing=True. Used to delimit the search for manifests
                        when generating a form without explicit manifest handles being given.
    @param subnamespace A string. Only relevant if from_nothing=True. Used to delimit search for manifests.
                    An optional string representing a slice of the namespace that further restricts
                    the manifest names to search. If set to None, not subspace is assumed.
                    Example: in the manifest name "modernization.default.dec-2020.fusionopus", the
                            token "modernization" is the subnamespace. The other tokens come from filing coordinates
                            for the posting from whence the manifest arose.
    '''

    def _run_basic_flow(self,   from_nothing,           namespace,                  subnamespace,       posting_api, 
                                excel_relative_path,    excel_file,                 excel_sheet, 
                                nb_manifests_expected,  generated_form_worksheet):
        '''
        Tests a basic flow for a single posting API consisting of:

        * Request a blind form (only if "from_nothing" = True)
        * Submit an initial posting
        * Request update form
        * Submit an update to initial posting
        '''
        try:
            root_trace                      = FunctionalTrace(parent_trace=None).doing("Test scenario", 
                                                    data={  'excel_file'    : excel_file,
                                                            'scenario'      : self.scenario(),
                                                            'test name'     : self.currentTestName()},
                                                    origination = {
                                                            'signaled_from' : __file__,
                                                            'concrete class': str(self.__class__.__name__)})

            my_trace                        = self.trace_environment(root_trace, "Isolating test case")
            if True:
                self.provisionIsolatedEnvironment(my_trace)
                self.check_environment_contents(my_trace)

            if from_nothing: # Make a blind call get `requestForm`, without knowing a priori the manifest handles
                my_trace                    = self.trace_environment(root_trace, "Blind call to 'requestForm' API")
                if True: 
                    store                   = self.stack().kb().store
                    blind_form_request      = store.getBlindFormRequest(    parent_trace    = my_trace, 
                                                                            relative_path   = excel_relative_path, 
                                                                            posting_api     = posting_api,
                                                                            namespace       = namespace,
                                                                            subnamespace    = subnamespace)

                    fr_response, fr_log_txt, \
                        fr_rep              = self.stack().kb().requestForm(parent_trace    = root_trace, 
                                                                            form_request    = blind_form_request) 

                    self.check_environment_contents(my_trace) 
                    layout_info, pl_fmt_info, \
                        ws_fmt_info         = self._generated_form_test_output( my_trace, 
                                                                                blind_form_request, 
                                                                                fr_response, 
                                                                                fr_log_txt, 
                                                                                fr_rep, 
                                                                                generated_form_worksheet)
                    api_called              = "initial requestForm"

                    self.check_log(my_trace, fr_log_txt, api_called=api_called)

                    self.check_xl_layout(my_trace, layout_info, generated_form_worksheet, api_called)

                    self.check_xl_format(my_trace, pl_fmt_info, ManfiestRepresenter.POSTING_LABEL_SHEET, api_called)

                    self.check_xl_format(my_trace, ws_fmt_info, generated_form_worksheet, api_called)


            my_trace                        = self.trace_environment(root_trace, "Calling 'postByFile' API")
            if True:
                clientURL                   = self.stack().store().current_environment(my_trace).clientURL(my_trace)
                posting_path                = clientURL + "/" + excel_relative_path + "/" + excel_file
                response, log_txt           = self.stack().kb().postByFile( parent_trace                = my_trace, 
                                                                            path_of_file_being_posted   = posting_path, 
                                                                            excel_sheet                 = excel_sheet)
                self.check_manifest_count(my_trace, response, nb_manifests_expected)

                self.check_manifests_contents(my_trace, response)

                self.check_environment_contents(   parent_trace    = my_trace)

                self.check_log(my_trace, log_txt, api_called="postByFile")

            my_trace                        = self.trace_environment(root_trace, "Calling 'requestForm' API")
            form_request_responses          = []
            if True:
                form_idx = 0

                for form_request in response.optionalForms() + response.mandatoryForms():
                    fr_response, fr_log_txt, \
                        fr_rep              = self.stack().kb().requestForm(parent_trace    = root_trace, 
                                                                            form_request    = form_request) 

                    self.check_environment_contents(my_trace) 
                    layout_info, pl_fmt_info, \
                        ws_fmt_info         = self._generated_form_test_output( my_trace, 
                                                                                form_request, 
                                                                                fr_response, 
                                                                                fr_log_txt, 
                                                                                fr_rep, 
                                                                                generated_form_worksheet)
                    api_called              = "requestForm #" + str(form_idx) 

                    self.check_log(my_trace, fr_log_txt, api_called=api_called)

                    self.check_xl_layout(my_trace, layout_info, generated_form_worksheet, api_called)

                    self.check_xl_format(my_trace, pl_fmt_info, ManfiestRepresenter.POSTING_LABEL_SHEET, api_called)

                    self.check_xl_format(my_trace, ws_fmt_info, generated_form_worksheet, api_called)

                    '''
                    Save the form before we change it
                    '''
                    self.snapshot_generated_form(my_trace, fr_response)

                    form_request_responses.append(fr_response)
                    form_idx += 1

            my_trace                        = self.trace_environment(root_trace, "Doing an update via 'postByFile' API")
            if True:
                for fr_response in form_request_responses:
                    # Copy the "modified form" that has some edits in it
                    self.modify_form(my_trace, fr_response)
                    form_path   = fr_response.clientURL(my_trace) + "/" + fr_response.getRelativePath(my_trace)

                    update_response, update_log_txt = self.stack().kb().postByFile( parent_trace                = my_trace, 
                                                                                path_of_file_being_posted   = form_path)

                    self.check_manifest_count(my_trace, update_response, nb_manifests_expected)

                    self.check_manifests_contents(my_trace, update_response)

                    self.check_environment_contents(   parent_trace    = my_trace)

                    self.check_log(my_trace, update_log_txt, api_called="postByFile")

            return
        except ApodeixiError as ex:
            print(ex.trace_message())                  

        # If we get this far, the tests failed since we should have returned within the try statement. 
        # So hardcode an informative failure.
        self.assertTrue("Shouldn't have gotten to this line" == 0)   


    def check_manifest_count(self, parent_trace, posting_response, nb_manifests_expected):
        # Check we created as many manifests as was expected
        if len(posting_response.createdManifests()) != nb_manifests_expected:
            raise ApodeixiError(parent_trace, 'Expected ' + str(nb_manifests_expected) + ' manifests, but found ' 
                                + str(len(posting_response.createdManifests())))

    def check_manifests_contents(self, parent_trace, posting_response):
        # Retrieve the manifests created and check they have the data we expect
        manifest_dict                       = {}
        for handle in posting_response.createdManifests():
            loop_trace                      = self.trace_environment(parent_trace, "Retrieving manifest for handle " 
                                                                                    + str(handle))
            manifest_dict, manifest_path    = self.stack().store().retrieveManifest(loop_trace, handle)
            self._compare_to_expected_yaml(loop_trace, manifest_dict, test_output_name = self.next_manifest(handle.kind))

    def check_log(self, parent_trace, log_data, api_called):
        self._compare_to_expected_txt(  parent_trace        = parent_trace,
                                        output_txt          = log_data,
                                        test_output_name    = self.next_log(api_called), 
                                        save_output_txt     = True)
        
    def check_xl_layout(self, parent_trace, layout_info, sheet, api_called):
        self._compare_to_expected_txt(  parent_trace    = parent_trace,
                                    output_txt          = layout_info,
                                    test_output_name    = self.next_xl_layout(sheet, api_called),
                                    save_output_txt     = True) 

    def check_xl_format(self, parent_trace, format_info, sheet, api_called):
        self._compare_to_expected_txt(  parent_trace        = parent_trace,
                                        output_txt          = format_info,
                                        test_output_name    = self.next_xl_format(sheet, api_called),
                                        save_output_txt     = True) 

    def _generated_form_test_output(self, parent_trace, form_request, fr_response, fr_log_txt, fr_rep, generated_form_worksheet):
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
        for key in fr_response.getManifestIdentifiers(parent_trace): #manifest_handles_dict.keys():
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

        # Extract Excel formatting for the generated posting label
        posting_label_ws_info               = fr_rep.worksheet_info_dict[ManfiestRepresenter.POSTING_LABEL_SHEET]
        pl_ws_info_nice                     = self._nice_ws_info(parent_trace, posting_label_ws_info)

        # Extract Excel formatting for the main worksheet containing the manifests' information
        worksheet_info                      = fr_rep.worksheet_info_dict[generated_form_worksheet]
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

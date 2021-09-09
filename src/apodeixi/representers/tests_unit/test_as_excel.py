import sys                                                      as _sys
import pandas                                                   as _pd

from apodeixi.testing_framework.a6i_unit_test                   import ApodeixiUnitTest
from apodeixi.testing_framework.controllers.mock_controller     import Mock_Controller
from apodeixi.util.formatting_utils                             import DictionaryFormatter
from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace

from apodeixi.controllers.util.skeleton_controller              import SkeletonController
from apodeixi.representers.as_excel                             import ManifestRepresenter
from apodeixi.text_layout.excel_layout                          import ManifestXLWriteConfig, \
                                                                        AsExcel_Config_Table, \
                                                                        PostingLabelXLWriteConfig


class Test_ManifestRepresenter(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_dataframe_2_xl(self):

        NAME                    = 'test_dataframe_2_xl'
        INPUT_FOLDER            = self.input_data
        INPUT_FILE              = NAME + '_INPUT.csv'
        OUTPUT_FOLDER           = self.output_data
        EXCEL_FILE              = NAME + '_MANIFEST.xlsx'
        SHEET                   = 'Manifest'
        OUTPUT_FILE             = NAME
 
        WS_INFO_FILE     = NAME + '_worksheet_info'

        PL_WS_INFO_FILE     = NAME + '_posting_label_ws_info'

        MANIFEST_NAME           = 'Manifest for ' + NAME + ".57"
        output_dict             = {}

        worksheet_info_dict     = {}
        try:
            root_trace          = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing generating an Excel from a manifest")
            my_trace            = root_trace.doing("Loading input CSV file for test")
            data_df             = self.load_csv(my_trace, INPUT_FOLDER + '/' + INPUT_FILE)

            # data_df.columns are ['UID', 'jobs-to-be-done', 'Stakeholders', 'UID-1', 'Capabilities', 'UID-2', 'Feature', 'UID-3', 'Story']
            # Make editable any column not starting with "UID"
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            
            xlw_config          = ManifestXLWriteConfig(sheet               = SHEET,
                                                        manifest_name       = MANIFEST_NAME,
                                                        read_only           = False,
                                                        is_transposed       = False,     
                                                        viewport_width      = 100,  
                                                        viewport_height     = 40,   
                                                        max_word_length     = 20, 
                                                        editable_cols       = editable_cols, 
                                                        hidden_cols         = [],  
                                                        editable_headers    = [],   
                                                        x_offset            = 0,    
                                                        y_offset            = 0)
            xlw_config_table        = AsExcel_Config_Table()
            xlw_config_table.addManifestXLWriteConfig(my_trace, xlw_config)

            my_trace            = root_trace.doing("Creating Excel layout for Posting Label")
            label_dict          = {"Testing from": "test_as_excel.py", 
                                    "Verifying": "Correct population of Excel with respect to data, layout and formatting"}
            label_xlw_config    = PostingLabelXLWriteConfig(     sheet               = ManifestRepresenter.POSTING_LABEL_SHEET,
                                                            viewport_width      = 100,  
                                                            viewport_height     = 40,   
                                                            max_word_length     = 20,  
                                                            editable_fields     = [],   
                                                            x_offset            = 1,    
                                                            y_offset            = 1)
            xlw_config_table.setPostingLabelXLWriteConfig(my_trace, label_xlw_config)

            my_trace            = root_trace.doing("Creating content to display")
            # The ManifestRepresenter API requires a dict of ManifestInfo objects, but for this test
            # we only care about the part of the ManifestInfo that is the DataFrame. So we create a
            # ManifestInfo with a dummy manifest_dict, and then manually set the DataFrame we want in the
            # ManifestInfo (overwriting the DataFrame that was generated from the dummy manifest_dict)
            #
            # We also need a dummy controller consistent with the dummy manifest
            dummy_manifest_dict = {"kind": "hierarchy", "assertion": {"asset-class": {}}}
            dummy_controller    = Mock_Controller(root_trace, store=None, a6i_config = self.a6i_config)
            dummy_manifest_info = SkeletonController._ManifestInfo( parent_trace            = my_trace,
                                                                    key                     = MANIFEST_NAME,
                                                                    manifest_dict           = dummy_manifest_dict,
                                                                    controller              = dummy_controller)
            # A bit of a hack, since content_df should be generated from the ManifestInfo's manifest_dict, but
            # for our unit test this is the DataFrame we want to use.
            dummy_manifest_info._contents_df                    = data_df 
            dummy_content_dict                                  = {"JTBD1": 
                                                                    {"UID":                     "JTBD1",
                                                                    "Capabilities": {"C1": 
                                                                        {"UID":                 "JTBD1.C1",
                                                                        "Feature": {"F1": 
                                                                            {"UID":             "JTBD1.C1.F1",
                                                                            "Story": {"S1": 
                                                                                {"UID":         "JTBD1.C1.F1.S1"}}}}}}}}
            
            dummy_manifest_dict['assertion']['asset-class']     = dummy_content_dict

            my_trace            = root_trace.doing("Displaying the content in Excel")
            rep                 = ManifestRepresenter(  parent_trace        = my_trace,
                                                        xlw_config_table    = xlw_config_table,
                                                        label_ctx           = label_dict,
                                                        manifestInfo_dict   = {MANIFEST_NAME: dummy_manifest_info},)

            status              = rep.dataframe_to_xl(  parent_trace    = my_trace, 
                                                        excel_folder    = OUTPUT_FOLDER, 
                                                        excel_filename  = EXCEL_FILE)

            worksheet_info                      = rep.worksheet_info_dict[SHEET]
            posting_label_ws_info               = rep.worksheet_info_dict[ManifestRepresenter.POSTING_LABEL_SHEET]

            output_dict['status']           = status
            output_dict['layout span']      = rep.span_dict[MANIFEST_NAME]
            widths_dict                     = rep.widths_dict_dict[MANIFEST_NAME]
            output_dict['column widths']    = DictionaryFormatter().dict_2_nice(parent_trace = root_trace, 
                                                                                a_dict = widths_dict)
            output_dict['total width']      = sum([widths_dict[k]['width'] for k in widths_dict.keys()])

            output_nice         = DictionaryFormatter().dict_2_nice(parent_trace = root_trace, a_dict = output_dict)

            self._compare_to_expected_txt(  parent_trace    = root_trace,
                                        output_txt          = output_nice,
                                        test_output_name    = OUTPUT_FILE, 
                                        save_output_txt     = True) 

            ws_info_nice         = self._nice_ws_info(root_trace, worksheet_info)
            self._compare_to_expected_txt(  parent_trace    = root_trace,
                                        output_txt          = ws_info_nice,
                                        test_output_name    = WS_INFO_FILE, 
                                        save_output_txt     = True)

            pl_ws_info_nice         = self._nice_ws_info(root_trace, posting_label_ws_info)
            self._compare_to_expected_txt(  parent_trace    = root_trace,
                                        output_txt          = pl_ws_info_nice,
                                        test_output_name    = PL_WS_INFO_FILE, 
                                        save_output_txt     = True)

        except ApodeixiError as ex:
            print(ex.trace_message())
            self.assertTrue(1==2)                                                                                        

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
        T = Test_ManifestRepresenter()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='dataframe_2_xl':
            T.test_dataframe_2_xl()


    main(_sys.argv)
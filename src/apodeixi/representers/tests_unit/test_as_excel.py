import sys                                  as _sys
import pandas                               as _pd

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.formatting_utils             import DictionaryFormatter
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace

from apodeixi.representers.as_excel             import Manifest_Representer
from apodeixi.text_layout.excel_layout          import ManifestXLConfig, AsExcel_Config_Table, PostingLabelXLConfig


class Test_Manifest_Representer(ApodeixiUnitTest):

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

        MANIFEST_NAME           = 'Manifest for ' + NAME
        output_dict             = {}

        worksheet_info_dict     = {}
        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Testing generating an Excel from a manifest")
            my_trace            = root_trace.doing("Loading input CSV file for test")
            data_df             = self.load_csv(my_trace, INPUT_FOLDER + '/' + INPUT_FILE)

            # data_df.columns are ['UID', 'jobs-to-be-done', 'Stakeholders', 'UID-1', 'Capabilities', 'UID-2', 'Feature', 'UID-3', 'Story']
            # Make editable any column not starting with "UID"
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            
            config              = ManifestXLConfig( sheet               = SHEET,
                                                    manifest_name       = MANIFEST_NAME,    
                                                    viewport_width      = 100,  
                                                    viewport_height     = 40,   
                                                    max_word_length     = 20, 
                                                    editable_cols       = editable_cols,   
                                                    editable_headers    = [],   
                                                    x_offset            = 0,    
                                                    y_offset            = 0)
            config_table        = AsExcel_Config_Table()
            config_table.addManifestXLConfig(my_trace, config)

            my_trace            = root_trace.doing("Creating Excel layout for Posting Label")
            label_dict          = {"Testing from": "test_as_excel.py", 
                                    "Verifying": "Correct population of Excel with respect to data, layout and formatting"}
            label_config        = PostingLabelXLConfig(     sheet               = Manifest_Representer.POSTING_LABEL_SHEET,
                                                            viewport_width      = 100,  
                                                            viewport_height     = 40,   
                                                            max_word_length     = 20,  
                                                            editable_fields     = [],   
                                                            x_offset            = 1,    
                                                            y_offset            = 1)
            config_table.setPostingLabelXLConfig(my_trace, label_config)

            rep                 = Manifest_Representer(config_table)

            status              = rep.dataframe_to_xl(  parent_trace    = root_trace, 
                                                        content_df_dict = {MANIFEST_NAME: data_df}, 
                                                        label_dict      = label_dict,
                                                        excel_folder    = OUTPUT_FOLDER, 
                                                        excel_filename  = EXCEL_FILE)

            worksheet_info                      = rep.worksheet_info_dict[SHEET]
            posting_label_ws_info               = rep.worksheet_info_dict[Manifest_Representer.POSTING_LABEL_SHEET]

            output_dict['status']           = status
            output_dict['layout span']      = rep.span_dict[MANIFEST_NAME]
            widths_dict                     = rep.widths_dict_dict[MANIFEST_NAME]
            output_dict['column widths']    = DictionaryFormatter().dict_2_nice(parent_trace = root_trace, 
                                                                                a_dict = widths_dict)
            output_dict['total width']      = sum([widths_dict[k]['width'] for k in widths_dict.keys()])

            output_nice         = DictionaryFormatter().dict_2_nice(parent_trace = root_trace, a_dict = output_dict)

            self._compare_to_expected_txt(  output_txt      = output_nice,
                                        test_case_name      = OUTPUT_FILE, 
                                        save_output_txt     = True) 

            ws_info_nice         = self._nice_ws_info(root_trace, worksheet_info)
            self._compare_to_expected_txt(  output_txt      = ws_info_nice,
                                        test_case_name      = WS_INFO_FILE, 
                                        save_output_txt     = True)

            pl_ws_info_nice         = self._nice_ws_info(root_trace, posting_label_ws_info)
            self._compare_to_expected_txt(  output_txt      = pl_ws_info_nice,
                                        test_case_name      = PL_WS_INFO_FILE, 
                                        save_output_txt     = True)

        except ApodeixiError as ex:
            print(ex.trace_message())                                                                                        

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
        T = Test_Manifest_Representer()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='dataframe_2_xl':
            T.test_dataframe_2_xl()


    main(_sys.argv)
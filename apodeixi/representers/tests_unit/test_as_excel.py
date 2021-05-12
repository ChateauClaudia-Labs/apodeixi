import sys                                  as _sys
import pandas                               as _pd

from apodeixi.util.a6i_unit_test            import ApodeixiUnitTest
from apodeixi.util.a6i_error                import ApodeixiError, FunctionalTrace

from apodeixi.representers.as_excel         import Manifest_Representer
from apodeixi.text_layout.excel_layout      import Manifest_Config #, ManifestLayout


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
        OUTPUT_FILE             = NAME + '_OUTPUT.txt'
        EXPECTED_FILE           = NAME + '_EXPECTED.txt'

        WS_INFO_OUTPUT_FILE     = NAME + '_worksheet_info_OUTPUT.txt'
        WS_INFO_EXPECTED_FILE   = NAME + '_worksheet_info_EXPECTED.txt'

        MANIFEST_NAME           = 'Manifest for ' + NAME
        output_dict             = {}
        expected                = None # Make it different than output so we don't accidentally pass the test if processing aborts

        worksheet_info_dict     = {}
        ws_info_expected        = None
        try:

            data_df             = self.load_csv(INPUT_FOLDER + '/' + INPUT_FILE)

            # data_df.columns are ['UID', 'jobs-to-be-done', 'Stakeholders', 'UID-1', 'Capabilities', 'UID-2', 'Feature', 'UID-3', 'Story']
            # Make editable any column not starting with "UID"
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            root_trace          = FunctionalTrace(parent_trace=None).doing("Testing generating an Excel from a manifest")
            config              = Manifest_Config(  name_list           = [MANIFEST_NAME],    
                                                    viewport_width      = 100,  
                                                    viewport_height     = 40,   
                                                    max_word_length     = 20, 
                                                    editable_cols       = editable_cols,   
                                                    editable_headers    = [],   
                                                    x_offset            = 0,    
                                                    y_offset            = 0)

            rep                 = Manifest_Representer(config)

            status              = rep.dataframe_to_xl(  parent_trace    = root_trace, 
                                                        content_df_dict = {MANIFEST_NAME: data_df}, 
                                                        excel_folder    = OUTPUT_FOLDER, 
                                                        excel_filename  = EXCEL_FILE, 
                                                        sheet           = SHEET)

            worksheet_info                      = rep.worksheet_info
            #worksheet_info_dict['Column info']  = worksheet_info.colinfo

            
            #worksheet_info_dict['Format info']  = self.dict_2_nice(worksheet_info.format_dict)

            #span                            = rep.config.layout.getSpan(root_trace)
            output_dict['status']           = status
            output_dict['layout span']      = rep.span
            output_dict['column widths']    = self.dict_2_nice(rep.widths_dict)
            output_dict['total width']      = sum([rep.widths_dict[k]['width'] for k in rep.widths_dict.keys()])
            #output_dict['max row height']   = max([widths_dict[k]['nb_lines'] for k in widths_dict.keys()])
            # Save output in case we want to do a diff to expected output during a failure/debugging
            output_nice         = self.dict_2_nice(output_dict)
            with open(OUTPUT_FOLDER + '/' + OUTPUT_FILE, 'w') as file:
                file            .write(output_nice)
            ws_info_nice         = self._nice_ws_info(worksheet_info)
            with open(OUTPUT_FOLDER + '/' + WS_INFO_OUTPUT_FILE, 'w') as file:
                file            .write(ws_info_nice)

            # Load expected output
            with open(OUTPUT_FOLDER + '/' + EXPECTED_FILE, 'r') as file:
                expected        = file.read()
            with open(OUTPUT_FOLDER + '/' + WS_INFO_EXPECTED_FILE, 'r') as file:
                ws_info_expected        = file.read()

        except ApodeixiError as ex:
            print(ex.trace_message())                                                                                        

        self.assertEqual(output_nice,       expected)
        self.assertEqual(ws_info_nice,  ws_info_expected)

    def _nice_ws_info(self, worksheet_info):
        nice_format                     = ''
        nice_format += "\n======================== Column information =========================="
        nice_format += self.dict_2_nice(worksheet_info.colinfo)

        fmt_dict                        = worksheet_info.format_dict
        for row_nb in fmt_dict.keys():
            row_dict                    = fmt_dict[row_nb]
            for col_nb in row_dict.keys():
                nice_format += "\n\n================ Formats row = " + str(row_nb) + ", col = " + str(col_nb) + " ============"
                cell_fmt_dict           = row_dict[col_nb]
                nice                    = self.dict_2_nice(cell_fmt_dict)
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
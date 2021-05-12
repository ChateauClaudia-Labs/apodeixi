import pandas                               as _pd
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range

from apodeixi.util.a6i_error                import ApodeixiError
from apodeixi.text_layout.excel_layout      import ManifestLayout
from apodeixi.text_layout.column_layout     import ColumnWidthCalculator
from .as_dataframe                          import AsDataframe_Representer

class Manifest_Representer:
    '''
    Class that can represent an Apodeixi manifest as an Excel spreadsheet

    @param An Manifest_Config object
    '''
    def __init__(self, config):
        self.config             = config

        # Some intermediate values computed in the course of processing, which are saved as state to facilitate debugging
        self.widths_dict        = None
        self.span               = None
        self.worksheet_info     = None

        return

    def yaml_2_xl(self, parent_trace, 
                        manifests_folder, manifests_file,       # Path to the YAML file to load
                        contents_path,                          # Path inside the YAML tree to the sub-tree with the content
                        excel_folder, excel_filename, sheet,    # Path to the Excel spreadsheet to be created
                        ):
        df_rep                  = AsDataframe_Representer()
        content_df, subtree     = df_rep.yaml_to_df(parent_trace, manifests_folder, manifests_file, contents_path)

        self.dataframe_to_xl(parent_trace, content_df, excel_folder, excel_filename, sheet)

    def dataframe_to_xl(self, parent_trace, content_df_dict, excel_folder, excel_filename, sheet):
    
        my_trace                = parent_trace.doing("Creating Excel workbook",
                                                        data = {'folder': excel_folder, 'filename': excel_filename, 'sheet': sheet})
        workbook                = xlsxwriter.Workbook(excel_folder + '/' + excel_filename)
        worksheet               = workbook.add_worksheet(sheet) 

        # We want to protect only some cells that we put in. For their protection to turn on, we must protect the worksheet. 
        worksheet.protect(options = {'insert_rows': True, 'insert_columns': True})

        for name in content_df_dict.keys():
            df                  = content_df_dict[name]
            layout              = self.config.layouts_dict[name]
            self._populate_content(my_trace, df, layout, workbook, worksheet)
        
        # Now we must unprotect a large area outside the cells we pasted
        self._unprotect_free_space(my_trace, worksheet)

        # Before we close the workbook, remember some of the worksheet's formatting info in  simple-types-only dictionaries
        # to support regression testing
        self.worksheet_info     = XL_WorksheetInfo()
        self.worksheet_info.build(worksheet)

        workbook.close()

        return "Success"

    def _populate_posting_label(self, parent_trace):
        raise ApodeixiError(parent_trace, "Not impelemented")

    def _populate_content(self, parent_trace, content_df, layout, workbook, worksheet):
        '''
        Helper method to write the block in Excel that comes from the manifest's content (as opposed to the Posting Label data).
        Returns the layout against which the `content_df` was pasted.
        '''
        #layout                  = self.config.layout
        my_trace                = parent_trace.doing("Building out the layout")
        if True:
            layout.build(parent_trace, content_df,  editable_cols       = self.config.editable_cols, 
                                                    editable_headers    = self.config.editable_headers, 
                                                    x_offset            = self.config.x_offset, 
                                                    y_offset            = self.config.y_offset)
            layout.validate(my_trace)
            span                = layout.getSpan(my_trace) # Useful to carry around for debugging
            inner_trace         = my_trace.doing("Computing optimal column widths", data = {'layout span': str(span)})
            # Compute optimal widths for the columns
            calc                = ColumnWidthCalculator(    data_df             = content_df, 
                                                            viewport_width      = self.config.viewport_width, 
                                                            viewport_height     = self.config.viewport_height, 
                                                            max_word_length     = self.config.max_word_length)
            
            # Dictionary - keys are columns of content_df, vals are sub-dicts {'width': <number>, 'nb_lines': <number>}
            widths_dict         = calc.calc(inner_trace) 

            # Remember these to support debugging
            self.widths_dict    = widths_dict
            self.span           = span

        
        # Now we start laying out content on the worksheet. Start by re-sizing the columns and setting the 
        if True:
            my_trace            = parent_trace.doing("Populating headers", data = {'layout span': str(span)})
            columns             = content_df.columns
            for idx in range(len(columns)):
                col             = columns[idx]
                loop_trace      = my_trace.doing("Processing column '" + col + "'")
                width           = int(widths_dict[col]['width']) # Cast to int to avoid errors if width is e.g. 20.0
                x               = self.config.x_offset + idx
                y               = self.config.y_offset
                fmt_dict        = layout.getFormat(loop_trace, x, y)
                fmt             = workbook.add_format(fmt_dict)
                worksheet.set_column(x, x, width)
                worksheet.write(y, x, col, fmt)

        # Now lay out the content
        my_trace                = parent_trace.doing("Populating content", data = {'layout span': str(span)})
        if True:
            for row in content_df.iterrows():
                row_nb      = row[0]
                row_content = row[1]
                for idx in range(len(columns)):
                    col             = columns[idx]
                    loop_trace      = my_trace.doing("Processing column = '" + col + "' row = '" + str(row_nb) + "'")
                    x               = self.config.x_offset + idx 
                    y               = self.config.y_offset + 1 + row_nb # An extra '1' because of the headers
                    fmt_dict        = layout.getFormat(loop_trace, x, y)
                    fmt             = workbook.add_format(fmt_dict)
                    worksheet.write(y, x, row_content[col], fmt)

       
    def _unprotect_free_space(self, my_trace, worksheet):
        '''
        Scans a large range of cells (limit is hard coded) and unprotects any cell that is not in any layout
        '''
        LIMIT                           = 500
        layouts                         = [self.config.layouts_dict[k] for k in self.config.layouts_dict.keys()]

        # Recall that layout.getSpan return [[xmin, ymin], [xmax, ymax]]
        global_xmin                     = min([layout.getSpan(my_trace)[0][0] for layout in layouts])
        global_ymin                     = min([layout.getSpan(my_trace)[0][1] for layout in layouts])
        global_xmax                     = max([layout.getSpan(my_trace)[1][0] for layout in layouts])
        global_ymax                     = max([layout.getSpan(my_trace)[1][1] for layout in layouts])

        # Outside the global area, unprotect entire ranges. If global span is A1:F20, we unprotect G1:ZZ500 and A21:ZZ500, kind of
        distant_columns = xl_range( 0,                          global_xmax + 1,    
                                    LIMIT,                      LIMIT + global_xmax + 1)

        distant_rows    = xl_range( global_ymax + 1,    0,                  
                                    LIMIT + global_ymax + 1,    LIMIT)

        worksheet.unprotect_range(distant_columns)
        worksheet.unprotect_range(distant_rows)
        
        # With the global area, unprotect any empty space not in any layout (e.g., if pasting multiple
        # manifests, there will be empty space between them)
        for x in range(global_xmin, global_xmax + 1):
            for y in range(global_ymin,global_ymax + 1):
                hits = [layout.name for layout in layouts if layout.contains(my_trace, x, y)]
                if len(hits) == 0: # We never pasted this point, so unprotect it
                    cell                = xl_rowcol_to_cell(y, x)
                    worksheet.unprotect_range(cell)




class XL_WorksheetInfo():
    '''
    Helper class used to record formatting information about a worksheet in a dictionary form that only relies on simple types.
    Helpful for developing regression tests to confirm that there is not regression in how an Excel spreadsheet is
    formatted.
    '''
    def __init__(self):
        self.format_dict = {}
        self.colinfo     = {}
    
    def build(self, worksheet):
        self.colinfo     = worksheet.__dict__['colinfo']
        
        table = worksheet.__dict__['table']
        for row_nb in table.keys():
            self.format_dict[row_nb] = {}
            row_dict = table[row_nb]
            for col_nb in row_dict.keys():
                self.format_dict[row_nb][col_nb] = {}
                cell_struct = row_dict[col_nb]
                fmt        = cell_struct.format.__dict__
                self.format_dict[row_nb][col_nb] = fmt
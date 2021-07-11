import pandas                               as _pd
import xlsxwriter
from xlsxwriter.utility                     import xl_rowcol_to_cell, xl_range

from apodeixi.util.a6i_error                import ApodeixiError
from apodeixi.text_layout.column_layout     import ColumnWidthCalculator
from apodeixi.text_layout.excel_layout      import PostingLayout
from apodeixi.representers.as_dataframe     import AsDataframe_Representer

class Manifest_Representer:
    '''
    Class that can represent an Apodeixi manifest as an Excel spreadsheet

    @param An AsExcel_Config_Table object
    '''
    def __init__(self, config_table):
        self.config_table       = config_table

        # Some intermediate values computed in the course of processing, which are saved as state to facilitate debugging
        self.widths_dict_dict       = {}
        self.span_dict              = {}
        self.hidden_cols_dict       = {}
        self.worksheet_info_dict    = {}

        return

    POSTING_LABEL_SHEET     = "Posting Label"
    SUCCESS                 = "Success"

    def dataframe_to_xl(self, parent_trace, content_df_dict, label_dict, excel_folder, excel_filename):
        '''
        '''
        my_trace                = parent_trace.doing("Creating Excel workbook",
                                                        data = {'folder': excel_folder, 'filename': excel_filename})
        workbook                = xlsxwriter.Workbook(excel_folder + '/' + excel_filename)

        inner_trace             = parent_trace.doing("Creating Posting Label")
        self._write_posting_label(inner_trace, workbook, label_dict)

        inner_trace             = parent_trace.doing("Writing manifest's data")
        self._write_dataframes(inner_trace, workbook, content_df_dict)

        workbook.close()

        return Manifest_Representer.SUCCESS

    def _write_dataframes(self, parent_trace, workbook, content_df_dict):
        '''
        Creates and populates one or more worksheets, each containing data for one or more manifests.
        Each manifest's data is inputed as a DataFrame.

        The worksheet onto which a manifest's data is laid out is the worksheet whose name is listed in
        self.config_table[key] where key is a string identifying a manifest (i.e., a dataset). These
        `key' strings are the same as the dictionary keys in content_df_dict.

        @content_df_dict A dict object, whose keys are strings representing the name of a dataset, and the
                        values are the manifests expressed as a Pandas DataFrame
        '''

        manifest_worksheet_list = []
        for name in content_df_dict.keys():
            loop_trace          = parent_trace.doing("Populating Excel content for '" + str(name) + "'")
            df                  = content_df_dict[name]
            config              = self.config_table.getManifestXLConfig(loop_trace, name)
            worksheet               = workbook.get_worksheet_by_name(config.sheet)
            if worksheet == None:
                worksheet               = workbook.add_worksheet(config.sheet) 
                # We want to protect only some cells that we put in. For their protection to turn on, we must protect the worksheet. 
                worksheet.protect(options = {'insert_rows': True, 'insert_columns': True})
                manifest_worksheet_list.append(worksheet)
            self._populate_worksheet(loop_trace, df, config, workbook, worksheet)
            self._write_text_label( parent_trace    = loop_trace, 
                                    workbook        = workbook,
                                    worksheet       = worksheet, 
                                    xl_config       = config, 
                                    text            = name)
        
        # Now we must unprotect a large area outside the cells we pasted, which may span multiple
        # manifests per worksheet, potentially
        for worksheet in manifest_worksheet_list:
            self._unprotect_free_space(parent_trace, worksheet = worksheet)
            self._remember_formatting(worksheet, worksheet.get_name())

    def _write_posting_label(self, parent_trace, workbook, label_dict):
        '''
        Creates and populates a PostingLabel worksheet
        '''
        ME                      = Manifest_Representer
        label_config            = self.config_table.getPostingLabelXLConfig(parent_trace)


        tmp_dict                = {}
        for key in label_dict.keys():
            tmp_dict[key] = [label_dict[key]]
        label_df         = _pd.DataFrame(tmp_dict)
        
        posting_label_worksheet  = workbook.add_worksheet(label_config.sheet) 
        # We want to protect only some cells that we put in. For their protection to turn on, we must protect the worksheet. 
        posting_label_worksheet.protect(options = {'insert_rows': True, 'insert_columns': True})
        self._populate_worksheet(parent_trace, label_df, label_config, workbook, posting_label_worksheet)

        # Write the title above the PostingLabel
        self._write_text_label( parent_trace    = parent_trace, 
                                workbook        = workbook,
                                worksheet       = posting_label_worksheet, 
                                xl_config       = label_config, 
                                text            = ME.POSTING_LABEL_SHEET)

        self._remember_formatting(posting_label_worksheet, ME.POSTING_LABEL_SHEET)

    def _write_text_label(self, parent_trace, workbook, worksheet, xl_config, text):
        '''
        Writes a string (parameter `text`) right above the area in the worksheet where the data defined by
        `xl_config` would go. Used, for example, to put a title like "Posting Label" in an Excel cell right above
        where the posting label data would be laid out

        If there is no space (e.g., if the xl_config would lay out the data starting at row 0, so any text label
        would go on "inexistent" row -1), then this method
        does not raise an error but the changes it makes to the behind-the-scenes Excel formatting state will not
        be visible to the user.

        @param xl_config An object derived from AsExcel_Config, defining where a piece of data (e.g., a manifest,
                            posting label, or other) is to be laid out in an Excel spreadsheet.
        '''
        title_x             = xl_config.x_offset
        title_y             = xl_config.y_offset - 1
        title               = text
        fmt_dict            ={'bold': True, 'font_color': PostingLayout.DARK_BLUE}
        fmt                 = workbook.add_format(fmt_dict)
        worksheet.write(title_y, title_x, title, fmt)

    def _remember_formatting(self, worksheet, sheet):
        '''
        Remembers some of the worksheet's formatting info in  simple-types-only dictionaries
        to support regression testing
        '''
        worksheet_info                      = XL_WorksheetInfo()
        worksheet_info.build(worksheet)
        self.worksheet_info_dict[sheet]     = worksheet_info

    def _set_column_width(self, parent_trace, worksheet, xl_x, column_width, layout):
        '''
        Helper method to set a column width for a worksheet
        '''
        worksheet.set_column(xl_x,      xl_x,       column_width)

    def _write_val(self, parent_trace, workbook, worksheet, layout_x, layout_y, val, layout):
        
        if layout.is_transposed:
            xl_x            = layout_y
            xl_y            = layout_x
        else:
            xl_x            = layout_x
            xl_y            = layout_y
        
        fmt_dict        = layout.getFormat(parent_trace, layout_x, layout_y)
        fmt             = workbook.add_format(fmt_dict)
        worksheet.write(xl_y, xl_x, val, fmt)

    def _populate_worksheet(self, parent_trace, content_df, config, workbook, worksheet):
        '''
        Helper method to write the block in Excel that comes from the manifest's content (as opposed to the Posting Label data).
        Returns the layout against which the `content_df` was pasted.

        Transpose functionality is supported. So we have 2 spaces:

        1. "Layout space" - those are the coordinates for content_df and config, config.layout. We use layout_x, layout_y
            for these coordinates.
        2. "Excel space" - the coordinates in Excel. We use xl_x, xl_y for these coordinates.

        The relationship between both spaces depends on the config.layout.is_transposed flag. If True, then

            xl_x = layout_y and xl_y = layout_x.

        Otherwise, xl_x = layout_x and xl_y = layout_y

        @param config An AsExcel_Config object specifying how the data in `content_df` should be laid out on 
                        the worksheet
        '''
        layout                  = config.layout
        is_transposed           = layout.is_transposed

        my_trace                = parent_trace.doing("Building out the layout")

        if True:
            displayable_cols    = [col for col in content_df.columns if not col in config.hidden_cols]
            displayable_df      = content_df[displayable_cols]
            config.buildLayout(parent_trace, content_df)

            #layout              = config.layout
            layout.validate(my_trace)
            span                = layout.getSpan(my_trace) # Useful to carry around for debugging
            inner_trace         = my_trace.doing("Computing optimal column widths", data = {'layout span': str(span)})
            # Compute optimal widths for the columns
            if is_transposed:
                # Besides transposing, reset index so layout headers become a column, so they get included in 
                # calculation of widths (else they are ignored, being an index in the transpose)
                xl_df           = displayable_df.transpose().reset_index() 
                
            else:
                xl_df           = displayable_df
            calc                = ColumnWidthCalculator(    data_df             = xl_df, 
                                                            viewport_width      = config.viewport_width, 
                                                            viewport_height     = config.viewport_height, 
                                                            max_word_length     = config.max_word_length)
            
            # Dictionary - keys are columns of displayable_df, vals are sub-dicts {'width': <number>, 'nb_lines': <number>}
            widths_dict         = calc.calc(inner_trace) 

            # Remember these to support debugging
            name                            = layout.name
            self.widths_dict_dict[name]     = widths_dict
            self.span_dict[name]            = span
            self.hidden_cols_dict[name]     = config.hidden_cols

        
        # Now we start laying out content on the worksheet. 
        # Start by re-sizing the columns.
        if True:
            my_trace            = parent_trace.doing("Setting column widths")
            xl_columns          = xl_df.columns 
            for xl_idx in range(len(xl_columns)): # GOTCHA: Loop is in "Excel space"
                col             = xl_columns[xl_idx]
                loop_trace      = my_trace.doing("Processing XL column '" + col + "'")
                width           = int(widths_dict[col]['width']) # Cast to int to avoid errors if width is e.g. 20.0
                if is_transposed:
                    xl_x        = config.y_offset + xl_idx
                else:
                    xl_x        = config.x_offset + xl_idx
                self._set_column_width(loop_trace, worksheet, xl_x, width, layout)
   
        # Now populate headers
        if True:
            my_trace            = parent_trace.doing("Populating headers", data = {'layout span': str(span)})
            columns             = displayable_df.columns
            for layout_idx in range(len(columns)): # GOTCHA: Loop is in "Layout space"
                col             = columns[layout_idx]
                loop_trace      = my_trace.doing("Processing layout column '" + col + "'")
                #width           = int(widths_dict[col]['width']) # Cast to int to avoid errors if width is e.g. 20.0
                layout_x        = config.x_offset + layout_idx
                layout_y        = config.y_offset
                if is_transposed:
                    xl_x        = layout_y
                else:
                    xl_x        = layout_x
                #self._set_column_width(loop_trace, worksheet, xl_x, width, layout)
                self._write_val(loop_trace, workbook, worksheet, layout_x, layout_y, col, layout)


        # Now lay out the content
        my_trace                = parent_trace.doing("Populating content", data = {'layout span': str(span)})
        if True:
            for row in displayable_df.iterrows(): # GOTCHA: Loop is in "Layout space"
                row_nb      = row[0]
                row_content = row[1]
                for layout_idx in range(len(columns)):
                    col             = columns[layout_idx]
                    loop_trace      = my_trace.doing("Processing column = '" + col + "' row = '" + str(row_nb) + "'")
                    layout_x        = config.x_offset + layout_idx 
                    layout_y        = config.y_offset + 1 + row_nb # An extra '1' because of the headers
                 
                    self._write_val(parent_trace, workbook, worksheet, layout_x, layout_y, row_content[col], layout)

    def _unprotect_free_space(self, my_trace, worksheet):
        '''
        Scans a large range of cells (limit is hard coded) and unprotects any cell that is not in any layout
        for any manifest
        '''
        LIMIT                           = 500

        layouts                         = [config.layout for config in self.config_table.manifest_configs()]

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
                #self.format_dict[row_nb][col_nb] = {}
                cell_struct = row_dict[col_nb]
                fmt        = cell_struct.format.__dict__
                self.format_dict[row_nb][col_nb] = fmt
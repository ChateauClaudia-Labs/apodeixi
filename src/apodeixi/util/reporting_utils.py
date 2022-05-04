
from apodeixi.text_layout.excel_layout                          import Palette

from apodeixi.util.a6i_error                                    import ApodeixiError
from apodeixi.util.dataframe_utils                              import DataFrameUtils



class ReportWriterUtils():
    '''
    Utility class aiming to provide common methods for writing Excel reports
    '''
    def __init__(self):

        # We call self.write_report multiple times, and want each subsequent time to never shrink columns to
        # less than previously set.
        # That is the purpose of this dictionary
        #
        #   Keys are ints (column number starting at 0), and values are floats (column width)
        self.remembered_column_widths = {}

    def _set_column_width(self, parent_trace, report_ws, column_nb, width):
        '''
        Helper method.
        Wraps the corresponding xlsxwriter method by "remembering" widths and making sure they are never
        less than what might have been previously set as the width for the column in question.

        This comes handy when multiple DataFrames are reported on the same worksheet.

        @column_nb An int, representing a column number, starting at 0
        @width A float, representing the width of a column
        '''
        if column_nb in self.remembered_column_widths.keys():
            prior_width             = self.remembered_column_widths[column_nb]
            width_to_use            = max(width, prior_width)
        else:
            width_to_use            = width

        self.remembered_column_widths[column_nb] = width_to_use

        report_ws.set_column(column_nb, column_nb, width_to_use)

    def write_report(self, parent_trace, report_df, column_widths, workbook, sheet, description, x_offset=0, y_offset=0):
        '''
        Helper method used as part of the process to create one or more reports in an Excel file.

        The caller determines how many worksheets the Excel file should have, and is reponsible for persisting the
        Excel file.
        
        This method helps with the portion of that process that populates the contents of one of the worksheets, i.e.,
        one report.
        Thus the caller is expected to have initialized the an xlsxwriter.Workbook object, to which a call to 
        this method results in adding and populating a worksheet.

        After this method returns, the caller is responsible for saving the `workbook` object.

        The content for the report populated by this method comes from  `data`, with headers taken from `columns`

        The amount of space taken by the report is (N + 2) * (M + 1), where:
        * N is the number of rows in `report_df`. Two additioal rows are added at the top: for the description, and the columns.
        * M is the number of columns. An additional column is added on the left, for the index of `report_df`

        @param report_df A DataFrame, whose contents are to be written into Excel
        @param column_widths: A list of floats, whose length must equal the number of elements in `columns`.
            They determine how wide each of the Excel columns should be
        @param workbook An xlsxwriter.Workbook object, to which the report must be added in a dedicated worksheet
        @param sheet A string, corresponding to the name in the `workbook` into which the report must be written
        @param description A string, used to give a description of the report. Example: "big-rock_v1-v2_diff".

        @param x_offset The first Excel column with content for this report. Defaults to 0. 
        @param y_offset The first Excel column for the content of this report. Defaults to 0. 
        '''
        ROOT_FMT                        = {'text_wrap': True, 'valign': 'top', 'border': True, 'border_color': Palette.WHITE}
        HEADER_FMT                      = ROOT_FMT | {'bold': True, 'font_color': Palette.WHITE, 'align': 'center','border_color': Palette.WHITE, 
                                                            'right': True, 'fg_color':     Palette.DARK_BLUE} 

        header_format                   = workbook.add_format(HEADER_FMT)  

        report_ws                       = workbook.get_worksheet_by_name(sheet)
        if report_ws == None:
            report_ws                   = workbook.add_worksheet(sheet)
            report_ws.set_zoom(85)

        contextual_trace                = parent_trace.doing("Writing a report",
                                            data = {"description": str(description), "sheet": str(sheet)})
        my_trace                        = contextual_trace.doing("Writing out the description")
        if True:
            fmt_dict            ={'bold': True, 'font_color': Palette.DARK_BLUE}
            fmt                 = workbook.add_format(fmt_dict)
            self._write_val(    parent_trace    = my_trace, 
                                ws              = report_ws, 
                                x               = x_offset + 1, 
                                y               = y_offset, 
                                val             = description, 
                                fmt             = fmt) 

        my_trace                        = contextual_trace.doing("Extracting data and row labels")
        if True:
            # GOTCHA -
            #       For some reports, the index is not an integer. If we do DataFrame.iterrows(), 
            #   the "index" row[0] might be a string, not an int, as we need for the "idx%s" remainder logic to alternate
            #   row colors.
            #   So we do a prepartory loop to get the row data into a list of series objects, and another loop on a 
            #   list so we have integer indexing as we count row numbers
            data_rows                               =  [] # A list of series, one per row
            row_labels                              = []
            for row in report_df.iterrows():
                data_rows.append(row[1])
                row_labels.append(str(row[0]))
            labels_width = max([len(label) for label in row_labels]) * 1.1
            # Make enough room for the row labels
            #report_ws.set_column(x_offset, x_offset, labels_width)
            self._set_column_width(parent_trace, report_ws, x_offset, labels_width)

        my_trace                        = contextual_trace.doing("Writing out columns")  
        columns                         = list(report_df.columns)
        # Check if we have a multi-level index
        if type(columns[0]) == tuple:
            nb_levels = len(columns[0])
            y_offset                    += nb_levels - 1

        if True:
            # Write the headers. 
            for idx in range(len(columns)):
                #report_ws.set_column(idx + x_offset + 1, idx + x_offset + 1, column_widths[idx])
                self._set_column_width(parent_trace, report_ws, idx + x_offset + 1, column_widths[idx])
                col                     = columns[idx]
                if type(col) == tuple:
                    for level in range(nb_levels):
                        self._write_val(    parent_trace    = my_trace, 
                                            ws              = report_ws, 
                                            x               = idx + x_offset + 1, 
                                            y               = y_offset + 2 - nb_levels + level, 
                                            val             = col[level], 
                                            fmt             = header_format) 
                else:
                    self._write_val(        parent_trace    = my_trace, 
                                            ws              = report_ws, 
                                            x               = idx + x_offset + 1, 
                                            y               = y_offset + 1, 
                                            val             = col, 
                                            fmt             = header_format) 

        
        my_trace                        = contextual_trace.doing("Writing the rows")
        if True:

            for idx in range(len(data_rows)):
                row                                 = data_rows[idx]
                # First write the row label
                self._write_val(    parent_trace    = my_trace, 
                                    ws              = report_ws, 
                                    x               = x_offset, 
                                    y               = idx + y_offset + 2, 
                                    val             = row_labels[idx], 
                                    fmt             = header_format) 
                # Now write the "real" columns                
                for jdx in range(len(columns)):
                    col                             = columns[jdx]
                    val                             = row[col]
                    clean_val                       = DataFrameUtils().clean(val)
                    fmt_dict                        = ROOT_FMT.copy()
                    if idx%2 == 0: 
                        fmt_dict                    |= {'bg_color': Palette.LIGHT_BLUE}
                    fmt                             = workbook.add_format(fmt_dict)
                     
                    # GOTCHA
                    # 
                    #   For some reports (e.g., diffs of manifests), the clean_val might be a "field name", i.e., the column in 
                    # a DataFrame's column for a manifest being diff-ed.
                    # In such cases, clean_val might be a tuple if it is a MultiLevel column in the manifest's DataFrame. 
                    # If so, covert it to a string to avoid errors writing it out.
                    #
                    if type(clean_val) == tuple:
                        clean_val                   = str(clean_val)

                    self._write_val(    parent_trace    = my_trace, 
                                        ws              = report_ws, 
                                        x               = jdx + x_offset + 1, 
                                        y               = idx + y_offset + 2, 
                                        val             = clean_val, 
                                        fmt             = fmt)           

    def _write_val(self, parent_trace, ws, x, y, val, fmt):
        '''
        Helper method to wrap xlsxwriter in order to catch its Exceptions
        '''
        try:
            ws.write(y, x, val, fmt)
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Unable to write value to Excel",
                                    data = {"x": str(x), "y": str(y), "val": str(val), "error": str(ex)})


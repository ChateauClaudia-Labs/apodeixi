
from apodeixi.text_layout.excel_layout                          import Palette

from apodeixi.util.a6i_error                                    import ApodeixiError
from apodeixi.util.dataframe_utils                              import DataFrameUtils
from apodeixi.util.time_buckets                                 import FY_Quarter

class ReportWriterUtils():
    '''
    Utility class aiming to provide common methods for writing Ecel reports
    '''
    def __init__(self):
        pass

    def write_report(self, parent_trace, report_df, column_widths, workbook, sheet, description):
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

        @param report_df A DataFrame, whose contents are to be written into Excel
        @param column_widths: A list of floats, whose length must equal the number of elements in `columns`.
            They determine how wide each of the Excel columns should be
        @param workbook An xlsxwriter.Workbook object, to which the report must be added in a dedicated worksheet
        @param sheet A string, corresponding to the name in the `workbook` into which the report must be written
        @param description A string, used to give a description of the report. Example: "big-rock_v1-v2_diff".
        '''
        ROOT_FMT                        = {'text_wrap': True, 'valign': 'top', 'border': True, 'border_color': Palette.WHITE}
        HEADER_FMT                      = ROOT_FMT | {'bold': True, 'font_color': Palette.WHITE, 'align': 'center','border_color': Palette.WHITE, 
                                                            'right': True, 'fg_color':     Palette.DARK_BLUE} 

        header_format                   = workbook.add_format(HEADER_FMT)  

        report_ws                       = workbook.add_worksheet(sheet)
        x_offset                        = 1
        y_offset                        = 3
        contextual_trace                = parent_trace.doing("Writing a report",
                                            data = {"description": str(description), "sheet": str(sheet)})
        my_trace                        = contextual_trace.doing("Writing out the description")
        if True:
            self._write_val(    parent_trace    = my_trace, 
                                ws              = report_ws, 
                                x               = x_offset, 
                                y               = 0, 
                                val             = description, 
                                fmt             = None) 

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
            report_ws.set_column(x_offset-1, x_offset-1, labels_width)

        my_trace                        = contextual_trace.doing("Writing out columns")  
        columns                         = list(report_df.columns)
        # Check if we have a multi-level index
        if type(columns[0]) == tuple:
            nb_levels = len(columns[0])
            y_offset                    += nb_levels - 1

        if True:
            # Write the headers. 
            for idx in range(len(columns)):
                report_ws.set_column(idx + x_offset, idx + x_offset, column_widths[idx])
                col                     = columns[idx]
                if type(col) == tuple:
                    for level in range(nb_levels):
                        self._write_val(    parent_trace    = my_trace, 
                                            ws              = report_ws, 
                                            x               = idx + x_offset, 
                                            y               = y_offset - nb_levels + level, 
                                            val             = col[level], 
                                            fmt             = header_format) 
                else:
                    self._write_val(        parent_trace    = my_trace, 
                                            ws              = report_ws, 
                                            x               = idx + x_offset, 
                                            y               = y_offset - 1, 
                                            val             = col, 
                                            fmt             = header_format) 

        
        my_trace                        = contextual_trace.doing("Writing the rows")
        if True:

            for idx in range(len(data_rows)):
                row                                 = data_rows[idx]
                # First write the row label
                self._write_val(    parent_trace    = my_trace, 
                                    ws              = report_ws, 
                                    x               = x_offset -1, 
                                    y               = idx + y_offset, 
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
                    
                    #report_ws.write(idx + y_offset, jdx + x_offset, val, fmt) 
                    self._write_val(    parent_trace    = my_trace, 
                                        ws              = report_ws, 
                                        x               = jdx + x_offset, 
                                        y               = idx + y_offset, 
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


    def to_timebucket_columns(self, parent_trace, a6i_config, df):
        '''
        Returns a DataFrame, identical to df except that columns are modified as follows:

        * Any column of form ("Q2", "FY23") - is mapped to a FY_Quarter object
        * Any consecutive segment of FY_Quarter objects are sorted
        * The returned DataFrame's columns are strings created from the FY_Quarter objects, for columns that are time buckets 
        * Other columns are "left as is" unless they are tuples, in which case they are flattened to a string by concatenating
          stringified tuple members
        * Columns that are not time buckets appear in the same location as in the original `df`
        * Columns that are time buckets are "locally sorted", meaning: each consecutive interval of time buckets is sorted, but
          time buckets from different intervals are not compared in sorting ("different intervals" as in: there is a non-time bucket
          column between the intervals)
        '''
        original_columns                = list(df.columns)

        my_trace                        = parent_trace.doing("Flattening (<Quarter>, <Fiscal Year>) column tuples")
        unsorted_flattened_columns      = []
        # As we flatten columns in the loop below, we also partition the columns into intervals, where each interval
        # either consists only of FY_Quarter objects, or only of strings which don't represent time buckets.
        # So intervals is a list of pairs: first member is the type for the interval (str or FY_Quarter), and second
        # member is the elements of the interval (as a list)
        intervals                       = []
        current_typed_interval          = None # A pair of (type, list)
        current_type                    = None # In the loop, this is either str or FY_Quarter
        month_fiscal_year_starts        = a6i_config.getMonthFiscalYearStarts(my_trace)

        def _add_flattened_col(val):
            '''
            Helper method to handle all the "state management" of the loop when a new flattened column is added.
            This means:
            * Appending to the unsorted_flattened_columns
            * Determining if we are entering a new interval, and if so create it
            * Append to the current interval
            '''
            nonlocal current_type
            nonlocal current_typed_interval
            nonlocal intervals
            nonlocal unsorted_flattened_columns
            if type(val) == FY_Quarter:
                unsorted_flattened_columns.append(val.display())
            else:
                unsorted_flattened_columns.append(val)
            if type(val) != current_type:
                # We are entering a new interval
                current_type            = type(val)
                current_typed_interval  = [type(val), []]
                intervals.append(current_typed_interval)
            # Add to current interval
            current_typed_interval[1].append(val)
            # Initialize for next cycle of loop
            

        for col in original_columns:
            loop_trace                  = my_trace.doing("Considering to create a FY_Quarter for " + str(col))
            if type(col) == tuple:
                flattened_col           = " ".join([str(elt) for elt in col]).strip()
                try:
                    timebucket              = FY_Quarter.build_FY_Quarter(loop_trace, flattened_col, month_fiscal_year_starts)
                except ApodeixiError as ex:
                    pass # This column is not a timebucket, so "leave flattening as is"
                    _add_flattened_col(flattened_col)
                # If we get here, then there is a real timebucket, so add its formatted representation
                _add_flattened_col(timebucket)
            else:
                # Column is not a tuple, so leave it "as is"
                _add_flattened_col(col)

        unsorted_df                     = df.copy()
        unsorted_df.columns             = unsorted_flattened_columns

        # Now sort and concatenate the intervals
        sorted_columns                  = []
        for typed_interval in intervals:
            if typed_interval[0] == FY_Quarter:
                unsorted_timebuckets    = typed_interval[1]
                # We sort by year first, then by quarter. A trick to accomplish this is to use a key where we multiply the year by 100,
                # so quarters become the last significant digit modulo 100
                sorted_timebuckets      = sorted(unsorted_timebuckets, key = lambda bucket: bucket.fiscal_year*100 + bucket.quarter)
                sorted_columns.extend([bucket.display() for bucket in sorted_timebuckets])
            else:
                sorted_columns.extend(typed_interval[1])

        sorted_df                       = unsorted_df[sorted_columns]
        return sorted_df

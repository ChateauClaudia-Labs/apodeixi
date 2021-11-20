
import pandas                                                   as _pd

from apodeixi.text_layout.excel_layout                          import Palette

from apodeixi.util.a6i_error                                    import ApodeixiError
from apodeixi.util.dataframe_utils                              import DataFrameUtils
from apodeixi.util.time_buckets                                 import FY_Quarter

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

class TimebucketStandardizer():
    '''
    Utility class to transform DataFrame columns with timebucket-like information into a standardized representation
    for them.
    Works with both MultiLevel or string columns in the original DataFrame.

    Example: For a column like "2023", its standardized equivalent would be "FY23"
    Example: For a column like 
                ("Sales", "Q3", "2024", "Actuals"), 
            its standardized equivalent would be
                ("Sales", "Q3 FY24", "Actuals")

    This class ensures consistency in how standardization is done across MultiLevel columns, in that
    it validates that all columns with time bucket information contains that information at the same levels.
    '''
    def __init__(self):
        '''
        '''
        return

    def is_a_timebucket_column(self, parent_trace, raw_col, a6i_config):
        '''
        Returns a boolean stating if `raw_col` is for a timebucket column.

        @raw_col A string or a tuple of strings.
        '''
        standarized_col, timebucket, timebucket_indices = self.standardizeOneTimebucketColumn(
                                                                    parent_trace                = parent_trace, 
                                                                    raw_col                     = raw_col, 
                                                                    a6i_config                  = a6i_config, 
                                                                    expected_collapsing_info    = None)
        if timebucket != None:
            return True
        else:
            return False

    def standardizeAllTimebucketColumns(self, parent_trace, a6i_config, df):
        '''
        Returns two things:
        
        1. A DataFrame, identical to df except that columns are modified as per the list below
        1. A TimebucketStandardizationInfo object, containing information on how the standardization was done (e.g.,
            for multi-level columns, which level was the time bucket and which levels were collapsed, if any)

        * Any column of form ("Q2", "FY23") - is mapped to a FY_Quarter object
        * Any consecutive "consistent" segment of FY_Quarter objects are sorted - and two FY_Quarter objects are "consistent"
          if they arise from columns whose higher-order levels (if any) are the same. 
            Example: ("Sales", "Q2", "FY 23", "Actual") and ("Sales", "Q1", "2005", "Target") are consistent: level 0 is
                    the same for both columns ("Sales")
            Example: ("Actuals", "Q2", "FY 23") and ("Target", "Q1", "2005") are *not* consistent since level 0 has different
                    values in the columns ("Actuals" vs "Target"), so they are viewed as belonging to different intervals, 
                    for sorting purposes.
        * The returned DataFrame's columns are strings created from the FY_Quarter objects, for columns that are time buckets 
        * Lower-level columns are "left as is" unless they are tuples, in which case they are flattened to a string by concatenating
          stringified tuple members
        * Columns that are not time buckets appear in the same location as in the original `df`
        * Columns that are time buckets are "locally sorted", meaning: each consecutive interval of time buckets is sorted, but
          time buckets from different intervals are not compared in sorting ("different intervals" as in: there is a non-time bucket
          column between the intervals)
        '''
        original_columns                = list(df.columns)

        unsorted_flattened_columns      = []
        # As we flatten columns in the loop below, we also partition the columns into intervals, where each interval
        # either consists only of FY_Quarter objects, or only of strings which don't represent time buckets.
        #
        # So intervals is a list of triples: 
        #  1. a boolean tag T that determines whether the interval is for columns containing time buckets (True)
        #  2. a list X of for columns (possibly tuples) that comprise the interval
        #  3. a list Y such that:
        #       a) len(Y)  == len(X)
        #       b) For each idx in range, Y[idx] is either None or a FY_Quarter object
        #       c) If tag T is False, then Y[idx] == None for all idx
        #       d) if tag T is True, then Y[idx] is a FY_Quarter object for all idx, corresponding to the timebucket
        #           that appears in X[idx] in string form
        # .
        # 
        intervals                               = []

        # A pair of (boolean, list), where the boolean is true if this interval is for columns containing time buckets
        current_interval                        = None
        current_interval_is_timebuckets         = False

        def _add_flattened_col(val, timebucket, timebucket_indices):
            '''
            Helper method to handle all the "state management" of the loop when a new flattened column is added.
            This means:
            * Appending to the unsorted_flattened_columns
            * Determining if we are entering a new interval, and if so create it
            * Append to the current interval
            '''
            nonlocal current_interval_is_timebuckets
            nonlocal current_interval
            nonlocal intervals
            nonlocal unsorted_flattened_columns

            unsorted_flattened_columns.append(val)

            val_is_a_timebucket                 = type(timebucket) == FY_Quarter # A boolean


            if current_interval_is_timebuckets != val_is_a_timebucket:
                # We toggled from/to having time buckets, so are entering a new interval since one has time buckets
                # and the other does not, making them different intervals
                entering_new_interval           = True
            elif val_is_a_timebucket and type(val) ==tuple and current_interval != None:
                # While both current and prior columns have time bickets, we need to check if they are
                # "consistent", i.e., higher-level values of the multi level index are the same. If they are not
                # then we should treat the prior and current columns as belonging to different intervals and not
                # be sorted together.
                #    Example: ("Sales", "Q2", "FY 23", "Actual") and ("Sales", "Q1", "2005", "Target") are consistent: level 0 is
                #            the same for both columns ("Sales")
                #    Example: ("Actuals", "Q2", "FY 23") and ("Target", "Q1", "2005") are *not* consistent since level 0 has different
                #            values in the columns ("Actuals" vs "Target"), so they are viewed as belonging to different intervals, 
                #            for sorting purposes.     
                #            
                prior_val                       = current_interval[1][-1] # We know this is a tuple and therefore timebucket_indices is not empty
                timebucket_idx                  = timebucket_indices[0]
                if prior_val[:timebucket_idx] == val[:timebucket_idx]:
                    entering_new_interval       = False
                else:
                    entering_new_interval       = True
            else:
                entering_new_interval           = False

            if entering_new_interval:
                # We toggled, so are entering a new interval
                current_interval_is_timebuckets = val_is_a_timebucket
                current_interval                = [val_is_a_timebucket, [], []]
                intervals.append(current_interval)
            elif current_interval == None: # This only happens in first cycle of loop and if first column is not a timebucket
                current_interval                = [False, [], []]
                intervals.append(current_interval)

            # Add to current interval
            current_interval[1].append(val)
            current_interval[2].append(timebucket)
           
        # This is used to ensure that we have consistency across the columns in terms of where the
        # timebucket columns get collapsed, if they get collapsed. 
        # It can be inferred when we encounter the first column that is a timebucket, which means we will have to
        # a preparatory pass through the columns, just to figure out the collapsing_info.
        #
        # Once we have it, we loop again throught the columns, this time doing the real work, enforcing consistency
        # as per that expected collapsing info
        # 
        my_trace                                = parent_trace.doing("Preparatory loop to determine the standardization_info")
        if True:
            standardization_info                = None
            for idx in range(len(original_columns)):
                col                             = original_columns[idx]
                loop_trace                      = my_trace.doing("Searcing for common_collapsing info from column " + str(col))
                flattened_col, timebucket, timebucket_indices   = self.standardizeOneTimebucketColumn(loop_trace, 
                                                                            raw_col                     = col, 
                                                                            a6i_config                  = a6i_config,
                                                                            expected_collapsing_info    = None)

                if timebucket != None: # Found it! Initialize the collapsing expection we can then apply to process cols
                    if type(flattened_col) == str:
                        final_size              = 1
                    else: # flattened_col is a tuple
                        final_size              = len(flattened_col)
                    if type(col) == str:
                        initial_size            = 1
                    else: # col is a tuple
                        initial_size            = len(col)
                    standardization_info      = TimebucketStandardizationInfo(loop_trace, 
                                                                initial_size            = initial_size, 
                                                                final_size              = final_size, 
                                                                timebucket_indices      = timebucket_indices)
                    break

        my_trace                                = parent_trace.doing("Looping through the columns to flatten them")
        if True:
            for idx in range(len(original_columns)):
                col                                 = original_columns[idx]
                loop_trace                          = my_trace.doing("Considering to create a FY_Quarter for " + str(col))
                flattened_col, timebucket, timebucket_indices   = self.standardizeOneTimebucketColumn(loop_trace, 
                                                                            raw_col                     = col, 
                                                                            a6i_config                  = a6i_config,
                                                                            expected_collapsing_info    = standardization_info)

                if timebucket == None and idx > 0 and current_interval_is_timebuckets and type(col) == tuple:
                    # This column is not a timebucket, so we might do additional
                    # cleaning of the tuple `flattened_col` because the preceding column was a timebucket
                    # (since current_interval_is_timebuckets=True, and at this stage of the loop that boolean still
                    # refers to the prior column, as we have not yet called _add_flattened_col)
                    #
                    # The following example illustrates the issue that needs cleaning:
                    #
                    # Example: supppose in Excel the column is a string like "Actuals", but is preceded by a
                    #           multi-level column in Excel called ("Q4", "FY 24"). Then when the Excel is loaded in
                    #       Pandas, all columns are treated as tuples, and empty tuple entries are taken from the
                    #       predecessor column, so "Actuals" is turned into ("Q4", "Actuals") and flattened_col
                    #       has the value "Q4 Actuals", which is wrong. 
                    #       
                    # To fix this, we check if the prior column was a time bucket, and if so we blank out any values
                    # in col that come from that timebucket
                    #
                    prior_col       = original_columns[idx-1]
                    # We need to re-flatten col because it was flattened incorrectly, with some elements of the tuple
                    # that should be removed because Pandas just set them to be equal to the preceding column,
                    # when in reality they probably where blanks in the Excel from where the DataFrame having
                    # these columns was loaded
                    cleaned_col     = tuple([col[idx] if col[idx] != prior_col[idx] else "" for idx in range(len(col))])
                    
                    flattened_col, timebucket, timebucket_indices   = self.standardizeOneTimebucketColumn(loop_trace, 
                                                                            raw_col                     = cleaned_col, 
                                                                            a6i_config                  = a6i_config,
                                                                            expected_collapsing_info    = standardization_info)

    
                _add_flattened_col(flattened_col, timebucket, timebucket_indices)

        unsorted_df                             = df.copy()
        unsorted_df.columns                     = self._disambiguate_duplicates(parent_trace, unsorted_flattened_columns)

        my_trace                                = parent_trace.doing("Sort and concatenate intervals")
        if True:
            sorted_columns                      = []
            for tagged_interval in intervals:
                if tagged_interval[0]:
                    unsorted_timebuckets        = tagged_interval[2]
                    unsorted_interval_columns   = tagged_interval[1]
                    # We want to sort the actual columns in the interval (which might be tuples) the same way 
                    # we would sort the corresponding timebuckets.
                    #
                    # To accomplish this, we "join" the two lists in a temporary data structure of pairs, sort that
                    # joined list, and then extract the part of the joined result that is columns
                    #
                    unsorted_joined_list        = [[unsorted_interval_columns[idx], unsorted_timebuckets[idx]] 
                                                    for idx in range(len(unsorted_interval_columns))]

                    # We sort by year first, then by quarter. A trick to accomplish this is to use a key where we multiply the year by 100,
                    # so quarters become the last significant digit modulo 100
                    sorted_joined_list          = sorted(unsorted_joined_list,
                                                        key = lambda pair: pair[1].fiscal_year*100 + pair[1].quarter)

                    sorted_interval_columns     = [pair[0] for pair in sorted_joined_list]
                    sorted_columns.extend(sorted_interval_columns)
                else:
                    sorted_columns.extend(tagged_interval[1])

            sorted_df                       = unsorted_df[self._disambiguate_duplicates(parent_trace, sorted_columns)]

            # If the columns of sorted_df are tuples, change them to MultiLevel index
            if standardization_info.final_size > 1:
                
                # GOTCHA
                #   Some of the elements in sorted_df.columns may be strings instead of tuples. If so, we need to 
                # create a tuple out of it of the correct size, applying padding if needed
                # Otherwise, when we create the MultiIndex.from_tuples something bad happens. For example,
                # if the columns were ['bigRock', ('FY 23', 'Actual')], the MultiLevel index created would
                # treat 'bigRock' like a tuple of 7 elements (one per letter), and a horrible 7-level index would be created,
                # like
                #   ('b','i','g','R','o','c','k'), ('FY 23', 'Actual', nan, nan, nan, nan, nan)
                tuple_cols                  = []
                for sorted_col in sorted_df.columns:
                    if type(sorted_col) == tuple:
                        tuple_cols.append(sorted_col)
                    else: 
                        padded_col          = [""]*(standardization_info.final_size-1) + [sorted_col]
                        tuple_cols.append(tuple(padded_col))

                multi_level_cols            = _pd.MultiIndex.from_tuples(tuple_cols)
                sorted_df.columns           = multi_level_cols

        return sorted_df, standardization_info

    def standardizeOneTimebucketColumn(self, parent_trace, raw_col, a6i_config, expected_collapsing_info = None):
        '''
        Utility method used when a DataFrame has columns corresponding to timebuckets, used in the
        context where the caller desires to re-name the DataFrame columns so that time buckets follow the
        standard conventions of the FY_Quarter class.

        This method returns three things:

        * A "standardized" column that can be used to replace `raw_col`
        * A FY_Quarter object that corresponds to that column. If None, that means the `raw_col` does not
          correspond to a timebucket, and the first value returned is just `raw_col`
        * A list of the integer indices in `raw_col` where the timebucket was found. It has length 2 if 
            `raw_col` is a tuple and the timebucket 2 levels (that were collapsed); it has length 1 if `raw_col`
            is a tuple and the timebucket in a single level of `raw_col`. Otherwise (i.e., there is timebucket
            or `raw_col` is not a tuple) then the returned list is empty

        The standardization provided by this method is quite general, and supports multi-level columns.
        This is best illustraded with examples:

        1. If raw_col is a string, then an attempt is made to parse it into a valid FY_Quarter object,
           whose string display is then returned.

            Example: if `raw_col` is "Q3 FY 2022", then this method creates a FY_Quarter object x
                    for Q3 FY22, and returns the triple (x.display(), x, [])
            Example: if `raw_col` is "Actuals", then this method returns the triple ("Actuals", None, [])

        2. If raw_col is a tuple for a multi-level column, then this method aims to find the first level,
            or first pair of consecutive levels, which are a timebucket, leaving the others "as is".
            When two levels are needed to represent a timebucket, then they are collapsed.

            Example: if `raw_col` is ("Q3 FY 2022", "Actuals"), then this method creates a FY_Quarter object
                x from "Q3 FY 2022" and returns the triple ((x.display(), "Actuals"), x, [])

            Example: if `raw_col` is ("Q3", "2024"), then this method creates an FY_Quarter x for Q3 FY24
            and returns the triple (x.display(), x, [0,1]). In this case the tuple is collapsed to a string.

            Example: if `raw_col` is ("Metrics", "Q3", "2024", "Actuals"), then this method creates an
                FY_Quarter object for Q3 FY24 and returns the triple
                
                         (("Metrics", x.display(), "Actuals"), x, [1,2])

                In this case the 4-tuple column is collapsed to a 3-typle.

            Example: if `raw_col` is ("Geo", "Americas"), then this method returns the triple 
                        (("Geo", "Americas"), None, [])

        @param expected_collapsing_info An optional TimebucketStandardizationInfo object. 
            If not None, then this method behaves as follows:

            1. If this method's algoritm encounters a timebucket, then it must be collapsed exactly as
                per the `expected_collapsing_info`. Otherwise, this method errors out

            2. If this method's algorithm does not encounter a timebucket, then it will force
                a collapse of the resulting column before returning.

            3. If `raw_col` is not a tuple of a length as per the `expected_collapsing_info`, that is an error.
        '''
        if type(raw_col) != str and type(raw_col) != tuple:
            raise ApodeixiError(parent_trace, "This kind of column can't have its timebuckets standardized: expected "
                                                + "a string or a tuple, not a '" + str(type(raw_col)) + "'",
                                                data = {"raw_col": str(raw_col)})

        if type(raw_col) == tuple:
            bad_elts                        = [elt for elt in raw_col if type(elt) != str and type(elt) != int]
            if len(bad_elts) > 0:
                raise ApodeixiError(parent_trace, "This kind of multi-level column can't have time buckets standardized: "
                                                + str(len(bad_elts)) + " of its members are not strings or ints",
                                                data = {"non-string elements": str(bad_elts),
                                                        "raw_col": str(raw_col)})
            if len(raw_col) == 0:
                raise ApodeixiError(parent_trace, "An empty tuple is not a valid column to have time buckets standardized")

            if expected_collapsing_info != None and len(raw_col) != expected_collapsing_info.initial_size:
                raise ApodeixiError(parent_trace, "Bad column for standardization: it should be a tuple of length exactly "
                                                        + str(expected_collapsing_info.initial_size) + " elements",
                                                        data = {"raw_col": str(raw_col)})

        def _singleton_to_timebucket(parent_trace, txt):
            '''
            Aims to convert the objet to a FY_Quarter object out of a string, and returns it. If it fails, it returns None.
            '''
            month_fiscal_year_starts        = a6i_config.getMonthFiscalYearStarts(parent_trace)
            cleaned_txt                     = _strip_pandas_disambiguation(txt)
            try:
                timebucket          = FY_Quarter.build_FY_Quarter(parent_trace, cleaned_txt, month_fiscal_year_starts)
                return timebucket
            except ApodeixiError as ex:
                return None

        def _pair_to_timebucket(parent_trace, txt1, txt2):
            '''
            Aims to convert a pair of strings like "Q3", "FY 24" to a FY_Quarter object, and returns it. 
            If it fails, it returns None.
            '''
            month_fiscal_year_starts        = a6i_config.getMonthFiscalYearStarts(parent_trace)
            cleaned_txt1                    = _strip_pandas_disambiguation(txt1)
            cleaned_txt2                    = _strip_pandas_disambiguation(txt2)

            # It is possible that the caller passed `txt2` to be something like "23" instead of "FY 23".
            # If so, add the "FY" prefix so that the FY_Quarter parser won't fail
            if cleaned_txt2.isnumeric():
                cleaned_txt2                = "FY" + cleaned_txt2
            full_txt                        = cleaned_txt1 + " " + cleaned_txt2
            try:
                timebucket          = FY_Quarter.build_FY_Quarter(parent_trace, full_txt, month_fiscal_year_starts)
                return timebucket
            except ApodeixiError as ex:
                return None

        def _strip_pandas_disambiguation(txt):
            '''
            Helper method to prevent FY_Quarter parsing errors for column names that are modified by Pandas when
            loading an Excel file.
            For example, if the column name "Q3 FY24" appears in two different columns in Excel, when Pandas
            loads the Excel it will re-name the second column as "Q3 FY24.1". This would fail to be parsed
            by the FY_Quarter parser, so this method returns any portion of the column name that lies after
            a period, and returns it.
            '''
            return txt.split(".")[0]

        if type(raw_col) == str:
            timebucket                      = _singleton_to_timebucket(parent_trace, raw_col)
            if timebucket == None:
                return raw_col, None, []
            else:
                return timebucket.display(), timebucket, []

        # If we get this far, `raw_col` is a tuple, part of a multi-level column index
        # We loop through the tuple trying to parse a timebucket, either for a single level or for two
        # consecutive levels. At the first success we stop
        result_list                         = []
        timebucket                          = None
        for idx in range(len(raw_col)):
            loop_trace                      = parent_trace.doing("Processing column '" + str(raw_col) + "'")
            timebucket_indices              = []
            txt1                            = str(raw_col[idx])
            # First parsing try: for a singleton
            timebucket                      = _singleton_to_timebucket(loop_trace, txt1)
            if timebucket != None: # Found it!
                result_list.append(timebucket.display())
                # For the remaining members of the tuple, take them as they are in raw_col
                result_list                 = result_list + list(raw_col[idx + 1:])
                timebucket_indices          = [idx]
                break
            # First parsing attempt failed, so try with a pair instead of a singleton:
            if idx + 1 < len(raw_col):
                txt2                        = str(raw_col[idx + 1])
                timebucket                  = _pair_to_timebucket(loop_trace, txt1, txt2)
                if timebucket != None: # Found it!
                    result_list.append(timebucket.display())
                    # For the remaining members of the tuple, take them as they are in raw_col
                    result_list             = result_list + list(raw_col[idx + 2:])
                    timebucket_indices      = [idx, idx + 1]
                    break
            # If we get here, both parsing attempts failed, so this element of the tuple is not part of
            # a FY_Quarter. So just add it "as is" and try our luck in the next cycle of the loop
            #
            # But before we add it, we need to make a check to avoid adding something the user might have
            # never intended as part of a column but which Pandas introduced.
            # This arrises in this context:
            #
            # If this DataFrame was created by loading an Excel spreadsheet, then Pandas might have 
            # "padded" empty cells in a multi-level with strings like "Unnamed: 1_level_0" in the tuple 
            # to complete it. If so, don't include such frivolous strings as a valid part of the result_list
            if not txt1.startswith("Unnamed:") and not "_level_" in txt1:            
                result_list.append(txt1)
            else:
                result_list.append("")

        my_trace                    = parent_trace.doing("Applying collapsing expectations")
        if expected_collapsing_info != None:
            if timebucket != None: # Check expectations were met
                if len(result_list) != expected_collapsing_info.final_size:
                    raise ApodeixiError(my_trace, "Column name standardization fails expectations: should have size "
                                                        + str(expected_collapsing_info.final_size),
                                                    data = {"result_list": str(result_list)})
                if timebucket_indices != expected_collapsing_info.timebucket_indices:
                    raise ApodeixiError(my_trace, "Column name standardization fails expectations: should have timebucket "
                                                        "indices " + str(expected_collapsing_info.timebucket_indices),
                                                    data = {"timebucket_indices": str(timebucket_indices)})
            
            else: # No timebucket, so we did no collapse, so should force one now
                result_list         = self._collapse_if_needed(my_trace, result_list, expected_collapsing_info)
 
        if len(result_list) != 1:
            return tuple(result_list), timebucket, timebucket_indices
        else:
            return result_list[0], timebucket, timebucket_indices

    def _collapse_if_needed(self, parent_trace, a_list, expected_collapsing_info):
        '''
        Subroutine used as part of collapsing tuple column names that have time buckets.
        Will collapse `a_list` as per the `expected_collapsed_info`, if it hasn't already been collapsed,
        and return the collapsed list

        @param expected_collapsing_info A TimebucketStandardizationInfo object
        '''
        if len(a_list) == expected_collapsing_info.final_size: # List is already collapsed
            return a_list
        elif len(a_list) != expected_collapsing_info.initial_size:
            raise ApodeixiError(parent_trace, "Can't collapse list because it should be of length " 
                                                + str(expected_collapsing_info.initial_size),
                                            data = {"len(a_list)":  str(len(a_list)),
                                                    "a_list":       str(a_list)})
        else:
            idx1                = expected_collapsing_info.timebucket_indices[0]
            idx2                = expected_collapsing_info.timebucket_indices[1]
            if idx1 != idx2:
                boundary_val    = a_list[idx1] + " " + a_list[idx2]
                boundary_val    = boundary_val.strip()
            else:
                boundary_val    = a_list[idx1]
            result_list         = a_list[:idx1] + [boundary_val] + a_list[idx2+1:]

            return result_list

    def _disambiguate_duplicates(self, parent_trace, raw_columns):
        '''
        Helper method to avoid a situation where we might use the same string as the name of two different
        columns for a DataFrame.

        It returns a list of columns, of same length as the input `raw_columns`, where each element is the same
        as in `raw_columns` except possibly for a suffix ".1", ".2", etc that is added for duplicate column names

        @param raw_columns A list of strings
        '''
        result                          = []
        for col in raw_columns:
            if col in result: # Means this is a duplicate. So look for the first integer that disambiguates it
                idx                     = 1
                if type(col) == tuple:
                    duplicate_txt       = str(col[-1]).strip()
                    # GOTCHA: Avoid empty strings, as regression tests would fail by causing the cell in Excel
                    # to be ".1" which will be read as 0.1
                    if len(duplicate_txt) == 0:
                        duplicate_txt   = "_"
                    candidate           = tuple(list(col[:-1]) + [duplicate_txt + "." + str(idx)])

                else:
                    duplicate_txt       = str(col).strip()
                    # GOTCHA: Avoid empty strings, as regression tests would fail by causing the cell in Excel
                    # to be ".1" which will be read as 0.1
                    if len(duplicate_txt) == 0:
                        duplicate_txt   = "_"
                    candidate               = duplicate_txt + "." + str(idx)
                LIMIT                   = 1000 # To avoid infinite loops if there is a bug, constrain unbounded search
                while idx < LIMIT:
                    if not candidate in result:
                        result.append(candidate)
                        break
                    idx                 += 1
            else:
                result.append(col)

        # Check our unbounded search didn't miss some column
        if len(result) != len(raw_columns):
            raise ApodeixiError(parent_trace, "Internal error in algorithm to disambiguate duplicate columns: result "
                                                " should have been of exact same size as input",
                                                data = {"input length":         str(len(raw_columns)),
                                                        "result length":        str(len(result)),
                                                        "input":                str(raw_columns),
                                                        "result":               str(result)})

        return result

class TimebucketStandardizationInfo():
    '''
    Helper class used when standardizing timebucket columns. It defines the expectations on all
    columns before and after the standardization, in terms of sizes and in terms of the indices that are "collapsed"
    i.e., levels in an original MultiLevel column that are collapsed to a single level. 
    Example: For a column like ("Sales", "Q3", "2024", "Actuals"), its standardized equivalent would be
            ("Sales", "Q3 FY24", "Actuals"). In that case, this object recalls that:
            * Initial size of tuple was 4
            * Final size of tuple was 3
            * The timebucket was present and indices [1, 2] in the original
    
    @param initial_size An int, corresponding to the original tuple length for a column name prior to standardization
    @param final_size An int, corresponding to the final tuple length for a column name after standardization
    @param timebucket_indices A list of either 0, 1 or 2 consecutive integers, corresponding to the indices that
            contain a timebucket in the column name's tuple, if any.
    '''
    def __init__(self, parent_trace, initial_size, final_size, timebucket_indices):
        self.initial_size           = initial_size
        self.final_size             = final_size

        if type(timebucket_indices) != list:
            raise ApodeixiError(parent_trace, "Bad timebucket indices: should be a list",
                                                data = {"type(timebucket_indices)": str(type(timebucket_indices))})
        if not len(timebucket_indices) in [0,1,2]:
            raise ApodeixiError(parent_trace, "Bad timebucket indices: should be a list of size 0, 1 or 2",
                                                data = {"timebucket_indices)": str(timebucket_indices)})  

        if len([elt for elt in timebucket_indices if type(elt) != int]) > 0:
            raise ApodeixiError(parent_trace, "Bad timebucket indices: should be a list of integers",
                                                data = {"timebucket_indices)": str(timebucket_indices)})  

        if len(timebucket_indices) ==2:
            first_idx               = timebucket_indices[0]
            second_idx              = timebucket_indices[1]    
            if first_idx +1 != second_idx:
                raise ApodeixiError(parent_trace, "Bad timebucket indices: list should be consecutive integers",
                                                data = {"timebucket_indices)": str(timebucket_indices)}) 
        for idx in timebucket_indices:
            if idx < 0:      
                raise ApodeixiError(parent_trace, "Bad timebucket indices: they should be non-negative",
                                                data = {"timebucket_indices)": str(timebucket_indices)})  

            if idx >= initial_size or idx >= initial_size:      
                raise ApodeixiError(parent_trace, "Bad timebucket indices: they should be less than the initial size",
                                                data = {"intial_size":      str(initial_size),
                                                        "timebucket_indices)": str(timebucket_indices)})   

        self.timebucket_indices     = timebucket_indices
import datetime                                 as _datetime
import calendar                                 as _calendar
import re                                       as _re
import pandas                                   as _pd
import warnings

from unittest import result

from apodeixi.util.a6i_error                    import ApodeixiError
from apodeixi.util.dataframe_utils              import TupleColumnUtils
from apodeixi.util.warning_utils                import WarningUtils


class FY_Quarter():
    '''
    Represents a quarter in the fiscal year. The fiscal year runs from the 1st of the month initialized in the constructure. 
    Years are only supported from 2001 onwards.
    
    @param month_fiscal_year_starts: an integer, representing the month of the year when the fiscal year starts. Defaults to January
    @param year: an integer, representing a fiscal year. For example, 2022 represents the fiscal year from June 1st 2021 
                     to May 31st 2022.
    @param quarter: an integer between 1 and 4, representing a quarter. For example, if year=2022 then quarter=3 represents 
                    the 3 months from December 1st 2021 to February 28 2022.
    '''
    def __init__(self, fiscal_year, quarter, month_fiscal_year_starts=1):
        if fiscal_year < 2001:
            raise ValueError("Fiscal Year " + str(fiscal_year) + " is not supported as a valid year. Only years after 2001 are supported")
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Quarter " + str(quarter) + " is not a valid quarter. Must be of of: 1, 2, 3, or 4")

        if month_fiscal_year_starts not in range(1, 13):
            raise ValueError("Invalid `month_fiscal_year_starts`: should be an integer between 1 and 12, but got "
                                + str(month_fiscal_year_starts) + " instead.")
        self.month_fiscal_year_starts   = month_fiscal_year_starts
        self.fiscal_year                = fiscal_year
        self.quarter                    = quarter

        # This flag determines whether the time bucket represents a whole fiscal year, or just a quarter
        # It is false by default. When it is True, this object still has a `quarter` attribute, which is
        # recommended to be 4, to signify that the time bucket represents a full fiscal year up to 
        # Q4 of that year.
        self.is_a_year_bucket           = False

    def build_FY_Quarter(parent_trace, formatted_time_bucket_txt, month_fiscal_year_starts=1, default_quarter=4):
        '''
        Parses the string `formatted_time_bucket_txt`, and returns a FY_Quarter object constructed from that.

        If the parsing is not possible then it raises an Apodeixi error.

        The quarter portion might be optional, and spaces are allowed. Thus, all of the following are valid
        possible values for `formatted_time_bucket_txt`:
         
            "Q3 FY23", "Q3 FY 23", " Q3 FY 23 ", "FY23", "FY 25", "FY 2026", "Q 4 FY 29" 

        If the quarter is not provided, it is assumed to be Q4, and self.is_a_year_bucket is set to True.

        @param month_fiscal_year_starts An int between 1 and 12, corresponding to the month of the year
                        when the fiscal year starts. January is 1 and December is 12.
        @param default_quarter An int between 1 and 4. In situations where the quarter is not provided (e.g., 
                        `formatted_time_bucket_txt` is something like "FY 22"), then this is used as the default
                        value for the quarter in the result. Otherwise this parameter is ignored.
        '''
        REGEX                       = "^\s*(Q\s*([1-4]))?\s*FY\s*(([0-9][0-9])?[0-9][0-9])\s*$"
        if type(formatted_time_bucket_txt) != str:
            raise ApodeixiError(parent_trace, "Invalid time bucket: expected a string, but instead was given a "
                                                + str(type(formatted_time_bucket_txt)))
        m                           = _re.search(REGEX, formatted_time_bucket_txt)
        if m==None or len(m.groups())!= 4:
            raise ApodeixiError(parent_trace, "Invalid time bucket `" + formatted_time_bucket_txt + "`. Use a valid format, "
                                                + "such as 'Q2 FY23', 'Q1 FY 25', 'FY 26', or FY 1974")

        # If the input is "Q 4 FY 29", then [m.group(1), m.group(2), m.group(3), m.group(4)] is:
        #       
        #           ['Q 4', '4', '29', None]
        #
        if m.group(2) == None:
            if not default_quarter in [1, 2, 3, 4]:
                raise ApodeixiError(parent_trace, "Problem with parsing time bucket `" + formatted_time_bucket_txt + "`: "
                                                    + " the given default_quarter should be an integer between 1 and 4, not "
                                                    + str(default_quarter))
            quarter                 = default_quarter
            is_a_year_bucket        = True
        else:
            quarter                 = int(m.group(2))
            is_a_year_bucket        = False
        year                        = int(m.group(3))
        if year < 100:
            year                    += 2000     # For example, FY23 means the year is 2023, not 23
        
        result                      = FY_Quarter(year, quarter, month_fiscal_year_starts=1)
        result.is_a_year_bucket     = is_a_year_bucket
        return result


    def less_than(self, parent_trace, other_quarter):
        '''
        Returns True or False, depending on whether self lies before the other_quarter (returns True), or
        not (return False).

        Raises an ApodeixiError if the `other_quarter` is not an FY_Quarter object.
        '''
        if type(other_quarter) != FY_Quarter:
            raise ApodeixiError(parent_trace, "Can only do `less_than` comparison against another FY_Quarter, but "
                                                "was give a '" + str(type(other_quarter)) + "' instead")

        my_last_day         = self.last_day()
        other_last_day      = other_quarter.last_day()

        if my_last_day < other_last_day:
            return True
        else:
            return False
        
        
    def getQuarter(date, month_fiscal_year_starts):
        '''
        Returns a new FY_Quarter object that contains the given `date` parameter
        '''
        calendar_year = date.year
        # Search neighboring quarters for a match
        for fy in [calendar_year, calendar_year + 1]:
            for quarter in [1, 2, 3, 4]:
                candidate = FY_Quarter( fiscal_year                 = fy, 
                                        quarter                     = quarter, 
                                        month_fiscal_year_starts    = month_fiscal_year_starts)
                if candidate.contains(date):
                    return candidate
                
        # If we get this far we have a serious bug, since we should have found a quarter that contained the date
        assert(False)
        
    def contains(self, date):
        '''
        Returns True or False, depending on whether the given date falls within this quarter
        '''
        if date != None and self.first_day() <= date and date <= self.last_day():
            return True
        else:
            return False
           
    def last_day(self):
        '''
        Returns a datetime.date object, corresponding to the last day of the quarter
        '''
        month, year_delta  = self._ends_on_month()
        calendar_year      = self.fiscal_year + year_delta
        last_day_of_month  = _calendar.monthrange(calendar_year, month)[1]
        d = _datetime.date(calendar_year, month, last_day_of_month)
        return d
    
    def first_day(self):
        '''
        Returns a datetime.date object, corresponding to the first calendar day of this quarter.
        '''
        month, year_delta   = self._starts_on_month()
        calendar_year       = self.fiscal_year + year_delta
        first_day_of_month  = 1
        d = _datetime.date(calendar_year, month, first_day_of_month)
        return d
    
    def displayFY(self, spacing=None):
        '''
        @param spacing Optional parameter, null by default. If set to a string (such as " " or "-") it will be used
            as a delimeter. For example, to display "FY 22" instead of "FY22" if a space is used as delimeter
        '''
        if type(spacing)==str:
            return 'FY' + spacing + str(self.fiscal_year%100)
        else:
            return 'FY' + str(self.fiscal_year%100)
    
    def displayQuarter(self):
        return 'Q' + str(self.quarter)
    
    def display(self):
        if self.is_a_year_bucket:
            return self.displayFY()
        else:
            return self.displayQuarter() + " " + self.displayFY()

    def _starts_on_month(self):
        '''
        Helper method to compute the calendar month when the quarter starts. 
        Returns two integers. The first one is the month when the quarter starts,
        and is set as follows:
        
        If self.is_a_year_bucket, then self.month_fiscal_year_starts

        Else:
        self.quarter=1 ---> self.month_fiscal_year_starts
        self.quarter=2 ---> self.month_fiscal_year_starts + 3 %12
        self.quarter=3 ---> self.month_fiscal_year_starts + 6 %12
        self.quarter=4 ---> self.month_fiscal_year_starts + 9 %12
        
        The second integer is either 0 or -1, depending on whether the time bucket starts in calendar year
        self.fiscal_year or self.fiscal_year-1
        '''
        if self.is_a_year_bucket:
            months_since_new_year = self.month_fiscal_year_starts
        else:
            months_since_new_year = (self.month_fiscal_year_starts -1) + self.quarter*3 -2
        return (months_since_new_year-1) % 12+1, int((months_since_new_year-1)/12) -1
    
    def _ends_on_month(self):
        '''
        Helper method to compute the calendar month when the quarter ends. 
        Returns two integers. The first one is the month when the quarter ends:

        If self.is_a_year_bucket, then self.month_fiscal_year_starts - 1
        
        self.quarter=1 ---> self.month_fiscal_year_starts + 2 %12
        self.quarter=2 ---> self.month_fiscal_year_starts + 5 %12
        self.quarter=3 ---> self.month_fiscal_year_starts + 8 %12
        self.quarter=4 ---> self.month_fiscal_year_starts + 11 %12
        
        The second integer is either 0 or -1, depending on whether the quarter ends in calendar year
        self.fiscal_year or self.fiscal_year-1
        '''
        if self.is_a_year_bucket:
            months_since_new_year = (self.month_fiscal_year_starts - 1) + 12
        else:
            months_since_new_year = (self.month_fiscal_year_starts - 1) + self.quarter*3
        return (months_since_new_year -1) % 12 + 1, int((months_since_new_year-1)/12) -1


class TimebucketDataFrameJoiner():
    '''
    Utility class to join DataFrames so that timebuckets are grouped together and sorted, and return the resulting
    DataFrame

    For example, imagine having three DataFrames:
        * A DataFrame of sales regions - columns are strings like "Region", "Country"
        * A DataFrame of sales targets for 2 years - columns are tuples for timebuckets, like ("Q1", "FY23"), ...., ("Q4", "FY24)
        * A DataFrame of sales actuals for 3 quarters- columns are tuples like ("Q1", "FY23"), ..., ("Q3", "FY23")

    Morever, assume that the DataFrames for sales targets and actuals either have the same index as the DataFrame for sales regions,
    or else have a foreign key pointing to the sales regions (as a not necessarily injection, i.e., some regions may lack 
    a sales target or actual)

    Then this class provides functionality to "merge" all these 3 DataFrames into 1 DataFrame with columns that are
    2-level tuples, returning someting that looks like this:

                         | Q1 FY23          | Q2 FY23          | Q3 FY23          | Q4 FY23 | Q1 FY24 | Q2 FY24 | Q3 FY24 | Q4 FY24 
        Region | Country | Target  | Actual | Target  | Actual | Target  | Actual | Target  | Target  | Target  | Target  | Target  
        =============================================================================================================================
               |         |         |        |         |        |         |        |         |         |         |         |

    In particular:
     
    * Timebuckets are standardized. If they are provided as tuples, they are turned into strings
    * A lower level (like "Target" and "Actual") can be introduced by the caller. The caller can also introduce "higher levels"
      and the standard grouping semantics are enforced: lower-levels are grouped within the same time bucket, whereas time buckets
      are grouped per higher level value, if higher levels are provided.
    * Timebuckets may be provided as size-2 tuples or as size-1 tuples or as strings
    * The non-timebucket columns are made to appear to the left, as the first columns

    @param reference_df A DataFrame none of whose columns are for a timebucket. All columns must be strings.
    @param link_field May be None. If not null, must be a column of `reference_df` (i.e., a string) such that 
            "could be used as an index", in the sense that all rows of `reference_df` have a different value for this column.
    @param timebucket_df_list A list of DataFrames all of which have only timebucket columns. A "timebucket column" can be
            either a string or a tuple whole last 1 or 2 levels can be parsed as a FY_Quarter object. Valid examples:
            "Q2 FY23", "FY 2025", ("Q2", "FY 24"), ("Q2 FY22").
            The index for all these DataFrames must be the same (or a subset) of the index of `reference_df`, or else
            must contain a column whose name equals the `link_field` parameter, and which has unique values per row.
    @param timebucket_df_lower_tags May be None. If not null, must be a list of the same length as `timebucket_df_list`,
            all of it strings or all of it tuples of strings of the same size.
    @param timebucket_df_upper_tags May be None. If not null, must be a list of the same length as `timebucket_df_list`,
            all of it strings or all of it tuples of strings of the same size.
    @param a6i_config Apodeixi configuration.

    @return A DataFrame
    '''
    def __init__(self, parent_trace, reference_df, link_field, timebucket_df_list, 
                        timebucket_df_lower_tags, timebucket_df_upper_tags, a6i_config):

        standardizer                    = TimebucketStandardizer()
        my_trace                        = parent_trace.doing("Validating inputs provided to TimebucketDataFrameJoiner")
        if True:
            # Check reference_df is a DataFrame
            if not type(reference_df) == _pd.DataFrame:
                raise ApodeixiError(my_trace, "Bad reference_df provided: it should be a DataFrame, not a '" 
                                                + str(type(reference_df)) + "'")
            # Check no column of reference_df is a timebucket
            bad_cols                    = [col for col in reference_df.columns if standardizer.is_a_timebucket_column(my_trace, 
                                                                                                                        col, 
                                                                                                                        a6i_config)]
            if len(bad_cols) > 0:
                raise ApodeixiError(my_trace, "Invalid reference DataFrame provided: it contains some timebucket columns, but it "
                                                + "shouldn't",
                                                data = {"ts_cols": str(bad_cols)})

            # Check every column of reference_df is a string
            bad_cols                    = [col for col in reference_df.columns if not type(col)==str]
            if len(bad_cols) > 0:
                raise ApodeixiError(my_trace, "Invalid reference DataFrame provided: it contains some non-string columns, but it "
                                                + "shouldn't",
                                                data = {"ts_cols": str(bad_cols)})

            # Check link_field is either null or is a valid column of reference_df
            if link_field != None and not link_field in reference_df.columns:
                raise ApodeixiError(my_trace, "Invalid link field provided: it should be a column in reference DataFrame ",
                                                data = {"link_field": str(link_field),
                                                        "reference_df.columns": str(reference_df.columns)}) 
            # Check timebucket_df_list is a list
            if type(timebucket_df_list) != list:
                raise ApodeixiError(my_trace, "Invalid timebucket_df_list provided: should be a list, not a '" 
                                                    + str(type(timebucket_df_list)) + "'")

            # Check timebucket_df_list is not empty list
            if len(timebucket_df_list) == 0:
                raise ApodeixiError(my_trace, "Invalid timebucket_df_list provided: it is emtpy, and it shouldn't")

            # Check timebucket_df_lower_tags is a list
            if timebucket_df_lower_tags !=None and type(timebucket_df_lower_tags) != list:
                raise ApodeixiError(my_trace, "Invalid timebucket_df_lower_tags provided: should be a list, not a '" 
                                                    + str(type(timebucket_df_lower_tags)) + "'")
            # Check timebucket_df_upper_tags is a list
            if timebucket_df_upper_tags != None and type(timebucket_df_upper_tags) != list:
                raise ApodeixiError(my_trace, "Invalid timebucket_df_upper_tags provided: should be a list, not a '" 
                                                    + str(type(timebucket_df_upper_tags)) + "'")

            # Check timebucket_df_lower_tags are unique
            if timebucket_df_lower_tags !=None and len(timebucket_df_lower_tags) != len(set(timebucket_df_lower_tags)):
                raise ApodeixiError(my_trace, "Invalid timebucket_df_lower_tags provided: it has duplicates, and shouldn't: '" 
                                                    + str(timebucket_df_lower_tags) + "'")
            # Check timebucket_df_upper_tags are unique
            if timebucket_df_upper_tags !=None and len(timebucket_df_upper_tags) != len(set(timebucket_df_upper_tags)):
                raise ApodeixiError(my_trace, "Invalid timebucket_df_upper_tags provided: it has duplicates, and shouldn't: '" 
                                                    + str(timebucket_df_upper_tags) + "'")

            # Check all members of timebucket_df_list are DataFrames
            bad_list                    = [elt for elt in timebucket_df_list if type(elt) != _pd.DataFrame]
            if len(bad_list) > 0:
                raise ApodeixiError(my_trace, "Invalid timebucket_df_list provided: some elements are not DataFrames. "
                                                + "Instead they are " + ", ".join([str(type(elt)) for elt in bad_list]))
            # Check all columns for members of timebucket_df_list are timebuckets, except for the linkfield, if it exists
            for df in timebucket_df_list:
                for col in df.columns:
                    if self._is_a_link_column(col, link_field):                  
                        # Skip if col "is" the linkfield, where "is" must be tuple-sensitive (i.e., maybe the last level of col
                        # is the link_field)
                        continue

                    flattened_col, timebucket, timebucket_indices   = standardizer.standardizeOneTimebucketColumn(my_trace, 
                                                                            raw_col                     = col, 
                                                                            a6i_config                  = a6i_config,
                                                                            expected_collapsing_info    = None)

                    if timebucket == None:
                        raise ApodeixiError(my_trace, "Invalid timebucket_df_list: all columns of all DataFrames should be "
                                                        + "timebuckets, but at least one column is not: '" + str(col) + "'")
                    if type(flattened_col) == tuple and max(timebucket_indices) < len(flattened_col) - 1:
                        raise ApodeixiError(my_trace, "Invalid timebucket_df_list: at least 1 DataFrame has a column "
                                                        + "has lower levels below the timebucket levels: '" + str(col) + "'")

            # Check all members of timebucket_df_list contain the link_field, if it is set
            if link_field != None:
                for df in timebucket_df_list:
                    if len([col for col in df.columns if self._is_a_link_column(col, link_field)]) == 0:
                        raise ApodeixiError(my_trace, "Invalid link_field '" + str(link_field) + "' : it is not present "
                                            + "as a column in at least some of the input dataframes supposed to join on that field",
                                            data = {"dataframe columns": str(df.columns)})
                    if len([col for col in df.columns if self._is_a_link_column(col, link_field)]) > 1:
                        raise ApodeixiError(my_trace, "Invalid link_field '" + str(link_field) + "' : it present "
                                            + "in multiple columns in at least some of the input dataframes supposed to join "
                                            + "on that field (should be present in exactly 1 column",
                                            data = {"dataframe columns": str(df.columns)})

            # Check tags lists (if not null) are of the right length
            if timebucket_df_lower_tags != None and len(timebucket_df_lower_tags) != len(timebucket_df_list):
                raise ApodeixiError(my_trace, "Invalid timebucket_df_lower_tags: size does not match that of timebucket_df_list",
                                                data = {"len(timebucket_df_lower_tags)": str(len(timebucket_df_lower_tags)),
                                                        "len(timebucket_df_list)": str(len(timebucket_df_list))})
            if timebucket_df_upper_tags != None and len(timebucket_df_upper_tags) != len(timebucket_df_list):
                raise ApodeixiError(my_trace, "Invalid timebucket_df_upper_tags: size does not match that of timebucket_df_list",
                                                data = {"len(timebucket_df_upper_tags)": str(len(timebucket_df_upper_tags)),
                                                        "len(timebucket_df_list)": str(len(timebucket_df_list))})
            # Check tag lists (if not null) are of the same number of MultiIndex levels
            if timebucket_df_lower_tags != None:
                tag_lengths             = [len(tag) if type(tag)==tuple else 0 for tag in timebucket_df_lower_tags]
                tag_lengths             = list(set(tag_lengths)) # Remove duplicates
                if len(tag_lengths) != 1:
                    raise ApodeixiError(my_trace, "Invalid timebucket_df_lower_tags: there are tags of various lengths",
                                                data = {"tag_lengths": str(tag_lengths)})
            if timebucket_df_upper_tags != None:
                tag_lengths             = [len(tag) if type(tag)==tuple else 0 for tag in timebucket_df_upper_tags]
                tag_lengths             = list(set(tag_lengths)) # Remove duplicates
                if len(tag_lengths) != 1:
                    raise ApodeixiError(my_trace, "Invalid timebucket_df_upper_tags: there are tags of various lengths",
                                                data = {"tag_lengths": str(tag_lengths)})

        self.reference_df               = reference_df
        self.link_field                 = link_field
        self.timebucket_df_list         = timebucket_df_list
        self.timebucket_df_lower_tags   = timebucket_df_lower_tags
        self.timebucket_df_upper_tags   = timebucket_df_upper_tags
        self.a6i_config                 = a6i_config

    BINARY_OPERATION            = "BINARY_OPERATION"
    UNARY_OPERATION             = "UNARY_OPERATION"
    CUMULATIVE_OPERATION        = "CUMULATIVE_OPERATION"

    def _is_a_link_column(self, col, link_field):
        '''
        Helper method that returns a boolean, determining if a DataFrame's column `col` "is" the link_field, where "is linke field" is 
        interpreted in a tuple-sensitive way: ie, a column `col` is considered to be the `link_field` if either
        * col == link_field
        * or col is a tuple and link_field is col's last level

        @param col A DataFrame's column
        @param link_field A string
        '''
        if col==link_field or (type(col)==tuple and col[-1]==link_field):
            return True
        else:
            return False

    def _untuple_link_column(self, parent_trace, df):
        '''
        Returns a DataFrame almost identical to the input `df`, except that it might rename "the link_field column" of df, if
        self.link_field is not null, so that it is a string in the event it is a tuple.

        Example: Suppose the link_field is "Country". Because of how Pandas reads Excel into DataFrames such as `df`, it is
                possible that in `df` the column is held as a tuple, like ("", "", Country).
                In that case, that thuple column is replaced by a string column "Country"
        '''
        if self.link_field == None: # Nothing to do
            return df

        matching_columns        = [col for col in df.columns if self._is_a_link_column(col, self.link_field)]
        if len(matching_columns) == 0: # No column to rename
            return df
        elif len(matching_columns) > 1:
            raise ApodeixiError(parent_trace, "Invalid DataFrame provided: multiple columns can be considered to have "
                                    + "the link field '" + self.link_field + "'",
                                    data = {"df columns":   str(df.columns)})

        original_link_field_col     = matching_columns[0]
        # Now replace the column of df from possibly ("", "Country") to "Country" (see comments in Example above)
        cleaned_df                  = df.copy()
        cleaned_df.columns          = [col if col != original_link_field_col else self.link_field for col in df.columns]
        return cleaned_df

    def enrich_with_tb_binary_operation(self, parent_trace, a_ltag, b_ltag, c_ltag, func):
        '''
        Used to compute derived DataFrames.

        Example use case: suppose that self.timebucket_df_list has two DataFrames, with lower tags called
                        "Sales Target", "Sales Actual". Then this methoc can be used to derive a third DataFrame
                        which the caller (via the c_ltag) can choose to tag as "% Target Achieved", computed
                        (via the `func` function parameter) as the ration of actuals to targets, row-by-row.

        More generally:

        This method enlarges self.timebucket_df_list by adding 1 additional DataFrame C_df, derived from two of the 
        pre-existing DataFrames A_df, B_df already in self.timebucket_df_list, so that the following holds true:

        1) A_df is the unique member self.timebucket_df_list[idx] such that a_ltag = self.timebucket_df_lower_tags[idx]
        2) Same as 1), but for B_df and b_ltag
        3) For each timebucket column col in both A_df, and B_df, C_df[col] = func(A_df[col], B_df[col])
        4) If self.link_field is not null, then C_df[link_field] = A_df[link_field]
        5) If A_df and B_df don't have the "same rows", then the above hold true with A_df, B_df replaced by the intersection
           of rows both in A_df and B_df. By "same rows" we mean: rows where A_df, B_df have the same value for 
           self.link_field or, if self._link_field is null, rows with the same index value.

        It also enriches self.timebucket_df_lower_tags by adding c_ltag for C_df
        
        @param a_ltag A string, which must belong to self.timebucket_df_lower_tags, and the latter must not be null
        @param b_ltag A string, which must belong to self.timebucket_df_lower_tags, and the latter must not be null
        @param c_ltag A string that should be used as a lower tag for the result. It must not already exist in 
                self.timebucket_df_lower_tags, and it is appended to the latter, increasing its size by 1.
        @func A function that takes 3 arguments: a FunctionalTrace object, and two Pandas series, and returns a third series.
                The function may assume that both input series have the same index.
        '''
        with warnings.catch_warnings(record=True) as w:
            WarningUtils().turn_traceback_on(parent_trace, warnings_list=w)

            my_trace                        = parent_trace.doing("Checking if a_ltag is valid")
            if True:
                if not a_ltag in self.timebucket_df_lower_tags:
                    raise ApodeixiError(my_trace, "Can't use tag '" + str(a_ltag) + "' to identify which DataFrame to use as an "
                                                + " enrichment input because "
                                                + "tag is not in valid list of tags",
                                                data = {"allowed tags": str(self.timebucket_df_lower_tags)})
    
            my_trace                        = parent_trace.doing("Identifying a_df")
            if True:
                a_idx                       = self.timebucket_df_lower_tags.index(a_ltag)
                a_df                        = self.timebucket_df_list[a_idx]

            self._enrich_with_tb_operation(parent_trace,    a_df            = a_df, 
                                                            b_ltag          = b_ltag, 
                                                            c_ltag          = c_ltag, 
                                                            func            = func, 
                                                            operation_type  = self.BINARY_OPERATION, 
                                                            ref_column      = None)

            WarningUtils().handle_warnings(parent_trace, warning_list=w)
        
        return

    def enrich_with_tb_unary_operation(self, parent_trace, ref_column, b_ltag, c_ltag, func):
        '''
        Used to compute derived DataFrames.

        Example use case: suppose that self.reference_df has a column called "Journey Target", to represent
                        how many modernization tasks to do over the course of a multi-year modernization program.
                        And suppose self.timebucket_df_list contains a DataFrame (identified by lower tag b_ltag)
                        with quarterly targets for such tasks.
                        Then this this methoc can be used to derive another DataFrame corresponding 
                        to "% Target Achieved", computed
                        (via the `func` function parameter) as the ration of actuals to targets, row-by-row.
                        This derived DataFrame would get a lower tag given by c_ltag.

        More generally:

        This method enlarges self.timebucket_df_list by adding 1 additional DataFrame C_df, derived from 
        self.reference_df and from a pre-existing DataFrame ref_df, B_df already in self.timebucket_df, 
        so that the following holds true:

        1) ref_column is a column in self.reference_df
        2) B_df is the unique member self.timebucket_df_list[idx] such that b_ltag = self.timebucket_df_lower_tags[idx]
        3) For each timebucket column col in B_df, C_df[col] = func(self.reference_df[ref_column], B_df[col])
        4) If self.link_field is not null, then C_df[link_field] = A_df[link_field]
        5) If self.reference_df and B_df don't have the "same rows", then the above hold true with 
            self.reference_df, B_df replaced by the intersection
           of rows both in self.reference_df and B_df. By "same rows" we mean: rows where self.reference_df, 
           B_df have the same value for self.link_field or, if self._link_field is null, rows with the same index value.

        It also enriches self.timebucket_df_lower_tags by adding c_ltag for C_df
        
        @param ref_column A string, which must be a column in self.reference_df
        @param b_ltag A string, which must belong to self.timebucket_df_lower_tags, and the latter must not be null
        @param c_ltag A string that should be used as a lower tag for the result. It must not already exist in 
                self.timebucket_df_lower_tags, and it is appended to the latter, increasing its size by 1.
        @func A function that takes 3 arguments: a FunctionalTrace object, and two Pandas series, and returns a third series.
                The function may assume that both input series have the same index.
        '''
        with warnings.catch_warnings(record=True) as w:
            WarningUtils().turn_traceback_on(parent_trace, warnings_list=w)

            if not ref_column in self.reference_df.columns:
                raise ApodeixiError(parent_trace, "Can't apply unary operation to enrich DataFrames list because '" 
                                                    + str(ref_column) + "' is not a valid column for self.reference_df",
                                                    data = {"valid columns": str(self.reference_df.columns)})

            self._enrich_with_tb_operation(parent_trace,    a_df            = self.reference_df, 
                                                            b_ltag          = b_ltag, 
                                                            c_ltag          = c_ltag, 
                                                            func            = func, 
                                                            operation_type  = self.UNARY_OPERATION, 
                                                            ref_column      = ref_column)

            WarningUtils().handle_warnings(parent_trace, warning_list=w)
 

    def enrich_with_tb_cumulative_operation(self, parent_trace, b_ltag, c_ltag, func):
        '''
        Used to compute derived DataFrames.

        Example use case: suppose that self.reference_df has a column called "Sales", to represent
                        sales per quarter, and you would like to have an additional column "Cum Sales" for
                        the accumulated sales for all prior quarters, up to the current quarter.
                        Then this this methoc can be used to derive another DataFrame corresponding 
                        to "Cum Sales", computed
                        (via the `func` function parameter) as the accumulation of quarterly sales, row-by-row.
                        This derived DataFrame would get a lower tag given by c_ltag.

        More generally:

        This method enlarges self.timebucket_df_list by adding 1 additional DataFrame C_df, derived from 
        a pre-existing DataFrame ref_df, B_df already in self.timebucket_df, 
        so that the following holds true:

        1) B_df is the unique member self.timebucket_df_list[idx] such that b_ltag = self.timebucket_df_lower_tags[idx]
        2) For each timebucket column col in B_df, C_df[col] = func(C_df[col-], B_df[col]) where col- is the column
           in C_df preceding col, unless col is the first row in C_df, in whic case C_df[col-] = None
        3) If self.link_field is not null, then C_df[link_field] = A_df[link_field]

        It also enriches self.timebucket_df_lower_tags by adding c_ltag for C_df
        
        @param b_ltag A string, which must belong to self.timebucket_df_lower_tags, and the latter must not be null
        @param c_ltag A string that should be used as a lower tag for the result. It must not already exist in 
                self.timebucket_df_lower_tags, and it is appended to the latter, increasing its size by 1.
        @func A function that takes 3 arguments: a FunctionalTrace object, and two Pandas Series.
            It returns a third series. The function may assume that both input series have the same index.
        '''
        with warnings.catch_warnings(record=True) as w:
            WarningUtils().turn_traceback_on(parent_trace, warnings_list=w)

            self._enrich_with_tb_operation(parent_trace,    a_df            = None, 
                                                            b_ltag          = b_ltag, 
                                                            c_ltag          = c_ltag, 
                                                            func            = func, 
                                                            operation_type  = self.CUMULATIVE_OPERATION, 
                                                            ref_column      = None)

            WarningUtils().handle_warnings(parent_trace, warning_list=w)

    def _enrich_with_tb_operation(self, parent_trace, a_df, b_ltag, c_ltag, func, operation_type, ref_column):  
        '''
        @param operation_type A string, which must be one of: self.BINARY_OPERATION, self.UNARY_OPERATION, self.CUMULATIVE_OPERATION
        '''
        my_trace                        = parent_trace.doing("Validate inputs to enrich_with_binary_operation method")
        if True:
            if self.timebucket_df_lower_tags == None:
                raise ApodeixiError(my_trace, "Can't use enrich list of DataFrames to join unless lower tags are provided")
            if c_ltag in self.timebucket_df_lower_tags:
                raise ApodeixiError(my_trace, "Can't use tag '" + str(c_ltag) + "' to enrich list of DataFrames because "
                                            + "tag is already used by another DataFrame in the list",
                                            data = {"tags already used": str(self.timebucket_df_lower_tags)})
            if not b_ltag in self.timebucket_df_lower_tags:
                raise ApodeixiError(my_trace, "Can't use tag '" + str(b_ltag) + "' to identify which DataFrame to use as an "
                                            + " enrichment input because "
                                            + "tag is not in valid list of tags",
                                            data = {"allowed tags": str(self.timebucket_df_lower_tags)})
            if not operation_type in [self.BINARY_OPERATION, self.UNARY_OPERATION, self.CUMULATIVE_OPERATION]:
                raise ApodeixiError(my_trace, "Invalid operation type '" + str(operation_type) + "': should be one of: "
                                            + str([self.BINARY_OPERATION, self.UNARY_OPERATION, self.CUMULATIVE_OPERATION]))

        my_trace                        = parent_trace.doing("Combining DataFrames as preparation to applying binary operation")
        if True:
            LEFT_SUFFIX                 = "_left"
            RIGHT_SUFFIX                = "_right"
            b_idx                       = self.timebucket_df_lower_tags.index(b_ltag)
            b_df                        = self.timebucket_df_list[b_idx]
            if operation_type in [self.BINARY_OPERATION, self.UNARY_OPERATION]:
                left_df                 = a_df.copy()
                right_df                = b_df.copy()
                if self.link_field != None:
                    left_df             = self._untuple_link_column(my_trace, left_df) # Need to untuple before setting index
                    right_df            = self._untuple_link_column(my_trace, right_df) # Need to untuple before setting index
                    right_df            = right_df.set_index(self.link_field)
                    joined_df           = left_df.join(right_df, on=self.link_field, how="inner", 
                                                                    lsuffix=LEFT_SUFFIX, rsuffix=RIGHT_SUFFIX)
                else:
                    joined_df           = left_df.join(right_df, how="inner", 
                                                                    lsuffix=LEFT_SUFFIX, rsuffix=RIGHT_SUFFIX)
            else:
                # b_df might not have columns sorted by timebucket, but we need to sort them before we start doing the cumulative
                # operation, since cumulative operations are order dependent
                standardizer            = TimebucketStandardizer()
                joined_df, info         = standardizer.standardizeAllTimebucketColumns(my_trace, 
                                                                                        a6i_config      = self.a6i_config, 
                                                                                        df              = b_df, 
                                                                                        lower_level_key = None)

        my_trace                        = parent_trace.doing("Populating derived DataFrame")
        if True:
            derived_df                  = _pd.DataFrame({})
            if self.link_field != None:
                # Find the (possible tuple) column corresponding to link_field
                matches                 = [col for col in joined_df.columns if self._is_a_link_column(col, self.link_field)]
                if len(matches) == 0:
                    raise ApodeixiError(my_trace, "Invalid link_field '" + str(self.link_field) + "' : it is not present "
                                        + "as a column in at least some of the input dataframes supposed to join on that field",
                                        data = {"dataframe columns": str(joined_df.columns)}) 
                link_col                = matches[0]               
                derived_df[link_col]    = joined_df[link_col]
            
            if operation_type == self.BINARY_OPERATION:
                common_columns          = [col for col in left_df.columns if col in right_df.columns]
                for col in common_columns:
                    derived_df[col]     = func(my_trace, joined_df[str(col) + LEFT_SUFFIX], 
                                                        joined_df[str(col) + RIGHT_SUFFIX])
            elif operation_type == self.UNARY_OPERATION:
                for col in right_df.columns:
                    derived_df[col]     = func(my_trace, joined_df[ref_column], 
                                                        joined_df[col])
            elif operation_type == self.CUMULATIVE_OPERATION:
                tb_columns              = [col for col in joined_df.columns if not self._is_a_link_column(col, self.link_field)]
                for idx in range(len(tb_columns)):
                    col                 = tb_columns[idx]
                    if idx == 0:
                        prior_derived_s = None
                    else:
                        prior_col       = tb_columns[idx-1]
                        prior_derived_s = derived_df[prior_col]
                    derived_df[col]     = func(my_trace, prior_derived_s, joined_df[col])
            else:
                raise ApodeixiError(my_trace, "Invalid operation type '" + str(operation_type) + "': should be one of: "
                                            + str([self.BINARY_OPERATION, self.UNARY_OPERATION, self.CUMULATIVE_OPERATION]))

        my_trace                        = parent_trace.doing("Extending self's list of DataFrames and lower tags")
        if True:
            self.timebucket_df_list.append(derived_df)
            self.timebucket_df_lower_tags.append(c_ltag)
            if self.timebucket_df_upper_tags != None:
                # Need to add upper tag for the newly derived DataFrame. Should match what we used for b_df,
                # since they should be grouped together
                upper_tag               = self.timebucket_df_upper_tags[b_idx]
                self.timebucket_df_upper_tags.append(upper_tag)

        return

    def join_dataframes(self, parent_trace):
        '''
        Returns a DataFrame, resulting from joining this class's inputs (as set in the constructor, possibly
        enriched via the self.enrich... methods). The join adheres to this class' semantics, in terms of:
        - Adding lower/upper tags if they are provided
        - Sorting the results by upper tag, time bucket, and lower tag, in that order
        - Ensuring reference columns appear first, before timebucket columns
        '''
        with warnings.catch_warnings(record=True) as w:
            WarningUtils().turn_traceback_on(parent_trace, warnings_list=w)

            standardizer                    = TimebucketStandardizer()

            my_trace                        = parent_trace.doing("Build reference portion of result")
            if True:
                result_df                   = self.reference_df.copy()

            post_standardization_size       = None # Will be set when we loop through DataFrames to standardize
            my_trace                        = parent_trace.doing("Validating all non-reference DataFrame inputs will standardize the same way")
            for idx in range(len(self.timebucket_df_list)):
                loop_trace                  = my_trace.doing("Validating dataframe #" + str(idx))
                df_tmp_1                    = self.timebucket_df_list[idx]
                inner_trace                 = loop_trace.doing("Figure out standardization info, for later use")
                if True:
                    df_tmp_2, info          = standardizer.standardizeAllTimebucketColumns(inner_trace, 
                                                                                            a6i_config      = self.a6i_config, 
                                                                                            df              = df_tmp_1, 
                                                                                            lower_level_key = None) 

                    if post_standardization_size == None: # This must be the first cycle of the loop, so initialise it
                        post_standardization_size   = info.final_size
                    else: # This cycle of the loop must be consistent with prior cycles in this regard
                        if post_standardization_size != info.final_size:
                            raise ApodeixiError(inner_trace, "Can't join DataFrames because they don't all standardize the same "
                                                            + "way in terms the final zise to which levels are collapsed",
                                                            data = {'One DFs final size':      str(post_standardization_size),
                                                                    "Another DF's final size": str(info.final_size)})

            my_trace                        = parent_trace.doing("Determining the number of levels that result should have")
            if True:
                # This is the # of levels in the non-reference DataFrame inputs before tags get added
                result_nb_levels            = post_standardization_size 
                
                if self.timebucket_df_lower_tags != None:
                    # Add additional levels, for each tag. Because of constructor's validation, we know all have same number of levels and at
                    # least one exists
                    typical_tag             = self.timebucket_df_lower_tags[0]
                    if type(type) == tuple:
                        result_nb_levels    += len(typical_tag)
                    else:
                        result_nb_levels    += 1 # Tags are probably strings, so they only take 1 level
                if self.timebucket_df_upper_tags != None:
                    # Add additional levels, for each tag. Because of constructor's validation, we know all have same number of levels and at
                    # least one exists
                    typical_tag             = self.timebucket_df_upper_tags[0]
                    if type(type) == tuple:
                        result_nb_levels    += len(typical_tag)
                    else:
                        result_nb_levels    += 1 # Tags are probably strings, so they only take 1 level

            my_trace                        = parent_trace.doing("Append timebucket dataframes to result")
            for idx in range(len(self.timebucket_df_list)):
                loop_trace                  = my_trace.doing("Appending dataframe #" + str(idx))
                df1                         = self.timebucket_df_list[idx]
                inner_trace                 = loop_trace.doing("Standardizing timebuckets")
                if True:
                    df2, info               = standardizer.standardizeAllTimebucketColumns(inner_trace, 
                                                                                            a6i_config      = self.a6i_config, 
                                                                                            df              = df1, 
                                                                                            lower_level_key = None) 

                inner_trace                 = loop_trace.doing("Setting dataframe's index to be the linked_field, as preparation for the join")
                if self.link_field != None:

                    # We need to do some cleanup with the columns of df2 before we reset the index. 
                    # Example: perhaps the link_field is "Country", and it is a valid column in self.reference_df, whereas in
                    #           df2 it might be a tuple like ("", "Country").
                    #       In that case, change that particular column of df2 to be "Country"
                    #
                    df2                     = self._untuple_link_column(my_trace, df2)

                    # Now do what this was all about: setting index to be the link_field as preparation for the join we will
                    # do later with self.reference_df
                    try:
                        df2                 = df2.set_index(self.link_field)
                    except Exception as ex:
                        raise ApodeixiError(inner_trace, "Unable to use '" + self.link_field 
                                                        + "' as the index for the join in the reference DataFrame. Is it a valid column?",
                                                data = {"dataframe columns": str(df2.columns)} )

                inner_trace                 = loop_trace.doing("Adding tags, if any")   
                if True:
                    # Because of the validations we made in the constructor, we know that at this point the 
                    # columns of df2 are tuples of size 1 or strings (since the timebucket_df_list's columns have no level
                    # other than timebucket level)
                    #       
                    df3                     = df2.copy()   
                    if result_nb_levels > 1: # In this case, any string column and tag must become a tuple
                        df3.columns         = [(col,)   if type(col) != tuple and not self._is_a_link_column(col, self.link_field)
                                                        else col
                                                        for col in df3.columns]  

                    if self.timebucket_df_upper_tags != None:
                        utags               = self.timebucket_df_upper_tags.copy()
                        # First ensure any string column and tag must become a tuple
                        utags               = [(tag,)  for tag in utags if type(tag) != tuple]
                        # By now we know all columns and all tags are tuples. So we can use tuple addition to append
                        # tags 
                        df3.columns         = [utags[idx] + col
                                                        if not self._is_a_link_column(col, self.link_field)
                                                        else col
                                                        for col in df3.columns] 

                    if self.timebucket_df_lower_tags != None:
                        ltags               = self.timebucket_df_lower_tags.copy() 
                        # First ensure any string column and tag must become a tuple
                        ltags               = [(tag,)  for tag in ltags if type(tag) != tuple]
                        # By now we know all columns and all tags are tuples. So we can use tuple addition to append
                        # tags
                        df3.columns         = [col + ltags[idx] 
                                                        if not self._is_a_link_column(col, self.link_field)
                                                        else col
                                                        for col in df3.columns] 

                inner_trace                 = loop_trace.doing("Joining next DataFrame into result")
                if True:
                    try:
                        if self.link_field != None:
                            # In this case, the index of df3 is a foreign key to the link_field
                            result_df       = result_df.join(df3, on=self.link_field)
                        else:
                            # In this case the index of df3 is required to be (subset of) the index of self.reference_df,
                            # hence of result_df
                            result_df       = result_df.join(df3)
                    except Exception as ex:
                        raise ApodeixiError(inner_trace, "Encountered problem joining DataFrame into result: " + str(ex))
                    
            my_trace                        = parent_trace.doing("Sorting the result")
            if True:
                # First we need to sort by the "upper levels" above the timebuckets, to ensure that the result
                # is grouped by such "upper levels", if any. 
                # Example: Say inputs are dataframes A_df and B_df, and each of them has upper levels called
                #               "Sales", "Profit". If we had lower tags called "Target" (for A_df) and "Actual" (for B_df)
                #               then this first pass ast sorting is to move from columns like
                #
                #       Sales   | Sales   | Profit  | Profit  | Sales   | Sales   | Profit  | Profit  |
                #       Q1 FY22 | Q2 FY22 | Q1 FY22 | Q2 FY22 | Q1 FY22 | Q2 FY22 | Q1 FY22 | Q2 FY22 |
                #       Target  | Target  | Target  | Target  | Actual  | Actual  | Actual  | Actual  |
                #
                # to something that groups the upper levels, like:
                #
                #       Sales   | Sales   | Sales   | Sales   | Profit  | Profit   | Profit  | Profit  |
                #       Q1 FY22 | Q2 FY22 | Q1 FY22 | Q2 FY22 | Q1 FY22 | Q2 FY22 | Q1 FY22 | Q2 FY22 |
                #       Target  | Target  | Actual  | Actual  | Target  | Target  | Actual  | Actual  |
                #
                # Then on the second pass of the sorting, we realy on the standardizer to get a grouping by timebucket, like:
                #
                #       Sales   | Sales   | Sales  | Sales    | Profit  | Profit  | Profit  | Profit  |
                #       Q1 FY22 | Q1 FY22 | Q2 FY22 | Q2 FY22 | Q1 FY22 | Q1 FY22 | Q2 FY22 | Q2 FY22 |
                #       Target  | Actual  | Target  | Actual  | Target  | Actual  | Actual  | Actual  |

                if result_nb_levels > 1:
                    # We use the "pairing trick" to sort: create a pair where one member is the item on which
                    # we sort, the the second member is the item that must be in the sorted result. By glueing them
                    # like this we can re-use the generic sort function for lists
                    #
                    # To ensure that reference columns stay "in relative order", for them the first member of the pair
                    # will be the original index location for such reference colum.
                    #
                    # To use this trick, we first have to determine the cutoff for the upper levels
                    #
                    upper_level_cutoff      = result_nb_levels - 1 # Subtract 1 for the time buckets, a string taking 1 level
                    ltags                   = self.timebucket_df_lower_tags
                    if ltags != None:
                        a_random_tag        = ltags[0] # All tags have the same number of levels, so we can look at any
                        if type(a_random_tag) == tuple:
                            upper_level_cutoff  -= len(a_random_tag)
                        else:
                            upper_level_cutoff  -= 1 # Tag only consumes 1 level if it is a string
                        
                    # We know result_df.colums are tuples since result_nb_levels > 1, except for reference columns
                    # For which it is a string
                    originals               = result_df.columns
                    unsorted_pairs_l        = [[originals[idx][:upper_level_cutoff], originals[idx]] 
                                                    if type(originals[idx]) == tuple
                                                    else [str(idx), originals[idx]]
                                                    for idx in range(len(originals))]

                    # Not 100% proof, but to get unique hashcode for a tuple we will use the "weird string" DELIM below
                    # to join tuple's levels into a single string, hoping that since it is so weird then the
                    # hash code of different tuples will be different.
                    # We also make it so that it should (hopefully) be sorted after any "reference" string column
                    # We take into account that when sorting strings, this holds true:
                    #   "!" < "#" < "9" < "@" < "A" < "Z" < "a" < "z"
                    #
                    # In other words, we need our "weird string" to start with lower case "z" we want it to go last.
                    # To ensure it is after any other valid column that starts with "z", with put multiple "z"'s at the start
                    # of the "weird string", hopefully ensuring any valid column is an English word not starting with multiple "z"'s
                    # 
                    DELIM                   = "zzz@#!"
                    
                    sorted_pairs_l          = sorted(unsorted_pairs_l,
                                                    key = lambda pair: DELIM + DELIM.join(pair[0])
                                                                        if type(pair[1]) == tuple
                                                                        else pair[0])
                    
                    sorted_columns          = [pair[1] for pair in sorted_pairs_l]

                    # GOTCHA: It may be that result_df has heterogeneous columns (mix of string columns and tuple
                    #           columns). Pandas doesn't like that and will issue warnings when selecting on them.
                    #       To prevent that, homogenize the columns so they are all tuples, in such a situation
                    #
                    result_df.columns        = TupleColumnUtils().homogenize_columns(parent_trace, 
                                                                                heterogeneous_columns   = result_df.columns)

                    sorted_columns          = TupleColumnUtils().homogenize_columns(parent_trace, 
                                                                                heterogeneous_columns   = sorted_columns)

                    # Now this Pandas select call is safe, now that we homogenized columns:
                    result_df               = result_df[sorted_columns]

                # Now the second pass, to sort so that lower levels are grouped by timebucket
                result_df, info             = standardizer.standardizeAllTimebucketColumns(inner_trace, 
                                                                                            a6i_config      = self.a6i_config, 
                                                                                            df              = result_df, 
                                                                                            lower_level_key = None) 

            WarningUtils().handle_warnings(parent_trace, warning_list=w)

        return result_df
    

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

    def containsTimebucketColumns(self, parent_trace, a6i_config, df):
        '''
        Returns a boolean, to determine if parameter `df` contains any columns which are time buckets.
        '''
        if df is None or len(df.columns)==0 or len(df.index)==0:
            raise ApodeixiError(parent_trace, "Invalid DataFrame provided to containsTimebucketColumns: DataFrame is empty")

        original_columns                = list(df.columns)

        if len([col for col in original_columns if self.is_a_timebucket_column(parent_trace, col, a6i_config)])==0:
            return False
        else:
            return True

    def standardizeAllTimebucketColumns(self, parent_trace, a6i_config, df, lower_level_key=None):
        '''
        Returns two things:
        
        1. A DataFrame, identical to df except that columns are modified as per the description below
        2. A TimebucketStandardizationInfo object, containing information on how the standardization was done (e.g.,
            for multi-level columns, which level was the time bucket and which levels were collapsed, if any)

        The modifications to the columns is done as follows:

        * What we call "timebucket columns" might be a string column (like "FY23") or tuples, where 1 or 2 consecutive
          levels represent a timebucket. 
            Example: ("Sales", "Q2", "FY23", "Actual"), in which levels [1,2] represent the timebucket
            Example: ("Sales", "Q2 FY23", "Actual"), in which level [1] represents the tiebucket
            Example: ("Q2", "FY23")
            Example: ("Q1 FY2024", "Sales")
        * Any "timebucket column" is mapped to a FY_Quarter object
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
        * In the time bucket sorting, an optional "key" may be provided for sorting lower-order levels below the time buckets, if any.
            Example: if the columns are ("Q2 FY 23", "Actual") and ("Q2 FY 23", "Target"), then if we want "Target" columns to be
                    to the left of "Actual" columns, we can pass a key that acts on the lower levels [("Actual"), ("Target")]
                    to sort them so that ("Q2 FY 23", "Target") appears first and ("Q2 FY 23", "Actual") appears afterwards.
                    The "key"

        @param lower_level_key Optional parameter, defaults to None. If not null, it should be a lambda that acts on tuples
            and returns a positive decimal, i.e., a number x such that 0 < x < 1. This restriction is important to guarantee
            that the sorting algorithm works.
            This returned value is used as a key to sort tuples. The tuples it acts on are sub-tuples of the columns of the
            DataFrame being built, corresponding to levels below the timebuckets, if any. 
            For example, if the resulting DataFrame has columns ("Q2 FY 23", "Actual") and ("Q2 FY 23", "Target"), then the
            `lower_level_key` is a function that acts on tuples ("Actual") and ("Target") and sorts them.
        '''
        if df is None or len(df.columns)==0 or len(df.index)==0:
            raise ApodeixiError(parent_trace, "Invalid DataFrame provided to TimebucketStandardizer: DataFrame is empty")

        original_columns                = list(df.columns)

        #if len([col for col in original_columns if self.is_a_timebucket_column(parent_trace, col, a6i_config)])==0:
        if not self.containsTimebucketColumns(parent_trace, a6i_config, df):
            raise ApodeixiError(parent_trace,  "Invalid DataFrame provided to TimebucketStandardizer: it lacks any timebucket columns - should at least have 1",
                                            data = {"df.columns": str([str(col) for col in original_columns])})

        unsorted_flattened_columns      = []
        # As we flatten columns in the loop below, we also partition the columns into intervals, where each interval
        # either consists only of columns with FY_Quarter objects, or only of strings which don't represent time buckets.
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
                    # The sorting happens at 2-3 levels:
                    #   * First by year
                    #   * Then by quarter
                    #   * Finally, if lower levels exist in a multi-level index an if `lower_level_key` != None,
                    #     by `lower_level_key`.
                    #
                    # The algorithm works because we know quarters are between 1 and 4, and any lower level key is
                    # less than 1. 
                    #
                    def _sorting_aggregate_key(column, timebucket):
                        year                    = timebucket.fiscal_year
                        quarter                 = timebucket.quarter

                        # GOTCHA: 
                        #   If the timebucket is for a full year, we want it to appear *after* any other timebucket for the
                        #   same year, so artificially make a "5th" quarter is it is sorted after Q4
                        #
                        if timebucket.is_a_year_bucket:
                            quarter             = 5

                        # quarter < 10, so by multiplying by 100 we make quarter the least significant digit, guaranteeing key is unique
                        # (i.e, can have different timebuckets with the same key)
                        key                     = year*100 + quarter 
                        if type(column) == tuple and len(standardization_info.timebucket_indices) > 0 \
                                                and len(column) > standardization_info.timebucket_indices[0] + 1 \
                                                and lower_level_key != None:
                            # In this case we have lower levels in the column, below the timebucket, and we are expected
                            # to sort them with the caller-provided key function
                            cutoff              = standardization_info.timebucket_indices[0]
                            lower_levels        = column[cutoff+1:]
                            extra_key           = lower_level_key(lower_levels)
                            if type(extra_key) != float or extra_key <= 0 or extra_key >= 1:
                                raise ApodeixiError(my_trace, "Bad sorting key provided: should return a value bigger than 0 "
                                                                + "and less than 1",
                                                                data = {"returned key":             str(extra_key),
                                                                        "key applies to column":    str(column),
                                                                        "key is for sub-tuple":     str(lower_levels)})
                            key                 += extra_key
                        return key
                            
                    # To sort the columns, we create this bigger data structure to "join" all the data needed for sorting.
                    # After we sort this bigger structure we will extract the sorted columns as a sub-structure
                    #
                    unsorted_joined_list        = [[unsorted_interval_columns[idx], unsorted_timebuckets[idx]] 
                                                    for idx in range(len(unsorted_interval_columns))]

                    # Sort by key, using the aggregated key function above that combines sorting by year, by quarter, and
                    # (optionally) by lower levels using a caller-provided key
                    sorted_joined_list          = sorted(unsorted_joined_list,
                                                        key = lambda pair: _sorting_aggregate_key(pair[0], pair[1]))

                    sorted_interval_columns     = [pair[0] for pair in sorted_joined_list]
                    sorted_columns.extend(sorted_interval_columns)
                else:
                    sorted_columns.extend(tagged_interval[1])

            # GOTCHA: It may be that result_df has heterogeneous columns (mix of string columns and tuple
            #           columns). Pandas doesn't like that and will issue warnings when selecting on them.
            #       To prevent that, homogenize the columns so they are all tuples, in such a situation
            #
            unsorted_df.columns             = TupleColumnUtils().homogenize_columns(parent_trace, 
                                                                        heterogeneous_columns   = unsorted_df.columns)

            sorted_columns                  = self._disambiguate_duplicates(parent_trace, sorted_columns)
            sorted_columns                  = TupleColumnUtils().homogenize_columns(parent_trace, 
                                                                        heterogeneous_columns   = sorted_columns)

            sorted_df                       = unsorted_df[sorted_columns]

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
                LIMIT                   = 1000 # To avoid infinite loops if there is a bug, constrain unbounded search
                while idx < LIMIT:
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
            ("Sales", "Q3 FY24", "Actuals"). In that case, this object records that:
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

    def __eq__(self, other):
        if isinstance(other, TimebucketStandardizationInfo):
            return self.timebucket_indices == other.timebucket_indices and self.final_size == other.final_size

        return False
import numpy                                    as _numpy
import math                                     as _math
import pandas                                   as _pd
import datetime    as _datetime
import warnings

from apodeixi.util.a6i_error                    import ApodeixiError  
from apodeixi.util.warning_utils                import WarningUtils

from apodeixi.util.list_utils              		import ListMerger 

class DataFrameUtils():
    def __init__(self):
        return

    def _numpy_2_float(self, x):
        '''
        Cleans problems with numbers in the trees being built. Turns out that if they are numpy classes then the
        YAML produced is unreadable and sometimes won't load. So move anything numpy to floats. If there are no decimals, returns an int
        '''
        if type(x)==_numpy.int32 or type(x)==_numpy.int64:
            return int(x)
        elif type(x)==_numpy.float32 or type(x)==_numpy.float64 or type(x)== float: 
            y = float(x)
            if not _math.isnan(x) and int(x) - y == 0: # this is really an int
                return int(x)
            else:
                return y # This is really a float
        else:
            return x

    def clean(self, x):
        '''
        Addresses a number of problems with cell values returned by Pandas when which are not formattable outside Pandas
        in a nice way. Things like: nan, NaT, dates, numpy classes, ...

        So it returns a "cleaned up" version of x, safe to use in text messages or as values in a YAML file.
        It preserves the "natural type" of x - numbers become int or float, dates become datetime, strings remain strings,
        and "bad stuff" (nans, NaT, etc) become an empty string.

        If there is nothing to clean, just return x
        '''
        # Clean up numerical stuff, if any
        y           = self._numpy_2_float(x)
        if type(y)==float and _math.isnan(y):
            y       = ''

        # Clean up NaT stuff, if any
        if type(y) == type(_pd.NaT): 
            y       = ''

        # Clean up dates, if any
        if 'strftime' in dir(y):
            y       = y.strftime('%Y-%m-%d') # As required by YAML: ISO-8601 simple date format
            y       = _datetime.datetime.strptime(y, '%Y-%m-%d') # Now parse into a datetime

        # Tidy up strings, if needed - remove new lines, trailing or leading spaces
        '''
        if type(y)==str:
            y       = y.replace('\n', '').strip(' ')
        '''
        return y

    def safely_drop_duplicates(self, parent_trace, df):
        '''
        Implements dropping of duplicates for DataFrame `df` in a more robust manner than Pandas' default implementation,
        which fails if the cells in the DataFrame are not hashable.
        
        For example, lists are not hashable. If the DataFrame contains lists then an attempt to drop duplicates
        would produce an error "TypeError: unhashable type: 'list'".

        In Apodeixi this happens often - for example, when manifests contain many-to-many mappings to other manifests
        (e.g., the milestones kind has a list to reference big-rocks). So it is a problem to address since dropping of
        duplicates happens in various use cases (such as when comparing a manifest to its previous version, by
        creating 2 DataFrames and comparing interval-by-interval, dropping duplicates for each interval)'

        This method remedies this problem by converting DataFrame contents to a string, dropping duplicates, and using
        the index of the result to select in the original DataFrame, so the returned DataFrame's cells are the same object as
        when initially provided (e.g., lists)

        This implementation is inspired by https://newbedev.com/pandas-drop-duplicates-method-not-working

        @param df A Pandas DataFrame
        @return A DataFrame, obtained from the first by dropping duplicates
        '''
        try:
            strings_df                  = df.astype(str)
            no_duplicates_strings_df    = strings_df.drop_duplicates()
            no_duplicates_df            = df.loc[no_duplicates_strings_df.index]

            return no_duplicates_df
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Encountered problem when dropping duplicates from a DataFrame",
                                            data = {"type(error)": str(type(ex)), "error": str(ex)})

    def safe_unique(self, parent_trace, df, column_name):
        '''
        More robust implementation than Pandas for obtaining a list of the unique values for a column in 
        a DataFrame.

        In Pandas, one might typically do something like:

            df[column_name].unique()

        This has proven not robust enough in the Apodeixi code base because it can obscurely mask a defect
        elsewhere in Apodeixi, with a cryptic message like:

            'DataFrame' object has no attribute 'unique'

        The problem arises because there might be "duplicates" (usually due to another defect in the code)
        in the columns of DataFrame df. While technically speaking columns are "unique", the way Pandas
        handles a "user bad practice" of putting multiple columns with the same name is to treat the column
        index as based on objects, not strings. That allows effectively to have duplicates among the columns
        of DataFrame df, like so:

            UID |   Area    | UID-1 | Indicator |   UID-2   | Sub-Indicator | UID-2     | UID-3         | Space
            ---------------------------------------------------------------------------------------------------------
            A1  |  Adopt    | A1.I1 | throughput|           |               | A1.I1.S1  |               | tests
            A1  |  Adopt    | A1.I2 | latency   | A1.I2.SU1 |   interactive |           | A1.I2.SU1.S1  | tests  

        The second occurrence of "UID-2" should have been merged into the "UID-3" column, but we once had an Apodeixi defect
        that didn't, instead having two columns called "UID2". This is because Apodeixi was incorrectly using
        "UID-n" if the UID had exactly n tokens, which is not a unique acronym path if some of the entities
        are blank as in the example above, where the first row has no sub-indicator.

        Upshot: the dataframe columns have "UID-2" duplicated, so an attempt to do 

                df["UID-2]

        would produce a DataFrame, not a Series, so calling "unique()" on it would error out with a very cryptic
        message:

            'DataFrame' object has no attribute 'unique'

        Instead, what this "more robust" method does is check if the column in question is not unique, and so it will
        error out with hopefully a less criptic message. 
        If column is unique, it will return a list.

        @param column_name A string, corresponding to the name of a column in the DataFrame
        @param df A DataFrame. It is expected to have the `column_name` parameter as one of its columns.
        '''
        if type(column_name) != str:
            raise ApodeixiError(parent_trace, "Can't get unique values for a DataFrame's column because column name provided is a '"
                                + str(type(column_name)) + "' was provided instead of a string as expected") 
        if type(df) != _pd.DataFrame:
            raise ApodeixiError(parent_trace, "Can't get unique values for column '" + str(column_name) + "' because a '"
                                + str(type(df)) + "' was provided instead of a DataFrame as expected")

        if len(column_name.strip()) ==0:
            raise ApodeixiError(parent_trace, "Can't get unique values for a DataFrame's column because column name provided is blank")
 
        columns                 = list(df.columns)
        matches                 = [col for col in columns if col == column_name]

        if len(matches) == 0:
            raise ApodeixiError(parent_trace, "Can't get unique values in a DataFrame for column '" + str(column_name) + "' because it "
                                + " is not one of the DataFrame's columns",
                                data    = {"df columns": str(columns)})
        elif len(matches) > 1:
            raise ApodeixiError(parent_trace, "Can't get unique values in a DataFrame for column '" + str(column_name) + "' because it "
                                + "appears multiple times as a column in the DataFrame",
                                data    = {"df columns": str(columns)})

        # All is good, so now it is safe to call the Pandas unique() function
        return list(df[column_name].unique())
       
    def replicate_dataframe(self, parent_trace, seed_df, categories_list):
        '''
        Creates and returns a DataFrame, by replicating the `seed_df` for each member of the `categories_list`,
        and concatenating them horizonally.
        The columns are also added a new top level, from `categories_list`.

        A usecase where this is used is to create templates for product-related manifests where similar content
        must exist per sub-product.
        
        Example:

        Suppose a product has subproducts ["Basic", "Premium], and this is provided as the `categories_list`.
        Suppose the `seed_df` is some estimates about the product, such as:

                bigRock  FY 19  FY 20  FY 21
            ================================
            0    None    150    150    150
            1    None    100    100    100
            2    None      0      0      0
            3    None     45     45     45
            4    None      0      0      0
            5    None    300    300    300
            6    None    140    140    140

        Then this method would return the following DataFrame

                        Basic                |          Premium
                bigRock  FY 19  FY 20  FY 21 |  bigRock  FY 19  FY 20  FY 21
            ====================================================================
            0    None    150    150    150      None    150    150    150   
            1    None    100    100    100      None    100    100    100
            2    None      0      0      0      None      0      0      0
            3    None     45     45     45      None     45     45     45
            4    None      0      0      0      None      0      0      0
            5    None    300    300    300      None    300    300    300
            6    None    140    140    140      None    140    140    140

        @param categories_list A list of hashable objects, such as strings or ints
        '''
        with warnings.catch_warnings(record=True) as w:
            WarningUtils().turn_traceback_on(parent_trace, warnings_list=w)
            
            dfs_dict                = {}
            for category in categories_list:
                dfs_dict[category]  = seed_df.copy()
            
            replicas_df             = _pd.concat(dfs_dict, axis=1)
            
            WarningUtils().handle_warnings(parent_trace, warning_list=w)

            return replicas_df

    def is_UID_column(self, parent_trace, column):
        '''
        Returns a boolean: True if `column` is the name of a UID column, False otherwise.

        Examples: "UID", "UID-1", "UID-3", ("SubProductA", "UID-4") are all examples of UID columns.
        '''
        if type(column)==str:
            return column.startswith('UID')
        elif type(column)==tuple:
            if len(column)==0 or type(column[-1]) != str:
                raise ApodeixiError(parent_trace, "Invalid MultiIndex DataFrame column: tuple should not be empty and "
                                                    + "its last member should be a string",
                                                    data = {"column": str(column)})
            return column[-1].startswith('UID')

    def re_index(self, parent_trace, input_df):
        '''
        Returns a new DataFrame that is "amost the same" as the `input_df`, in the sense that the columns, the number and
        order of the rows, and data content are the same.

        The only difference is that the index is reset, so it becomes a successive set of ordinals 0,1,2,..., without adding
        any additional columns.
        '''
        df2                 = input_df.reset_index()
        
        # Now we have to drop the column that was added as part of the reset. If the column index is not multi-level, then
        # that column is called "index" (a string).
        # However, if the column index is multi-level (say, it has 2 levels) then the column is a tuple like ("index", "")
        if type(df2.columns) == _pd.core.indexes.multi.MultiIndex:
            N               = len(df2.columns.levels)
            INDEX_COLUMN    = tuple(["index"] + ['']*(N-1))
        else:
            INDEX_COLUMN    = "index"

        df3                 = df2.drop(INDEX_COLUMN, axis=1)
        return df3

class TupleColumnUtils():
    '''
    Utility methods to deal with situations when a DataFrame uses tuples for (some or all) of its columns
    '''
    def __init__(self):
        return

    def homogenize_columns(self, parent_trace, heterogeneous_columns):
        '''
        Used for situations when a DataFrame has a mix of string and tuple columns.
        In that case, this method creates and returns a new set of columns all of which are tuples of the same length,
        and returns it as a list.

        This method's processing of a particular column X is as follows:
        * If X is a tuple, it must have the same length as all other columns that are tuples
        * If X is a string, then it will be replaced by the tuple  (X, "", "", ..., "",)
        '''
        # Validate inputs are as expected
        bad_columns         = [col for col in heterogeneous_columns if type(col) != tuple and type(col) != str]
        if len(bad_columns) > 0:
            raise ApodeixiError(parent_trace, "Can't homogenize columns because not all members are tuples or strings",
                                            data = {"bad columns": str([str(col) for col in bad_columns])})
        nb_levels_l             = list(set([len(col) for col in heterogeneous_columns if type(col)==tuple]))
        if len(nb_levels_l) == 0: # This happens if no column is a tuple. If so, just return unmodified input
            return heterogeneous_columns
        elif len(nb_levels_l) > 1:
            raise ApodeixiError(parent_trace, "Can't homogenize columns because not all tuples are of the same length",
                                                data = {"tuple lengths": str([str(nb) for nb in nb_levels_l])})

        # If we get this far, there is a unique level, which is what we expected
        nb_levels           = nb_levels_l[0]

        def _homogenize_one_column(col):
            if type(col)==tuple:
                return col
            else:
                return (col,) + ("",)*(nb_levels-1)

        homogenized_columns     = [_homogenize_one_column(col) for col in heterogeneous_columns]
        return homogenized_columns

    def validate_homogeneity(self, parent_trace, columns):
        '''
        Helper method to validate that all columns are homogeneous, i.e., either all columns are strings or
        else all columns are tuples of the same length.

        If the columns are not homogenous, it raises an exception.
        If they are homogeneous, then it returns an integer:

        * Returns 0 if all columns are strings
        * Returns N if all columns are tuples, where N is the common length of all tuple columns
        '''
        ALL_COLUMNS_ARE_STRINGS = 0
        bad_columns         = [col for col in columns if type(col) != tuple and type(col) != str]
        if len(bad_columns) > 0:
            raise ApodeixiError(parent_trace, "Columns are not homogeneous: not all members are tuples or strings",
                                            data = {"bad columns": str([str(col) for col in bad_columns])})

        string_columns          = [col for col in columns if type(col) == str] 
        tuple_columns           = [col for col in columns if type(col) == tuple] 

        if len(string_columns) > 0 and len(tuple_columns) > 0:
            raise ApodeixiError(parent_trace, "Columns are not homogeneous: there is a mix of string and tuple columns")

        if len(string_columns) == len(columns): # all columns are strings, so return that
            return ALL_COLUMNS_ARE_STRINGS
        
        # If we get this far, all columns are tuples. Check they have the same length
        nb_levels_l             = list(set([len(col) for col in tuple_columns]))
        if len(nb_levels_l) > 1:
            raise ApodeixiError(parent_trace, "Columns are not homogeneous: not all tuples are of the same length",
                                                data = {"tuple lengths": str([str(nb) for nb in nb_levels_l])})

        # All is good, in that all columns are tuples of the same size. So return that size
        nb_levels               = nb_levels_l[0]
        return nb_levels



class DataFrameComparator():
    '''
    Helper class to check if two datafames are "equal where it matters".

    @df1 A dataframe to compare
    @df2 The other dataframe to compare
    @df1_name A string, for the label that text output should have when referencing df1
    @df2_name A string, for the label that text output should have when referencing df2
    @param id_column A string representing the column that should be used to identify rows in comparison text produced. 
                        If set to None, then the row index is used.
    '''
    def __init__(self, df1, df2, df1_name, df2_name, id_column=None):
        self.df1                    = df1.copy() # Make a  since we might mutate self.df1 (e.g., by resetting its index to ease comparisons)
        self.df2                    = df2.copy() # Make a  since we might mutate self.df1 (e.g., by resetting its index to ease comparisons)
        self.df1_name               = df1_name
        self.df2_name               = df2_name
        self.id_column              = id_column


    def compare(self, parent_trace):
        '''
        Helper method used in lieu of dataframe.equals, which fails for spurious reasons.
        Under this method's policy, two dataframes are equal if they have the same columns, indices, and are
        point-wise equal.

        Method returns two things: a boolean result of the comparison, and a dictionary to pin point where there are
        differences, if any
        '''
        # Prepare an explanation of where the dataframes differ, if they do differ. This visibility helps with debugging
        comparison_dict                                 = {}
        comparison_dict[self.df1_name + ' shape']       = str(self.df1.shape)
        comparison_dict[self.df2_name + ' shape']       = str(self.df2.shape)

        # Initialize true until profen false
        check                                           = True

        my_trace                                        = parent_trace.doing("Re-setting DataFrames index")
        self._init_row_index(my_trace)

        my_trace                                        = parent_trace.doing("Comparing column names")
        common_cols, col_names_diff_dict                = self._column_names_diff(my_trace)
        if len(col_names_diff_dict.keys()) > 0:
            check                                       = False
        comparison_dict                                 = comparison_dict | col_names_diff_dict



        my_trace                                        = parent_trace.doing("Looping throw the rows")
        only_in_df1                                     = []
        only_in_df2                                     = []
        cell_dict                                       = {}
        for row_pair in SimultaneousRowIterator(        parent_trace    = my_trace, 
                                                        df1             = self.df1, 
                                                        df1_name        = self.df1_name, 
                                                        df2             = self.df2, 
                                                        df2_name        = self.df2_name):
            row_idx                                     = row_pair[0]
            row1                                        = row_pair[1]
            row2                                        = row_pair[2]
            if type(row1) == type(None): # Can't compare a series to None for some reason, so compare types
                only_in_df2.append(row_idx)
                check                                   = False
                continue
            if type(row2) == type(None): # Can't compare a series to None for some reason, so compare types
                check                                   = False
                only_in_df1.append(row_idx)
                continue

            for col in common_cols: # use common_cols that is a deterministic list
                val1                                                    = row1[col]
                val2                                                    = row2[col]
                if val1 != val2:
                    check                                               = False
                    coords                                              = '[' + str(col) + '][' + str(row_idx) + "]"
                    types_differ                                    = type(val1) != type(val2)

                    cell_dict[coords] = {self.df1_name: str(val1), self.df2_name: str(val2)}
                    if types_differ:
                        cell_dict[coords + " type"] = {self.df1_name: type(val1), self.df2_name: type(val2)}

        comparison_dict['only in ' + self.df1_name]                     = only_in_df1  
        comparison_dict['only in ' + self.df2_name]                     = only_in_df2  
        comparison_dict['elt-by-elt comparison']                        = cell_dict

        if check:
            comparison_dict['Result of elt-by-elt comparison'] = "Everything matches"

        return check, comparison_dict

    def _column_names_diff(self, parent_trace):

        cols_diff_dict                                  = {}

        cols_1                                          = set(self.df1.columns)
        cols_2                                          = set(self.df2.columns)

        # Ensure determinism with sort
        common_cols                                     = list(cols_1.intersection(cols_2))
        common_cols.sort() 
        missing_in_1                                    = list(cols_2.difference(cols_1))
        missing_in_1.sort()
        missing_in_2                                    = list(cols_1.difference(cols_2))
        missing_in_2.sort()

        if len(missing_in_1) > 0:
            cols_diff_dict[self.df1_name + ' missing columns']  = '\n'.join([str(col) for col in missing_in_1])
        if len(missing_in_2) > 0:
            cols_diff_dict[self.df2_name + ' missing columns']  = '\n'.join([str(col) for col in missing_in_2])

        return common_cols, cols_diff_dict

    def _init_row_index(self, parent_trace):

        if self.id_column != None:
            if self.id_column not in self.df1.columns:
                raise ApodeixiError(parent_trace, "Can't initialize an iterator because '" + self.id_column + "' is not in the column of df1")
            if self.id_column not in self.df2.columns:
                raise ApodeixiError(parent_trace, "Can't initialize an iterator because '" + self.id_column + "' is not in the column of df2")
        
            ids1 = DataFrameUtils().safe_unique(parent_trace, self.df1, self.id_column)
            ids2 = DataFrameUtils().safe_unique(parent_trace, self.df2, self.id_column)

            if len(self.df1.index) != len(ids1):
                raise ApodeixiError(parent_trace, "Can't reset df1's index to '" + self.id_column + "' because it is not unique across df1 rows")
            if len(self.df2.index) != len(ids2):
                raise ApodeixiError(parent_trace, "Can't reset df2's index to '" + self.id_column + "' because it is not unique across df2 rows")

            self.df1 = self.df1.set_index([self.id_column])
            self.df2 = self.df2.set_index([self.id_column])

class SimultaneousRowIterator():
    '''
    Helper class to iterate throw the rows of two DataFrames simultaneously. It is presumed that both DataFrames have "consistent" row indices,
    where consistency means that overlapping indices appear in the same order in both DataFrames. More specifically:

    Let df be a dataframe. For x, y in df1.index, we say x is before y in df if df.iloc[x] precedes df.iloc[y] in the df.iterrows enumeration.

    Then we say that for two DataFrames df1, df2 that they have "consistent" row indices if for every x, y in both df1.index and df2.index,
    then x is before y in df1 and and oly if x is before y in df2.

    Under such consitency conditions, the iterator returns a triple

    `[x, row_1, row_2]`

    where x is an index in df1, df2, or both, and row_i is dfi.iloc[x] if x is an index of dfi, or None otherwise, for i =1,2.

    @df1 First of two DataFrames over whose rows to iterate.
    @df2 Second of two DataFrames over whose rows to iterate.
    @df1_name A string, for the label that text output should have when referencing df1
    @df2_name A string, for the label that text output should have when referencing df2
    '''
    def __init__(self, parent_trace, df1, df1_name, df2, df2_name):
        self.df1                    = df1.copy() # Make a  since we might mutate self.df1 (e.g., by resetting its index to ease comparisons)
        self.df2                    = df2.copy() # Make a  since we might mutate self.df1 (e.g., by resetting its index to ease comparisons)
        self.df1_name               = df1_name
        self.df2_name               = df2_name

        my_trace                    = parent_trace.doing("Merging indices from two DataFrames to initialize SimultaneousRowIterator")
        self.merger                 = ListMerger(   parent_trace        = my_trace,
                                                    list1               = list(self.df1.index),
                                                    list2               = list(self.df2.index), 
                                                    list1_name          = df1_name + ".index", 
                                                    list2_name          = df2_name + ".index")

        self.merged_indices         = self.merger.merge(parent_trace)

        if len(self.merged_indices) == 0:
            raise ApodeixiError("Can't initialize an iterator with an empty list of merged indices",
                                data    = { 'df1_name':     df1_name,
                                            'df2_name':     df2_name})
        self.current_idx            = 0 # Used to track where we are in the iteration through the rows


        # Verify consistency of indices, and if so
        ME                          = SimultaneousRowIterator

    def __iter__(self):
        return self

    def __next__(self):
        if self._iteration_is_over():
            raise StopIteration

        current_index_metadata      = self.merged_indices[self.current_idx]
        row_idx                     = current_index_metadata[0]
        row1                        = self._get_row(  df  = self.df1,     row_idx = row_idx,  row_exists  = current_index_metadata[1])
        row2                        = self._get_row(  df  = self.df2,     row_idx = row_idx,  row_exists  = current_index_metadata[2])
        entry                       = [row_idx, row1, row2]
        self.current_idx            += 1
        return entry

    def _get_row(self, df, row_idx, row_exists):
        '''
        '''
        if not row_exists:
            return None
        return df.loc[row_idx]

    def _iteration_is_over(self):
        '''
        Returns True if there is we have traversed through all the elements in self.merged_indices
        '''
        if self.current_idx >= len(self.merged_indices):
            return True
        return False

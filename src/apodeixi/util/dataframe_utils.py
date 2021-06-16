import numpy                                    as _numpy
import math                                     as _math

from apodeixi.util.a6i_error                    import ApodeixiError    

from apodeixi.util.list_utils              		import ListMerger 

class DataFrameUtils():
    def __init__(self):
        return

    def numpy_2_float(self, x):
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
                    coords                                              = '[' + col + '][' + str(row_idx) + "]"
                    types_differ                                    = type(val1) != type(val2)

                    cell_dict[coords] = {self.df1_name: str(val1), self.df2_name: str(val2)}
                    if types_differ:
                        cell_dict[coords + " type"] = {self.df1_name: type(val1), self.df2_name: type(val2)}
                    '''
                    cell_dict[self.df1_name + coords]             = str(val1)
                    if types_differ:
                        cell_dict[self.df1_name + coords + " type"]   = str(type(val1))
                    cell_dict[self.df2_name + coords]             = str(val2)
                    if types_differ:
                        cell_dict[self.df2_name + coords + " type"]   = str(type(val2))
                    '''
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
            cols_diff_dict[df1_name + ' missing columns']  = '\n'.join(missing_in_1)
        if len(missing_in_2) > 0:
            cols_diff_dict[df2_name + ' missing columns']  = '\n'.join(missing_in_2)

        return common_cols, cols_diff_dict

    def _init_row_index(self, parent_trace):

        if self.id_column != None:
            if self.id_column not in self.df1.columns:
                raise ApodeixiError(parent_trace, "Can't initialize an iterator because '" + self.id_column + "' is not in the column of df1")
            if self.id_column not in self.df2.columns:
                raise ApodeixiError(parent_trace, "Can't initialize an iterator because '" + self.id_column + "' is not in the column of df2")
        
            ids1 = list(self.df1[self.id_column].unique())
            ids2 = list(self.df2[self.id_column].unique())
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

import numpy                        as _numpy

class DataFrameUtils():
    def __init__(self):
        return

    def numpy_2_float(self, x):
        '''
        Cleans problems with numbers in the trees being built. Turns out that if they are numpy classes then the
        YAML produced is unreadable and sometimes won't load. So move anything numpy to floats.
        '''
        if type(x)==_numpy.int32 or type(x)==_numpy.int64 or type(x)==_numpy.float32 or type(x)==_numpy.float64:
            return float(x)
        else:
            return x


    def compare_dataframes(self, df1, df2, df1_name, df2_name):
        '''
        Helper method used in lieu of dataframe.equals, which fails for spurious reasons.
        Under this method's policy, two dataframes are equal if they have the same columns, indices, and are
        point-wise equal.

        Method returns two things: a boolean result of the comparison, and a dictionary to pin point where there are
        differences, if any
        '''
        # Prepare an explanation of where the dataframes differ, if they do differ. This visibility helps with debugging
        comparison_dict                                 = {}
        cols_1                                          = set(df1.columns)
        cols_2                                          = set(df2.columns)

        # Ensure determinism with sort
        common_cols                                     = list(cols_1.intersection(cols_2))
        common_cols.sort() 
        missing_in_1                                    = list(cols_2.difference(cols_1))
        missing_in_1.sort()
        missing_in_2                                    = list(cols_1.difference(cols_2))
        missing_in_2.sort()

        comparison_dict[df1_name + ' shape']            = str(df1.shape)
        comparison_dict[df2_name + ' shape']            = str(df2.shape)
        if len(missing_in_1) > 0:
            comparison_dict[df1_name + ' missing columns']  = '\n'.join(missing_in_1)
        if len(missing_in_2) > 0:
            comparison_dict[df2_name + ' missing columns']  = '\n'.join(missing_in_2)

        # Initialize true until profen false
        check                                           = True

        if not df1.index.equals(df2.index): 
            check                                       = False
        else: # Compare element by element for the common_cols
            cell_dict                                   = {}
            for row in df1.iterrows():
                row1_nb                                 = row[0]
                row1_data                               = row[1]
                for col in common_cols: # use common_cols that is a deterministic list
                    val1                                = row1_data[col]
                    val2                                = df2.iloc[row1_nb][col]
                    if val1 != val2:
                        check                                           = False
                        coords                                          = col + '.row' + str(row1_nb)
                        cell_dict[coords]                               = "values differ"
                        cell_dict[coords + '.' + df1_name]              = str(val1)
                        cell_dict[coords + '.' + df1_name + " type"]    = str(type(val1))
                        cell_dict[coords + '.' + df2_name]              = str(val2)
                        cell_dict[coords + '.' + df2_name + " type"]    = str(type(val2))
            comparison_dict['elt-by-elt comparison']   = cell_dict

            if check:
                comparison_dict['Result of elt-by-elt comparison'] = "Everything matches"

        return check, comparison_dict
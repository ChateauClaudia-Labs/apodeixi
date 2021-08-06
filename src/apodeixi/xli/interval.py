import math                                     as _math
from nltk.tokenize                              import SExprTokenizer 
import pandas                                   as _pd

from apodeixi.util.a6i_error                    import ApodeixiError
from apodeixi.util.dataframe_utils              import DataFrameUtils
from apodeixi.util.formatting_utils             import ListUtils, StringUtils

class IntervalUtils():
    def __init__(self):
        return

    def infer_first_entity(self, parent_trace, linear_space):
        '''
        Helper method that returns the first "cleaned-up" entity, defined as the first column that is not a UID
        in the linear space, cleaned up by removal of potential comments within parenthesis
        '''
        entity_name                 = None
        for col in linear_space:
            if self.is_a_UID_column(parent_trace, col):
                continue
            else:
                entity_name         = self.without_comments_in_parenthesis(parent_trace, col)
                break
        return entity_name

    def is_a_UID_column(self, parent_trace, col):
        '''
        Helper method that returns true if the given column `col` is a UID column. Used to not treat as "entity content" any
        Excel columns with UIDs populated by controller logic during previously done postings from the user.
        '''
        return col.startswith(Interval.UID)

    def without_comments_in_parenthesis(self, parent_trace, txt):
        '''
        Returns a substring of `txt` ignoring any sub-text within `txt` that is in parenthesis. It also strips
        any leading or trailing spaces.
        
        For example, if txt is 'Effort (man days) to deliver', then this function return 'Effort to deliver'
        '''
        stripped_txt = StringUtils().strip(txt)
        # Remove text within parenthesis, if any, using the natural language tool nltk.tokenize.SExprTokenizer
        sexpr                       = SExprTokenizer(strict=False)
        sexpr_tokens                = sexpr.tokenize(stripped_txt)
        parenthesis_free_tokens     = [t for t in sexpr_tokens if not ')' in t and not '(' in t]
        parentheis_free_txt         = ' '.join(parenthesis_free_tokens)
        return parentheis_free_txt



    def is_blank(self, txt):
        '''
        Returns True if 'txt' is NaN or just spaces
        '''
        CLEAN           = DataFrameUtils().clean  # Avoid problems with nan, numpy classes, dates, NaTs, etc.
        y               = CLEAN(txt)
        if type(y)==str:
            return StringUtils().is_blank(y)
        else:
            return False

class IntervalSpec():
    '''
    Abstract helper class used to construct Interval objects. This is needed because sometimes all columns in an Interval
    are not known at configuration time, and are only known at runtime.
    
    For example, perhaps at configuration time we know where an interval starts, but not where it ends, since the
    end user might add columns to an Excel spreadsheet that quality as part of the interval. Thus, only at runtime
    in the context of a particular set of Excel columns (a "linear space") can it be determined which are the columns
    that qualify as belonging to an interval.

    Example: Say an interval spec is: "All columns from A to F, not inclusive". Then if the linear space is
    [Q, R, A, T, Y, U, F, G, W], the application of the spec to the linear space yields the Interval [A, T, Y, U]

    Concrete classes implement different "spec" algorithms, so this particular class is just an abstract class.
    '''
    def __init__(self, entity_name = None):
        self.entity_name            = entity_name

    def buildIntervals(self, parent_trace, linear_space):
        '''
        Implemented by concrete derived classes.
        Must return a list of Interval objects, constructed by applying the concrete class's semantics
        to the specificity of the linear_space given.

        Example: Say an interval spec is: 
        
        "One interval is the list of all columns up to A (non inclusive, then columns from A to F, not inclusive, and the remaining
        columns form the last interval". 
        
        Then if the linear space is
        [Q, R, A, T, Y, U, F, G, W], the application of the spec to the linear space yields these 3 Intervals:
        
        * [Q, R]
        * [A, T, Y, U]
        * [F, G, W]
        '''
        raise NotImplementedError("Class " + str(self.__class__) + " forgot to implement method buildInterval") 

class GreedyIntervalSpec(IntervalSpec):
    '''
    Concrete interval spec class which builds a list consisting of a 
    single interval taking all the columns found in Excel (i.e., all the 'linear space')

    Example: Say the linear space is [Q, R, A, T, Y, U, F, G, W].
    
    Then this class returns the list containing just one interval: [Q, R, A, T, Y, U, F, G, W]
    '''
    def __init__(self, parent_trace, entity_name = None, mandatory_columns = []):
        super().__init__(entity_name)
        self.mandatory_columns          = mandatory_columns

    def buildIntervals(self, parent_trace, linear_space):
        '''
        '''
        if self.entity_name == None:
            self.entity_name            = IntervalUtils().infer_first_entity(parent_trace, linear_space)

        my_trace                        = parent_trace.doing("Validating mandatory columns are present")

        missing_cols                    = [col for col in self.mandatory_columns if not col in linear_space]
        if len(missing_cols) > 0:
            raise ApodeixiError(my_trace, "Posting lacks some mandatory columns",
                                                data = {    'Missing columns':    missing_cols,
                                                            'Posted columns':     linear_space})

        return [Interval(parent_trace, linear_space, self.entity_name)]

class MinimalistIntervalSpec(IntervalSpec):
    '''
    Concrete interval spec class which builds minimalist intervals, where each interval has exactly 1 non-UID column 
    from the linear space.

    For example, if the linear space is 
    
    ['UID', 'Big Rock', 'UID.1', 'Breakdown 1', 'UID.2', 'Breakdown 2'], then calling the

    `buildIntervals` method will produce these intervals: 
    
    * ['UID', 'Big Rock']
    * ['UID.1', 'Breakdown 1']
    * ['UID.2', 'Breakdown 2']
    '''
    def __init__(self, parent_trace, entity_name = None, mandatory_columns = []):

        super().__init__(entity_name)
        self.mandatory_columns          = mandatory_columns

    def buildIntervals(self, parent_trace, linear_space):
        '''
        '''
        if self.entity_name == None:
            self.entity_name                = IntervalUtils().infer_first_entity(parent_trace, linear_space)

        my_trace                        = parent_trace.doing("Validating mandatory columns are present")

        missing_cols                    = [col for col in self.mandatory_columns if not col in linear_space]
        if len(missing_cols) > 0:
            raise ApodeixiError(my_trace, "Posting lacks some mandatory columns",
                                                data = {    'Missing columns':    missing_cols,
                                                            'Posted columns':     linear_space})

        interval_columns                = []
        interval_entity                 = None
        intervals_list                  = []

        #for col in linear_space[start_idx:]:
        current_interval_cols           = []
        for idx in range(len(linear_space)):
            loop_trace                  = parent_trace.doing("Looping through linear space to build intervals",
                                                                data = {    'linear_space':             str(linear_space),
                                                                            'idx in loop':              str(idx),
                                                                            'current_interval_cols':    str(current_interval_cols)})
            col                         = linear_space[idx]
            if IntervalUtils().is_a_UID_column(loop_trace, col): # append all UIDs until you hit a non-UID, and stop there
                current_interval_cols.append(col)
                continue
            else: # This is the end of the interval
                current_interval_cols.append(col)
                interval_entity         = col
                intervals_list.append(Interval(loop_trace, current_interval_cols, interval_entity))

                # Reset for next interval to process
                current_interval_cols   = []
                continue

        return intervals_list

class ClosedOpenIntervalSpec(IntervalSpec):
    '''
    Concrete interval spec class which builds a list of interval based on knowing the intervals' endpoints, where each endpoint
    is the start of an interval (and not the end of the previous interval).

    Example: Say an interval spec is: 
    
    "Split the linear space at [A, F]" 
    
    Then if the linear space is
    [Q, R, A, T, Y, U, F, G, W], the application of the spec to the linear space yields these 3 Intervals:
    
    * [Q, R]
    * [A, T, Y, U]
    * [F, G, W]

    @param splitting_columns The columns inside the interval that partition it. In the above example,
                            that would be [A, F]
    '''
    def __init__(self, parent_trace, splitting_columns, entity_name):
        super().__init__(entity_name)

        self.splitting_columns      = splitting_columns

    def buildIntervals(self, parent_trace, linear_space):
        '''
        '''
        if self.entity_name == None:
            self.entity_name                    = IntervalUtils().infer_first_entity(parent_trace, linear_space)

        my_trace                                = parent_trace.doing("Checking splitting columns all belong to linear_spac_")
        if True:
            missing                             = [col for col in self.splitting_columns if not col in linear_space]
            if len(missing) > 0:
                raise ApodeixiError(my_trace, "Can't build intervals because some splitting columns are not in linear space. "
                                               + "\n\t=> This sometimes happens if the ranges in the Posting Label don't cover all "
                                               + "the data.",
                                                data = {    'linear_space':             str(linear_space),
                                                            'splitting_columns':        str(self.splitting_columns),
                                                            'missing in linear space':  str(missing)    })

        my_trace                                = parent_trace.doing("Splitting linear space",
                                                data = {    'linear_space':             str(linear_space),
                                                            'splitting_columns':        str(self.splitting_columns)})
        if True:
            intervals_list                      = []
            remaining_cols                      = linear_space 
            

            # We add a synthetic extra point at the end for loop to work, since if there are N splitting columns we
            # will end up with N+1 intervals, so we need to loop through N+1 cycles, not N
            # That makes the loop below work (otherwise the last interval is not produced, which is a bug)
            class _PointAtInfinity():
                '''
                Helper class to represent an additional object "after" all the others.
                '''
                def __str__(self):
                    return "PointAtInfinity"
            
            # Add POINT_AT_INFINITY for loop to work
            #  for loop to work, since if there are N splitting columns we
            # will end up with N+1 intervals, so we need to loop through N+1 cycles, not N
            # That makes the loop below work (otherwise the last interval is not produced, which is a bug)
            interval_endpoints                  = self.splitting_columns.copy()                    
            interval_endpoints.                 append(Interval.POINT_AT_INFINITY) 

            for col in interval_endpoints:
                loop_trace                      = my_trace.doing("Cycle in loop for one of the splitting_columns",
                                                                    data    = {'col': str(col)})

                if col != Interval.POINT_AT_INFINITY: # We split by 'col' if it is not the POINT_AT_INFINITY
                    #
                    # GOTCHA: if the submitted form has UIDs, then there probably is a UID column to the left
                    # of `col`. If so, include such UID if it exists, else it will erroneously be considered part
                    # of the entity to the left of `col`, which might then error out thinking it has two UID
                    # columns, which is not legal.
                    #
                    col_idx                      = linear_space.index(col)
                    if col_idx > 0 and IntervalUtils().is_a_UID_column(loop_trace, linear_space[col_idx - 1]):
                        split_by                 = [linear_space[col_idx-1]]
                    else:
                        split_by                 = [col]

                            
                    check, pre_cols, post_cols = ListUtils().is_sublist(    parent_trace        = loop_trace, 
                                                                            super_list          = remaining_cols, 
                                                                            alleged_sub_list    = split_by)
                    if not check:
                        raise ApodeixiError(loop_trace, "Strange internal error: couldn't split columns by column",
                                                        data = {    'columns_to_split':     remaining_cols,
                                                                    'splitting_column':     col})
                else: # This is the last interval, splitting by the POINT_AT_INFINITY 
                    pre_cols                        = remaining_cols
                    post_cols                       = []

                interval_entity                 = IntervalUtils().infer_first_entity(loop_trace, remaining_cols)

                intervals_list.append(Interval( parent_trace        = loop_trace,
                                                columns             = pre_cols, 
                                                entity_name         = interval_entity))
                # Initialize data for next cycle in loop
                remaining_cols                  = split_by
                remaining_cols.extend(post_cols)

        return intervals_list

class Interval():
    '''
    Helper class used as part of the configuration for parsing a table in an Excel spreadsheet. It represents
    a list of string-valued column names in Excel, ordered from left to right, all for a given entity.
    Additionally, it indicates which of those column names is the name of the entity (as opposed to a property of)
    the entity. 
    '''
    def __init__(self, parent_trace, columns, entity_name = None):
        if type(columns) != list or len(columns) == 0:
            raise ApodeixiError(parent_trace, "Unable to instantiate an Interval from a null or empty list")
        self.columns                = columns
        if entity_name == None:
            self.entity_name        = IntervalUtils().without_comments_in_parenthesis(  parent_trace    = parent_trace,
                                                                                        txt             = columns[0])
        else:
            self.entity_name        = entity_name

    UID                    = 'UID'  # Field name for anything that is a UID

    # Sometimes we need a synthetic extra point at the end of an interval.
    class _PointAtInfinity():
        '''
        Helper class to represent an additional object "after" all the others.
        '''
        def __str__(self):
            return "PointAtInfinity"
    POINT_AT_INFINITY       = _PointAtInfinity()

    def is_subset(self, columns):
        '''
        UID-aware method to test if this Interval is a subset of the given columns. By "UID-aware" we mean
        that the method ignores any UID column when determining subset condition.
        For example, ['UID', 'Car', 'Make'] would be considered a subset of ['Car', 'Make', 'Driver']

        For internal reasons, it also has POINT_AT_INFINITY awareness
        '''
        me                          = set(self.columns).difference(set([Interval.UID])).difference(set([Interval.POINT_AT_INFINITY]))
        them                        = set(columns)
        return me.issubset(them)

    def non_entity_cols(self):
        '''
        Returns a list of strings, corresponding to the Interval's columns that are not the entity type
        '''
        #GOTCHA: Don't compare column names to the entity name directly, since there might be spurious
        #       differences due to lower/upper case. Instead, format as a yaml field to have a standard
        #       policy on case, space, hyphens, etc. prior to comparison
        FMT         = StringUtils().format_as_yaml_fieldname
        result      = [col for col in self.columns if FMT(col) != FMT(self.entity_name)]
        return result

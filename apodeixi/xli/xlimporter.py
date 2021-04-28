# Use underscore prefixes for all objects that should not be exposed as part of this module's APIs.
# Python's default behavior will then be not not expose them, because of the underscore
# Alternatively, use the __all__ property in __init__.py to explicitly declare what to expose


import pandas      as _pd
import yaml        as _yaml
import re          as _re
import sys         as _sys
import os          as _os
import math        as _math
import datetime    as _datetime


_PRODUCT              = 'product'
_JOURNEY              = 'journey'
_PLAN_TYPE            = 'planType'
_SCENARIO             = 'scenario'
_ENVIRONMENT          = 'environment'
_SCORING_CYCLE        = 'scoringCycle'
_SCORING_MATURITY     = 'scoringMaturity'
_ESTIMATED_BY         = 'estimatedBy'
_ESTIMATED_ON         = 'estimatedOn'
_RECORDED_BY          = 'recordedBy'

_CONTEXT_FIELDS = [_PRODUCT, _JOURNEY, _PLAN_TYPE, _SCENARIO, _ENVIRONMENT,
                  _SCORING_CYCLE, _SCORING_MATURITY, 
                  _ESTIMATED_BY, _ESTIMATED_ON, _RECORDED_BY]


class SchemaUtils:

    
    def __remove_blanks(column):
        '''
        Utility that returns a filter (i.e., a boolean-valued function that acts on DataFrame rows).
        The filter will 'eliminate' (i.e., return false) for any row for which row[column] is a 'blank',
        i.e., NaN or a string that is empty or just whitespace.
        '''
        def _filter(row):
            val = row[column]
            if type(val) == str and len(val.strip())==0:
                return False
            if type(val) == float and _math.isnan(val):
                return False

            return True
        return _filter
    
    def drop_blanks(df, column):
        return df[df.apply(SchemaUtils.__remove_blanks(column), axis=1)]

    def to_yaml_date(original_date, BAD_SCHEMA_MSG):
        '''
        Converts the input into another form of date that is suitable to be placed in a YAML document.
        
        For the date, need to convert to a YAML date string 'YYYY-MM-DD', which in turn requires checking
        that value can be formatted into a date (with method 'strftime') to subsequently parse it
        as a datetime object, which from trial and error I found was the date representation that the
        Python yaml module would correctly interpret as a date when creating the YAML document.
        '''
        M                  = SchemaUtils.ValidationMonad(BAD_SCHEMA_MSG)
        converted_date     = M.validate(original_date).has_ducktype_method('Date', 'strftime')    
        converted_date     = converted_date.strftime('%Y-%m-%d') # As required by YAML: ISO-8601 simple date format
        converted_date     = _datetime.datetime.strptime(converted_date, '%Y-%m-%d') # Now parse into a datetime
        return converted_date
    
    class ValidationMonad:
        '''
        Monad used to hold context for potentially multiple validations against multiple values.
        When asked to validate a specific value, it returns a more specific Monad that wraps the
        value in question along with the more general context in this Monad.
        '''
        def __init__(self, callerMsg):
            self.callerMsg   = callerMsg

        def validate(self, val):
            return SchemaUtils._ValToValidateMonad(val, self.callerMsg)
        
    class _ValToValidateMonad:
        '''
        This is a 'passthrough' Monad: calling its methods just returns the value wrapped in the Monad,
        unless the value violates the check made by the method in question, in which case it
        raises an exception. The message is a combination of the more contextual message from
        the caller (wrapped in the Monad) and the specific validation violation as per the validation
        method called
        '''
        def __init__(self, val, callerMsg):
            self.val         = val
            self.callerMsg   = callerMsg

        def is_of_type(self, allowed_types):
            '''
            If type(self.val) is one of the 'allowed_types', returns self.val. Else it raises an exception. 
            @param allowed_types: list of types for the possible types that self.val may be. Example: [float, int]
            '''
            for t in allowed_types:
                if type(self.val) == t:
                    return self.val
            
            # If we get this far, we didn't match any allowed type so error out with a nice informative message
            formatted_types_txt = ",".join(["'" + t.__name__ + "'" for t in allowed_types])
            if len(allowed_types)>1:
                formatted_types_txt = "one of " + formatted_types_txt
            else:
                formatted_types_txt = "a " + formatted_types_txt

            msg = "For value '" + str(self.val) + "', expected " + formatted_types_txt  \
                    + " but instead received a '" + type(self.val).__name__ + "'."
            raise ValueError(self.callerMsg + '\n' + msg)
        
        def has_ducktype_method(self, friendly_duck_type_name, method_name):
            if method_name not in dir(self.val):
                val_txt = str(self.val)
                if val_txt == 'nan': # This probably came from Pandas, not from the user who probably 
                                     # left field blank. So for error message, revert to user friendly text
                    val_txt = ''
                msg = "Value '" + val_txt + "', is not a valid " + friendly_duck_type_name  + "."
                raise ValueError(self.callerMsg + '\n' + msg)
                
            return self.val        

class ExcelTableReader:
    '''
    Reads a table of data from an Excel spreadsheet and creates a Pandas DataFrame from it.
    The table is required to have a single row of column headers at the top of the table.
    @param url A path to an Excel spreadsheet with the name of the sheet appended after a colon.
               Example: 'C:/myDocuments/mySpreadsheets/wonderful.xlsx:Sheet1'
    @param excel_range A string representing a range in Excel. The first row must be the column headers.
                       Example: "A3:D10"
    @param horizontally A boolean to determine whether the data to be read is arranged in rows (horizontally=True)
                        or columns (horizontally=False). It is True by default
    @return A Pandas DataFrame built from the data provided.
    '''
    def __init__(self, url, excel_range, horizontally=True):
        self.url          = url
        self.excel_range  = excel_range.upper()
        self.horizontally = horizontally
        
    def read(self, horizontally=True):
        path, sheet                                    = self.__parse_url()
        
        first_column, last_column, first_row, last_row = self.__parse_range()
        
        if first_row < 1:
            raise ValueError ("Incorrectly formatted Excel range was given: '" + self.excel_range 
                              + "'. Row numbers must be 1 or higher")
            
        if first_row >= last_row:
            raise ValueError ("Incorrectly formatted Excel range was given: '" + self.excel_range 
                              + "'. It spans 0 rows")
        
        # Not that Excel columns start at 1, but Pandas counts rows from 0, so need to offset the
        # header by 1
        if self.horizontally==True:
            header = first_row - 1
            nrows  = last_row - first_row
        else:
            if first_row > 1:
                header = first_row -2
            else:
                header = None 
            nrows  = last_row - first_row +1 # First row is data, not header, so nrows is 1 bigger
        df                                             = _pd.read_excel(io         = path, 
                                                                       sheet_name = sheet,
                                                                       header     = header, 
                                                                       usecols    = first_column + ':' + last_column, 
                                                                       nrows      = nrows)
        
        if len(df.columns)==0:
            raise ValueError ("Incorrectly formatted Excel range was given: '" + self.excel_range 
                              + "'. It spans no columns with data")
        if len(df.index)==0:
            raise ValueError ("Incorrectly formatted Excel range was given: '" + self.excel_range 
                              + "'. It spans no rows with data")
            
        if self.horizontally==False:
            df = self.__rotate(df)
        
        return df
    
    def __parse_url(self):
        '''
        Given a url of form "<some string A, maybe with colons>:<some string B without colons>"
        it returns the two substrings separated by the last colon
        '''
        s = _re.split(':', self.url)
        if len(s) < 2:
            raise ValueError ("Incorrectly formatted url was given: '" + self.url
                             +"'. Should instead be formmated like this example: "
                             + "'C:/MyDocuments/MySpreadsheets/Wonderful.xlsx:SheetName'")
        sheet = s[len(s)-1]
        path = self.url.split(':' + sheet)[0]
        if len(path) == 0 or len(sheet) ==0:
            raise ValueError ("Incorrectly formatted url was given: \n\t'" + self.url
                             + "'\nShould instead be formmated like this example, with a non-empty path and a non-empty"
                             + " sheet name separated by the last colon in the url: \n"
                             + "\t'C:/My Documents/My Spreadsheets/Wonderful.xlsx:SheetName'")
        return path, sheet
    
    def __parse_range(self):
        '''
        Parses strings for Excel ranges like 'C5:DA15' and returns the columns and rows: 'C', 'DA', 5, 15.
        If the given range is not correctly formatted then throws an exception
        '''
        REGEX = '^([a-zA-Z]+)([1-9][0-9]*):([a-zA-Z]+)([1-9][0-9]*)$'
        res = _re.match(REGEX, self.excel_range)
        if (res == None or len(res.groups()) != 4):
            raise ValueError ("Incorrectly formatted Excel range was given: '" + self.excel_range 
                              + "'. Should instead be formatted like this example: 'C5:DA15'")
            
            
        # Allow for possibility that range is expressed non-monotically. E.g 'B10:D4' instead of 'B4:D10' 
        # So 'correct' user-provided non-monotonic ranges by sorting.
        # Also, to avoid Excel errors, capitalize columns
        # CATCHA: must capitalize before sorting, not the other way around, since a > C so would
        # get wrong result (no columns read). Capitalizing first gives A < C and then you get columns.
        first_column = min(res.group(1).upper(), res.group(3).upper())
        last_column  = max(res.group(1).upper(), res.group(3).upper())
        first_row    = min(int(res.group(2)), int(res.group(4)))
        last_row     = max(int(res.group(2)), int(res.group(4)))
                           
        return first_column, last_column, first_row, last_row
        #return res.group(1), res.group(3), int(res.group(2)), int(res.group(4))
    
    def __rotate(self, df):
        '''
        Used when self.horizontally is false, and we read from Excel that needs to be transposed.
        In that case, the first column of the parameter 'df' is considered to be the columns of the
        rotated dataframe to be computed
        '''
        #df2 = df.dropna()
        keys_p = list(df.columns)[0] # "pointer" to the list of keys, i.e., Excel header for column of keys
        #df2 = df[df.apply(remove_blanks(header_for_list_of_keys), 
        #                  axis=1)] # Drops keys that are NaN, blanks, etc.
        df2 = SchemaUtils.drop_blanks(df, keys_p)
        df2 = df2.set_index(keys_p)
        df2.index.name = None
        df2 = df2.transpose()
        df2 = df2.reset_index()
        df2 = df2.drop(columns=['index'])
        
        return df2       

def readContext(url, excel_range):
    excel_range    = excel_range.upper()
    reader         = ExcelTableReader(url, excel_range, horizontally=False)
    context_df     = reader.read()
    
    # Check context has the right number of rows (which are columns in Excel, since we transposed)
    if len(context_df.index) != 1:
        raise ValueError("Bad Excel range provided: " + excel_range
                        + "\nShould contain exactly two columns: keys and values")
    
    missing_cols = set(_CONTEXT_FIELDS).difference(set(context_df.columns))
    if len(missing_cols) > 0:
        missing_txt = ", ".join(["'" + col + "'" for col in missing_cols])
        raise ValueError("Range '" + excel_range + "' lacks these mandatory context fields: "
                        + missing_txt)
        
    BAD_SCHEMA_MSG      = "Incorrect schema for field '" + _ESTIMATED_ON + "' when processing the context in range '" \
                            + excel_range + "'."
    M                   = SchemaUtils.ValidationMonad(BAD_SCHEMA_MSG)
        
    ctx = {}
    for field in _CONTEXT_FIELDS:
        ctx[field] = context_df.iloc[0][field]
        
    # Validations for some fields
    ctx[_ESTIMATED_ON]  = SchemaUtils.to_yaml_date(ctx[_ESTIMATED_ON], BAD_SCHEMA_MSG)
    
    return ctx 

def applyMarathonJourneyPlan(ctx, url, excel_range, repo_root_dir):
    product             = ctx[_PRODUCT]
    scoring_cycle       = ctx[_SCORING_CYCLE]
    plan_maturity       = ctx[_SCORING_MATURITY]
    environment         = ctx[_ENVIRONMENT]
    planning_scenario   = ctx[_SCENARIO]
    estimating_mgr      = ctx[_ESTIMATED_BY]
    user                = ctx[_RECORDED_BY]
    plan_type           = ctx[_PLAN_TYPE]
    journey             = ctx[_JOURNEY]
    
    BAD_SCHEMA_MSG      = "Bad estimation date provided in context"
    estimation_date     = SchemaUtils.to_yaml_date(ctx[_ESTIMATED_ON], BAD_SCHEMA_MSG)
    
    reader              = ExcelTableReader(url, excel_range)
    
    plan_df             = reader.read()
    if len(plan_df.columns) != 2:
        raise ValueError ("Badly formatted Marathon Plan: should have exactly two columns, ideally called: 'Workstream' and "
                         + "'Effort'. Error when processing range= '" + excel_range + "' and url=\n\t" + url)
    plan_df.columns     = ['Workstream', 'Effort']
    
    # Drop workstreams that were not defined
    plan_df             = SchemaUtils.drop_blanks(plan_df, 'Workstream')
   
    
    manifest_dict       = {}
    workstreams         = []
    WORKSTREAM_ID       = 1
    
    BAD_SCHEMA_MSG      = "Incorrect schema for a Marathon Plan in range '" + excel_range + "'."
    M                   = SchemaUtils.ValidationMonad(BAD_SCHEMA_MSG)
    
    for row in plan_df.iterrows():
        workstream      = row[1]['Workstream']
        effort          = row[1]['Effort']
        effort          = M.validate(effort).is_of_type([float, int])
        
        workstreams.append({'workstream'   : workstream, 
                            'effort'       : effort, 
                            'workstream-id': 'ws-' + str(WORKSTREAM_ID)})
        WORKSTREAM_ID += 1

    # Namespae would typically be something like 'Development' or 'Production'
    metadata      = {'namespace': environment + '.' + scoring_cycle, 
                     'name': product + '.' + journey + '.' + planning_scenario,
                     'labels': {'product': product, 'scoringCycle': scoring_cycle, 'scenario': planning_scenario,
                                                  'journey': journey}}

    manifest_dict['apiVersion']     = 'journeys.inbound.a6i.io/v1dev'
    manifest_dict['kind']           = 'JourneyPlan'
    manifest_dict['metadata']       = metadata
    # Plan maturity can be one of: 'Not done', 'Drafted', 'Checked', 'Published'
    manifest_dict['planMaturity']   = plan_maturity
    manifest_dict['plan']           = {'type': plan_type, 
                                       'estimated_by': estimating_mgr, 
                                        'estimated_on': estimation_date,
                                        'recorded_by': user,
                                       'workstreams': workstreams}    
    
    _yaml.dump(manifest_dict, _sys.stdout)
    
    with open(repo_root_dir + '/' + product + '-marathon-plan.yaml', 'w') as file:
        _yaml.dump(manifest_dict, file)


def applyInvestmentCommittment(ctx, url, excel_range, repo_root_dir):
    
    product             = ctx[_PRODUCT]
    scoring_cycle       = ctx[_SCORING_CYCLE]
    plan_maturity       = ctx[_SCORING_MATURITY]
    environment         = ctx[_ENVIRONMENT]
    planning_scenario   = ctx[_SCENARIO]
    committing_mgr      = ctx[_ESTIMATED_BY]
    user                = ctx[_RECORDED_BY]
    plan_type           = ctx[_PLAN_TYPE]
    journey             = ctx[_JOURNEY]
    
    BAD_SCHEMA_MSG      = "Bad estimation date provided in context"
    committing_date     = SchemaUtils.to_yaml_date(ctx[_ESTIMATED_ON], BAD_SCHEMA_MSG)
    
    # Load data and validate its geometric shape
    reader        = ExcelTableReader(url, excel_range)
    
    plan_df       = reader.read()
    if len(plan_df.columns) != 2:
        raise ValueError ("Badly formatted Investment Plan: should have exactly two columns, "\
                          + "ideally called: 'Period' and Investment'. "\
                          + "Error when processing range= '" + excel_range + "' and url=\n\t" + url)
    plan_df.columns = ['Period', 'Investment']
    
    # Drop workstreams that were not defined
    plan_df             = SchemaUtils.drop_blanks(plan_df, 'Period')
    
    manifest_dict = {}
    investment_ts   = []
    BAD_SCHEMA_MSG      = "Incorrect schema for a Investment Plan in range '" + excel_range + "'."
    M                   = SchemaUtils.ValidationMonad(BAD_SCHEMA_MSG)
    
    for row in plan_df.iterrows():
        period          = row[1]['Period']
        investment      = row[1]['Investment']
        investment      = M.validate(investment).is_of_type([float, int])
        investment_ts.append({'period'      : period, 
                              'investment'  : investment,
                              'units'       : 'person-days'})

    # Namespace would typically be something like 'Development' or 'Production'
    metadata      = {'namespace': environment + '.' + scoring_cycle, 
                     'name'     : product + '.' + journey + '.' + planning_scenario,
                     'labels'   : {'product': product, 
                                   'scoringCycle': scoring_cycle, 
                                   'scenario': planning_scenario,
                                   'journey': journey}}

    manifest_dict['apiVersion']     = 'journeys.inbound.a6i.io/v1dev'
    manifest_dict['kind']           = 'JourneyInvestment'
    manifest_dict['metadata']       = metadata
    # Plan maturity can be one of: 'Not done', 'Drafted', 'Checked', 'Published'
    manifest_dict['planMaturity']   = plan_maturity
    manifest_dict['committment']           = {'committed_by': committing_mgr, 
                                              'committed_on': committing_date,
                                              'recorded_by': user,
                                              'investment': investment_ts}    
    
    _yaml.dump(manifest_dict, _sys.stdout)
    
    with open(repo_root_dir + '/' + product + '-investment-committment.yaml', 'w') as file:
        _yaml.dump(manifest_dict, file)


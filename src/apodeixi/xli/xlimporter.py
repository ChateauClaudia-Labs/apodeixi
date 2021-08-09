import pandas      as _pd
import yaml        as _yaml
import re          as _re
import sys         as _sys
import os          as _os
import math        as _math
import datetime    as _datetime

from apodeixi.util.a6i_error    import *

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

class XLReadConfig():
    '''
    Abstract class.

    Concrete classes know how the layout on an Excel spreadsheet should be interpreted to create a DataFrame
    representation of a manifest. It handles issues like:

    * Knowing whether to read Excel rows as DataFrame rows or as columns
    * Whether the Excel columns (or rows) reprsent properties for an entity in the manifest, or something else
      (such as a mapping between two manifests)
    '''
    def __init__(self):
        return

    def pandasRowParameters(self, parent_trace, first_row, last_row):
        '''
        Returns two ints: header and number_of_rows, which are the row parameters Pandas
        needs to load a portion of Excel real estate.

        @first_row An int, representing the first Excel row (numbering starts at 1
                            of real estate that is to be loaded
        @last_row An int, representing the first Excel row (numbering starts at 1)
                            of real estate that is to be loaded
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'pandasRowParameters' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})   

    def toManifestDF(self, parent_trace, raw_df, first_row, last_row):
        '''
        Abstract method 

        Based on a raw DataFrame as loaded by Pandas from Excel, it computes and returns a potentially different
        DataFrame which represents the manifest whose content was diplayed in Excel.

        The reason both might be different is that the visualization in Excel may introduce additional
        elements, such as:

        * Perhaps manifest is rotated, so rows in Excel correspond to manifest DataFrame columns, not rows
        * Perhaps some rows (or columns) in Excel are not entity properties of the manifest, but are visual
          expressions of a mapping/join between two manifests

        @param raw_df A DataFrame for a dataset loaded by Pandas from Excel
        @param first_row An int, corresponding to the row number in Excel where the dataset starts
        @param last_row An int, corresponding to the last row number in Excel where the dataset appears
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'toManifestDF' in concrete class",
                                        origination = {'concrete class': str(self.__class__.__name__), 
                                                        'signaled_from': __file__}) 

class PostingLabelXLReadConfig(XLReadConfig):
    '''
    Configuration on how to read the Excel content corresponding to a PostingLabel.
    '''
    def __init__(self):
        super().__init__()
        return

    def pandasRowParameters(self, parent_trace, first_row, last_row):
        '''
        Returns two ints: header and number_of_rows, which are the row parameters Pandas
        needs to load a portion of Excel real estate.

        @first_row An int, representing the first Excel row (numbering starts at 1
                            of real estate that is to be loaded
        @last_row An int, representing the first Excel row (numbering starts at 1)
                            of real estate that is to be loaded
        '''
        if first_row > 1:
            header = first_row -2 
        else:
            header = None 
        nrows  = last_row - first_row +1 # First row must be included, so nrows is 1 bigger

        return header, nrows

    def toManifestDF(self, parent_trace, raw_df, first_row, last_row):
        '''
        Based on a raw DataFrame as loaded by Pandas from Excel, it computes and returns a potentially different
        DataFrame which represents the manifest whose content was diplayed in Excel.

        The reason both might be different is that the visualization in Excel may introduce additional
        elements, such as:

        * Perhaps manifest is rotated, so rows in Excel correspond to manifest DataFrame columns, not rows
        * Perhaps some rows (or columns) in Excel are not entity properties of the manifest, but are visual
          expressions of a mapping/join between two manifests

        @param raw_df A DataFrame for a dataset loaded by Pandas from Excel
        @param first_row An int, corresponding to the row number in Excel where the dataset starts
        @param last_row An int, corresponding to the last row number in Excel where the dataset appears
        '''
        #In the case of a PostingLabel, we must rotate the raw_df and eliminate any Excel rows where
        # the first column is blank (since the first column are the PostingLabel field names, and a blank
        # field name is not allowed)
        keys_p          = list(raw_df.columns)[0] # "pointer" to the list of keys, i.e., Excel header for column of keys
        df2             = SchemaUtils.drop_blanks(raw_df, keys_p)
        df2             = df2.set_index(keys_p)
        df2.index.name = None
        df2             = df2.transpose()
        df2             = df2.reset_index()
        df2             = df2.drop(columns=['index'])

        manifest_df     = df2
        
        return manifest_df 

class ManifestXLReadConfig(XLReadConfig):
    '''
    Abstract class
    Configuration on how to read the Excel content corresponding to a manifest.
    '''
    def __init__(self):
        super().__init__()
        self.horizontally           = True # Default. Derived classes my overwrite
        self.is_a_mapping           = False # Default. Derived classes my overwrite
         
        # If this is mapping, must be set to the `kind` of the manifest we are mapped from
        self.kind_mapped_from       = None

        # If this is a mapping, must be set in calling path before self.toManifestDF is called
        self.posting_label          = None

        return

    def pandasRowParameters(self, parent_trace, first_row, last_row):
        '''
        Returns two ints: header and number_of_rows, which are the row parameters Pandas
        needs to load a portion of Excel real estate.

        @first_row An int, representing the first Excel row (numbering starts at 1
                            of real estate that is to be loaded
        @last_row An int, representing the first Excel row (numbering starts at 1)
                            of real estate that is to be loaded
        '''
        if self.horizontally==True:
            header = first_row - 1
            nrows  = last_row - first_row
        elif self.is_a_mapping == False:
            if first_row > 1:
                header = first_row -2 
            else:
                header = None 
            nrows  = last_row - first_row +1 # First row must be included, so nrows is 1 bigger
        else: # We are processing a mapping
            header = first_row - 1
            nrows  = last_row - first_row

        return header, nrows

    def toManifestDF(self, parent_trace, raw_df, first_row, last_row):
        '''
        Based on a raw DataFrame as loaded by Pandas from Excel, it computes and returns a potentially different
        DataFrame which represents the manifest whose content was diplayed in Excel.

        The reason both might be different is that the visualization in Excel may introduce additional
        elements, such as:

        * Perhaps manifest is rotated, so rows in Excel correspond to manifest DataFrame columns, not rows
        * Perhaps some rows (or columns) in Excel are not entity properties of the manifest, but are visual
          expressions of a mapping/join between two manifests

        @param raw_df A DataFrame for a dataset loaded by Pandas from Excel
        @param first_row An int, corresponding to the row number in Excel where the dataset starts
        @param last_row An int, corresponding to the last row number in Excel where the dataset appears
        '''
        if self.horizontally == True:
            manifest_df     = raw_df

        elif self.is_a_mapping == False:
            #In thise case we must rotate the raw_df and eliminate any Excel rows where
            # the first column is blank (since those will become the columns of the manifest DataFrame, and
            # shouldn't be blank)
            keys_p          = list(raw_df.columns)[0] # "pointer" to the list of keys, i.e., Excel header for column of keys
            df2             = SchemaUtils.drop_blanks(raw_df, keys_p)
            df2             = df2.set_index(keys_p)
            df2.index.name = None
            df2             = df2.transpose()
            df2             = df2.reset_index()
            df2             = df2.drop(columns=['index'])

            manifest_df     = df2
        
        else: # We must process a mapping
            if self.posting_label == None:
                raise ApodeixiError(parent_trace, "Can't read mapping manifest information because the posting label "
                                                    + "was not set in the PostingConfig ahead of time")
            if self.kind_mapped_from == None:
                raise ApodeixiError(parent_trace, "Can't read mapping manifest information because the `kind` "
                                                    + "of the manifest we map from was not set in the PostingConfig "
                                                    + "ahead of time")
            manifest_df     = self.controller.linkMappedManifest(   parent_trace, 
                                                                    refKind         = self.kind_mapped_from, 
                                                                    my_entity       = self.entity_name(),
                                                                    raw_df          = raw_df, 
                                                                    first_row       = first_row, 
                                                                    last_row        = last_row)
        
        return manifest_df 

class ExcelTableReader:
    '''
    Reads a table of data from an Excel spreadsheet and creates a Pandas DataFrame from it.
    The table is required to have a single row of column headers at the top of the table.
    @param excel_fullpath A path to an Excel spreadsheet.
               Example: 'C:/myDocuments/mySpreadsheets/wonderful.xlsx'
    @param excel_sheet Name of the worksheet in the Excel spreadsheet where we should retrieve content from.
    @param excel_range A string representing a range in Excel. The first row must be the column headers.
                       Example: "A3:D10"
    @return A Pandas DataFrame built from the data provided.
    '''
    def __init__(self, parent_trace, excel_fullpath, excel_sheet, excel_range, xlr_config):
        self.excel_fullpath     = excel_fullpath
        self.excel_sheet        = excel_sheet
        self.excel_range        = excel_range.upper()
        self.xlr_config         = xlr_config
        
    def read(self, parent_trace):
        '''
        Loads the Apodeixi object in Excel that this ExcelTableReader was initialized for, and returns it
        as a Pandas DataFrame 
        '''
        my_trace                = parent_trace.doing("Parsing excel range",
                                                         data = {"excel_range": str(self.excel_range)})        
        first_column, last_column, first_row, last_row  = ExcelTableReader.parse_range(my_trace, self.excel_range)
        
        header, nrows           = self.xlr_config.pandasRowParameters(parent_trace, first_row, last_row)
        my_trace                = parent_trace.doing("Loading Excel spreadsheet",
                                                        data = {"excel_fullpath": str(self.excel_fullpath)})
        try:
            df                  = _pd.read_excel(   io         = self.excel_fullpath,
                                                    sheet_name = self.excel_sheet,
                                                    header     = header, 
                                                    usecols    = first_column + ':' + last_column, 
                                                    nrows      = nrows)
        except PermissionError as ex:
            raise ApodeixiError(my_trace, "Was not allowed to access excel file. Perhaps you have it open?",
                                        data = {"excel_fullpath": str(self.excel_fullpath),
                                                "error":         str(ex)},
                                        origination = {'concrete class': str(self.__class__.__name__), 
                                                                        'signaled_from': __file__})
        except ValueError as ex:
            error_msg           = str(ex)
            if error_msg.startswith("Worksheet named '") and error_msg.endswith("' not found"):
                raise ApodeixiError(my_trace, "Did you forget to define a Posting Label in the Excel spreadsheet? Got this error:"
                                                + "\n\n" + error_msg)
            else:
                raise ApodeixiError(my_trace, "Found an error while reading the Excel file",
                                                data = {'error':    error_msg})
        except FileNotFoundError as ex:
            error_msg           = str(ex)
            if error_msg.startswith("Worksheet named '") and error_msg.endswith("' not found"):
                raise ApodeixiError(my_trace, "Is your Posting Label right in the Excel spreadsheet? Got this error:"
                                                + "\n\n" + error_msg)
            else:
                raise ApodeixiError(my_trace, "Found an error while reading the Excel file",
                                                data = {'error':    error_msg})
                                                
        my_trace                = parent_trace.doing("Validating data loaded from Excel is not empty")
        if len(df.columns)==0:
            raise ApodeixiError (my_trace, "Incorrectly formatted Excel range was given: '" + self.excel_range 
                              + "'. It spans no columns with data",
                              data = {"excel_fullpath": str(self.excel_fullpath)},
                              origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})
        if len(df.index)==0:
            raise ApodeixiError (my_trace, "Incorrectly formatted Excel range was given: '" + self.excel_range 
                              + "'. It spans no rows with data",
                              data = {"excel_fullpath": str(self.excel_fullpath)},
                              origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})
            
        my_trace                = parent_trace.doing("Computing manifest DataFrame from raw DataFrame loaded from Excel")
        manifest_df             = self.xlr_config.toManifestDF( parent_trace        = my_trace, 
                                                                raw_df              = df, 
                                                                first_row           = first_row, 
                                                                last_row            = last_row)
        
        return manifest_df
    

    def parse_range(parent_trace, excel_range):
        '''
        Parses strings for Excel ranges like 'C5:DA15' and returns the columns and rows: 'C', 'DA', 5, 15.
        If the given range is not correctly formatted then throws an exception
        '''
        REGEX = '^([a-zA-Z]+)([1-9][0-9]*):([a-zA-Z]+)([1-9][0-9]*)$'
        res = _re.match(REGEX, excel_range)
        if (res == None or len(res.groups()) != 4):
            raise ApodeixiError (parent_trace, "Incorrectly formatted Excel range was given: '" + excel_range 
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
                           
        my_trace                = parent_trace.doing("Checking excel range is correctly formatted")
        if first_row < 1:
            raise ApodeixiError (my_trace, "Incorrectly formatted Excel range was given: '" + excel_range 
                              + "'. Row numbers must be 1 or higher")
            
        if first_row >= last_row:
            raise ApodeixiError (my_trace, "Incorrectly formatted Excel range was given: '" + excel_range 
                              + "'. It spans 0 rows")
        return first_column, last_column, first_row, last_row
        
    
    def df_2_xl_row(parent_trace, df_row_nb, excel_range):
        '''
        Helper method available to other Apodeixi classes. Particularly helpful in creating user-friendly error messages by
        inferring user-visible information (a row number in Excel) from an internal parsing information (a DataFrame row number)
        '''
        first_column, last_column, first_row, last_row = ExcelTableReader.parse_range( parent_trace = parent_trace, 
                                                                                    excel_range     = excel_range)

        # DataFrame rows start at 0, which in Excel is the row after the row of column headers.
        # Hence the extra "+1"
        return first_row + 1 + df_row_nb


      




import datetime                         as _datetime

from apodeixi.util.a6i_error            import ApodeixiError
from apodeixi.util.formatting_utils     import StringUtils


class Excel_Block():
    '''
    Represents a rectangular area in Excel that should be formmated the same way. The coordinates are
    integers starting at 0, for both rows and columns.
    @param xInterval A list of two integers: [x0, x1] delineating the block's perimeter's columns
    @param yInterval A list of two integers: [y0, y1] delineating the block's perimeter's rows 
    @param fmt A dictionary containing the formatting information for the block
    '''
    def __init__(self, xInterval, yInterval, fmt):
        self.x0      = xInterval[0]
        self.y0      = yInterval[0]
        self.x1      = xInterval[1]
        self.y1      = yInterval[1]
        self.fmt     = fmt
        
class Excel_Layout():
    '''
    Represents a rectangular layout for a self-contained element, such as an Apodeixi manifest. It consists of
    1 or more Excel_Block objects, each with potentially independent formatting and coordinates, that
    partition the Excel_Layout's real estate. I.e., each cell in the Excel_Layout belongs to exactly one block.
    
    @param name A string used to give a unique name to this layout (e.g., "Roadmap" would be the name for the
                layout used to display an Apodeixi Roadmap manifest, say)
    @param blocks A list of Excel_Block objects
    @param is_transposed A boolean which defaults to False. If True, then the layout is transposed before it
                        is applied to Excel. I.e., a point (x, y) on this Excel_Layout object would be displayed
                        at cell (y, x) in Excel
    '''
    def __init__(self, name, is_transposed):
        
        self.blocks             = []
        self.name               = name
        self.is_transposed      = is_transposed
        return

    def validate(self, parent_trace):
        '''
        Validates that the blocks do partition the entire layout
        '''
        if len(self.blocks) == 0:
            raise ApodeixiError(parent_trace, "No blocks given",
                                                origination ={'signaled_from': __file__,})
        bad_types       = [str(type(b)) for b in self.blocks if type(b) != Excel_Block]
        if len(bad_types) > 0:
            raise ApodeixiError(parent_trace, "Expected only Excel_Blocks, but received " + ", ".join(bad_types),
                                                origination ={'signaled_from': __file__,})
        xmin            = min([block.x0 for block in self.blocks])
        xmax            = max([block.x1 for block in self.blocks])
        ymin            = min([block.y0 for block in self.blocks])
        ymax            = max([block.y1 for block in self.blocks])
        # For each cell in the layout, check it exists in exactly one block
        missed          = []
        multiple        = []
        for x in range(xmin, xmax + 1):
            for y in range(ymin, ymax + 1) :
                #hits = [b for b in self.blocks if b.x0 <= x and x <= b.x1 and b.y0 <= y and y <= b.y1]
                hits = self._locate_block(parent_trace, x, y)
                if len(hits) == 0:
                    missed.append('[' + str(x) + ', '+ str(y) + ']')
                if len(hits) > 1:
                    multiple.append('[' + str(x) + ', '+ str(y) + ']')
        if len(missed) > 0:
            raise ApodeixiError(parent_trace, "Cells not present in any block: " + ", ".join(missed),
                                                origination ={'signaled_from': __file__,})
        if len(multiple) > 0:
            raise ApodeixiError(parent_trace, "Cells present multiple blocks: " + ", ".join(multiple),
                                                origination ={'signaled_from': __file__,})  

    def _locate_block(self, parent_trace, x, y):
        '''
        Helper method that returns a list of blocks from self.blocks that contain cell [x, y]
        '''
        hits = [b for b in self.blocks if b.x0 <= x and x <= b.x1 and b.y0 <= y and y <= b.y1]
        return hits

    def contains(self, parent_trace, x, y):
        '''
        Returns a boolean, stating whether point [x, y] falls in this layout's span/real-estate area.
        '''
        hits = self._locate_block(parent_trace, x, y)
        return len(hits) > 0

    def getFormat(self, parent_trace, x, y):
        '''
        Identifies the the unique Excel_Block that as been configured for cell [x, y], and then returns
        that Excel_Block's format.

        Raises an ApodeixiError if there is not a unique Excel_Block containing [x, y]
        '''
        hits = self._locate_block(parent_trace, x, y)
        if len(hits) == 0:
            raise ApodeixiError(parent_trace, "Can't retrieve format because layout '" + self.name 
                                                + "' does not contain [" + str(x) + ", " + str(y) + "]",
                                                origination ={'signaled_from': __file__,})
        if len(hits) > 1:
            raise ApodeixiError(parent_trace, "Can't retrieve format because layout '" + self.name 
                                                + "' has multiple blocks containing [" + str(x) + ", " + str(y) + "]",
                                                origination ={'signaled_from': __file__,})

        block   = hits[0] # The unique block containing [x,y]
        return block.fmt

    def getSpan(self, parent_trace):
        '''
        Returns a list of lists, in the format [[xmin, ymin], [xmax, ymax]] representing the coordinates of the
        layout (i.e., the upper left corner and the lower right corner)
        '''
        if self.blocks == None or len(self.blocks) == 0:
            raise ApodeixiError(parent_trace, "Layout '" + self.name + "' has no blocks, so can't compute its span",
                                                origination ={'signaled_from': __file__,})
        xmin            = min([block.x0 for block in self.blocks])
        xmax            = max([block.x1 for block in self.blocks])
        ymin            = min([block.y0 for block in self.blocks])
        ymax            = max([block.y1 for block in self.blocks])

        return [[xmin, ymin], [xmax, ymax]]

class Palette():

    # Static colors.
    DARK_BLUE                   = '#0070C0'
    WHITE                       = '#FFFFFF'
    DARK_GREEN                  = '#548235'
    LIGHT_GREEN                 = '#E2EFDA' # '#E5EDD3' # '#EBF1DE'
    DARK_GREY                   = '#808080'
    VERY_DARK_GREY              = "#606060"
    LIGHT_GREY                  = '#F2F2F2' # '#E8E8E8

class NumFormats():

    # Static Excel formats for dates and numbers
    INT                         = '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)'       # Example: 4,500
    DOUBLE                      = '_(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(@_)' # Example: 4,500.00
    DATE                        = "[$-en-US]mmmm d, yyyy;@"                         # Example: August 29, 2021"
    TEXT                        = "@"                                               # Example: '7.10'

    def xl_to_txt_formatters(xl_formatters_dict):
        '''
        Takes a dict as an input and returns another dict, with the same keys.

        The input dict `xl_formatters_dic` should map manifest dataset column names to Excel formatters
        known to this class, such as NumFormats.INT, NumFormats.DOUBLE, or NumFormats.DATE. In other words,
        the formatters that Excel will use to render text, if any such formatter is configured for a column.

        The output dict also maps manifets dataset column names to formatters, but not the kind of formatters
        used by Excel to render output. Instead, these are normal "Python programmatic" formatters.
        For example:

            NumFormats.INT renders a number like 4500 as "4,500" in Excel. So the return dict would
            provide lambda fmt such that fmt(4500) = "4,500".

        This service allows programmatic Python code to anticipate how a value will be rendered in Excel.
        That can be used, for example, to correctly predict the number of characters needed by a value in Excel,
        so that Excel column widths can be configured big enough for the rendered value to display.
        This is important since rendered values (such as "4,500" may require more characters than the value
        itself "4500")
        '''
        output_dict                 = {}
        for col in xl_formatters_dict:
            xl_fmt                  = xl_formatters_dict[col]
            if xl_fmt == NumFormats.INT: 
                formatter           = lambda x: "{:,.0f}".format(float(x)) # Render 4500 as 4,500
                output_dict[col]    = formatter
            elif xl_fmt == NumFormats.DOUBLE:
                formatter           = lambda x: "{:,.2f}".format(float(x)) # Render 4500 as 4,500.00
                output_dict[col]    = formatter
            elif xl_fmt == NumFormats.DATE: # Render dates like "August 21, 20220"
                formatter           = lambda x: _datetime.datetime.strftime(x, "%B %d, %Y")
                output_dict[col]    = formatter
            elif xl_fmt == NumFormats.TXT:
                formatter           = str
                output_dict[col]    = formatter

        return output_dict

class ExcelFormulas:
    '''
    Helper class to represent excel formulas that should be added to the Excel spreadsheet in the vicinity
    of the layout for a manifest.

    Typically this is for usability, to provide the user some feedback that numbers entered by the user reconcile
    with the user expectations and/or with other numbers displayed or entered in the spreadsheet.
    '''
    def __init__(self, manifest_name):
        self._manifest_name         = manifest_name

        # Keys are column names, values are lists of _FormulaProxy objects. For a given column, there 
        # should be at most one _FormulaProxy object for each _FormulaProxy class
        self._formulas              = {} 

        return

    class _FormulaProxy():
        '''
        Parent class for light-weight hierarcy of "glorified statics" (materialized as classes) that 
        serve as a proxy for different kinds of formulas

        @param parameters A dict, where the keys are strings corresponding to settings that affect the behavior of
                how Excel formulas are to be laid out when based on this _FormulaProxy object.
        '''
        def __init__(self, parameters):
            self.parameters     = parameters

        def __eq__(self, other):
            if isinstance(other, self.__class__):
                return self.__dict__ == other.__dict__
            else:
                return False

    class COLUMN_TOTAL(_FormulaProxy):
        '''
        Proxy for a formula for a cell that adds up other cells values

        @param parameters A dict, where the keys are strings corresponding to settings that affect the behavior of
                how Excel formulas are to be laid out when based on this _FormulaProxy object. Supported parameters are
                as follows, where ME stands for the class ExcelFormulas.COLUMN_TOTAL:

                * ME.INCLUDE_LABEL: values are booleans. If True, a label named "Total" should be displayed in Excel
                                    to the left of the cell where the total are laid. If False, no such label should
                                    be displayed
        '''
        def __init__(self, parameters):
            super().__init__(parameters)

        INCLUDE_LABEL = "INCLUDE_LABEL" # Used as a key for a boolean parameter

    class CUMULATIVE_SUM(_FormulaProxy):
        '''
        Proxy for a formula for a column of cumulative sum of other cells' values

        @param parameters A dict, where the keys are strings corresponding to settings that affect the behavior of
                how Excel formulas are to be laid out when based on this _FormulaProxy object. 

                At present there are no supported parameters for this class.
        '''
        def __init__(self, parameters):
            super().__init__(parameters)

    def addTotal(self, parent_trace, column, parameters=None):
        self._addFormulatType(parent_trace, column, ExcelFormulas.COLUMN_TOTAL(parameters))

    def addCumulativeSum(self, parent_trace, column, parameters=None):
        self._addFormulatType(parent_trace, column, ExcelFormulas.CUMULATIVE_SUM(parameters))

    def hasTotal(self, parent_trace, column):
        return self._hasFormulaType(parent_trace, column, ExcelFormulas.COLUMN_TOTAL)

    def hasCumulativeSum(self, parent_trace, column):
        return self._hasFormulaType(parent_trace, column, ExcelFormulas.CUMULATIVE_SUM)

    def _addFormulatType(self, parent_trace, column, formula_proxy):
        if not column in self._formulas.keys():
            self._formulas[column]  = []
        
        formula_list                = self._formulas[column]
        if type(formula_proxy) not in [type(proxy) for proxy in formula_list]:
            formula_list.append(formula_proxy)
        else: # This type of formula proxy is already in the list. Make sure it is identical to the one submitted, else
            # error out since we should have at most one instance of a formula_proxy type in the formula_list
            existing_proxy          = [proxy for proxy in formula_list if type(proxy) == type(formula_proxy)][0]
            if existing_proxy != formula_proxy:
                raise ApodeixiError(parent_trace, "Can't add formula to Excel because a different formula of the same type "
                                                    + "has been previously configured")

    def _hasFormulaType(self, parent_trace, column, formula_proxy_type):
        if not column in self._formulas.keys():
            return False
        if formula_proxy_type in [type(proxy) for proxy in self._formulas[column]]:
            return True
        else:
            return False

    def getFormulaParameters(self, parent_trace, column, formula_proxy_type):
        '''
        Returns a dict of parameters for the formula of type `formula_proxy_type` configured for the given
        column, if some such formula has been configured.

        If no such formula has been configured, it returns None
        '''
        if not column in self._formulas.keys():
            raise ApodeixiError(parent_trace, "Can't retrieve Excel formula because it was not configured",
                                                data = {"column": str(column),
                                                        "formulay type": str(formula_proxy_type)})
        formula_list                = self._formulas[column]
        candidates                  = [proxy for proxy in formula_list if type(proxy) == formula_proxy_type]
        if len(candidates) == 0:
            return None
        else:
            return candidates[0].parameters
                
class PostingLayout(Excel_Layout):
    '''
    Class to assist in the construction of an Excel_Layout for one manifest. It enforces the appropriate Excel formatting
    and provides a simplifying API allowing only two types of Excel_Blocks: header rows and body column groups, each of them
    either read-only or writable
    '''
    def __init__(self, name, is_transposed):
        super().__init__(name, is_transposed = is_transposed)
        self._init_formats()

    def _init_formats(self):

        ROOT_FMT                = {'text_wrap': True, 'valign': 'top', 'border': True, 'border_color': Palette.WHITE}
        HEADER_CONTRIB          = {'bold': True, 'font_color': Palette.WHITE, 'align': 'center','border_color': Palette.WHITE, 
                                'right': True}
        R_CONTRIB               = {'locked': True}
        W_CONTRIB               = {'locked': False}
                    
        # NOTE: this "|" operator to merge dictionaries is only available in Python 3.9+. If this fails, check your Python version
        self.HEADER_R_FMT         = ROOT_FMT | HEADER_CONTRIB| R_CONTRIB |{'bg_color': Palette.DARK_GREY}
        self.HEADER_W_FMT         = ROOT_FMT | HEADER_CONTRIB| W_CONTRIB |{'bg_color': Palette.DARK_GREEN}

        self.BODY_R_FMT           = ROOT_FMT | R_CONTRIB | {'bg_color': Palette.LIGHT_GREY}
        self.BODY_W_FMT           = ROOT_FMT | W_CONTRIB | {'bg_color': Palette.LIGHT_GREEN}

        self.FORMULA_W_FMT        = ROOT_FMT | HEADER_CONTRIB | W_CONTRIB | {'bg_color': Palette.DARK_GREEN}
        self.FORMULA_HEADER_FMT   = ROOT_FMT | HEADER_CONTRIB | R_CONTRIB | {'bg_color': Palette.VERY_DARK_GREY}

    def addHeader(self, parent_trace, xInterval, y, mode):
        '''
        Adds an Excel_Block that can serve as a header

        @param xInterval A list of two integers, like [2, 5] to delimit the column perimeter for the block. Note
                        that Excel columns start at 1 (not at 0)
        @param y        An integer, like 1, for the row in which this headers are supposed to be placed. Excel rows
                        start at 1 (not at 0)
        @param mode A string. Either "r" or "w", to indicate whether the block will be read-only or writable.
        '''
        if mode=='r':
            self.blocks.append(Excel_Block(xInterval=xInterval, yInterval=[y,y], fmt = self.HEADER_R_FMT))
        elif mode=='w':
            self.blocks.append(Excel_Block(xInterval=xInterval, yInterval=[y,y], fmt = self.HEADER_W_FMT))
        else:
            raise ApodeixiError(parent_trace, "Invalid mode '" + mode + "'; expected 'r' or 'w'",
                                                origination ={'signaled_from': __file__,})

    def addBody(self, parent_trace, xInterval, yInterval, mode):
        '''
        Adds an Excel_Block that can serve as a header. Note: Excel columns and rows start at 1 (not at 0)

        @param xInterval A list of two integers, like [4, 4] to delimit the column perimeter for the block
        @param yInterval A list of two integers, like [2, 6] to delimit the row perimeter for the block
        @param mode A string. Either "r" or "w", to indicate whether the block will be read-only or writable.
        '''
        if mode=='r':
            self.blocks.append(Excel_Block(xInterval=xInterval, yInterval=yInterval, fmt = self.BODY_R_FMT))
        elif mode=='w':
            self.blocks.append(Excel_Block(xInterval=xInterval, yInterval=yInterval, fmt = self.BODY_W_FMT))
        else:
            raise ApodeixiError(parent_trace, "Invalid mode '" + mode + "'; expected 'r' or 'w'",
                                                origination ={'signaled_from': __file__,})

    def build(self, parent_trace,   columns, nb_rows, editable_cols=[], hidden_cols=[], editable_headers=[], 
                                    x_offset=0, y_offset=0, has_headers=True):
        '''
        Builds out this layout, by adding blocks as appropriate to end up with an N * M layout such that:
        
        1. M is the number of columns minus the number of hidden columns
        2. The first layout's row is the header for the columns (the "headers"), but only if `has_headers` is True
        3. The subsequent N-1 rows (or N rows, if `has_headers` is False) in the layout are for the "body", 
           where N is nb_rows
        4. All body cells are by default read-only, unless they lie in a column in `editable_cols`
        5. All column headers are by default read-only, unless the column appears in the `editable_headers` list
        6. The layout starts at cell [x_offset, y_offset] and extends to the right and below that cell.

        As a side effect, calling this method will destroy any pre-existing blocks

        '''
        self.blocks                     = []
        visible_columns                 = [col for col in columns if not col in hidden_cols]
        for idx in range(len(visible_columns)):
            col                         = visible_columns[idx]
            header_mode                 = 'r'
            body_mode                   = 'r'

            if editable_headers != None and col in editable_headers:
                header_mode             = 'w'
            if editable_cols != None and col in editable_cols:
                body_mode               = 'w'


            if has_headers:
                self.addHeader(parent_trace,    xInterval   = [idx + x_offset, idx + x_offset], 
                                                y           = y_offset, 
                                                mode        = header_mode)
                next_y_offset           = y_offset + 1
            else:
                next_y_offset           = y_offset

            self.addBody(parent_trace,      xInterval   = [idx + x_offset, idx + x_offset], 
                                            yInterval   = [next_y_offset, nb_rows + y_offset], 
                                            mode        = body_mode)

class AsExcel_Config():
    def __init__(self, sheet, hidden_cols = [], num_formats = {}, excel_formulas = None,
                    viewport_width=100, viewport_height=40, max_word_length=20, x_offset=0, y_offset=0):
        '''
        Configuration for laying out an Apodeixi data object, such as a manifest, into a rectangular area in 
        Excel
        
        @param sheet        A string, corresponding to the name of the worksheet in the Excel spreadsheet onto
                            which the data object is to be laid out.
        @param hidden_cols  A list of strings, possibly empty, corresponding to cloumn's in the manifest's tabular
                            display that should not be shown.
        @param viewport_width  Horizontal length of visible screen allocated to this element (in number of characters)
        @param viewport_height Vertical length of visible screen allocated to this element (in number of characters)
        @param max_word_length Integer for the size of a string after which it is considered a "ridiculously long"
                               word" not deserving efforts widen columns enough to make it appear in a single line.
        @param x_offset An int, giving the location of the left-most column for the layout. Smallest value is 0,
                            corresponding to what in Excel is column "A"
        @param y_offset An int, giving the location of the upper row for the layout. Smallest value is 0, corresponding
                            to what in Excel is row "1"
        
        '''
        self.sheet                  = sheet
        self.viewport_width         = viewport_width
        self.viewport_height        = viewport_height
        self.max_word_length        = max_word_length

        self.x_offset               = x_offset
        self.y_offset               = y_offset

        self.hidden_cols            = hidden_cols
        self.num_formats            = num_formats
        self.excel_formulas         = excel_formulas
               
    def df_xy_2_excel_xy(self, parent_trace, displayable_df, df_row_number, df_col_number, representer):
        '''
        Maps layout x-y coordinates to excel row-column coordinates, taking into account offsets
        and (if appropriate) any transpose.

        Returns 4 integers:

        1) and 2)  excel_row, excel_col
                Determines the Excel row number and column number in which to display a piece of datum that 
                is originating on a DataFrame representation of a manifest, given the datum's row number 
                and column number in the dataframe.

                Basically, it maps from DataFrame row numbers to Excel row numbers, leveraging the knowledge
                that has been configured in this config object in order to make that determination.

        2) last_excel_row, last_excel_col for manifest:
                It also computes the last row and column in Excel that this manifest would be populating, to demarcate
                the end of a region.
    
        @param displayable_df A DataFrame, that corresponds exactly to what must be displayed, expressed in layout
                                space. Thus, the other parameters (df_row_number and df_column_number) are
                                with respect to this DataFrame.
                                **NOTE** displayable_df differs from self.data_df because self.data_df may include
                                "hidden columns" that have been dropped in displayable_df because they are not
                                supposed to be displayed. Depending on the situation, one or the other may be needed.
        @param df_row_number An int, representing the row number in `displayable_df` for the datum
                                    to be displayed. If it is -1, then it is assumed to correspond
                                    to the headers
        @param df_col_number An int, representing the column number in `displayable_df` for the datum to be
                                    displayed.
        @param representer A ManifestReprenter object that is running the process of writing the Excel spreadsheet
                            in question, and which probably led to this method being called. Provided in case the
                            logic to determine an Excel row needs to access some state of where the overall process
                            is at, which the ManifestRepresenter tracks.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'df_xy_2_excel_xy' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})


class ManifestXLWriteConfig(AsExcel_Config):
    '''
    The configuration for laying out and formatting a manifest's data on an Excel spreadsheet

    @param manifest_name A string representing the name of a manifest that will be pasted on the same Excel worksheet.
    @param editable_cols A list of strings, corresponding to the columns in the manifest's tabular display that
                            can be edited. All other columns will be protected by Excel (user can't change them)
                            
                            For example, if the manifest is represented by a DataFrame like

                                Theme       |           Task            |   Subtask
                                -----------------------------------------------------------------
                                Usability   | Define spec               | Interview users
                                Scalability | Parallelize calculations  | Refactor calculation code    

                            then if `editable_columns` = ['Subtask'], this means that the user
                            can change 'Interview users' and 'Refactor calculation code', 
                            but not any value in other columns: 'Usability', 'Define spec', 'Scalability'
                            and 'Parallelize calculations' will be protected in Excel and the user won't be able
                            to modify the value of those cells.

    @param hidden_cols  A list of strings, possibly empty, corresponding to column's in the manifest's tabular
                            display that should not be shown.

    @param num_formats A dictionary, possibly empty. Any key should be a column and the value should be a string
                        for how to do number formatting for that column in Excel (e.g., whether a number has
                        decimals or a comma for thousands, or whether to format as a date, and how)

    @param editable_headers A list of strings, corresponding to the column headers in the manifest's tabular display that
                            can be edited. All other headers will be protected by Excel (user can't change them)
                            
                            For example, if the manifest is represented by a DataFrame like

                                Theme       |           Task            |   Subtask
                                -----------------------------------------------------------------
                                Usability   | Define spec               | Interview users
                                Scalability | Parallelize calculations  | Refactor calcuation code    

                            then if `editable_headers` = ['Subtask'], this means that the user
                            can change 'Subtask' but not 'Theme' or 'Task'    

    @param excel_formulas   An ExcelFormulas object that expresses which formulas (if any) should be written
                            to the excel spreadsheet in the vicinity of the area where the manifest was laid out.
    @param excel_formulas   An ExcelFormulas object that expresses which formulas (if any) should be written
                            to the excel spreadsheet in the vicinity of the area where the manifest was laid out.

    @param df_xy_2_excel_xy_mapper A function that is needed to figure the Excel row number in which to display
                            a datum. It's signature as as in this example:

                                def my_mapper(manifest_df, manifest_df_row_number, representer)

                            where parameters are as follows:
                            
                            @param manifest_df is a Pandas DataFrame holding all the data for the manifest we
                                    are displaying in Excel.
                                    IMPORTANT: this is the *full* manifest data, including manifest data we might not be 
                                    displaying, such as the UIDs for referencing manifests which need to be consulted in 
                                    join situations even if not displayed.

                            @param manifest_df_row_number is an int, for the row number in manifest_df that my_mapper
                                    must map to an Excel row number for displaying data from such row
                            @param representer A ManifestRepresenter running the process of displaying to Excel, in case
                                    its state needs to be interrogated.

    '''
    def __init__(self, manifest_name,  read_only, is_transposed, sheet,  
                                viewport_width  = 100,  viewport_height     = 40,   max_word_length = 20, 
                                editable_cols   = [],   hidden_cols = [], num_formats = {}, editable_headers    = [], 
                                excel_formulas  = None,  df_xy_2_excel_xy_mapper = None,
                                x_offset        = 0,    y_offset = 0):
        super().__init__(sheet, hidden_cols = hidden_cols, num_formats = num_formats, excel_formulas = excel_formulas,
                            viewport_width = viewport_width, viewport_height = viewport_height, 
                            max_word_length = max_word_length, x_offset = x_offset, y_offset = y_offset)

        self.editable_cols          = editable_cols
        
        self.editable_headers       = editable_headers

        self.manifest_name          = manifest_name
        
        self.read_only              = read_only

        self.layout                 =  PostingLayout(manifest_name, is_transposed)

        self.df_xy_2_excel_xy_mapper  = df_xy_2_excel_xy_mapper

        # Set during a call to _buildLayout
        self.data_df             = None


    def getName(self, parent_trace):
        return self.layout.name

    def _buildLayout(self, parent_trace, content_df):
        columns                         = list(content_df.columns)
        nb_rows                         = len(content_df.index)
        self.layout.build(parent_trace, columns             = columns,
                                        nb_rows             = nb_rows,
                                        editable_cols       = self.editable_cols, 
                                        hidden_cols         = self.hidden_cols,
                                        editable_headers    = self.editable_headers, 
                                        x_offset            = self.x_offset, 
                                        y_offset            = self.y_offset,
                                        has_headers         = True)
        # Remember content_df in case it must be interrogated later during processing
        self.data_df                 = content_df

    def build_displayable_df(self, parent_trace, content_df, representer):
        '''
        Helper method to take the content of a manifest (in `content_df`) and create an
        new DataFrame whose columns and rows are suitable to be rendered on an Excel spreadsheet.

        The returned DataFrame (the "displayable_df") may differ from `content_df` in situations such as:

        * Perhaps some columns are hidden, so displayable_df would not include those columns of content_df
        * Perhaps some posting controllers need a specialized type of display. If so, they can use a derived
          class from this one (ManifestXLWriteConfig) to handle that. A common use case is for many-to-many
          mappings between two manifests rendered in the same Excel posting. That is handled by derived
          class MappedManifestXLWriteConfig

        Additionally, it takes this opportunity to build the layout for self.

        @param representer A ManifestRepresenter instance that has the context for the process that is
                        displaying possibly multiple manifests onto the same Excel workbook.
        '''
        displayable_cols    = [col for col in content_df.columns if not col in self.hidden_cols]
        displayable_df      = content_df[displayable_cols]

        self._buildLayout(parent_trace, content_df)

        return displayable_df


    def df_xy_2_excel_xy(self, parent_trace, displayable_df, df_row_number, df_col_number, representer):
        '''
        Maps layout x-y coordinates to excel row-column coordinates, taking into account offsets
        and (if appropriate) any transpose.

        Returns 4 integers:

        1) and 2)  excel_row, excel_col
                Determines the Excel row number and column number in which to display a piece of datum that 
                is originating on a DataFrame representation of a manifest, given the datum's row number 
                and column number in the dataframe.

                Basically, it maps from DataFrame row numbers to Excel row numbers, leveraging the knowledge
                that has been configured in this config object in order to make that determination.

        2) last_excel_row, last_excel_col for manifest:
                It also computes the last row and column in Excel that this manifest would be populating, to demarcate
                the end of a region.
    
        @param displayable_df A DataFrame, that corresponds exactly to what must be displayed, expressed in layout
                                space. Thus, the other parameters (df_row_number and df_column_number) are
                                with respect to this DataFrame.
                                **NOTE** displayable_df differs from self.data_df because self.data_df may include
                                "hidden columns" that have been dropped in displayable_df because they are not
                                supposed to be displayed. Depending on the situation, one or the other may be needed.
        @param df_row_number An int, representing the row number in `displayable_df` for the datum
                                    to be displayed. If it is -1, then it is assumed to correspond
                                    to the headers
        @param df_col_number An int, representing the column number in `displayable_df` for the datum to be
                                    displayed.
        @param representer A ManifestReprenter object that is running the process of writing the Excel spreadsheet
                            in question, and which probably led to this method being called. Provided in case the
                            logic to determine an Excel row needs to access some state of where the overall process
                            is at, which the ManifestRepresenter tracks.
        '''
        if self.df_xy_2_excel_xy_mapper != None:
            # TODO - ADD SUPPORT FOR transposes
            if df_row_number == -1: 
                # TODO - For now we can't support mappers for headers (header is when df_row_number=-1), as there 
                # is no UID to map to
                excel_row                   = self.y_offset + 1 + df_row_number # An extra '1' because of the headers
                final_excel_row             = None # Doesn't matter what this is if we are doing headers
            else:
                # GOTCHA The parameter `displayable_df` may have fewer columns than self.data_df, though they have
                #           the same row numbers. Wnen we call the mapper we should pass self.data_df because
                #           that has the full manifest's data, and possibly the mapper needs to access some hidden
                #           columns that are in self.data_df but not in `displayable_df`
                #           EXAMPLE: column 'big-rock' is hidden for big-rock-estimate manifests, but is needed
                #                   by the mapper to aligh the estimate numbers on the same row as the big rock
                #                   that they are for.
                excel_row, final_excel_row  = self.df_xy_2_excel_xy_mapper( manifest_df             = self.data_df, 
                                                                            manifest_df_row_number  = df_row_number, 
                                                                            representer             = representer)
            excel_col                   = self.x_offset + df_col_number
            final_excel_col             = self.x_offset + len(displayable_df.columns) - 1
            return excel_row, excel_col, final_excel_row, final_excel_col
        else:
            if self.layout.is_transposed:
                excel_col                   = self.y_offset + 1 + df_row_number # An extra '1' because of the headers
                final_excel_col             = self.y_offset + len(displayable_df.index) # Don't do len(index)-1 since headers add a row
    
                excel_row                   = self.x_offset + df_col_number
                final_excel_row             = self.x_offset + len(displayable_df.columns) - 1
            else:
                excel_row                   = self.y_offset + 1 + df_row_number # An extra '1' because of the headers
                final_excel_row             = self.y_offset + len(displayable_df.index) # Don't do len(index)-1 since headers add a row
    
                excel_col                   = self.x_offset + df_col_number
                final_excel_col             = self.x_offset + len(displayable_df.columns) - 1
        return excel_row, excel_col, final_excel_row, final_excel_col

class MappedManifestXLWriteConfig(ManifestXLWriteConfig):
    '''
    Please refer to the documentation of the parent class for overall explanation on the  constructor parameters.

    This is a specialized class to configure how to display in Excel a manifest that has a many-to-many mapping
    to another manifest.

    It requires the referenced manifest to also appear in the same Excel worksheet, and for it to be displayed
    at 90 degrees relative to this referencing manifest, so that the mapping can be expressed by a tabular map
    where an "x" indicates a mapping between UIDs from the two manifests.
    '''
    def __init__(self, manifest_name,  read_only, referenced_manifest_name, my_entity, mapped_entity, is_transposed, sheet,  
                                viewport_width  = 100,  viewport_height     = 40,   max_word_length = 20, 
                                editable_cols   = [],   hidden_cols = [], num_formats = {}, editable_headers    = [], 
                                excel_formulas  = None,  df_xy_2_excel_xy_mapper = None,
                                x_offset        = 0,    y_offset = 0):

        super().__init__(manifest_name, read_only, is_transposed, sheet,  viewport_width,  viewport_height,   max_word_length, 
                                editable_cols,   hidden_cols, num_formats, editable_headers, 
                                excel_formulas,  df_xy_2_excel_xy_mapper,
                                x_offset,    y_offset)

        self.my_entity                  = my_entity
        self.referenced_manifest_name   = referenced_manifest_name
        self.mapped_entities            = mapped_entity

        self.original_content_df        = None # Will be the original manifest content, as it is in the YAML manifest

 
    def build_displayable_df(self, parent_trace, content_df, representer):
        '''
        Overwrites parent class's implementation to support displaying of many-to-many mappings
        between two manifests: the manifest being displayed in this call (the "referencing manifest"), 
        and a `reference manifest` that is assumed to have been previously displayed onto the same Excel worksheet.

        Like the parent, this is a helper method that takes the content of a manifest (in `content_df`) 
        and creates and returns a new DataFrame (the "displayable_df") whose columns and rows are suitable to be 
        rendered on an Excel spreadsheet.

        For this concrete class, the way how "displayable_df" differs from `content_df` is this:

        1. `displayable_df` will have the same number of rows as `content_df`
        2. All non-hidden columns of `content_df` are included in `displayable_df`, except for the 
           column self.mapped_entities
        3. The column self.mapped_entities is assumed to have values that are lists of UIDs for the
           referenced manifest. 
        4. This method takes the union of all referenced manifest's UIDs appearing in any row of
            `content_df[self.mapped_entities]`, and adds them as columns to `displayable_df`
        5. The refencing manifest is assumed to have a column self.my_entity whose values
           are unique and therefore identify a row in `displayable_df`
        6. For a row index idx in `displayable_df`, and a mapped_entities' UID A, we set

                displayable_df[A][idx] = "x"  if and only if 
                                A is a member of content_df[self.my_entity][idx]

                Otherwise, we set displayable_df[A][idx] = ""
    

        @param representer A ManifestRepresenter instance that has the context for the process that is
                        displaying possibly multiple manifests onto the same Excel workbook.
        '''
        all_mapped_UIDs_s               = set()
        # Check if content_df has any mappings before bothering to extract them, but columns in content_df
        # may differ from self.mapped_entities up to a YAML field formatting, so before comparing figure out the
        # column it maps to, if any
        #   => We define "col_to_use" as a column in content_df that "is" self.mapped_entities, up to YAML equivalence
        FMT                             = StringUtils().format_as_yaml_fieldname
        nice_cols                       = [FMT(col) for col in content_df.columns]
        mapping_col                     = FMT(self.mapped_entities)
        if mapping_col in nice_cols:
            col_to_use                  = [c for c in content_df.columns if FMT(c) == mapping_col][0]
        else:
            col_to_use                  = None 

        if col_to_use != None:
            for row in content_df.iterrows():
                row_mapped_UIDs         = row[1][col_to_use]
                if row_mapped_UIDs != None: 
                    if type(row_mapped_UIDs) != list:
                        raise ApodeixiError(parent_trace, "Expected a list for mapped UIDs, and instead found a'"
                                                            + str(type(row_mapped_UIDs)) + "'")
                    all_mapped_UIDs_s   = all_mapped_UIDs_s.union(row_mapped_UIDs)

        link_table                      = representer.link_table
        other_manifest_UIDs             = link_table.all_uids(  parent_trace        = parent_trace, 
                                                                manifest_identifier = self.referenced_manifest_name)

        all_mapped_UIDs                 = all_mapped_UIDs_s.union(other_manifest_UIDs) 

        def put_an_x_on_mappings(uid):
            def do_it(row):
                uid_list                = None
                if col_to_use != None:
                    uid_list            = row[col_to_use]
                if type(uid_list) == list and uid in uid_list:
                    return "x"
                else:
                    return ""
            return do_it

        # Now add the new columns to an enriched df. And we remember the original content df for 
        # future reference
        self.original_content_df        = content_df
        enriched_df                     = content_df.copy()
        for uid in all_mapped_UIDs:
            enriched_df[uid]         = enriched_df.apply(lambda row: put_an_x_on_mappings(uid)(row), axis = 1) 
            self.editable_cols.append(uid)  

        self._buildLayout(parent_trace, content_df = enriched_df)

        # Finally, drop the non-displayable columns. We didnt do it before because we needed to make the call
        # to self._buildLayout with all the original columns, including the hidden ones
        displayable_cols                = [col for col in enriched_df.columns if not col in self.hidden_cols]

        displayable_df                  = enriched_df[displayable_cols]
        if col_to_use != None and col_to_use in displayable_df.columns:
            displayable_df = displayable_df.drop(col_to_use, axis =1)

        return displayable_df


    def df_xy_2_excel_xy(self, parent_trace, displayable_df, df_row_number, df_col_number, representer):
        '''
        Maps layout x-y coordinates to excel row-column coordinates, taking into account offsets
        and (if appropriate) any transpose.

        Returns 4 integers:

        1) and 2)  excel_row, excel_col
                Determines the Excel row number and column number in which to display a piece of datum that 
                is originating on a DataFrame representation of a manifest, given the datum's row number 
                and column number in the dataframe.

                Basically, it maps from DataFrame row numbers to Excel row numbers, leveraging the knowledge
                that has been configured in this config object in order to make that determination.

        2) last_excel_row, last_excel_col for manifest:
                It also computes the last row and column in Excel that this manifest would be populating, to demarcate
                the end of a region.
    
        @param displayable_df A DataFrame, that corresponds exactly to what must be displayed, expressed in layout
                                space. Thus, the other parameters (df_row_number and df_column_number) are
                                with respect to this DataFrame.
                                **NOTE** displayable_df differs from self.data_df because self.data_df may include
                                "hidden columns" that have been dropped in displayable_df because they are not
                                supposed to be displayed. Depending on the situation, one or the other may be needed.
        @param df_row_number An int, representing the row number in `displayable_df` for the datum
                                    to be displayed. If it is -1, then it is assumed to correspond
                                    to the headers
        @param df_col_number An int, representing the column number in `displayable_df` for the datum to be
                                    displayed.
        @param representer A ManifestReprenter object that is running the process of writing the Excel spreadsheet
                            in question, and which probably led to this method being called. Provided in case the
                            logic to determine an Excel row needs to access some state of where the overall process
                            is at, which the ManifestRepresenter tracks.
        '''
        if self.df_xy_2_excel_xy_mapper != None: 
            #TODO - ADD SUPPORT FOR TRANSPOSES & REMOVE THIS METHOD IS SAME AS PARENT

            # GOTCHA The parameter `displayable_df` may have fewer columns than self.data_df, though they have
            #           the same row numbers. Wnen we call the mapper we should pass self.data_df because
            #           that has the full manifest's data, and possibly the mapper needs to access some hidden
            #           columns that are in self.data_df but not in `displayable_df`
            #           EXAMPLE: column 'big-rock' is hidden for big-rock-estimate manifests, but is needed
            #                   by the mapper to aligh the estimate numbers on the same row as the big rock
            #                   that they are for.
            excel_row, final_excel_row  = self.df_xy_2_excel_xy_mapper(     manifest_df             = self.data_df, 
                                                                            manifest_df_row_number  = df_row_number, 
                                                                            representer             = representer)
            excel_col                   = self.x_offset + df_col_number
            final_excel_col             = self.x_offset + len(displayable_df.columns) - 1
            return excel_row, excel_col, final_excel_row, final_excel_col
        else:
            if not self.layout.is_transposed:
                raise ApodeixiError(parent_trace, "Sorry, mapping between manifests is only suppored when referening "
                                                    + "manifest is transposed")

            link_table                  = representer.link_table
            column                      = displayable_df.columns[df_col_number]

            if column in self.original_content_df.columns: # This was not an enriched column
                excel_row               = self.x_offset + df_col_number
            else: # this is an enriched column correponding to a UID in another reference manifest
                referenced_uid          = column
                excel_row               = link_table.row_from_uid(  parent_trace        = parent_trace, 
                                                                    manifest_identifier = self.referenced_manifest_name, 
                                                                    uid                 = referenced_uid)
                if excel_row == None:
                    raise ApodeixiError(parent_trace, "Manifest seems corrupted: it references " + str(referenced_uid)
                                            + " in another manifest called '" + str(self.referenced_manifest_name)
                                            + "' but this other manifest lacks such UID")

            final_excel_row             = link_table.last_row_number(   
                                                                    parent_trace        = parent_trace,
                                                                    manifest_identifier = self.referenced_manifest_name)

            excel_col                   = self.y_offset + 1 + df_row_number # An extra '1' because of the headers
            final_excel_col             = self.y_offset + len(displayable_df.index) # Don't do len(index)-1 since headers add a row

        return excel_row, excel_col, final_excel_row, final_excel_col

class JoinedManifestXLWriteConfig(ManifestXLWriteConfig):
    '''
    Please refer to the documentation of the parent class for overall explanation on the  constructor parameters.

    This is a specialized class to configure how to display in Excel a manifest that has an injection
    relationship to another manifest, such that every single entry in this manifest is associated to a unique
    entry in the ther manifest.

    It requires the referenced manifest to also appear in the same Excel worksheet, and for it to be displayed
    aligned (row-by-row) with the referenced manifest.
    '''
    def __init__(self, manifest_name,  read_only, referenced_manifest_name, is_transposed, sheet,  
                                viewport_width  = 100,  viewport_height     = 40,   max_word_length = 20, 
                                editable_cols   = [],   hidden_cols = [], num_formats = {}, editable_headers    = [], 
                                excel_formulas  = None,  df_xy_2_excel_xy_mapper = None,
                                x_offset        = 0,    y_offset = 0):

        super().__init__(manifest_name, read_only, is_transposed, sheet,  viewport_width,  viewport_height,   max_word_length, 
                                editable_cols,   hidden_cols, num_formats, editable_headers, 
                                excel_formulas,  df_xy_2_excel_xy_mapper,
                                x_offset,    y_offset)

        self.referenced_manifest_name   = referenced_manifest_name



class PostingLabelXLWriteConfig(AsExcel_Config):
    '''
    The configuration for laying out and formatting a Posting Label data on an Excel spreadsheet

    @param editable_fields A list of strings, corresponding to the fields in the Posting Label that should be
                            editable. Any field not listed here will be protected, i.e., Excel won't allow the
                            user to change it.

                            For example, if the posting label looks like

                                manifest API    | delivery-plans.journeys.a6i.io/v2.1
                                product         | OpusPlus
                                recordedBy      | jill.the.architect@magicorp.com    

                            then if `editable_fields` = ['recordedBy'], this means that the user will be allowed
                            by Excel to change 'jill.the.architect@magicorp.com ' but not 
                            'delivery-plans.journeys.a6i.io/v2.1' or 'OpusPlus'    
    '''
    def __init__(self, sheet, viewport_width  = 100,  viewport_height     = 40,   max_word_length = 20, 
                        editable_fields   = [],  date_fields = [],  x_offset        = 0,    y_offset = 0):
        num_formats                 = {}
        for col in date_fields:
            num_formats[col]        = NumFormats.DATE

        super().__init__(sheet, hidden_cols = [], num_formats = num_formats,
                            viewport_width = viewport_width, viewport_height = viewport_height, 
                            max_word_length = max_word_length, x_offset = x_offset, y_offset = y_offset)

        ME                          = PostingLabelXLWriteConfig
        self.editable_fields        = editable_fields

        self.layout                 =  PostingLayout(ME._POSTING_LABEL, is_transposed = True)

    _POSTING_LABEL              = "Posting Label"

    def _buildLayout(self, parent_trace, label_df):
        ME                          = PostingLabelXLWriteConfig
        fields                      = label_df.columns

        self.layout.build(parent_trace, columns             = fields,
                                        nb_rows             = 2,
                                        editable_cols       = self.editable_fields,
                                        hidden_cols         = self.hidden_cols, 
                                        editable_headers    = [], 
                                        x_offset            = self.x_offset, 
                                        y_offset            = self.y_offset,
                                        has_headers         = True)

    def build_displayable_df(self, parent_trace, content_df, representer):
        '''
        Helper method to take the content of the posting label (in `content_df`) and create an
        new DataFrame whose columns and rows are suitable to be rendered on an Excel spreadsheet.

        The returned DataFrame (the "displayable_df") may differ from `content_df` in situations such as:

        * Perhaps some columns are hidden, so displayable_df would not include those columns of content_df

        Additionally, it takes this opportunity to build the layout for self.

        @param representer A ManifestRepresenter instance that has the context for the process that is
                        displaying possibly multiple manifests onto the same Excel workbook.
        '''
        displayable_cols    = [col for col in content_df.columns if not col in self.hidden_cols]
        displayable_df      = content_df[displayable_cols]

        self._buildLayout(parent_trace, content_df)

        return displayable_df

    def df_xy_2_excel_xy(self, parent_trace, displayable_df, df_row_number, df_col_number, representer):
        '''
        Maps layout x-y coordinates to excel row-column coordinates, taking into account offsets
        and (if appropriate) any transpose.

        Returns 4 integers:

        1) and 2)  excel_row, excel_col
                Determines the Excel row number and column number in which to display a piece of datum that 
                is originating on a DataFrame representation of a manifest, given the datum's row number 
                and column number in the dataframe.

                Basically, it maps from DataFrame row numbers to Excel row numbers, leveraging the knowledge
                that has been configured in this config object in order to make that determination.

        2) last_excel_row, last_excel_col for manifest:
                It also computes the last row and column in Excel that this manifest would be populating, to demarcate
                the end of a region.
    
        @param displayable_df A DataFrame, that corresponds exactly to what must be displayed, expressed in layout
                                space. Thus, the other parameters (df_row_number and df_column_number) are
                                with respect to this DataFrame.
                                **NOTE** displayable_df differs from self.data_df because self.data_df may include
                                "hidden columns" that have been dropped in displayable_df because they are not
                                supposed to be displayed. Depending on the situation, one or the other may be needed.
        @param df_row_number An int, representing the row number in `displayable_df` for the datum
                                    to be displayed. If it is -1, then it is assumed to correspond
                                    to the headers
        @param df_col_number An int, representing the column number in `displayable_df` for the datum to be
                                    displayed.
        @param representer A ManifestReprenter object that is running the process of writing the Excel spreadsheet
                            in question, and which probably led to this method being called. Provided in case the
                            logic to determine an Excel row needs to access some state of where the overall process
                            is at, which the ManifestRepresenter tracks.
        '''
        # Posting labels are transposed
        excel_col                   = self.y_offset + 1 + df_row_number # An extra '1' because of the 
        
        final_excel_col             = None #self.y_offset + len(df.index) # Don't do len(index)-1 since headers add a row
 
        excel_row                   = self.x_offset + df_col_number
        final_excel_row             = None #self.x_offset + len(df.columns) - 1

        return excel_row, excel_col, final_excel_row, final_excel_col


class AsExcel_Config_Table():
    '''
    Encapsulates set of AsExcel_Config objects, identified by their name
    '''
    def __init__(self):
        self.manifest_xlw_config_dict       = {}
        self.posting_label_xlw_config       = None
        return
    
    def addManifestXLWriteConfig(self, parent_trace, xlw_config):
        '''
        @param config A ManifestXLWriteConfig object for a manifest
        '''
        if not issubclass(type(xlw_config), ManifestXLWriteConfig):
            raise ApodeixiError(parent_trace, "Expected something derived from 'ManifestXLWriteConfig', "
                                                + "but instead was given a '" 
                                                + str(type(xlw_config).__name__) + "'")
    
        name                                = xlw_config.getName(parent_trace)
        self.manifest_xlw_config_dict[name] = xlw_config

    def getManifestXLWriteConfig(self, parent_trace, name):
        '''
        Returns a ManifestXLWriteConfig object for the manifest that is uniquely identified by the given `name`, and 
        raises an ApodeixiError if none exists

        @param name The unique name of the ManifestXLWriteConfig in self
        '''
        if not name in self.manifest_xlw_config_dict.keys():
            raise ApodeixiError(parent_trace, "No ManifestXLWriteConfig exists with name '" + str(name) + "'")
    
        return self.manifest_xlw_config_dict[name]

    def manifest_configs(self):
        return self.manifest_xlw_config_dict.values()

    def setPostingLabelXLWriteConfig(self, parent_trace, label_xlw_config):
        '''
        @param config A PostingLabelXLWriteConfig object for a posting label
        '''
        if type(label_xlw_config) != PostingLabelXLWriteConfig:
            raise ApodeixiError(parent_trace, "Expected a PostingLabelXLWriteConfig, but instead was given a " 
                                                    + str(type(label_xlw_config)))
    
        self.posting_label_xlw_config     = label_xlw_config

    def getPostingLabelXLWriteConfig(self, parent_trace):
        '''
        Returns the PostingLabelXLWriteConfig object for this object.

        '''
        return self.posting_label_xlw_config

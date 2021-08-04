import datetime                         as _datetime

from apodeixi.util.a6i_error            import ApodeixiError


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
    def __init__(self, name, is_transposed = False):
        
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
    def __init__(self, name):
        super().__init__(name)
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
        4. All body cells are by default read-only, unless they lie in a column in `editable_cols
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
               
    def df_row_2_excel_row(self, parent_trace, df_row_number, representer):
        '''
        Returns two int: the excel_row from the mapper, and the final_excel_row this manifest might populate.

        1) excel row from mapper:
                Determines the Excel row number in which to display a piece of datum that is originating on a 
                DataFrame representation of a manifest, given the datum's row number in the dataframe.

                Basically, it maps from DataFrame row numbers to Excel row numbers, leveraging the knowledge
                that has been configured in this config object in order to make that determination.
        2) final excel row for manifest:
                It also computes the last row in Excel that this manifest would be populating, to demarcate
                the end of a region.
    
        @param df_row_number An int, representing the row number in a DataFrame in which the datum
                                    to be displayed appears.
        @param representer A ManifestReprenter object that is running the process of writing the Excel spreadsheet
                            in question, and which probably led to this method being called. Provided in case the
                            logic to determine an Excel row needs to access some state of where the overall process
                            is at, which the ManifestRepresenter tracks.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'df_row_2_excel_row' in concrete class",
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

    @param df_row_2_excel_row_mapper A function that is needed to figure the Excel row number in which to display
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
    def __init__(self, manifest_name,  sheet,  viewport_width  = 100,  viewport_height     = 40,   max_word_length = 20, 
                                editable_cols   = [],   hidden_cols = [], num_formats = {}, editable_headers    = [], 
                                excel_formulas  = None,  df_row_2_excel_row_mapper = None,
                                x_offset        = 0,    y_offset = 0):
        super().__init__(sheet, hidden_cols = hidden_cols, num_formats = num_formats, excel_formulas = excel_formulas,
                            viewport_width = viewport_width, viewport_height = viewport_height, 
                            max_word_length = max_word_length, x_offset = x_offset, y_offset = y_offset)

        self.editable_cols          = editable_cols
        
        self.editable_headers       = editable_headers

        self.layout                 =  PostingLayout(manifest_name)

        self.df_row_2_excel_row_mapper  = df_row_2_excel_row_mapper

        # Set during a call to buildLayout
        self.content_df             = None

    def getName(self, parent_trace):
        return self.layout.name

    def buildLayout(self, parent_trace, content_df):
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
        self.content_df                 = content_df

    def df_row_2_excel_row(self, parent_trace, df_row_number, representer):
        '''
        Determines the Excel row number in which to display a piece of datum that is originating on a 
        DataFrame representation of a manifest, given the datum's row number in the dataframe.

        Basically, it maps from DataFrame row numbers to Excel row numbers, leveraging the knowledge
        that has been configured in this config object in order to make that determination.

        It supports a "hook" for external code to determine the Excel row number. 
        An example of such a "hook" usage is for displaying joins: if the desired behavior
        is for the referencing manifest's rows to align with those of the referenced manifest,
        then the representer.link_table needs to be consulted to map the foreign key UID in the
        referencing manifest to the row number in which the corresponding referenced manifest row was displayed.

        @param df_row_number An int, representing the row number in a DataFrame in which the datum
                                    to be displayed appears.
        @param representer A ManifestReprenter object that is running the process of writing the Excel spreadsheet
                            in question, and which probably led to this method being called. Provided in case the
                            logic to determine an Excel row needs to access some state of where the overall process
                            is at, which the ManifestRepresenter tracks.
        '''
        if self.df_row_2_excel_row_mapper != None:
            excel_row, final_excel_row  = self.df_row_2_excel_row_mapper(   manifest_df             = self.content_df, 
                                                                            manifest_df_row_number  = df_row_number, 
                                                                            representer             = representer)
        else:
            excel_row                   = self.y_offset + 1 + df_row_number # An extra '1' because of the headers

            manifest_identifer          = self.getName(parent_trace) # Something like "big-rock.0"

            content_df                  = representer.content_df_dict[manifest_identifer]

            final_excel_row             = self.y_offset + len(content_df.index) # Don't do len(index)-1 since headers add a row
 
        return excel_row, final_excel_row

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

        self.layout                 =  PostingLayout(ME._POSTING_LABEL)
        self.layout.is_transposed   = True

    _POSTING_LABEL              = "Posting Label"

    def buildLayout(self, parent_trace, label_df):
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


    def df_row_2_excel_row(self, parent_trace, df_row_number, representer):
        '''
        Returns two int: the excel_row from the mapper, and the final_excel_row this posting label might populate.

        1) excel row from mapper:
                Determines the Excel row number in which to display a piece of datum that is originating on a 
                DataFrame representation of a manifest, given the datum's row number in the dataframe.

                Basically, it maps from DataFrame row numbers to Excel row numbers, leveraging the knowledge
                that has been configured in this config object in order to make that determination.
        2) final excel row for manifest:
                It also computes the last row in Excel that this manifest would be populating, to demarcate
                the end of a region.
    
        @param df_row_number An int, representing the row number in a DataFrame in which the datum
                                    to be displayed appears.
        @param representer A ManifestReprenter object that is running the process of writing the Excel spreadsheet
                            in question, and which probably led to this method being called. Provided in case the
                            logic to determine an Excel row needs to access some state of where the overall process
                            is at, which the ManifestRepresenter tracks.
        '''
        excel_row                   = self.y_offset + 1 + df_row_number # An extra '1' because of the headers

        #manifest_identifer          = self.getName(parent_trace) # Something like "big-rock.0"

        #content_df                  = representer.content_df_dict[manifest_identifer]

        #final_excel_row             = self.y_offset + len(content_df.index) # Don't do len(index)-1 since headers add a row

        return excel_row, None #final_excel_row


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
        if type(xlw_config) != ManifestXLWriteConfig:
            raise ApodeixiError(parent_trace, "Expected a ManifestXLWriteConfig, but instead was given a " + str(type(config)))
    
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

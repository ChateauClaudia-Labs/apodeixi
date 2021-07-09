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

class PostingLayout(Excel_Layout):
    '''
    Class to assist in the construction of an Excel_Layout for one manifest. It enforces the appropriate Excel formatting
    and provides a simplifying API allowing only two types of Excel_Blocks: header rows and body column groups, each of them
    either read-only or writable
    '''
    def __init__(self, name):
        super().__init__(name)

    WHITE                   = '#FFFFFF'
    DARK_GREEN              = '#375623'
    LIGHT_GREEN             = '#E5EDD3' # '#EBF1DE'
    DARK_GREY               = '#808080'
    LIGHT_GREY              = '#E8E8E8' # '#F2F2F2'

    ROOT_FMT                = {'text_wrap': True, 'valign': 'top', 'border': True, 'border_color': WHITE}
    HEADER_CONTRIB          = {'bold': True, 'font_color': WHITE, 'align': 'center','border_color': WHITE, 
                            'right': True}
    R_CONTRIB               = {'locked': True}
    W_CONTRIB               = {'locked': False}
                
    # NOTE: this "|" operator to merge dictionaries is only available in Python 3.9+. If this fails, check your Python version
    HEADER_R_FMT         = ROOT_FMT | HEADER_CONTRIB| R_CONTRIB |{'bg_color': DARK_GREY}
    HEADER_W_FMT         = ROOT_FMT | HEADER_CONTRIB| W_CONTRIB |{'bg_color': DARK_GREEN}

    BODY_R_FMT           = ROOT_FMT | R_CONTRIB | {'bg_color': LIGHT_GREY}
    BODY_W_FMT           = ROOT_FMT | W_CONTRIB | {'bg_color': LIGHT_GREEN}

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
            self.blocks.append(Excel_Block(xInterval=xInterval, yInterval=[y,y], fmt = PostingLayout.HEADER_R_FMT))
        elif mode=='w':
            self.blocks.append(Excel_Block(xInterval=xInterval, yInterval=[y,y], fmt = PostingLayout.HEADER_W_FMT))
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
            self.blocks.append(Excel_Block(xInterval=xInterval, yInterval=yInterval, fmt = PostingLayout.BODY_R_FMT))
        elif mode=='w':
            self.blocks.append(Excel_Block(xInterval=xInterval, yInterval=yInterval, fmt = PostingLayout.BODY_W_FMT))
        else:
            raise ApodeixiError(parent_trace, "Invalid mode '" + mode + "'; expected 'r' or 'w'",
                                                origination ={'signaled_from': __file__,})

    def build(self, parent_trace,   columns, nb_rows, editable_cols=[], editable_headers=[], 
                                    x_offset=0, y_offset=0, has_headers=True):
        '''
        Builds out this layout, by adding blocks as appropriate to end up with an N * M layout such that:
        
        1. M is the number of columns
        2. The first layout's row is the header for the columns (the "headers"), but only if `has_headers` is True
        3. The subsequent N-1 rows (or N rows, if `has_headers` is False) in the layout are for the "body", 
           where N is nb_rows
        4. All body cells are by default read-only, unless they lie in a column in `editable_cols
        5. All column headers are by default read-only, unless the column appears in the `editable_headers` list
        6. The layout starts at cell [x_offset, y_offset] and extends to the right and below that cell.

        As a side effect, calling this method will destroy any pre-existing blocks

        '''
        self.blocks                     = []
        for idx in range(len(columns)):
            col                         = columns[idx]
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
    def __init__(self, viewport_width=100, viewport_height=40, max_word_length=20):
        '''
        Configuration for laying out an Apodeixi object, such as a manifest, into a rectangular area in 
        Excel
        
        @param layout          An Excel_Layout object describing the real estate and formatting in which to place 
                               the data.
        @param viewport_width  Horizontal length of visible screen allocated to this element (in number of characters)
        @param viewport_height Vertical length of visible screen allocated to this element (in number of characters)
        @param max_word_length Integer for the size of a string after which it is considered a "ridiculously long"
                               word" not deserving efforts widen columns enough to make it appear in a single line.
        '''
        self.viewport_width         = viewport_width
        self.viewport_height        = viewport_height
        self.max_word_length        = max_word_length
        
        self.layouts_dict           = {} # To be set by derived classes. Key is a name for a manifest, value is its Excel_Layout object
       
class ManifestXLConfig(AsExcel_Config):
    '''
    @param manifest_name A string representing the name of a manifest that will be pasted on the same Excel worksheet.
    '''
    def __init__(self, manifest_name,    viewport_width  = 100,  viewport_height     = 40,   max_word_length = 20, 
                                editable_cols   = [],   editable_headers    = [],   x_offset        = 0,    y_offset = 0):
        super().__init__(viewport_width, viewport_height, max_word_length)

        self.editable_cols          = editable_cols
        self.editable_cols          = editable_cols
        self.editable_headers       = editable_headers
        self.x_offset               = x_offset
        self.y_offset               = y_offset

        self.layout                 =  PostingLayout(manifest_name)

    def getName(self, parent_trace):
        return self.layout.name

    def buildLayout(self, parent_trace, content_df):
        columns                         = list(content_df.columns)
        nb_rows                         = len(content_df.index)
        self.layout.build(parent_trace, columns             = columns,
                                        nb_rows             = nb_rows,
                                        editable_cols       = self.editable_cols, 
                                        editable_headers    = self.editable_headers, 
                                        x_offset            = self.x_offset, 
                                        y_offset            = self.y_offset,
                                        has_headers         = True)

class PostingLabelXLConfig(AsExcel_Config):
    '''

    '''
    def __init__(self, viewport_width  = 100,  viewport_height     = 40,   max_word_length = 20, 
                        editable_fields   = [],   x_offset        = 0,    y_offset = 0):
        super().__init__(viewport_width, viewport_height, max_word_length)

        ME                          = PostingLabelXLConfig
        self.editable_fields        = editable_fields
        self.x_offset               = x_offset
        self.y_offset               = y_offset

        self.layout                 =  PostingLayout(ME._POSTING_LABEL)
        self.layout.is_transposed   = True

    _POSTING_LABEL              = "Posting Label"

    def buildLayout(self, parent_trace, label_df):
        ME                          = PostingLabelXLConfig
        fields                      = label_df.columns

        self.layout.build(parent_trace, columns             = fields,
                                        nb_rows             = 2,
                                        editable_cols       = self.editable_fields, 
                                        editable_headers    = [], 
                                        x_offset            = self.x_offset, 
                                        y_offset            = self.y_offset,
                                        has_headers         = True)

class AsExcel_Config_Table():
    '''
    Encapsulates set of AsExcel_Config objects, identified by their name
    '''
    def __init__(self):
        self.manifest_config_dict           = {}
        self.posting_label_config           = None
        return
    
    def addManifestXLConfig(self, parent_trace, config):
        '''
        @param config A ManifestXLConfig object for a manifest
        '''
        if type(config) != ManifestXLConfig:
            raise ApodeixiError(parent_trace, "Expected a ManifestXLConfig, but instead was given a " + str(type(config)))
    
        name                                = config.getName(parent_trace)
        self.manifest_config_dict[name]     = config

    def getManifestXLConfig(self, parent_trace, name):
        '''
        Returns a ManifestXLConfig object for the manifest that is uniquely identified by the given `name`, and 
        raises an ApodeixiError if none exists

        @param name The unique name of the ManifestXLConfig in self
        '''
        if not name in self.manifest_config_dict.keys():
            raise ApodeixiError(parent_trace, "No ManifestXLConfig exists with name '" + str(name) + "'")
    
        return self.manifest_config_dict[name]

    def manifest_configs(self):
        return self.manifest_config_dict.values()

    def setPostingLabelXLConfig(self, parent_trace, config):
        '''
        @param config A PostingLabelXLConfig object for a posting label
        '''
        if type(config) != PostingLabelXLConfig:
            raise ApodeixiError(parent_trace, "Expected a PostingLabelXLConfig, but instead was given a " + str(type(config)))
    
        self.posting_label_config     = config

    def getPostingLabelXLConfig(self, parent_trace):
        '''
        Returns the PostingLabelXLConfig object for this object.

        '''
        return self.posting_label_config

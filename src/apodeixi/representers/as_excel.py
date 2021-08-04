
import xlsxwriter

import pandas                               as _pd

from xlsxwriter.utility                     import xl_rowcol_to_cell, xl_range

from apodeixi.util.a6i_error                import ApodeixiError
from apodeixi.util.path_utils               import PathUtils
from apodeixi.util.formatting_utils         import StringUtils
from apodeixi.text_layout.column_layout     import ColumnWidthCalculator
from apodeixi.text_layout.excel_layout      import Palette, NumFormats, ExcelFormulas
from apodeixi.representers.as_dataframe     import AsDataframe_Representer
from apodeixi.xli.interval                  import IntervalUtils

from apodeixi.tree_math.link_table          import LinkTable

class ManifestRepresenter:
    '''
    Class that can represent an Apodeixi manifest as an Excel spreadsheet

    @param config_table An AsExcel_Config_Table object
    @param content_df_dict A dictionary where the keys are the string identifiers of the manifests,
                and the values are DataFrames, each representing the content of a manifest.
    @param label_ctx A dictionary representing the key-value pairs representing the content of a PostingLabel
    '''
    def __init__(self, parent_trace, xlw_config_table, label_ctx, content_df_dict):
        self.xlw_config_table   = xlw_config_table
        self.label_ctx          = label_ctx
        self.content_df_dict    = content_df_dict

        # Used to track a mapping between UIDs and row numbers as we go along creating an Excel worksheet
        self.link_table         = LinkTable(parent_trace)

        # Some intermediate values computed in the course of processing, which are saved as state to facilitate debugging
        self.widths_dict_dict       = {}
        self.span_dict              = {}
        self.hidden_cols_dict       = {}
        self.worksheet_info_dict    = {}

        # If there are formulas to add to any worksheet, they may take space which may imply that we need to shift the
        # layout subsequent content (for other columns of a given manifest, or for other manifest).
        # This dictionary helps us remember such shifts, for each worksheet. The keys worksheets and the values
        # are FormulaShift instances
        #
        self.formula_shift_dict     = {}

        return

    POSTING_LABEL_SHEET     = "Posting Label"
    SUCCESS                 = "Success"

    FORMULA_SHIFT_X         = "FORMULA_SHIFT_X"
    FORMULA_SHIFT_Y         = "FORMULA_SHIFT_Y"

    def dataframe_to_xl(self, parent_trace, excel_folder, excel_filename):
        '''
        '''
        my_trace                = parent_trace.doing("Creating Excel workbook",
                                                        data = {'folder': excel_folder, 'filename': excel_filename})
        
        PathUtils().create_path_if_needed(my_trace, excel_folder)

        workbook                = xlsxwriter.Workbook(excel_folder + '/' + excel_filename)

        my_trace                = parent_trace.doing("Enriching Posting Label with location of manifest data")
        self._add_data_locations_to_posting_label(my_trace, workbook)

        my_trace                = parent_trace.doing("Creating Posting Label")
        self._write_posting_label(my_trace, workbook)

        my_trace                = parent_trace.doing("Writing manifest's data")
        self._write_dataframes(my_trace, workbook)

        my_trace                = parent_trace.doing("Saving Excel spreadsheet")
        try:
            workbook.close()
        except Exception as ex:
            raise ApodeixiError(my_trace, "Encountered a problem saving the Excel spreadsheet",
                            data = {"error": str(ex)})

        return ManifestRepresenter.SUCCESS

    def _add_data_locations_to_posting_label(self, parent_trace, workbook):
        '''
        Adds entries like

            data.kind.1
            data.range.1
            data.sheet.1

        to the `self.label_ctx`
        '''
        label_xlw_config        = self.xlw_config_table.getPostingLabelXLWriteConfig(parent_trace)
        for name in self.content_df_dict.keys():
            loop_trace          = parent_trace.doing("Adding location information for '" + str(name) + "'")
            df                  = self.content_df_dict[name]
            xlw_config          = self.xlw_config_table.getManifestXLWriteConfig(loop_trace, name)

            try:
                kind, nb            = name.split(".")
            except ValueError as ex:
                raise ApodeixiError(loop_trace, "Unable to parse name of dataset. Expected something like <kind>.<number>",
                                                data = {"dataset name":     "'" + name + "'",
                                                        "error":            str(ex)})

            x_0                 = xlw_config.x_offset
            
            
            # Some "hidden cols" arising from joins may not be in df_columns at this stage of the lifecyle
            real_hidden_cols    = [col for col in xlw_config.hidden_cols if col in df.columns] 
            
            # The "-1" is because x_0 was one of the columns, so count one less column
            x_1                 = x_0 + len(df.columns) - 1 - len(real_hidden_cols)
            
            y_0                 = xlw_config.y_offset
            # The "- 1" is because y_0 was one of the rows, so count one less row. 
            y_1                 = y_0 + len(df.index) -1 

            if xlw_config.layout.is_transposed:
                # Add an extra columns, for the headers
                x_1             += 1
            else: 
                # Add an extra row, for the headers
                y_1             += 1

            cell_0              = xl_rowcol_to_cell(y_0, x_0) 

            # x_i, y_i start at 0, whereas Excel ranges start at 1. 
            cell_1              = xl_rowcol_to_cell(y_1, x_1)

            DATA_KIND           = 'data.kind.'     + str(nb)
            DATA_RANGE          = 'data.range.'    + str(nb)
            DATA_SHEET          = 'data.sheet.'    + str(nb)
            self.label_ctx['data.kind.'     + str(nb)]     = kind
            self.label_ctx['data.range.'    + str(nb)]     = cell_0 + ":" + cell_1
            self.label_ctx['data.sheet.'    + str(nb)]     = xlw_config.sheet

            label_xlw_config.editable_fields.extend([DATA_RANGE, DATA_SHEET])

    def _write_dataframes(self, parent_trace, workbook):
        '''
        Creates and populates one or more worksheets, each containing data for one or more manifests.
        Each manifest's data is inputed as a DataFrame.

        The worksheet onto which a manifest's data is laid out is the worksheet whose name is listed in
        self.xlw_config_table[key] where key is a string identifying a manifest (i.e., a dataset). These
        `key' strings are the same as the dictionary keys in content_df_dict.
        '''

        manifest_worksheet_list = []
        for name in self.content_df_dict.keys():
            loop_trace          = parent_trace.doing("Populating Excel content for '" + str(name) + "'")
            df                  = self.content_df_dict[name]
            config              = self.xlw_config_table.getManifestXLWriteConfig(loop_trace, name)
            worksheet           = workbook.get_worksheet_by_name(config.sheet)
            if worksheet == None:
                worksheet               = workbook.add_worksheet(config.sheet) 
                # We want to protect only some cells that we put in. For their protection to turn on, we must protect the worksheet. 
                worksheet.protect(options = {'insert_rows': True, 'insert_columns': True})
                manifest_worksheet_list.append(worksheet)
            self._populate_worksheet(loop_trace, df, config, workbook, worksheet)
            self._write_text_label( parent_trace    = loop_trace, 
                                    workbook        = workbook,
                                    worksheet       = worksheet, 
                                    xl_config       = config, 
                                    text            = name)
        
        # Now we must unprotect a large area outside the cells we pasted, which may span multiple
        # manifests per worksheet, potentially
        for worksheet in manifest_worksheet_list:
            self._unprotect_free_space(parent_trace, worksheet = worksheet)
            self._remember_formatting(worksheet, worksheet.get_name())

    def _write_posting_label(self, parent_trace, workbook):
        '''
        Creates and populates a PostingLabel worksheet
        '''
        ME                      = ManifestRepresenter
        label_xlw_config        = self.xlw_config_table.getPostingLabelXLWriteConfig(parent_trace)


        tmp_dict                = {}
        for key in self.label_ctx.keys():
            tmp_dict[key] = [self.label_ctx[key]]
        label_df         = _pd.DataFrame(tmp_dict)
        
        posting_label_worksheet  = workbook.add_worksheet(label_xlw_config.sheet) 
        # We want to protect only some cells that we put in. For their protection to turn on, we must protect the worksheet. 
        posting_label_worksheet.protect(options = {'insert_rows': True, 'insert_columns': True})
        self._populate_worksheet(parent_trace, label_df, label_xlw_config, workbook, posting_label_worksheet)

        # Write the title above the PostingLabel
        self._write_text_label( parent_trace    = parent_trace, 
                                workbook        = workbook,
                                worksheet       = posting_label_worksheet, 
                                xl_config       = label_xlw_config, 
                                text            = ME.POSTING_LABEL_SHEET)

        self._remember_formatting(posting_label_worksheet, ME.POSTING_LABEL_SHEET)

    def _write_text_label(self, parent_trace, workbook, worksheet, xl_config, text):
        '''
        Writes a string (parameter `text`) right above the area in the worksheet where the data defined by
        `xl_config` would go. Used, for example, to put a title like "Posting Label" in an Excel cell right above
        where the posting label data would be laid out

        If there is no space (e.g., if the xl_config would lay out the data starting at row 0, so any text label
        would go on "inexistent" row -1), then this method
        does not raise an error but the changes it makes to the behind-the-scenes Excel formatting state will not
        be visible to the user.

        @param xl_config An object derived from AsExcel_Config, defining where a piece of data (e.g., a manifest,
                            posting label, or other) is to be laid out in an Excel spreadsheet.
        '''
        title_x             = xl_config.x_offset
        title_y             = xl_config.y_offset - 1
        title               = text
        fmt_dict            ={'bold': True, 'font_color': Palette.DARK_BLUE}
        fmt                 = workbook.add_format(fmt_dict)
        worksheet.write(title_y, title_x, title, fmt)

    def _remember_formatting(self, worksheet, sheet):
        '''
        Remembers some of the worksheet's formatting info in  simple-types-only dictionaries
        to support regression testing
        '''
        worksheet_info                      = XL_WorksheetInfo()
        worksheet_info.build(worksheet)
        self.worksheet_info_dict[sheet]     = worksheet_info

    def _set_column_width(self, parent_trace, worksheet, xl_x, column_width, layout):
        '''
        Helper method to set a column width for a worksheet
        '''
        # Excel by default uses font size 11, but widths are computed by Excel assuming font size 10.
        # So need to scale up to get the expected behavior
        scaled_width    = column_width * self._scale_to_font_size(parent_trace, font_size = 11)
        worksheet.set_column(xl_x,      xl_x,       scaled_width)

    def _write_val(self, parent_trace, workbook, worksheet, layout_x, layout_y, excel_row, val, layout, num_format):
        '''

        @param excel_row An int. Normally this should be the same as layout_y, except in cases where a mapper
                        has been configured to display the data in a different excel row number than layout_y.
                        This can happen when there are joins and the referencing manifest has fewer rows than the
                        referenced manifest, which means that to align the two displays by row there might be
                        "empty rows" throughout partso of the rferencing manifest's display. Example: a big-rocks-investment
                        referencing a big-rocks manifest that has multiple breakdown levels, but where the investment
                        is not at the level of the leaves of the big-rocks, but at a higher level of aggregation.
        '''
        
        if layout.is_transposed:
            xl_x            = excel_row
            xl_y            = layout_x
        else:
            xl_x            = layout_x
            xl_y            = excel_row
        
        fmt_dict        = layout.getFormat(parent_trace, layout_x, layout_y)
        if num_format != None:
            fmt_dict    = fmt_dict.copy() # GOTCHA - copy or else subsequent use of xlsxwriter will use a polluted format
            fmt_dict['num_format'] = num_format

        fmt             = workbook.add_format(fmt_dict)
        worksheet.write(xl_y, xl_x, val, fmt)

    def _populate_worksheet(self, parent_trace, content_df, config, workbook, worksheet):
        '''
        Helper method to write the block in Excel that comes from the manifest's content (as opposed to the Posting Label 
        data).
        Returns the layout against which the `content_df` was pasted.

        Transpose functionality is supported. So we have 2 spaces:

        1. "Layout space" - those are the coordinates for content_df and config, config.layout. We use layout_x, layout_y
            for these coordinates.
        2. "Excel space" - the coordinates in Excel. We use xl_x, xl_y for these coordinates.

        The relationship between both spaces depends on the config.layout.is_transposed flag. If True, then

            xl_x = layout_y and xl_y = layout_x.

        Otherwise, xl_x = layout_x and xl_y = layout_y

        @param config An AsExcel_Config object specifying how the data in `content_df` should be laid out on 
                        the worksheet
        '''
        layout                  = config.layout
        is_transposed           = layout.is_transposed

        my_trace                = parent_trace.doing("Building out the layout")
        if True:
            displayable_cols    = [col for col in content_df.columns if not col in config.hidden_cols]
            displayable_df      = content_df[displayable_cols]
            config.buildLayout(parent_trace, content_df)

            #layout              = config.layout
            layout.validate(my_trace)
            span                = layout.getSpan(my_trace) # Useful to carry around for debugging
            inner_trace         = my_trace.doing("Computing optimal column widths", data = {'layout span': str(span)})
            # Compute optimal widths for the columns
            if is_transposed:
                # Besides transposing, reset index so layout headers become a column, so they get included in 
                # calculation of widths (else they are ignored, being an index in the transpose)
                xl_df           = displayable_df.transpose().reset_index() 
                
            else:
                xl_df           = displayable_df

            column_formatters   = NumFormats.xl_to_txt_formatters(config.num_formats)
            calc                = ColumnWidthCalculator(    data_df             = xl_df, 
                                                            viewport_width      = config.viewport_width, 
                                                            viewport_height     = config.viewport_height, 
                                                            max_word_length     = config.max_word_length,
                                                            column_formatters   = column_formatters)
            
            # Dictionary - keys are columns of displayable_df, vals are sub-dicts {'width': <number>, 'nb_lines': <number>}
            widths_dict         = calc.calc(inner_trace) 

            # Remember these to support debugging
            # The layout.name *must* be the manifest_identifier if we are populating a manifest (as opposed to a posting label)
            name                            = layout.name 
            self.widths_dict_dict[name]     = widths_dict
            self.span_dict[name]            = span
            self.hidden_cols_dict[name]     = config.hidden_cols

        # Now we start laying out content on the worksheet. 
        # Start by re-sizing the columns.
        my_trace            = parent_trace.doing("Setting column widths")
        if True:            
            xl_columns          = xl_df.columns 
            for xl_idx in range(len(xl_columns)): # GOTCHA: Loop is in "Excel space"
                col             = xl_columns[xl_idx]
                loop_trace      = my_trace.doing("Processing XL column '" + col + "'")
                width           = float(widths_dict[col]['width']) # Cast to float to do float arithmetic in scaling to font size
                if is_transposed:
                    xl_x        = config.y_offset + xl_idx
                else:
                    xl_x        = config.x_offset + xl_idx
                self._set_column_width(loop_trace, worksheet, xl_x, width, layout)
   
        # Now populate headers
        my_trace                        = parent_trace.doing("Populating headers", data = {'layout span': str(span)})
        if True:            
            columns                     = displayable_df.columns
            for layout_idx in range(len(columns)): # GOTCHA: Loop is in "Layout space"
                col                     = columns[layout_idx]
                loop_trace              = my_trace.doing("Processing layout column '" + col + "'")
                layout_x                = config.x_offset + layout_idx
                layout_y                = config.y_offset
                if is_transposed:
                    xl_x                = layout_y
                else:
                    xl_x                = layout_x
                self._write_val(loop_trace, workbook, worksheet, layout_x, layout_y, layout_y, col, layout, num_format = None)

        # Now lay out the content
        my_trace                        = parent_trace.doing("Populating content", data = {'layout span': str(span)})
        if True:
            for layout_idx in range(len(columns)):
                col                     = columns[layout_idx]
                outer_loop_trace        = my_trace.doing("Processing column = '" + col + "'")

                # These are the coordinates of the first cell populated with content for this column
                # They are needed later to define the start of the range to which a column-level formula applies,
                # if such a formula has been configured to be required. They are set in the first cycle of the loop,
                # so we initialize them to None so that the loop uses that as the hint that it is on the first cycle
                first_x                 = None
                first_y                 = None
                # This will be set in each cycle of the loop, so after the loop they will correspond to the last
                # cell populated for this column
                last_x                  = None
                last_y                  = None
                for row in displayable_df.iterrows(): # GOTCHA: Loop is in "Layout space"
                    row_nb      = row[0]
                    row_content = row[1]
                
                    loop_trace          = outer_loop_trace.doing("Processing column = '" + col 
                                                                    + "' row = '" + str(row_nb) + "'")
                    layout_x            = config.x_offset + layout_idx 
                    layout_y            = config.y_offset + 1 + row_nb # An extra '1' because of the headers
                    excel_row, last_excel_row   = config.df_row_2_excel_row(    parent_trace            = parent_trace, 
                                                                                df_row_number           = row_nb,
                                                                                representer             = self)

                    # If we have inserted formulas that took space, shift accordingly 
                    if config.sheet in self.formula_shift_dict.keys():
                        formula_shift   = self.formula_shift_dict[config.sheet]
                        layout_x        += formula_shift.shift_x
                        layout_y        += formula_shift.shift_y  

                    if first_x == None:
                        first_x         = layout_x
                    if first_y == None:
                        first_y         = layout_y
                 
                    num_format      = None
                    if col in config.num_formats.keys():
                        num_format  = config.num_formats[col]

                    val             = row_content[col]
                    self._write_val(parent_trace, workbook, worksheet, layout_x, layout_y, excel_row,
                                    val, layout, num_format = num_format)

                    # Remember UID -> row mapping, for aligninig other joined manifests later on. But only if there
                    # is a value in the UID column, since we allow the case that it be blank in some rows if
                    # we default it from earlier rows (as when constructing an n-table instead of a b-table: refer
                    # to the AssertionTree documentation)
                    if IntervalUtils().is_a_UID_column(parent_trace, col) and not StringUtils().is_blank(val):
                        self.link_table.keep_row_last_UID(parent_trace, 
                                                            manifest_identifier     = name, 
                                                            row_nb                  = excel_row, 
                                                            uid                     = row_content[col])

                    last_x              = layout_x
                    last_y              = excel_row
                # Before exiting this row, write any formulas associated to this column
                # Sometimes where there are joins, the last_y is not the same as where the manifest's
                # area should end. In such cases we rely on the last_excel_row to tell us where the manifest's
                # area ended so we correctly position the formaulae
                if last_excel_row != None:
                    last_y              = last_excel_row
                self._add_formulas( parent_trace        = outer_loop_trace,
                                    column              = col,
                                    column_width        = width,
                                    first_x             = first_x,
                                    first_y             = first_y,
                                    last_x              = last_x,
                                    last_y              = last_y,
                                    data_df             = displayable_df,
                                    config              = config,
                                    workbook            = workbook,
                                    worksheet           = worksheet)

    def _add_formulas(self, parent_trace, column, column_width, first_x, first_y, last_x, last_y,
                        data_df, config, workbook, worksheet):
        '''
        Writes the formulas to the worksheet that pertain to column, if any
        '''
        if config.excel_formulas == None:
            return
        if config.layout.is_transposed:
            # TODO Logic in this method needs to be enhanced & refactored to support cases where layout
            # is transposed. For example, totals wouldn't be for Excel column but for Excel rows.
            raise ApodeixiError(parent_trace, "Sorry, but formulas are not yet supported for transposed layouts")

        if config.excel_formulas.hasTotal(parent_trace, column):
            my_trace                    = parent_trace.doing("Adjusting column width so totals will fit")
            if True:
                # To know the width, compute the total and format it to count how much space it needs
                total                   = data_df[column].sum()
                column_formatters       = NumFormats.xl_to_txt_formatters(config.num_formats)
                if column in column_formatters.keys():
                    formatter           = column_formatters[column]
                else:
                    formatter           = str
                total_txt               = formatter(total)
                new_width               = max(len(total_txt), column_width)
                self._set_column_width(my_trace, worksheet, last_x, new_width, config.layout)

            my_trace                    = parent_trace.doing("Writing down totals for column")
            if True:
                cell_first              = xl_rowcol_to_cell(first_y,        first_x) 
                cell_last               = xl_rowcol_to_cell(last_y,         last_x)
                cell_totals             = xl_rowcol_to_cell(last_y + 1,     last_x)
                formula                 = "=SUM(" + cell_first + ":" + cell_last + ")" # For example, "=SUM(C3:C6)"
                self._write_formula_val(parent_trace, cell_totals, formula, column, config, worksheet, workbook)

            my_trace                    = parent_trace.doing("Writing down label for totals, if so configured")
            if True:
                formula_params      = config.excel_formulas.getFormulaParameters(parent_trace, 
                                                                        column              = column, 
                                                                        formula_proxy_type  = ExcelFormulas.COLUMN_TOTAL)
                FLAG                = ExcelFormulas.COLUMN_TOTAL.INCLUDE_LABEL
                if formula_params != None and FLAG in formula_params.keys() and formula_params[FLAG] == True:
                    fmt_dict            ={'bold': True, 'align': 'right', 'font_color': Palette.DARK_BLUE}
                    fmt                 = workbook.add_format(fmt_dict)
                    worksheet.write(last_y + 1, last_x - 1, "Total:", fmt)          

        if config.excel_formulas.hasCumulativeSum(parent_trace, column):
            HEADER                      = "Cumulative"
            my_trace                    = parent_trace.doing("Setting up column width for extra column for cumulative totals")
            if True:
                # To correctly set the width of the column where we display cumulative sums, we
                # will need to use the ColumnWidthCalculator on a "transient dataframe" where we place the cumulative
                # sum and try to format it the same way as the column we are summing
                cumsum_df               = data_df[column].cumsum().to_frame()

                # NB: cumsum_df will have a single column, also called `column`, as in data_df. So the same
                # column formatters used for data_df will work for cumsum_df
                column_formatters       = NumFormats.xl_to_txt_formatters(config.num_formats)
                calc                    = ColumnWidthCalculator(    data_df             = cumsum_df, 
                                                                    viewport_width      = config.viewport_width, 
                                                                    viewport_height     = config.viewport_height, 
                                                                    max_word_length     = config.max_word_length,
                                                                    column_formatters   = column_formatters)
                
                # Dictionary - keys are columns of cumsum_df, vals are sub-dicts {'width': <number>, 'nb_lines': <number>}
                widths_dict             = calc.calc(my_trace)             
                width                   = float(widths_dict[column]['width']) # Cast to float to do float arithmetic in scaling to font size
                scaled_width            = max(width, len(HEADER))
                # Set width of Excel column last_x+1, which is where we will later write the cumulative sums
                self._set_column_width(my_trace, worksheet, last_x + 1, scaled_width, config.layout)   

            my_trace                    = parent_trace.doing("Writing out header for extra column for cumulative totals")
            if True:
                header_fmt_dict         = config.layout.FORMULA_HEADER_FMT
                header_fmt              = workbook.add_format(header_fmt_dict)
                worksheet.write(first_y - 1, last_x + 1, HEADER, header_fmt)

            my_trace                    = parent_trace.doing("Writing down extra column for cumulative totals")
            if True:
                cell_first              = xl_rowcol_to_cell(first_y,        first_x, row_abs=True) # For example: "C$3"
                for row_nb in range(first_y, last_y + 1):
                    cell_last           = xl_rowcol_to_cell(row_nb,         last_x)
                    cell_cumsum         = xl_rowcol_to_cell(row_nb,         last_x + 1)
                    formula             = "=SUM(" + cell_first + ":" + cell_last + ")" # For example, "=SUM(C$3:C6)"
                    self._write_formula_val(my_trace, cell_cumsum, formula, column, config, worksheet, workbook)
 

        # Default case: do nothing
        return

    def _write_formula_val(self, parent_trace, cell, formula, column, config, worksheet, workbook):
        '''
        Helper method to write the formula into the given cell

        @param column A string representing a column name for a manifest dataset, which is the column
                    for which a formula was configured (Note: depending on the formula type, the formula might 
                    not be written to the same Excel spreadsheet column as the dataset column that inspired
                    the need for the formula. For example, cumulative totals formulae are written to the
                    right of the dataset's column against which cumulative totals are computed).
        @param cell A string representing an Excel cell where a formula should be writte. Example: "D3"
        @param formula A string representing an Excel formula to be added to the cell. Example: "=SUM(C3:C6)"
        '''
        formula_fmt_dict        = config.layout.FORMULA_W_FMT

        if column in config.num_formats.keys():
            num_format  = config.num_formats[column]
            if num_format != None:
                formula_fmt_dict    = formula_fmt_dict.copy() # GOTCHA - copy or else subsequent use of xlsxwriter will use a polluted format
                formula_fmt_dict['num_format'] = num_format

        formula_fmt             = workbook.add_format(formula_fmt_dict)
        worksheet.write_formula(cell, formula, formula_fmt)

    def _scale_to_font_size(self, parent_trace, font_size):
        '''
        Helper method. This is needed because Excel column widths assume a font size of 10. So we must scale up
        widths by the ratio between the desired font_size (which in Excel defaults to 11 for displaying, at odds
        with the way Excel counts column widths, which assumes a font size of 10).

        So this method returns the ratio of font_size to the default assumed in Excel column widths (10)
        
        Refer to the Excel documentation: https://docs.microsoft.com/en-us/office/troubleshoot/excel/determine-column-widths
        '''
        return float(font_size)/10.0

    def _unprotect_free_space(self, my_trace, worksheet):
        '''
        Scans a large range of cells (limit is hard coded) and unprotects any cell that is not in any layout
        for any manifest
        '''
        LIMIT                           = 500

        layouts                         = [config.layout for config in self.xlw_config_table.manifest_configs()]

        # Recall that layout.getSpan return [[xmin, ymin], [xmax, ymax]]
        global_xmin                     = min([layout.getSpan(my_trace)[0][0] for layout in layouts])
        global_ymin                     = min([layout.getSpan(my_trace)[0][1] for layout in layouts])
        global_xmax                     = max([layout.getSpan(my_trace)[1][0] for layout in layouts])
        global_ymax                     = max([layout.getSpan(my_trace)[1][1] for layout in layouts])

        # Outside the global area, unprotect entire ranges. If global span is A1:F20, we unprotect G1:ZZ500 and A21:ZZ500, kind of
        distant_columns = xl_range( 0,                          global_xmax + 1,    
                                    LIMIT,                      LIMIT + global_xmax + 1)

        distant_rows    = xl_range( global_ymax + 1,    0,                  
                                    LIMIT + global_ymax + 1,    LIMIT)

        worksheet.unprotect_range(distant_columns)
        worksheet.unprotect_range(distant_rows)
        
        # With the global area, unprotect any empty space not in any layout (e.g., if pasting multiple
        # manifests, there will be empty space between them)
        for x in range(global_xmin, global_xmax + 1):
            for y in range(global_ymin,global_ymax + 1):
                hits = [layout.name for layout in layouts if layout.contains(my_trace, x, y)]
                if len(hits) == 0: # We never pasted this point, so unprotect it
                    cell                = xl_rowcol_to_cell(y, x)
                    worksheet.unprotect_range(cell)


class XL_WorksheetInfo():
    '''
    Helper class used to record formatting information about a worksheet in a dictionary form that only relies on simple types.
    Helpful for developing regression tests to confirm that there is not regression in how an Excel spreadsheet is
    formatted.
    '''
    def __init__(self):
        self.format_dict = {}
        self.colinfo     = {}
    
    def build(self, worksheet):
        raw_dict                = worksheet.__dict__['colinfo']
        # raw_dict has keys like '00001' and values like [1, 1, 16.5000000001, None, False, 0, False]
        # To make things easier to display, we want to format numbers to 2 decimals only,
        # so 16.5000000001 becomes 16.50
        def _round(val):
            if type(val) == float:
                return round(val, 2)
            else:
                return val

        nicer_dict              = {}
        for key in raw_dict.keys():
            nicer_dict[key]     = [_round(val) for val in raw_dict[key]]

        self.colinfo            = nicer_dict 
        
        table = worksheet.__dict__['table']
        for row_nb in table.keys():
            self.format_dict[row_nb] = {}
            row_dict = table[row_nb]
            for col_nb in row_dict.keys():
                #self.format_dict[row_nb][col_nb] = {}
                cell_struct = row_dict[col_nb]
                if cell_struct.format != None:
                    fmt        = cell_struct.format.__dict__
                    self.format_dict[row_nb][col_nb] = fmt

class FormulaShift():
    '''
    Helper class used when there are formulas to add to an Excel spreadsheet, in addition to the content of manifests.
    Since formulas can take some space, this object remembers the cumulative impact of prior formulas added, in that
    if a prior formula took a column, for example, then the subsequent writing of remaining columns and manifests
    should shift accordingly, since the space where they might otherwise have been written has been consumed by the
    new formula-based column, for example.
    '''
    def __init__(self):
        self.shift_x        = 0
        self.shift_y        = 0

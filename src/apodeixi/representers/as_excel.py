
import xlsxwriter
import pandas                               as _pd
from xlsxwriter.utility                     import xl_col_to_name, xl_rowcol_to_cell, xl_range, xl_range_abs

from apodeixi.util.a6i_error                import ApodeixiError
from apodeixi.util.path_utils               import PathUtils
from apodeixi.util.formatting_utils         import StringUtils
from apodeixi.util.dataframe_utils          import DataFrameUtils
from apodeixi.text_layout.column_layout     import ColumnWidthCalculator
from apodeixi.text_layout.excel_layout      import Palette, NumFormats, ExcelFormulas, MappedManifestXLWriteConfig, \
                                                    JoinedManifestXLWriteConfig

from apodeixi.xli.interval                  import IntervalUtils
from apodeixi.xli.uid_store                 import UID_Store, UID_Utils
from apodeixi.xli.uid_acronym_schema        import UID_Acronym_Schema

from apodeixi.tree_math.link_table          import LinkTable

class ManifestRepresenter:
    '''
    Class that can represent an Apodeixi manifest as an Excel spreadsheet

    @param config_table An AsExcel_Config_Table object
    @param manifestInfo_dict A dictionary where the keys are the string identifiers of the manifests,
                and the values are ManifestInfo object, containing a lot of information about manifests
                (a dictionary representation, a DataFrame representation, etc).
    @param label_ctx A dictionary representing the key-value pairs representing the content of a PostingLabel
    '''
    def __init__(self, parent_trace, xlw_config_table, label_ctx, manifestInfo_dict):
        self.xlw_config_table   = xlw_config_table
        self.label_ctx          = label_ctx

        self.manifestInfo_dict  = manifestInfo_dict

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
        for name in self.manifestInfo_dict.keys():
            loop_trace          = parent_trace.doing("Adding location information for '" + str(name) + "'")
            manifest_info       = self.manifestInfo_dict[name]
            df                  = manifest_info.getManifestContents(parent_trace)
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

            # If we are a mapping, we are at 90 degrees relative to the referenced manifest,
            # so need to add more *columns* by an amount equal to the referenced manifest's rows.
            if issubclass(type(xlw_config), MappedManifestXLWriteConfig):
                for referenced_manifest_name in xlw_config.referenced_manifest_name_list:
                    referenced_manifest_info        = self.manifestInfo_dict[referenced_manifest_name]
                    referenced_df                   = referenced_manifest_info.getManifestContents(parent_trace)
                    # TODO The arithmetic here only works if the referenced manifest is not displayed with
                    # extra padding, i.e., it is displayed "on the first row it can be displayed",
                    # meaning its headers are displayed in the first Excel row after the content of
                    # our manifest. Otherwise the arithmetic below will "fall short" and we will miss out
                    # some mapping rows from the range, and unless the user manually corrects the range in the
                    # Excel spreadsheet before submitting a posting, the mapping of those rows will not be
                    # captured.
                    #   That would be not exactly a bug (since the user "certified" the incorrect range
                    # by submitting the posting), but is certainly a usability problem; something easy for users
                    # to get wrong and not even know about it.
                    # To minimize this bug from happening, we add a buffer
                    #
                    BUG_WORKAROUND_BUFFER   = 10

                    # 1) extra +1 because of the headers of the referenced manifest, 
                    # 2) another +1 because when doing an update, there will be a "hidden row" for the column
                    #   in our manifest that references the other one. For example, in the Journey domain the
                    #   milestones manifest will have a "big-rock" column. It is not displayed but it will 
                    #   cause the referenced manifest to appear one row further down.
                    # 3) An additional + BUG_WORKAROUND_BUFFER for the reasons in the comment above.
                    #
                    x_1             += len(referenced_df.index) + 1 + 1 + BUG_WORKAROUND_BUFFER
            
            elif issubclass(type(xlw_config), JoinedManifestXLWriteConfig):
                # In this case, there is an injection between our manifest's rows and those of the 
                # referenced rows, which may not be a bijection, i.e., there may be empty Excel rows
                # between our manifest's rows. In that case, we need to record that the number of
                # Excel rows is at least as big as the Excel rows of the referenced manifest
                referenced_manifest_info        = self.manifestInfo_dict[xlw_config.referenced_manifest_name]
                referenced_df                   = referenced_manifest_info.getManifestContents(parent_trace)

                # The "-1" is because y_0 was one of the rows, so count one less row
                y_1             = max(y_1, y_0 + len(referenced_df.index) - 1)
                
            # Make room for the headers by adding extra columns.
            # We know that the number of header will be xlw_config.nb_header_levels, and that
            # y_0 as previously computed should be the last header. 
            # So move y_1 down by 1, and move y_0 up by nb_header_levels-1
            y_0             -= xlw_config.nb_header_levels - 1
            y_1             += 1
            if xlw_config.layout.is_transposed:
                cell_0          = xl_rowcol_to_cell(x_0, y_0) 
                cell_1          = xl_rowcol_to_cell(x_1, y_1)
            else: 
                cell_0          = xl_rowcol_to_cell(y_0, x_0) 
                cell_1          = xl_rowcol_to_cell(y_1, x_1)

            # x_i, y_i start at 0, whereas Excel ranges start at 1. 
            

            DATA_KIND           = 'data.kind.'      + str(nb)
            DATA_RANGE          = 'data.range.'     + str(nb)
            DATA_SHEET          = 'data.sheet.'     + str(nb)
            READ_ONLY           = 'readOnly.'       + str(nb)
            self.label_ctx['data.kind.'     + str(nb)]     = kind
            self.label_ctx['data.range.'    + str(nb)]     = cell_0 + ":" + cell_1
            self.label_ctx['data.sheet.'    + str(nb)]     = xlw_config.sheet

            if xlw_config.read_only == True:
                self.label_ctx[READ_ONLY]     = True

            label_xlw_config.editable_fields.extend([DATA_RANGE, DATA_SHEET])

    def _write_dataframes(self, parent_trace, workbook):
        '''
        Creates and populates one or more worksheets, each containing data for one or more manifests.
        Each manifest's data is inputed as a DataFrame.

        The worksheet onto which a manifest's data is laid out is the worksheet whose name is listed in
        self.xlw_config_table[key] where key is a string identifying a manifest (i.e., a dataset). These
        `key' strings are the same as the dictionary keys in manifestInfo_dict.
        '''

        manifest_worksheet_list = []
        for name in self.manifestInfo_dict.keys():
            loop_trace          = parent_trace.doing("Populating Excel content for '" + str(name) + "'")
            manifest_info       = self.manifestInfo_dict[name]
            df                  = manifest_info.getManifestContents(parent_trace)
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
            # BUG FIX ON OCTOBER 13, 2021 -  The code to unprotect is buggy for layouts that have vertical
            # displays, since it will switch what are the global x and global y ranges. Nasty if one mixes
            # a big horizontal layout of (say) 400 rows + a vertical mapping, as the mappings' 400 rows will
            # be incorrectly thought to be 400 columns, so the amount of internal state in Excel to protect
            # cells will get huge. So better to drop the functionality altogether - in practice the user
            # will simply remove protection if he/she needs to edit this space. 
            #
            #self._unprotect_free_space(parent_trace, worksheet = worksheet)

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
        if xl_config.layout.is_transposed == False:
            title_x             = xl_config.x_offset
            title_y             = xl_config.y_offset - xl_config.nb_header_levels
        else:
            title_x             = xl_config.y_offset 
            title_y             = xl_config.x_offset - xl_config.nb_header_levels
                      
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

    def _write_val(self,    parent_trace,   workbook,   worksheet,  layout_x,   layout_y, 
                            excel_row,      excel_col,  val,        layout,     num_format):
        '''
        Writes the value `val` to the given worksheet. The Excel location for writing the value is given 
        by the `excel_row` and `excel_col` parameters, which are in the Excel coordinate space.

        The `layout_x` and `layout_y` are in the layout space, which may be different than Excel's for
        different reasons, including:

        * For a join, there might be a mapper so the Excel rows are determined by a reference manifest's
          locations, not by the layout coordinates. In these cases a mapper is often used by the caller
          to determine what Excel row parameter to pass.
        * In situations when the data must be transposed, such as for many-to-many mappings between 
          manifests, Excel rows correspond to the layout x axis instead of the layout y axis. 
          The dual is true for Excel columns.

        @param layout_x An int. Represents the x-coordinate in layout space.
        @param layout_y An int. Represents the y-coordinates in layout space.
        @param excel_row An int. Normally this should be the same as layout_y, except in cases special
                            cases as described above.
        @param excel_col An int. Normally this should be the same as layout_x, except in cases special
                            cases as described above.
        @param num_format A string for an Excel formatter that is supported by the Apodeixi NumFormats class.
        '''
        clean_val   = DataFrameUtils().clean(val)

        if excel_row == None:
            raise ApodeixiError(parent_trace, "Can't write value to a null Excel row",
                                            data = {"val":              str(clean_val),
                                                    "layout.name":      str(layout.name),
                                                    "excel row":        str(excel_row),
                                                    "excel column":     str(excel_col)})
        if excel_col == None:
            raise ApodeixiError(parent_trace, "Can't write value to a null Excel column",
                                            data = {"val":              str(clean_val),
                                                    "layout.name":      str(layout.name),
                                                    "excel row":        str(excel_row),
                                                    "excel column":     str(excel_col)})
        fmt_dict        = layout.getFormat(parent_trace, layout_x, layout_y)
        if num_format != None:
            fmt_dict    = fmt_dict.copy() # GOTCHA - copy or else subsequent use of xlsxwriter will use a polluted format
            fmt_dict['num_format'] = num_format

        fmt             = workbook.add_format(fmt_dict)

        # clean_val might be an empty string if it was NaN or something like that. However, even an empty string
        # can cause problems later in the processing if the column in question is supposed to be a number,
        # especially if the column is associated to a formula that sums all the values of the column. In that
        # situation  we will get errors like "can't add an 'int' and a 'str'".
        # So if the column is for numbers, and if clean_val is the empty string, make the clean value a 0
        if type(clean_val) == str and len(clean_val.strip()) == 0 and (num_format == NumFormats.INT or num_format == NumFormats.DOUBLE):
            clean_val   = 0
        
        try:
            worksheet.write(excel_row, excel_col, clean_val, fmt)

        except Exception as ex:
            raise ApodeixiError(parent_trace, "Encountered a problem when writing a cell in Excel",
                                            data = {"problematic val":  str(clean_val),
                                                    "error":            str(ex),
                                                    "layout.name":      str(layout.name),
                                                    "excel row":        str(excel_row),
                                                    "excel column":     str(excel_col)})


    def _populate_worksheet(self, parent_trace, content_df, xlw_config, workbook, worksheet):
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

        @param xlw_config An AsExcel_Config object specifying how the data in `content_df` should be laid out on 
                        the worksheet
        '''
        layout                  = xlw_config.layout
        is_transposed           = layout.is_transposed

        my_trace                = parent_trace.doing("Building out the layout")
        if True:

            displayable_df      = xlw_config.build_displayable_df(parent_trace, content_df, representer=self)

            inner_trace                = parent_trace.doing("Cleaning up numerical columns")
            # If we find blanks in a numerical column, make them 0. This prevents errors when doing formulas,
            # such as a sum over the column, because the formula logic might involve DataFrame sums, and that
            # will error out if Pandas is asked to add a blank (i.e., an empty string) to a number. So turn
            # blanks into 0 for numerical columns
            #
            # GOTCHA: We might have a hybrid situation where some columns are strings and others are tuples
            #           In such cases, Pandas does not work well when doing an assignment via labels, like
            #
            #               displayable_df.loc[row[0], ("Q1 FY22", "Actuals")] = 0
            #
            #   In such situations, Pandas "misbehaves" and adds a new column "Q1 FY22" instead of modifying
            #   the column ("Q1 FY22", "Actuals").
            #   So instead we use iloc, not loc, which is why we need to get the column indices
            for row in displayable_df.iterrows():
                for jdx in range(len(displayable_df.columns)):
                #for col in displayable_df.columns:
                    col                 = displayable_df.columns[jdx]
                    if col in xlw_config.num_formats.keys():
                        num_format      = xlw_config.num_formats[col]
                        if num_format == NumFormats.INT or num_format == NumFormats.DOUBLE:

                            val             = row[1][col]
                            if type(val) == str and len(val.strip()) == 0:
                                #displayable_df.loc[row[0],col] = 0
                                displayable_df.iloc[row[0],jdx] = 0


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

            column_formatters   = NumFormats.xl_to_txt_formatters(xlw_config.num_formats)
            calc                = ColumnWidthCalculator(    data_df             = xl_df, 
                                                            viewport_width      = xlw_config.viewport_width, 
                                                            viewport_height     = xlw_config.viewport_height, 
                                                            max_word_length     = xlw_config.max_word_length,
                                                            column_formatters   = column_formatters)
            
            # Dictionary - keys are columns of displayable_df, vals are sub-dicts {'width': <number>, 'nb_lines': <number>}
            widths_dict         = calc.calc(inner_trace) 

            # Remember these to support debugging
            # The layout.name *must* be the manifest_identifier if we are populating a manifest (as opposed to a posting label)
            name                            = layout.name 
            self.widths_dict_dict[name]     = widths_dict
            self.span_dict[name]            = span
            self.hidden_cols_dict[name]     = xlw_config.hidden_cols

        # Now we start laying out content on the worksheet. 
        # Start by re-sizing the columns.
        my_trace            = parent_trace.doing("Setting column widths")
        if True:            
            xl_columns          = xl_df.columns 
            for xl_idx in range(len(xl_columns)): # GOTCHA: Loop is in "Excel space"
                col             = xl_columns[xl_idx]
                loop_trace      = my_trace.doing("Processing XL column '" + str(col) + "'")
                width           = float(widths_dict[col]['width']) # Cast to float to do float arithmetic in scaling to font size
                if is_transposed:
                    xl_x        = xlw_config.y_offset + xl_idx
                else:
                    xl_x        = xlw_config.x_offset + xl_idx
                self._set_column_width(loop_trace, worksheet, xl_x, width, layout)
   
        # Now populate headers
        my_trace                        = parent_trace.doing("Populating headers", data = {'layout span': str(span)})
        if True:            
            columns                     = displayable_df.columns
            for layout_idx in range(len(columns)): # GOTCHA: Loop is in "Layout space"
                col                     = columns[layout_idx]
                loop_trace              = my_trace.doing("Processing layout column '" + str(col) + "'")
                layout_x                = xlw_config.x_offset + layout_idx
                layout_y                = xlw_config.y_offset 

                excel_row, excel_col, last_excel_row, last_excel_col    = xlw_config.df_xy_2_excel_xy(
                                                                            parent_trace            = parent_trace, 
                                                                            displayable_df          = displayable_df,
                                                                            df_row_number           = -1, # -1 for headers
                                                                            df_col_number           = layout_idx,
                                                                            representer             = self)
                if type(col) == tuple: 
                    # This happens when displayble_df uses a MultiIndex. For example, when estimates data is specific to a subproduct
                    # so get columns like (<subproduct>, "Q1"), (<subproduct>, "Q2"), etc.
                    # In that case we need more than one row for the headers
                    headers             = list(col)
                else:
                    headers             = [col]
                
                for header_jdx in range(len(headers)):
                    col_val             = headers[header_jdx]
                    # If col is not a tuple, then xl_col = excel_col and xl_row = excel_row
                    # Otherwise, xl_row <= excel_row for non-transposed data sets, i.e., we place the multi-level headers
                    # so that the last row they use is excel_row.
                    # For transposed data sets is it similar, but xl_col <= excel_col in that case
                    if is_transposed:
                        xl_row          = excel_row
                        xl_col          = excel_col + header_jdx - len(headers) + 1

                    else:
                        xl_row          = excel_row + header_jdx - len(headers) + 1
                        xl_col          = excel_col
                    self._write_val(        parent_trace        = loop_trace, 
                                            workbook            = workbook, 
                                            worksheet           = worksheet, 
                                            layout_x            = layout_x, 
                                            layout_y            = layout_y, #No change even if col is a tuple, since in layout space columns are a single row, and layout_y is only relevenat for purposes of getting the formatters
                                            excel_row           = xl_row, 
                                            excel_col           = xl_col,
                                            val                 = col_val, 
                                            layout              = layout, 
                                            num_format          = None)
        # Now lay out the content
        my_trace                        = parent_trace.doing("Populating content", data = {'layout span': str(span)})
        if True:
            for layout_idx in range(len(columns)):
                col                     = columns[layout_idx]
                outer_loop_trace        = my_trace.doing("Processing column = '" + str(col) + "'")

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
                
                    loop_trace          = outer_loop_trace.doing("Processing column = '" + str(col) 
                                                                    + "' row = '" + str(row_nb) + "'")
                    layout_x            = xlw_config.x_offset + layout_idx 
                    layout_y            = xlw_config.y_offset + 1 + row_nb # An extra '1' because of the headers
                    excel_row, excel_col, last_excel_row, last_excel_col    = xlw_config.df_xy_2_excel_xy(
                                                                                parent_trace            = loop_trace,
                                                                                displayable_df          = displayable_df, 
                                                                                df_row_number           = row_nb,
                                                                                df_col_number           = layout_idx,
                                                                                representer             = self)

                    # If we have inserted formulas that took space, shift accordingly 
                    if xlw_config.sheet in self.formula_shift_dict.keys():
                        formula_shift   = self.formula_shift_dict[xlw_config.sheet]
                        layout_x        += formula_shift.shift_x
                        layout_y        += formula_shift.shift_y  

                    if first_x == None:
                        first_x         = layout_x
                    if first_y == None:
                        first_y         = layout_y
                 
                    num_format          = None
                    if col in xlw_config.num_formats.keys():
                        num_format      = xlw_config.num_formats[col]

                    val             = row_content[col]


                    self._write_val(    parent_trace        = loop_trace, 
                                        workbook            = workbook, 
                                        worksheet           = worksheet, 
                                        layout_x            = layout_x, 
                                        layout_y            = layout_y, 
                                        excel_row           = excel_row, 
                                        excel_col           = excel_col,
                                        val                 = val, 
                                        layout              = layout, 
                                        num_format          = num_format)

                    # Remember UID -> row mapping, for aligninig other joined manifests later on. But only if there
                    # is a value in the UID column, since we allow the case that it be blank in some rows if
                    # we default it from earlier rows (as when constructing an n-table instead of a b-table: refer
                    # to the AssertionTree documentation)
                    if IntervalUtils().is_a_UID_column(parent_trace, col) and not StringUtils().is_blank(val):

                        # Bug fix: raw_uid might be abbreviated, like "BR10.1". We need to unabbreviate it to
                        # something like "BR10.B1"
                        uid_store       = UID_Store(parent_trace)
                        manifest_info   = self.manifestInfo_dict[xlw_config.manifest_name]

                        manifest_dict   = manifest_info.getManifestDict(parent_trace)
      
                        acronym_schema  = UID_Acronym_Schema()
                        acronym_schema.build_schema_from_manifest(parent_trace, manifest_dict) 
                        uid_store.set_acronym_schema(parent_trace, acronym_schema) 

                        uid_store.initializeFromManifest(my_trace, manifest_dict)
                        raw_uid         = row_content[col]

                        good_uid        = UID_Utils().unabbreviate_uid( parent_trace        = loop_trace, 
                                                                        uid                 = str(raw_uid), 
                                                                        acronym_schema      = acronym_schema)

                        self.link_table.keep_row_last_UID(parent_trace, 
                                                            manifest_identifier     = name, 
                                                            row_nb                  = excel_row, 
                                                            uid                     = good_uid) 

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
                                    config              = xlw_config,
                                    workbook            = workbook,
                                    worksheet           = worksheet)

        # Add any drop downs that where configured
        # If we have drop downs for this column, add them to the worksheet
        my_trace                        = parent_trace.doing("Populating dropdowns", data = {'layout span': str(span)})
        self._add_dropdowns(my_trace, workbook, worksheet, xlw_config, displayable_df)

    def _add_dropdowns(self, parent_trace, workbook, worksheet, xlw_config, displayable_df):
        '''
        '''
        if xlw_config.excel_dropdowns != None:
            for dropdown_params in xlw_config.excel_dropdowns.getAll():
                x_0, y_0, x_1, y_1  = dropdown_params.range_lambda(displayable_df)    

                my_trace            = parent_trace.doing("Adding dropdown list reference sheet for '" 
                                                            + str(dropdown_params.name) + "'")
                if True:
                    # Due to not totally understood reasons, XlsxWriter will error out if we pass a
                    # list bigger than 6 entries as the source of a drop down. What seems to work instead is 
                    # to pass an Excel range of a list that is in Excel itself.
                    #
                    # So what we do is create a worksheet for the "static data" of the dropdown: it is a
                    # sheet where we write out the list we want the dropdown to display.
                    # Then we use the range of that Excel worksheet's data as the specification to XlsxWriter of
                    # the contents of the dropdown list
                    #
                    sheet_name          = dropdown_params.name.replace(" ", "_") # Excel won't allow spaces in data validation reference
                    reference_sheet     = workbook.add_worksheet(name = sheet_name)
                    HEADER              = "Source for dropdown list (generated - don't change it!)"
                    col_width           = max(len(HEADER), max(len(item) for item in dropdown_params.source)) * 1.2
                    xl_col              = 1
                    reference_sheet.set_column(xl_col,      xl_col,       col_width)

                    fmt_dict            = {'bold': True, 'font_color': Palette.WHITE, 'align': 'center', 
                                            'bg_color': Palette.VERY_DARK_GREY}

                    fmt                 = workbook.add_format(fmt_dict)
                    reference_sheet.write(0, xl_col, HEADER, fmt)

                    for idx in range(len(dropdown_params.source)):
                        item            = dropdown_params.source[idx]
                        xl_row          = idx + 1
                        
                        try:
                            reference_sheet.write(xl_row, xl_col, item)
                        except Exception as ex:
                            raise ApodeixiError(parent_trace, "Encountered a problem when writing a drop down list's "
                                                                + " contents as static data in Excel in dedicated worksheet",
                                                            data = {"problematic val":  str(item),
                                                                    "error":            str(ex),
                                                                    "dropdown.name":    str(dropdown_params.name),
                                                                    "excel row":        str(xl_row),
                                                                    "excel column":     str(xl_col)})
                dropdown_source_range   = xl_range_abs( first_row   = 1,
                                                        first_col   = 1,
                                                        last_row    = xl_row, # From last cycle of loop
                                                        last_col    = 1)    
                dropdown_source_range   = reference_sheet.get_name() + "!" + dropdown_source_range           
                    


                my_trace            = parent_trace.doing("Determining dropdown range for '" 
                                                            + str(dropdown_params.name) + "'")
                if True:
                    # We need to compute the first and last Excel row/column that correspond to what in
                    # layout space is the real-estate from (x0, y0) to (y1, y1).
                    #
                    # Unfortunately, we can't reliably just check what Excel coordinates correspond to
                    # the endpoints (x0, y0) and (x1, y1) because in some cases the manifest rows will be re-ordered.
                    #   For example, if this manifest is joined to another one, then its rows will
                    #   re-arrange to keep aligned with the referenced manifest, whose rows might re-sort due to 
                    #   the way UIDs are sorted.
                    #
                    # So we must do this "the hard way": loop through every point in layout space and pick the 
                    # min/max Excel coordinates
                    #
                    excel_row_0     = None # Will be minimized
                    excel_col_0     = None # Will be minimized 

                    excel_row_1     = None # Will be maxmized
                    excel_col_1     = None # Will be maxmized
                    for x in range(x_0, x_1 + 1):
                        for y in range(y_0, y_1 + 1):
                            row, col, last_row, last_col    = xlw_config.df_xy_2_excel_xy(
                                                                            parent_trace            = my_trace,
                                                                            displayable_df          = displayable_df, 
                                                                            df_row_number           = y,
                                                                            df_col_number           = x,
                                                                            representer             = self)
                            # Minimize row
                            if excel_row_0 == None:
                                excel_row_0 = row
                            else:
                                excel_row_0 = min(excel_row_0, row)

                            # Minimize column
                            if excel_col_0 == None:
                                excel_col_0 = col
                            else:
                                excel_col_0 = min(excel_col_0, col)

                            # Maximise row
                            if excel_row_1 == None:
                                excel_row_1 = row
                            else:
                                excel_row_1 = max(excel_row_1, row)  

                            # Maximize column
                            if excel_col_1 == None:
                                excel_col_1 = col
                            else:
                                excel_col_1 = max(excel_col_1, col)                          

                    '''
                    excel_row_0, excel_col_0, last_excel_row, last_excel_col    = xlw_config.df_xy_2_excel_xy(
                                                                            parent_trace            = my_trace,
                                                                            displayable_df          = displayable_df, 
                                                                            df_row_number           = y_0,
                                                                            df_col_number           = x_0,
                                                                            representer             = self)

                    excel_row_1, excel_col_1, last_excel_row, last_excel_col    = xlw_config.df_xy_2_excel_xy(
                                                                            parent_trace            = my_trace,
                                                                            displayable_df          = displayable_df, 
                                                                            df_row_number           = y_1,
                                                                            df_col_number           = x_1,
                                                                            representer             = self)
                    if xlw_config.layout.is_transposed == False and y_1 == len(displayable_df.index) -1:
                    
                        # GOTCHA
                        #   We are supposed to add the dropdown to all rows in Excel that show displayable_df, 
                        #   but we can't rely on the excel_col_1 computed above.
                        #   Reason: Excel rows may not be ordered the same way as the displayable_df rows they correspond to.
                        #   For example, if this manifest is joined to another one, then its rows will
                        #   re-arrange to keep aligned with the referenced manifest, whose rows might re-sort due to 
                        #   the way UIDs are sorted.
                        # That means that the last row in displayble_df might not be displayed at the last row in Excel,
                        # so we would rather take the last_row_excel as the row to use
                        excel_row_1         = last_excel_row
                    '''

                my_trace            = parent_trace.doing("Adding dropdown '" + str(dropdown_params.name) + "'",
                                                            data = {"first Excel row": str(excel_row_0),
                                                                    "last Excel row": str(excel_row_1),
                                                                    "first Excel col": str(excel_col_0),
                                                                    "last Excel col": str(excel_col_1),})
                if True:
                    status          = worksheet.data_validation(  
                                            first_row       = excel_row_0, 
                                            first_col       = excel_col_0, 
                                            last_row        = excel_row_1, 
                                            last_col        = excel_col_1, 
                                            options         = { 'validate':    'list',
                                                                'source':       "=" + dropdown_source_range})
                                                                #'source':       dropdown_params.source})
                    if status != 0:
                        raise ApodeixiError(my_trace, "Unable to add dropdown because the XlxsWriter library returned status="
                                                        + str(status))

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

                # Fix on March, 2022: turns out that some humans put things like "?" in numerical columns
                # in Excel, then post to a manifest. So when we get here we may get an exception if some
                # entry in data_df[column] is not a number. So fix that by avoiding
                #           
                #           total = data_df[column].sum()
                #
                # and instead adding a temporary copy of that column that "ignores" non-numbers (exclude them
                # from sum)
                tmp_series              = _pd.to_numeric(data_df[column], errors='coerce')
                tmp_series              = tmp_series.fillna(0)

                total                   = tmp_series.sum()
                column_formatters       = NumFormats.xl_to_txt_formatters(config.num_formats)
                if column in column_formatters.keys():
                    formatter           = column_formatters[column]
                    total_txt           = formatter(my_trace, total)
                else:
                    total_txt           = str(total)
                
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
                try:
                    cumsum_df               = data_df[column].cumsum().to_frame()
                except Exception as ex:
                    raise ApodeixiError(my_trace, "Encountered problem summing the values in a DataFrame column while "
                                                + "adding a cumulative sum formula in Excel",
                                                    data = {"column": str(column),
                                                            "error":    str(ex)})

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
        
        # Within the global area, unprotect any empty space not in any layout (e.g., if pasting multiple
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

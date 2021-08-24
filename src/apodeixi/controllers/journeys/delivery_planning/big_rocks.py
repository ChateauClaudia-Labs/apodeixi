import pandas                                                               as _pd

from apodeixi.util.a6i_error                                                import ApodeixiError
from apodeixi.util.formatting_utils                                         import StringUtils

from apodeixi.controllers.util.skeleton_controller                          import SkeletonController
from apodeixi.controllers.journeys.delivery_planning.journeys_posting_label  import JourneysPostingLabel
from apodeixi.controllers.journeys.delivery_planning.journeys_controller     import JourneysController

from apodeixi.text_layout.excel_layout                                      import AsExcel_Config_Table, \
                                                                                ManifestXLWriteConfig, \
                                                                                JoinedManifestXLWriteConfig, \
                                                                                NumFormats, ExcelFormulas

from apodeixi.xli.interval                                                  import IntervalUtils, GreedyIntervalSpec, \
                                                                                MinimalistIntervalSpec, Interval
from apodeixi.xli.posting_controller_utils                                  import PostingConfig, UpdatePolicy

class BigRocksEstimate_Controller(JourneysController):
    '''
    Class to process an Excel posting for big rocks estimates. It produces three YAML manifests:
    
    * One for the big rocks
    * One for the effort estimates
    * One for the investment promised

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)

        self.SUPPORTED_VERSIONS         = ['v1a']

        # GOTCHA: 
        # These must be listed in the order in which they are later processed in _build_manifestsXLWriteconfig
        # For example, since _build_manifestsXLWriteconfig assumes a key like 'big-rock.0', we must have
        # 'big-rock' as the first member of the list. 
        # Otherwise, self.generateForm(-) might fail for a blind form request because when it searches for manifests,
        # it doe so by kind in the order they appear here, and imputs a key like "big-rock.0" based on the order
        # here, and that key is later assumed in the _build_manifestsXLWriteconfig. If instead we put big-rock second end
        # of the list, the key would be 'big-rock.1' and _build_manifestsXLWriteconfig would error out as an
        # unrecognized key
        self.SUPPORTED_KINDS            = ['big-rock', 'big-rock-estimate', 'investment']

        self.variant                    = None # When reading the label it will be set to VARIANT_BURNOUT or VARIANT_EXPLAINED

    VARIANT_BURNOUT                     = "burnout"
    VARIANT_EXPLAINED                   = "explained"

    def getSupportedVersions(self):
        return self.SUPPORTED_VERSIONS 

    def getSupportedKinds(self):
        return self.SUPPORTED_KINDS

    def getPostingConfig(self, parent_trace, kind, manifest_nb):
        '''
        Return a PostingConfig, corresponding to the configuration that this concrete controller supports.
        '''
        ME                          = BigRocksEstimate_Controller
        if kind == 'big-rock':
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = ME._BigRocksConfig(           kind            = kind, 
                                                                        update_policy   = update_policy,
                                                                        manifest_nb     = manifest_nb, 
                                                                        controller      = self)
        elif kind == 'big-rock-estimate':
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
            xlr_config                  = ME._BigRocksEstimatesConfig(  kind            = kind, 
                                                                        update_policy   = update_policy, 
                                                                        manifest_nb     = manifest_nb,
                                                                        controller      = self)
        elif kind == 'investment':
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
            xlr_config                  = ME._InvestmentConfig(         kind            = kind, 
                                                                        update_policy   = update_policy, 
                                                                        manifest_nb     = manifest_nb,
                                                                        controller      = self)
        else:
            raise ApodeixiError(parent_trace, "Invalid domain object '" + kind + "' - should be one of "
                                                + ", ".join(self.SUPPORTED_KINDS),
                                                origination = {'signaled_from': __file__})

        return xlr_config 

    def getPostingLabel(self, parent_trace):
        '''
        Returns a PostingLabel, corresponding to the what is expected by this concrete controller class.
        '''
        ME                              = BigRocksEstimate_Controller
        return ME._MyPostingLabel(parent_trace, controller = self)

    def _build_manifestsXLWriteconfig(self, parent_trace, manifestInfo_dict):
        '''
        Overwrites parent's implementation

        Creates and returns an AsExcel_Config_Table containing the configuration data for how to lay out and format
        all the manifests of `manifestInfo_dict` onto an Excel spreadsheet
        '''
        ME                                  = BigRocksEstimate_Controller
        xlw_config_table                    = AsExcel_Config_Table()
        x_offset                            = 1
        y_offset                            = 1
        for key in manifestInfo_dict:
            loop_trace                      = parent_trace.doing("Creating layout configurations for manifest '"
                                                                + str(key) + "'")
            manifest_info                   = manifestInfo_dict[key]
            data_df                         = manifest_info.getManifestContents(parent_trace)
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            if key == 'big-rock.0':
                hidden_cols                 = []
                right_margin                = 0
                num_formats                 = {}
                excel_formulas              = None
                df_xy_2_excel_xy_mapper   = None
                xlw_config  = ManifestXLWriteConfig(sheet                   = SkeletonController.GENERATED_FORM_WORKSHEET,
                                                manifest_name               = key, 
                                                read_only                   = False,
                                                is_transposed               = False,    
                                                viewport_width              = 100,  
                                                viewport_height             = 40,   
                                                max_word_length             = 20, 
                                                editable_cols               = editable_cols,
                                                hidden_cols                 = hidden_cols,  
                                                num_formats                 = num_formats, 
                                                excel_formulas              = excel_formulas,
                                                df_xy_2_excel_xy_mapper   = df_xy_2_excel_xy_mapper,
                                                editable_headers            = [],   
                                                x_offset                    = x_offset,    
                                                y_offset                    = y_offset)
            elif key == 'big-rock-estimate.1':
                # Want the estimates to be displayed in the same row as the big rocks they estimate. So we need to
                # make a join, and pass the mapper that effects this associate
                def my_mapper(manifest_df, manifest_df_row_number, representer):
                    big_rock_uid        = manifest_df['bigRock'].iloc[manifest_df_row_number]      
                    link_table          = representer.link_table # Data structure that has join information
                    excel_row_nb        = link_table.row_from_uid(  parent_trace        = loop_trace, 
                                                                    manifest_identifier = 'big-rock.0', 
                                                                    uid                 = big_rock_uid)
                    if excel_row_nb == None:
                        raise ApodeixiError(loop_trace, "Unable to link big-rock-estimate referencing big-rock '"
                                                + str(big_rock_uid) + "': that big rock was not listed in the links",
                                            data = {"Known big-rock links": str(link_table.all_uids(loop_trace, 'big-rock.0'))})
                    final_excel_row     = link_table.last_row_number(   parent_trace        = loop_trace,
                                                                        manifest_identifier = 'big-rock.0')
                    return excel_row_nb, final_excel_row
                df_xy_2_excel_xy_mapper   = my_mapper  

                if self.variant ==  ME.VARIANT_BURNOUT:
                    hidden_cols             = ['UID', 'bigRock']
                    right_margin            = 1                    
                    num_formats             = {'effort': NumFormats.INT}
                    excel_formulas          = ExcelFormulas(key)
                    excel_formulas.addTotal(loop_trace, column = "effort", 
                                                        parameters = {ExcelFormulas.COLUMN_TOTAL.INCLUDE_LABEL: True})
                elif self.variant ==  ME.VARIANT_EXPLAINED:
                    hidden_cols             = ['UID', 'bigRock', 'effort']
                    right_margin            = 1      
                    estimate_cols           = [col for col in editable_cols if not col in hidden_cols] 
                    num_formats             = {} 
                    excel_formulas          = ExcelFormulas(key)
                    for col in estimate_cols:
                        num_formats[col]    = NumFormats.INT          
                        excel_formulas.addTotal(loop_trace, column = col,
                                                            parameters = {ExcelFormulas.COLUMN_TOTAL.INCLUDE_LABEL: False})
                else:
                    raise ApodeixiError(loop_trace, "Can't format Excel for '" + key + "' because variant is unsupported",
                                            data = {"variant given":        str(self.variant),
                                                    "supported variants": str([ME.VARIANT_BURNOUT, ME.VARIANT_EXPLAINED])})
                xlw_config  = JoinedManifestXLWriteConfig(sheet             = SkeletonController.GENERATED_FORM_WORKSHEET,
                                                manifest_name               = key, 
                                                read_only                   = False,
                                                referenced_manifest_name    = 'big-rock.0',
                                                is_transposed               = False,    
                                                viewport_width              = 100,  
                                                viewport_height             = 40,   
                                                max_word_length             = 20, 
                                                editable_cols               = editable_cols,
                                                hidden_cols                 = hidden_cols,  
                                                num_formats                 = num_formats, 
                                                excel_formulas              = excel_formulas,
                                                df_xy_2_excel_xy_mapper   = df_xy_2_excel_xy_mapper,
                                                editable_headers            = [],   
                                                x_offset                    = x_offset,    
                                                y_offset                    = y_offset)
            elif key == 'investment.2':
                hidden_cols                 = ['UID']
                right_margin                = 1

                num_formats                 = {'Incremental': NumFormats.INT}
                excel_formulas              = ExcelFormulas(key)
                excel_formulas.addCumulativeSum(parent_trace, 'Incremental')
                df_xy_2_excel_xy_mapper   = None
                xlw_config  = ManifestXLWriteConfig(sheet                   = SkeletonController.GENERATED_FORM_WORKSHEET,
                                                manifest_name               = key, 
                                                read_only                   = False,
                                                is_transposed               = False,    
                                                viewport_width              = 100,  
                                                viewport_height             = 40,   
                                                max_word_length             = 20, 
                                                editable_cols               = editable_cols,
                                                hidden_cols                 = hidden_cols,  
                                                num_formats                 = num_formats, 
                                                excel_formulas              = excel_formulas,
                                                df_xy_2_excel_xy_mapper   = df_xy_2_excel_xy_mapper,
                                                editable_headers            = [],   
                                                x_offset                    = x_offset,    
                                                y_offset                    = y_offset)
            else:
                raise ApodeixiError(loop_trace, "Invalid manifest key: '" + str(key) + "'")

            # Put next manifest to the right of this one, separated by an empty column
            x_offset                        += data_df.shape[1] -len(hidden_cols) + right_margin
            xlw_config_table.addManifestXLWriteConfig(loop_trace, xlw_config)
        return xlw_config_table

    def _buildAllManifests(self, parent_trace, posting_label_handle):

        all_manifests_dict, label       = super()._buildAllManifests(parent_trace, posting_label_handle)

        # Link effort entities of big-rock-estimate manifest to the big rock they correspond to
        bre_manifest_nb                 = self.manifest_nb_from_kind(parent_trace, 'big-rock-estimate')
        bre_manifest_dict               = all_manifests_dict[bre_manifest_nb]
        self.linkReferenceManifest(parent_trace, bre_manifest_dict,     entity      = 'effort', 
                                                                        linkField   = 'bigRock', 
                                                                        refKind     = 'big-rock',
                                                                        many_to_one = False)
        return all_manifests_dict, label

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, posting_data_handle, label)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to BigRocksEstimate_Controller") 

        plan_type                       = label.plan_type           (my_trace)
        variant                         = label.variant             (my_trace)
        
        my_trace                        = parent_trace.doing("Enriching generic manifest fields with additional fields "
                                                                + "specific to BigRocksEstimate_Controller")
        
        if True:
            metadata                                    = manifest_dict['metadata']

            MY_PL                                       = BigRocksEstimate_Controller._MyPostingLabel # Abbreviation for readability
            labels                                      = metadata['labels']
            labels[MY_PL._PLAN_TYPE]                    = plan_type
            labels[MY_PL._VARIANT]                      = variant

            assertion                                   = manifest_dict['assertion']

            assertion[MY_PL._PLAN_TYPE]                 = plan_type
            assertion[MY_PL._VARIANT]                   = variant
        
        return manifest_dict


    class _BigRocksConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for big rocks (potentially broken into subrocks, sub-subrocks, etc.)
        '''

        _ENTITY_NAME                    = 'Big Rock'

        def __init__(self, kind, manifest_nb, update_policy, controller):
            ME                          = BigRocksEstimate_Controller._BigRocksConfig
            super().__init__(   kind                = kind, 
                                update_policy       = update_policy, 
                                manifest_nb         = manifest_nb,
                                controller          = controller)
        
            interval_spec_big_rocks     = MinimalistIntervalSpec(  parent_trace        = None, 
                                                                    entity_name         = ME._ENTITY_NAME
                                                                    )

            self.interval_spec          = interval_spec_big_rocks

        def entity_as_yaml_fieldname(self):
            ME                          = BigRocksEstimate_Controller._BigRocksConfig
            return StringUtils().format_as_yaml_fieldname(ME._ENTITY_NAME)

        def preflightPostingValidation(self, parent_trace, posted_content_df):
            '''
            Method performs some initial validation of the `dataframe`, which is intended to be a DataFrame representation of the
            data posted in Excel.

            The intention for this preflight validation is to provide the user with more user-friendly error messages that
            educate the user on what he/she should change in the posting for it to be valid. In the absence of this 
            preflight validation, the posting error from the user would eventually be caught deeper in the parsing logic,
            by which time the error generated might not be too user friendly.

            Thus this method is not so much to avoid corruption of the data, since downstream logic will prevent corruption
            anyway. Rather, it is to provide usability by outputting high-level user-meaningful error messages.
            '''
            ME                              = BigRocksEstimate_Controller._BigRocksConfig

            # GOTCHA: A mandatory column like "Big Rocks" might become "big-rocks" after the first posting, i.e.,
            #           the generated form used for updates will have a column called "big-rocks", not "Big Rocks".
            #           To avoid erroring out when the situation is rather innocent, the check below does
            #           not compare "raw column names", but "formatted columns names" using a formatter that
            #           converts things like "Big Rocks" to "big-rocks"
            FMT                                         = StringUtils().format_as_yaml_fieldname # Abbreviation for readability

            posted_cols                     = [FMT(col) for col in posted_content_df.columns]
            mandatory_cols                  = [FMT(ME._ENTITY_NAME)]
            missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns. This often happens if "
                                                    + "ranges are wrong in Posting Label.",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})
        def entity_name(self):
            ME                      = BigRocksEstimate_Controller._BigRocksConfig
            return ME._ENTITY_NAME

    class _BigRocksEstimatesConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for big rock estimates
        '''

        _ENTITY_NAME                            = 'Effort'

        def __init__(self, kind, manifest_nb, update_policy, controller):
            ME                                  = BigRocksEstimate_Controller._BigRocksEstimatesConfig

            super().__init__(   kind            = kind, 
                                update_policy   = update_policy, 
                                manifest_nb     = manifest_nb,
                                controller      = controller)

            
            interval_spec_big_rocks_estimates   = GreedyIntervalSpec(parent_trace = None) 

            self.interval_spec                  = interval_spec_big_rocks_estimates

        def entity_as_yaml_fieldname(self):
            ME                          = BigRocksEstimate_Controller._BigRocksEstimatesConfig
            return StringUtils().format_as_yaml_fieldname(ME._ENTITY_NAME)

        def preflightPostingValidation(self, parent_trace, posted_content_df):
            '''
            Method performs some initial validation of the `dataframe`, which is intended to be a DataFrame representation of the
            data posted in Excel.

            The intention for this preflight validation is to provide the user with more user-friendly error messages that
            educate the user on what he/she should change in the posting for it to be valid. In the absence of this 
            preflight validation, the posting error from the user would eventually be caught deeper in the parsing logic,
            by which time the error generated might not be too user friendly.

            Thus this method is not so much to avoid corruption of the data, since downstream logic will prevent corruption
            anyway. Rather, it is to provide usability by outputting high-level user-meaningful error messages.
            '''
            ME                              = BigRocksEstimate_Controller._BigRocksEstimatesConfig
            CTRL                            = BigRocksEstimate_Controller

            # GOTCHA: A mandatory column like "Effort" might become "effort" after the first posting, i.e.,
            #           the generated form used for updates will have a column called "effort", not "Effort".
            #           To avoid erroring out when the situation is rather innocent, the check below does
            #           not compare "raw column names", but "formatted columns names" using a formatter that
            #           converts things like "Effort" to "effort"
            FMT                                         = StringUtils().format_as_yaml_fieldname # Abbreviation for readability

            if self.controller.variant == CTRL.VARIANT_BURNOUT: # In this case we need an "effort" column
                posted_cols                     = [FMT(col) for col in posted_content_df.columns]
                mandatory_cols                  = [FMT(ME._ENTITY_NAME)]
                missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
                if len(missing_cols) > 0:
                    raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns. Are you sure your "
                                                        + "'data.range.n' settings in the PostingLabel are correctly "
                                                        + " describing the real estate for the various data sets?"
                                                        + " (that is a common cause for this problem - for example, "
                                                        + " the range for the effort dataset should start where you "
                                                        + " positioned the effort column)",
                                                        data = {    'Missing columns':    missing_cols,
                                                                    'Posted columns':     posted_cols})

        def preprocessReadFragment(self, parent_trace, interval, dataframe_row):
            '''
            This is called by the BreakdownTree's readDataframeFragment method before attempting to parse a fragment
            from a row in a DataFrame.

            This method is offered as a "hook" to derived classes in case they want to "enrich" the input to the parser,
            by overwriting this method with the appropriate "enriching" logic.

            It returns "improved" versions of the `interval` and `dataframe_row` parameters.

            An example of where such "enriching" functionality is needed:
            some posting APIs choose to present the users with an Excel template that hides some information
            from the user. An example is the API for posting big rocks estimates: the "Effort" column is not included
            in the Excel spreadsheet in cases where the user chose the "explained" variant, since in that case the "Effort"
            is "implied" from the entries at multiple time buckets. Such examples make the Excel spreadsheet more user
            friendly but cause a side-effect problem for the parser: if it does not see a column like "Effort" in the
            row, which is mandatory since it is the "entity" for that row, the parser would raise an error. To address 
            this, the concrete PostingConfig class for the big rocks controller can take advantage of this method
            and implement it to "enrich" the `dataframe_row` with a synthetic "Effort" property that was not present 
            in the Excel input provided by the user.

            @param interval         An Interval object, corresponding to the columns in `row` that pertain to an entity being 
                                    processed in readDataframeFragment
            @param dataframe_row    A tuple `(idx, series)` representing a row in a larger Pandas Dataframe as yielded by
                                    the Dataframe `iterrows()` iterator.
            @returns                A pair: 1) an Interval object, and 2) tuple `(idx, series)` that may pass for a Pandas row
            '''
            CTRL                            = BigRocksEstimate_Controller
            ME                              = BigRocksEstimate_Controller._BigRocksEstimatesConfig

            # We will only enrich if the user provided some data at all - otherwise there is nothing to do
            non_blank_cols                  = [col for col in interval.columns \
                                                    if not IntervalUtils().is_blank(dataframe_row[1][col])]
            if self.controller.variant ==  CTRL.VARIANT_EXPLAINED and len(non_blank_cols) > 0:
                # Force the row to have a column called "Effort"
                enrichment                  = _pd.Series(["DERIVED"], index=[ME._ENTITY_NAME])
                row_nb                      = dataframe_row[0]
                row_series                  = dataframe_row[1]

                # The enriched row and interval must be consistent with regards to the columns. So make
                # sure the first column is the entity being added as an enrichment, followed by the
                # columns of the input dataframe_row, in that order. Same for the interval
                enriched_series             = enrichment.append(row_series)
                enriched_interval_columns   = [ME._ENTITY_NAME]
                enriched_interval_columns.extend(interval.columns)
                enriched_interval           = Interval( parent_trace        = parent_trace, 
                                                        columns             = enriched_interval_columns, 
                                                        entity_name         = ME._ENTITY_NAME)

                # Make sure to return a tuple for the row, not a list, to make it look like a Pandas row
                enriched_row                = (row_nb, enriched_series) 

                return enriched_interval, enriched_row
            else:
                return interval, dataframe_row

        def cleanFragmentValue(self, parent_trace, field_name, raw_value, data_series):
            '''
            Inherited from parent class, and enriched with additional behavior.

            Method to "clean up" a value read from a Pandas DataFrame just before it is inserted into
            the parsed tree created by the BreakdownTree's readDataframeFragment method.

            For example, a Pandas DataFrame may put some "garbage values" like nan, NaT, etc. That will later
            cause problems in the YAML created to represent manifests. In such cases, this method simply
            "cleans up the value" and replaces it with an appropriate default. For nan, that would be an empty string.

            Derived classes can overwrite this method and do additional "cleaning up". For example, a concrete
            class may know that the field in question represents a number, so may decide to replace any empty string
            by 0. Such "cleaning up" is important if later other processing code will attempt to do arithmetic on such
            values on the assumption that they are numbers - encountering an empty string will likely cause such code to
            error out. Better to pre-empt such situations by cleaning up the values at source, at the moment right before
            they are inserted into the BreakdownTree from which the manifest will later be built.

            @field_name A string, representing a column name of the DataFrame being processed. This is the column
                        where the val came from, and provides a hint to implementing code on how such a value should
                        be "cleaned up". For example, for columns of numbers an empty string should be replaced by a 0.
            @raw_value A datum, representing a particular cell value in the DataFrame being processed.
            @data_series A Pandas Series representing a "row" in a DataFrame from where the val came from.
            '''
            cleaned_val             = super().cleanFragmentValue(parent_trace, field_name, raw_value, data_series)

            # For the big rocks estimates, all columns are numbers (except for "special" columns like UID
            # or "effort", which are not passed to this method for cleaning up).
            # If any of this should-be-numbers value was missing in the Excel spreadsheet 
            # submitted by the user, chances are that Pandas made it an nan or something bad like that, 
            # and the parent class's method applied default cleaning logic, turning into an empty string. 
            # But here in this concrete class we know better, so so if that happened, replace '' by 0
            if cleaned_val == '':
                result_val = 0
            else:
                result_val = cleaned_val

            return result_val

        def entity_name(self):
            ME                      = BigRocksEstimate_Controller._BigRocksEstimatesConfig
            return ME._ENTITY_NAME

    class _InvestmentConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for big rock estimates and investment manifests
        '''

        _ENTITY_NAME                = 'Period'

        def __init__(self, kind, manifest_nb, update_policy, controller):
            ME                      = BigRocksEstimate_Controller._InvestmentConfig
            super().__init__(   kind                = kind, 
                                update_policy       = update_policy, 
                                manifest_nb         = manifest_nb,
                                controller          = controller)

            interval_spec_period    = GreedyIntervalSpec(None) 

            self.interval_spec      = interval_spec_period

        def entity_as_yaml_fieldname(self):
            ME                          = BigRocksEstimate_Controller._InvestmentConfig
            return StringUtils().format_as_yaml_fieldname(ME._ENTITY_NAME)

        def preflightPostingValidation(self, parent_trace, posted_content_df):
            '''
            Method performs some initial validation of the `dataframe`, which is intended to be a DataFrame representation of the
            data posted in Excel.

            The intention for this preflight validation is to provide the user with more user-friendly error messages that
            educate the user on what he/she should change in the posting for it to be valid. In the absence of this 
            preflight validation, the posting error from the user would eventually be caught deeper in the parsing logic,
            by which time the error generated might not be too user friendly.

            Thus this method is not so much to avoid corruption of the data, since downstream logic will prevent corruption
            anyway. Rather, it is to provide usability by outputting high-level user-meaningful error messages.
            '''
            ME                              = BigRocksEstimate_Controller._InvestmentConfig

            # GOTCHA: A mandatory column like "Period" might become "period" after the first posting, i.e.,
            #           the generated form used for updates will have a column called "period", not "Period".
            #           To avoid erroring out when the situation is rather innocent, the check below does
            #           not compare "raw column names", but "formatted columns names" using a formatter that
            #           converts things like "Period" to "period"
            FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability

            posted_cols                     = [FMT(col) for col in posted_content_df.columns]
            mandatory_cols                  = [FMT(ME._ENTITY_NAME)]
            missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns. This often happens if "
                                                    + "ranges are wrong in Posting Label.",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})

        def entity_name(self):
            ME                      = BigRocksEstimate_Controller._InvestmentConfig
            return ME._ENTITY_NAME

        def cleanFragmentValue(self, parent_trace, field_name, raw_value, data_series):
            '''
            Inherited from parent class, and enriched with additional behavior.

            Method to "clean up" a value read from a Pandas DataFrame just before it is inserted into
            the parsed tree created by the BreakdownTree's readDataframeFragment method.

            For example, a Pandas DataFrame may put some "garbage values" like nan, NaT, etc. That will later
            cause problems in the YAML created to represent manifests. In such cases, this method simply
            "cleans up the value" and replaces it with an appropriate default. For nan, that would be an empty string.

            Derived classes can overwrite this method and do additional "cleaning up". For example, a concrete
            class may know that the field in question represents a number, so may decide to replace any empty string
            by 0. Such "cleaning up" is important if later other processing code will attempt to do arithmetic on such
            values on the assumption that they are numbers - encountering an empty string will likely cause such code to
            error out. Better to pre-empt such situations by cleaning up the values at source, at the moment right before
            they are inserted into the BreakdownTree from which the manifest will later be built.

            @field_name A string, representing a column name of the DataFrame being processed. This is the column
                        where the val came from, and provides a hint to implementing code on how such a value should
                        be "cleaned up". For example, for columns of numbers an empty string should be replaced by a 0.
            @raw_value A datum, representing a particular cell value in the DataFrame being processed.
            @data_series A Pandas Series representing a "row" in a DataFrame from where the val came from.
            '''
            cleaned_val             = super().cleanFragmentValue(parent_trace, field_name, raw_value, data_series)

            # For the investment postings, all columns are numbers (except for "special" columns like UID
            # or "Period", which are not passed to this method for cleaning up).
            # If any of this should-be-numbers value was missing in the Excel spreadsheet 
            # submitted by the user, chances are that Pandas made it an nan or something bad like that, 
            # and the parent class's method applied default cleaning logic, turning into an empty string. 
            # But here in this concrete class we know better, so so if that happened, replace '' by 0
            if cleaned_val == '':
                result_val = 0
            else:
                result_val = cleaned_val

            return result_val

    class _MyPostingLabel(JourneysPostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting big rocks estimates. 
        '''
        _PLAN_TYPE                  = "planType"
        _VARIANT                    = "variant"

        def __init__(self, parent_trace, controller):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,

                                mandatory_fields    = [ ME._PLAN_TYPE,      ME._VARIANT],
                                optional_fields     = [],
                                date_fields         = [])

        def read(self, parent_trace, posting_label_handle):
            '''
            '''
            super().read(parent_trace, posting_label_handle)

            # Remember the variant so that later on we can consult it when intializing the posting config objects
            CTRL                        = BigRocksEstimate_Controller
            variant                     = self.variant(parent_trace)
            if variant != CTRL.VARIANT_BURNOUT and variant != CTRL.VARIANT_EXPLAINED:
                raise ApodeixiError(parent_trace, "Variant in Posting Label has an unsupported value: '" + str(variant) + "'",
                                    data = {"supported variants": str([CTRL.VARIANT_BURNOUT, CTRL.VARIANT_EXPLAINED])})
            self.controller.variant     = variant

        def  checkReferentialIntegrity(self, parent_trace):
            '''
            Used to check that the values of Posting Label fields are valid. Does not return a value, but will
            raise an exception if any field is "invalid".

            Sometimes this validation might be against data configured in the ApodeixiConfig. Example: "organization"

            In other situations the validation is against the existence of static data objects which the label
            references. Example: "product" in the case of the Journeys domain.

            NOTE: This method is intended to be called *after* label.read(-) has completed, including any label.read(-)
            implemented by derived classes. 
            That is why it can't be called within label.read(-) at the PostingLabel parent class level,
            and why the design choice was made to have the calling code invoke this check right after calling label.read()
            '''
            super().checkReferentialIntegrity(parent_trace)

        def infer(self, parent_trace, manifest_dict, manifest_key):
            '''
            Used in the context of generating a form to build the posting label information that should be
            embedded in the generated form.

            Accomplishes this by extracting the necesssary information from the manifest given by the `manifest_dict`

            Returns a list of the fields that may be editable

            @param manifest_dict A dict object containing the information of a manifest (such as obtained after loading
                                a manifest YAML file into a dict)
            @param manifest_key A string that identifies this manifest among others. For example, "big-rock.0". Typically
                        it should be in the format <kind>.<number>
            '''
            editable_fields     = super().infer(parent_trace, manifest_dict, manifest_key)

            ME = BigRocksEstimate_Controller._MyPostingLabel
            def _infer(fieldname, path_list):
                self._inferField(   parent_trace            = parent_trace, 
                                    fieldname               = fieldname, 
                                    path_list               = path_list, 
                                    manifest_dict           = manifest_dict)

            _infer(ME._PLAN_TYPE,           ["assertion",                   ME._PLAN_TYPE           ])
            _infer(ME._VARIANT,             ["assertion",                   ME._VARIANT             ])

            self.controller.variant     = self.variant(parent_trace)
            return editable_fields

        def plan_type(self, parent_trace):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._PLAN_TYPE)

        def variant(self, parent_trace):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._VARIANT)


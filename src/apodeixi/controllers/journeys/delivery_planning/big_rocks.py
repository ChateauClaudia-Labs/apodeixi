import pandas                                       as _pd

from apodeixi.controllers.util.manifest_api         import ManifestAPI
from apodeixi.util.a6i_error                        import ApodeixiError
from apodeixi.util.formatting_utils                 import StringUtils

from apodeixi.controllers.util.skeleton_controller  import SkeletonController
from apodeixi.knowledge_base.filing_coordinates     import JourneysFilingCoordinates
from apodeixi.text_layout.excel_layout              import AsExcel_Config_Table, ManifestXLConfig, NumFormats, ExcelFormulas

from apodeixi.xli.interval                          import IntervalUtils, GreedyIntervalSpec, MinimalistIntervalSpec, \
                                                            Interval
from apodeixi.xli.posting_controller_utils          import PostingConfig, PostingController, UpdatePolicy

class BigRocksEstimate_Controller(SkeletonController):
    '''
    Class to process an Excel posting for big rocks estimates. It produces three YAML manifests:
    
    * One for the big rocks
    * One for the effort estimates
    * One for the investment promised

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    '''
    def __init__(self, parent_trace, store):
        super().__init__(parent_trace, store)

        self.MANIFEST_API = ManifestAPI(    parent_trace    = parent_trace,
                                            subdomain       = 'delivery-planning', 
                                            domain          = 'journeys', 
                                            api_publisher   = 'a6i',
                                            extension       = 'io')
        self.SUPPORTED_VERSIONS         = ['v1a']
        self.SUPPORTED_KINDS            = ['big-rock-estimate', 'investment', 'big-rock']

        self.variant                    = None # When reading the label it will be set to VARIANT_BURNOUT or VARIANT_EXPLAINED

    VARIANT_BURNOUT                     = "burnout"
    VARIANT_EXPLAINED                   = "explained"

    def getManifestAPI(self):
        return self.MANIFEST_API

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
            config                      = ME._BigRocksConfig(           kind            = kind, 
                                                                        update_policy   = update_policy,
                                                                        manifest_nb     = manifest_nb, 
                                                                        controller      = self)
        elif kind == 'big-rock-estimate':
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
            config                      = ME._BigRocksEstimatesConfig(  kind            = kind, 
                                                                        update_policy   = update_policy, 
                                                                        manifest_nb     = manifest_nb,
                                                                        controller      = self)
        elif kind == 'investment':
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
            config                      = ME._InvestmentConfig(         kind            = kind, 
                                                                        update_policy   = update_policy, 
                                                                        manifest_nb     = manifest_nb,
                                                                        controller      = self)
        else:
            raise ApodeixiError(parent_trace, "Invalid domain object '" + kind + "' - should be one of "
                                                + ", ".join(self.SUPPORTED_KINDS),
                                                origination = {'signaled_from': __file__})

        return config 

    def getPostingLabel(self, parent_trace):
        '''
        Returns a PostingLabel, corresponding to the what is expected by this concrete controller class.
        '''
        ME                              = BigRocksEstimate_Controller
        return ME._MyPostingLabel(parent_trace, controller = self)

    def _build_manifestsXLconfig(self, parent_trace, manifestInfo_dict):
        '''
        Overwrites parent's implementation

        Creates and returns an AsExcel_Config_Table containing the configuration data for how to lay out and format
        all the manifests of `manifestInfo_dict` onto an Excel spreadsheet
        '''
        ME                                  = BigRocksEstimate_Controller
        config_table                        = AsExcel_Config_Table()
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
                df_row_2_excel_row_mapper   = None
            elif key == 'big-rock-estimate.1':
                # Want the estimates to be displayed in the same row as the big rocks they estimate. So we need to
                # make a join, and pass the mapper that effects this associate
                def my_mapper(manifest_df, manifest_df_row_number, representer):
                    big_rock_uid        = manifest_df['bigRock'].iloc[manifest_df_row_number]      
                    link_table          = representer.link_table # Data structure that has join information
                    excel_row_nb        = link_table.row_from_uid(  parent_trace        = loop_trace, 
                                                                    manifest_identifier = 'big-rock.0', 
                                                                    uid                 = big_rock_uid)
                    final_excel_row     = link_table.last_row_number(   parent_trace        = loop_trace,
                                                                        manifest_identifier = 'big-rock.0')
                    return excel_row_nb, final_excel_row
                df_row_2_excel_row_mapper   = my_mapper  

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

            elif key == 'investment.2':
                hidden_cols                 = ['UID']
                right_margin                = 1

                num_formats                 = {'Incremental': NumFormats.INT}
                excel_formulas              = ExcelFormulas(key)
                excel_formulas.addCumulativeSum(parent_trace, 'Incremental')
                df_row_2_excel_row_mapper   = None
            else:
                raise ApodeixiError(loop_trace, "Invalid manifest key: '" + str(key) + "'")
            config      = ManifestXLConfig( sheet                       = SkeletonController.GENERATED_FORM_WORKSHEET,
                                            manifest_name               = key,    
                                            viewport_width              = 100,  
                                            viewport_height             = 40,   
                                            max_word_length             = 20, 
                                            editable_cols               = editable_cols,
                                            hidden_cols                 = hidden_cols,  
                                            num_formats                 = num_formats, 
                                            excel_formulas              = excel_formulas,
                                            df_row_2_excel_row_mapper   = df_row_2_excel_row_mapper,
                                            editable_headers            = [],   
                                            x_offset                    = x_offset,    
                                            y_offset                    = y_offset)
            # Put next manifest to the right of this one, separated by an empty column
            x_offset                        += data_df.shape[1] -len(hidden_cols) + right_margin
            config_table.addManifestXLConfig(loop_trace, config)
        return config_table

    def _buildAllManifests(self, parent_trace, posting_label_handle):

        all_manifests_dict, label              = super()._buildAllManifests(parent_trace, posting_label_handle)

        my_trace                        = parent_trace.doing("Linking big-rock-estimate manifest to UIDs from big-rock manifest "
                                                                + "in BigRocksEstimate_Controller")
        referencing                     = 'big-rock-estimate'
        referenced                      = 'big-rock'

        # Expect exactly 1 match
        matching_nbs                    = [manifest_nb 
                                            for manifest_nb, kind, excel_range, excel_sheet 
                                            in self.show_your_work.manifest_metas()
                                            if kind == referencing]
        if len(matching_nbs)==0:
            raise ApodeixiError(my_trace, "Unable to find metadata in controller's show_your_work for kind='" + referencing + "'")
        if len(matching_nbs) > 1:
            raise ApodeixiError(my_trace, "Too many matches in controller's show_your_work metadata for kind='" + referencing 
                                            + "': expected exactly one match",
                                            data = {'kind': referencing, 'matching_nbs': str(matching_nbs)})

        # After checks above, this is safe:
        manifest_nb                     = matching_nbs[0]
        # The 'big-rock-estimate' is the 2nd manifest, hence index 1 (we start at index 0)

        effort_dict                     = all_manifests_dict[manifest_nb]['assertion']['effort']

        effort_uids                     = [e_uid for e_uid in effort_dict.keys() if not e_uid.endswith("-name")]
        UID_FINDER                      = self.link_table.find_foreign_uid # Abbreviation for readability
        for e_uid in effort_uids:
            br_uid                      = UID_FINDER(   parent_trace            = my_trace, 
                                                        our_manifest_id         = referencing, 
                                                        foreign_manifest_id     = referenced, 
                                                        our_manifest_uid        = e_uid)

            effort_dict[e_uid]['bigRock']  = br_uid

        return all_manifests_dict, label

    def manifestNameFromLabel(self, parent_trace, label):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        label
        '''
        product                         = label.product             (parent_trace)
        journey                         = label.journey             (parent_trace) 
        scenario                        = label.scenario            (parent_trace)
        scoring_cycle                   = label.scoring_cycle       (parent_trace)

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(journey + '.' + scenario + '.' + scoring_cycle + '.' + product)
        return name

    def manifestNameFromCoords(self, parent_trace, subnamespace, coords):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        filing coords, possibly complemented by the subnamespace.

        Example: consider a manifest name like "modernization.default.dec-2020.fusionopus"
                in namespace "my-corp.production". 

                To build such a name, this method must receive "modernization" as the subnamespace, and
                filing coords from which to infer "default", "dec-20220", and "fusionopus".

        @param subnamespace A string, which is allowed to be None. If not null, this is a further partioning of
                        the namespace into finer slices, and a manifest's name is supposed to identify the slice
                        in which the manifest resides.

        @param coords A FilingCoords object corresponding to this controller. It is used, possibly along with the
                        `subnamespace` parameter, to build a manifest name.
        '''
        if not type(coords) == JourneysFilingCoordinates:
            raise ApodeixiError(parent_trace, "Can't build manifest name because received wrong type of filing coordinates",
                                                data = {"Type of coords received": str(type(coords)),
                                                        "Expected type of coords": "JourneysFilingCoordinates"})

        if subnamespace == None:
            raise ApodeixiError(parent_trace, "Can't build manifest name becase subnamespace is null. Should be "
                                                + "set to a kind of journey. Example: 'modernization'")

        product                         = coords.product
        journey                         = subnamespace
        scenario                        = coords.scenario
        scoring_cycle                   = coords.scoring_cycle

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(journey + '.' + scenario + '.' + scoring_cycle + '.' + product)
        return name

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, posting_data_handle, label)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to BigRocksEstimate_Controller") 

        product                         = label.product             (my_trace)
        journey                         = label.journey             (my_trace) 
        scenario                        = label.scenario            (my_trace)
        plan_type                       = label.plan_type           (my_trace)
        variant                         = label.variant             (my_trace)
        scoring_cycle                   = label.scoring_cycle       (my_trace)
        scoring_maturity                = label.scoring_maturity    (my_trace)

        
        my_trace                        = parent_trace.doing("Enriching generic manifest fields with additional fields "
                                                                + "specific to BigRocksEstimate_Controller")
        
        if True:
            metadata                                    = manifest_dict['metadata']

            MY_PL                                       = BigRocksEstimate_Controller._MyPostingLabel # Abbreviation for readability
            labels                                      = metadata['labels']
            labels[MY_PL._PRODUCT]                      = product
            labels[MY_PL._JOURNEY]                      = journey
            labels[MY_PL._SCENARIO]                     = scenario
            labels[MY_PL._PLAN_TYPE]                    = plan_type
            labels[MY_PL._VARIANT]                      = variant
            labels[MY_PL._SCORING_CYCLE]                = scoring_cycle
            labels[MY_PL._SCORING_MATURITY]             = scoring_maturity

            assertion                                   = manifest_dict['assertion']

            assertion[MY_PL._SCENARIO]                  = scenario
            assertion[MY_PL._PLAN_TYPE]                 = plan_type
            assertion[MY_PL._VARIANT]                   = variant
            assertion[MY_PL._SCORING_CYCLE]             = scoring_cycle
            assertion[MY_PL._SCORING_MATURITY]          = scoring_maturity
        
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
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns",
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
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns",
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

    class _MyPostingLabel(SkeletonController._MyPostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting big rocks estimates. 
        '''
        _PRODUCT                    = "product"
        _JOURNEY                    = "journey"
        _PLAN_TYPE                  = "planType"
        _VARIANT                    = "variant"
        _SCENARIO                   = "scenario"
        _SCORING_CYCLE              = "scoringCycle"
        _SCORING_MATURITY           = "scoringMaturity"

        def __init__(self, parent_trace, controller):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,

                                mandatory_fields    = [ ME._PRODUCT,        ME._JOURNEY,            ME._SCENARIO,    # Determine name
                                                        ME._PLAN_TYPE,      ME._VARIANT,    
                                                        ME._SCORING_CYCLE,  ME._SCORING_MATURITY],
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

            _infer(ME._PRODUCT,             ["metadata",    "labels",       ME._PRODUCT             ])
            _infer(ME._JOURNEY,             ["metadata",    "labels",       ME._JOURNEY,            ])
            _infer(ME._PLAN_TYPE,           ["assertion",                   ME._PLAN_TYPE           ])
            _infer(ME._VARIANT,             ["assertion",                   ME._VARIANT             ])
            _infer(ME._SCENARIO,            ["assertion",                   ME._SCENARIO            ])
            _infer(ME._SCORING_CYCLE,       ["assertion",                   ME._SCORING_CYCLE       ])
            _infer(ME._SCORING_MATURITY,    ["assertion",                   ME._SCORING_MATURITY    ])

            editable_fields.extend([ME._SCORING_MATURITY])

            self.controller.variant     = self.variant(parent_trace)
            return editable_fields

        def product(self, parent_trace):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._PRODUCT)

        def journey(self, parent_trace):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._JOURNEY)

        def scenario(self, parent_trace):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._SCENARIO)

        def plan_type(self, parent_trace):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._PLAN_TYPE)

        def variant(self, parent_trace):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._VARIANT)

        def scoring_cycle(self, parent_trace):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._SCORING_CYCLE)

        def scoring_maturity(self, parent_trace):
            # Shortcut to reference class static variables
            ME = BigRocksEstimate_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._SCORING_MATURITY)


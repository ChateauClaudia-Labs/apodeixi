import os                                           as _os

from apodeixi.controllers.util.manifest_api         import ManifestAPI
from apodeixi.util.a6i_error                        import ApodeixiError

from apodeixi.controllers.util.skeleton_controller  import SkeletonController
from apodeixi.knowledge_base.knowledge_base_util    import PostingLabelHandle, FormRequestResponse
from apodeixi.representers.as_dataframe             import AsDataframe_Representer
from apodeixi.representers.as_excel                 import Manifest_Representer
from apodeixi.text_layout.excel_layout              import AsExcel_Config_Table, ManifestXLConfig, PostingLabelXLConfig

from apodeixi.xli.interval                          import IntervalUtils, GreedyIntervalSpec, MinimalistIntervalSpec
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
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
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
        UID_FINDER                      = self.show_your_work.find_referenced_uid # Abbreviation for readability
        for e_uid in effort_uids:
            br_uid                = UID_FINDER(   parent_trace            = my_trace, 
                                                        kind1                   = referencing, 
                                                        kind2                   = referenced, 
                                                        uid1                    = e_uid)

            effort_dict[e_uid]['bigRock']  = br_uid

        return all_manifests_dict, label

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
            FMT                                         = PostingController.format_as_yaml_fieldname # Abbreviation for readability
            metadata                                    = manifest_dict['metadata']
            metadata['name']                            = FMT(journey + '.' + scenario + '.' + scoring_cycle + '.' + product)

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

    def generateForm(self, parent_trace, form_request):
        '''
        Generates and saves an Excel spreadsheet that the caller can complete and then submit
        as a posting

        Returns a FormRequestResponse object, as well as a string corresponding the log made during the processing.
        '''
        my_trace                            = parent_trace.doing("Loading manifests to include in form")
        df_dict                             = {} # Keys will be manifest's kind, values the DataFrame representation of manifest
        for handle in form_request.manifestHandles(my_trace):
            loop_trace                      = my_trace.doing("Loading manifest as a DataFrame",
                                                                data = {"handle": handle.display(my_trace)})
            manifest_dict, manifest_path    = self.store.retrieveManifest(my_trace, handle)
            kind                            = manifest_dict['kind']
            posting_config                  = self.getPostingConfig(loop_trace, kind, 0)
            entity_yaml_field               = posting_config.entity_as_yaml_fieldname()
            content_dict                    = manifest_dict['assertion'][entity_yaml_field]
            rep                             = AsDataframe_Representer()
            contents_path                   = 'assertion.' + entity_yaml_field
            df                              = rep.dict_2_df(parent_trace, content_dict, contents_path)
            df_dict[kind]                   = df

        my_trace                            = parent_trace.doing("Creating Excel layouts for manifests")

        full_path                           = self.store.getPostingsURL(my_trace) \
                                                + "/" + form_request.getRelativePath(my_trace)
        output_folder, filename             = _os.path.split(full_path)
        sheet                               = "Big Rocks"
        config_table                        = AsExcel_Config_Table()
        x_offset                            = 1
        y_offset                            = 1
        for kind in df_dict.keys():
            loop_trace                      = my_trace.doing("Creating layout configurations for manifest '"
                                                                + str(kind) + "'")
            data_df                         = df_dict[kind]
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            config              = ManifestXLConfig( manifest_name       = kind,    
                                                    viewport_width      = 100,  
                                                    viewport_height     = 40,   
                                                    max_word_length     = 20, 
                                                    editable_cols       = editable_cols,   
                                                    editable_headers    = [],   
                                                    x_offset            = x_offset,    
                                                    y_offset            = y_offset)
            # Put next manifest to the right of this one, separated by an empty column
            x_offset                        += data_df.shape[1] + 1 
            config_table.addManifestXLConfig(loop_trace, config)

        my_trace                            = parent_trace.doing("Inferring posting label", 
                                                                origination = {'signaled_from': __file__})
          
        label                               = self.getPostingLabel(my_trace)
        editable_fields                     = label.infer(my_trace, manifest_dict)  
        
        my_trace                            = parent_trace.doing("Creating Excel layout for Posting Label")
        
        label_config            = PostingLabelXLConfig( viewport_width      = 100,  
                                                        viewport_height     = 40,   
                                                        max_word_length     = 20, 
                                                        editable_fields     = editable_fields,   
                                                        x_offset            = 1,    
                                                        y_offset            = 1)
        config_table.setPostingLabelXLConfig(my_trace, label_config)

 


        rep                                 = Manifest_Representer(config_table)

        status                              = rep.dataframe_to_xl(  parent_trace    = my_trace, 
                                                                    content_df_dict = df_dict, 
                                                                    label_dict      = label.ctx,
                                                                    excel_folder    = output_folder, 
                                                                    excel_filename  = filename, 
                                                                    sheet           = sheet)   
        my_trace                            = parent_trace.doing("Assembling FormRequest response")     

        POSTING_LABEL_SHEET                 = "Posting Label"
        POSTING_LABEL_RANGE                 = "B2:C100"
        response_handle                     = PostingLabelHandle(   
                                                    parent_trace            = my_trace,
                                                    excel_filename        = filename,
                                                    excel_sheet            = POSTING_LABEL_SHEET,
                                                    excel_range            = POSTING_LABEL_RANGE,
                                                    posting_api            = form_request.getPostingAPI(my_trace), 
                                                    filing_coords          = form_request.getFilingCoords(my_trace), 
                                                    kb_postings_url        = self.store.getPostingsURL(my_trace))

        response                            = FormRequestResponse()
        response.recordCreation(parent_trace=my_trace, response_handle=response_handle)

        self.log_txt                        = self.store.logFormRequestEvent(my_trace, form_request, response)
        return response



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
            return PostingController.format_as_yaml_fieldname(ME._ENTITY_NAME)

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
            posted_cols                     = list(posted_content_df.columns)
            mandatory_cols                  = [ME._ENTITY_NAME]
            #mandatory_cols.extend(ME._SPLITTING_COLUMNS)
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
            return PostingController.format_as_yaml_fieldname(ME._ENTITY_NAME)

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
            posted_cols                     = list(posted_content_df.columns)
            mandatory_cols                  = [ME._ENTITY_NAME]
            #mandatory_cols.extend(ME._SPLITTING_COLUMNS)
            missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})

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
            return PostingController.format_as_yaml_fieldname(ME._ENTITY_NAME)

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
            posted_cols                     = list(posted_content_df.columns)
            mandatory_cols                  = [ME._ENTITY_NAME]
            #mandatory_cols.extend(ME._SPLITTING_COLUMNS)
            missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})

        def entity_name(self):
            ME                      = BigRocksEstimate_Controller._InvestmentConfig
            return ME._ENTITY_NAME

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

        def infer(self, parent_trace, manifest_dict):
            '''
            Builds out the properties of a PostingLabel so that it can be used in a post request to update a
            manifest given by the `manifest_dict`

            Returns a list of the fields that may be editable

            @param manifest_dict A dict object containing the information of a manifest (such as obtained after loading
                                a manifest YAML file into a dict)
            '''
            editable_fields     = super().infer(parent_trace, manifest_dict)

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


from apodeixi.controllers.util.manifest_api         import ManifestAPI
from apodeixi.util.a6i_error                        import ApodeixiError

from apodeixi.controllers.util.skeleton_controller  import SkeletonController
from apodeixi.xli.breakdown_builder                 import _without_comments_in_parenthesis

from apodeixi.xli                                   import UpdatePolicy, PostingController, PostingConfig, \
                                                            FixedIntervalSpec, ClosedOpenIntervalSpec

class BigRocksEstimate_Controller(SkeletonController):
    '''
    Class to process an Excel posting for big rocks estimates. It produces two YAML manifests, since the investment
    to pay for the big rocks is expected to be posted in the same Excel spreadsheet.
    '''
    def __init__(self, parent_trace):
        super().__init__(parent_trace)

        self.MANIFEST_API = ManifestAPI(    parent_trace    = parent_trace,
                                            domain          = 'journeys', 
                                            subdomain       = 'delivery-planning', 
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

    def getPostingConfig(self, parent_trace, kind):
        '''
        Return a PostingConfig, corresponding to the configuration that this concrete controller supports.
        '''
        ME                          = BigRocksEstimate_Controller
        if kind == 'big-rock':
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
            config                      = ME._BigRocksConfig(update_policy)
        elif kind == 'big-rock-estimate':
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
            config                      = ME._BigRocksEstimatesConfig(update_policy = update_policy, controller = self)
        elif kind == 'investment':
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
            config                      = ME._InvestmentConfig(update_policy)
        else:
            raise ApodeixiError(parent_trace, "Invalid domain object '" + kind + "' - should be one of "
                                                + ", ".join(self.SUPPORTED_KINDS),
                                                data = {'signaled_from': __file__})

        return config 

    def getPostingLabel(self, parent_trace):
        '''
        Returns a PostingLabel, corresponding to the what is expected by this concrete controller class.
        '''
        ME                              = BigRocksEstimate_Controller
        return ME._MyPostingLabel(parent_trace, controller = self)

    def _buildAllManifests(self, parent_trace, url, ctx_range):

        all_manifests_dicts, label              = super()._buildAllManifests(parent_trace, url, ctx_range)

        my_trace                        = parent_trace.doing("Linking big-rock-estimate manifest to UIDs from big-rock manifest "
                                                                + "in BigRocksEstimate_Controller")

        # We know that kind='big-rock-estimate' has the 2nd index (so 1, since indices start at 0) because it appears as 'data.kind.2'
        # in the PostingLabel by convention. But perhaps this is precarious assumption, as it requires the PostingLabel to
        # list the 'data.kind.n' in growing order, and they must be processed in that order by 
        effort_dict                     = all_manifests_dicts[1]['assertion']['effort']

        br_uids_to_link                 = self.explanations['big-rock']
        # We rely on fact that UID Generator generated ordered UIDS, so if we loop through the key using alphabetical order
        # that would align 1-1 with the row numbers in the estimate
        effort_uids                     = list(effort_dict.keys())
        # We need to filter the effort_uids, because they come in pairs: for a key "E2" there is the companion "E2-name"
        # So we want to filter the "E2-name" out
        effort_uids                     = [uid for uid in effort_uids if not uid.endswith("-name")]
        effort_uids.sort() 
        br_row_numbers                  = list(br_uids_to_link.keys())
        # We need to filter the br_row_numbers because they might included some null rows
        br_row_numbers                  = [row_nb for row_nb in br_row_numbers if not br_uids_to_link[row_nb]['last_UID'] == None]
        br_row_numbers.sort()
        if len(effort_uids) != len(br_row_numbers):
            raise ApodeixiError(my_trace, "Different number of efforts (" + str(len(effort_uids)) + ") vs number of big rock rows ("
                                            + str(len(br_row_numbers)) + "). They should match in order to link them.")
        for idx in range(len(effort_uids)):
            br_row_nb                   = br_row_numbers[idx]
            br_uid                      = br_uids_to_link[br_row_nb]['last_UID']
            effort_uid                  = effort_uids[idx]
            effort_dict[effort_uid]['bigRock']  = br_uid

        

        return all_manifests_dicts, label

    def _buildOneManifest(self, parent_trace, url, label, kind, excel_range):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict, explanations     = super()._buildOneManifest(parent_trace, url, label, kind, excel_range)
           
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
            metadata['name']                            = FMT(scenario + '.' + journey + '.' + product)

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
        
        return manifest_dict, explanations

    def _genExcel(self, parent_trace, url, ctx_range, manifests_dir, manifest_file):
        '''
        Helper function that is amenable to unit testing (i.e., does not require a KnowledgeBase structure for I/O).

        Used to generate an Excel spreadsheet that represents the current state of the manifest, inclusive of UIDs.
        Such Excel spreadsheet is what the user would need to post in order to make changes to the manifest, since pre-existing
        UIDs must be repected.
        '''

    class _BigRocksConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for big rocks (potentially broken into subrocks, sub-subrocks, etc.)
        '''

        _ENTITY_NAME                    = 'Big Rock'

        def __init__(self, update_policy):
            ME                          = BigRocksEstimate_Controller._BigRocksConfig
            GIST_OF                     = _without_comments_in_parenthesis # Intentional abbreviation for clarity/readability
            super().__init__()
            self.update_policy          = update_policy

            interval_spec_big_rocks      = ClosedOpenIntervalSpec(  parent_trace        = None, 
                                                                    start_column        = ME._ENTITY_NAME,
                                                                    following_column    = GIST_OF('Effort (md)'),
                                                                    entity_name         = ME._ENTITY_NAME
                                                                    ) 
            #interval_spec_effort         = FixedIntervalSpec(None, ['Effort (md)'])

            self.interval_specs          = [interval_spec_big_rocks] #, interval_spec_effort]

        def entity_name(self):
            ME                      = BigRocksEstimate_Controller._BigRocksConfig
            return ME._ENTITY_NAME

    class _BigRocksEstimatesConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for big rock estimates
        '''

        _ENTITY_NAME                            = 'Effort'

        def __init__(self, update_policy, controller):
            ME                                  = BigRocksEstimate_Controller._BigRocksEstimatesConfig
            GIST_OF                 = _without_comments_in_parenthesis # Intentional abbreviation for clarity/readability

            super().__init__()
            self.update_policy                  = update_policy

            interval_spec_big_rocks_estimates   = FixedIntervalSpec(    parent_trace        = None, 
                                                                        columns             = [GIST_OF('Effort (md)')],
                                                                    ) 

            self.interval_specs                 = [interval_spec_big_rocks_estimates]

        def entity_name(self):
            ME                      = BigRocksEstimate_Controller._BigRocksEstimatesConfig
            return ME._ENTITY_NAME

    class _InvestmentConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for big rock estimates and investment manifests
        '''

        _ENTITY_NAME                = 'Period'

        def __init__(self, update_policy):
            ME                      = BigRocksEstimate_Controller._InvestmentConfig
            super().__init__()
            self.update_policy      = update_policy

            interval_spec_period    = FixedIntervalSpec(None, [ME._ENTITY_NAME, 'Incremental']) 

            self.interval_specs     = [interval_spec_period]

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


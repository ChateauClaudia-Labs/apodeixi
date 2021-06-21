from apodeixi.controllers.util.manifest_api                     import ManifestAPI
from apodeixi.util.a6i_error                                    import ApodeixiError

from apodeixi.controllers.util.skeleton_controller              import SkeletonController
from apodeixi.xli.interval                                      import GreedyIntervalSpec

from apodeixi.xli.posting_controller_utils                      import PostingConfig, PostingController
from apodeixi.xli                                               import UpdatePolicy
from apodeixi.controllers.journeys.delivery_planning.big_rocks  import BigRocksEstimate_Controller

class MilestonesController(SkeletonController):
    '''
    Class to process an Excel posting journey milestiones. It produces one YAML manifests.

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    '''
    def __init__(self, parent_trace, store):
        super().__init__(parent_trace, store)
        ME                              = MilestonesController

        self.MANIFEST_API = ManifestAPI(    parent_trace    = parent_trace,
                                            domain          = 'journeys', 
                                            subdomain       = 'milestone', 
                                            api_publisher   = 'a6i',
                                            extension       = 'io')
        self.SUPPORTED_VERSIONS         = ['v1']
        self.SUPPORTED_KINDS            = [ME.MY_KIND, ME.REFERENCED_KIND]

    MY_KIND                             = 'modernization-milestone'
    REFERENCED_KIND                     = 'big-rock'

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
        ME                              = MilestonesController
        if kind == ME.MY_KIND:
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
            config                      = ME._MilestonesConfig( update_policy       = update_policy, 
                                                                kind                = kind, 
                                                                manifest_nb         = manifest_nb,
                                                                controller          = self)
        elif kind == ME.REFERENCED_KIND:
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            config                      = BigRocksEstimate_Controller._BigRocksConfig(  update_policy       = update_policy, 
                                                                                        kind                = kind,
                                                                                        manifest_nb         = manifest_nb,
                                                                                        controller          = self)

        else:
            raise ApodeixiError(parent_trace, "Invalid domain object '" + kind + "' - should be one of "
                                                + ", ".join(self.SUPPORTED_KINDS),
                                                origination = {'signaled_from': __file__})

        return config 

    def getPostingLabel(self, parent_trace):
        '''
        Returns a PostingLabel, corresponding to the what is expected by this concrete controller class.
        '''
        ME                              = MilestonesController
        return ME._MyPostingLabel(parent_trace, controller = self)

    def _buildAllManifests(self, parent_trace, posting_label_handle):
        ME                              = MilestonesController
        all_manifests_dict, label       = super()._buildAllManifests(parent_trace, posting_label_handle)

        my_trace                        = parent_trace.doing("Linking " + ME.MY_KIND + " manifest to UIDs from " + ME.REFERENCED_KIND + " manifest "
                                                                + "in MilestonesController")
        referencing                     = ME.MY_KIND
        referenced                      = ME.REFERENCED_KIND

        # Expect exactly 1 match
        matching_nbs                    = [manifest_nb  for manifest_nb, kind, excel_range, excel_sheet 
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

        milestones_dict                 = all_manifests_dict[manifest_nb]['assertion']['milestone']

        milestones_uids                 = [e_uid for e_uid in milestones_dict.keys() if not e_uid.endswith("-name")]
        UID_FINDER                      = self.show_your_work.find_referenced_uid # Abbreviation for readability
        for e_uid in milestones_uids:
            br_uid                = UID_FINDER(   parent_trace                  = my_trace, 
                                                        kind1                   = referencing, 
                                                        kind2                   = referenced, 
                                                        uid1                    = e_uid)

            milestones_dict[e_uid][ME.REFERENCED_KIND]  = br_uid

        return all_manifests_dict, label

    def _buildOneManifest(self, parent_trace, manifest_nb, url, posting_data_handle, label, kind, excel_range):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, manifest_nb, url, posting_data_handle, label, kind, excel_range)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to MilestonesController") 

        product                         = label.product             (my_trace)
        journey                         = label.journey             (my_trace) 
        scenario                        = label.scenario            (my_trace)
        scoring_cycle                   = label.scoring_cycle       (my_trace)
        scoring_maturity                = label.scoring_maturity    (my_trace)  

        estimated_by                    = label.estimated_by        (my_trace)
        estimated_on                    = label.estimated_on        (my_trace)    


        my_trace                        = parent_trace.doing("Enriching generic manifest fields with additional fields "
                                                                + "specific to Milestone_Controller")
        
        if True:
            FMT                                         = PostingController.format_as_yaml_fieldname # Abbreviation for readability
            metadata                                    = manifest_dict['metadata']
            metadata['name']                            = FMT(journey + '.' + scenario + '.' + scoring_cycle + '.' + product)

            MY_PL                                       = MilestonesController._MyPostingLabel # Abbreviation for readability
            labels                                      = metadata['labels']
            labels[MY_PL._PRODUCT]                      = product
            labels[MY_PL._JOURNEY]                      = journey
            labels[MY_PL._SCENARIO]                     = scenario
            labels[MY_PL._SCORING_CYCLE]                = scoring_cycle
            labels[MY_PL._SCORING_MATURITY]             = scoring_maturity

            assertion                                   = manifest_dict['assertion']

            assertion[MY_PL._SCENARIO]                  = scenario
            assertion[MY_PL._SCORING_CYCLE]             = scoring_cycle
            assertion[MY_PL._SCORING_MATURITY]          = scoring_maturity
            assertion[MY_PL._ESTIMATED_BY]              = estimated_by
            assertion[MY_PL._ESTIMATED_ON]              = estimated_on
        
        return manifest_dict

    def _genExcel(self, parent_trace, url, ctx_range, manifests_dir, manifest_file):
        '''
        Helper function that is amenable to unit testing (i.e., does not require a KnowledgeBase structure for I/O).

        Used to generate an Excel spreadsheet that represents the current state of the manifest, inclusive of UIDs.
        Such Excel spreadsheet is what the user would need to post in order to make changes to the manifest, since pre-existing
        UIDs must be repected.
        '''

    class _MilestonesConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for modernization milestones
        '''

        _ENTITY_NAME                            = 'Milestone'

        def __init__(self, update_policy, kind, manifest_nb, controller):
            ME                                  = MilestonesController._MilestonesConfig

            super().__init__(   kind            = kind, 
                                update_policy   = update_policy, 
                                manifest_nb     = manifest_nb,
                                controller      = controller)
            self.horizontally                   = False # Replaces parent class's default, so we read Excel by columns, not by rows

            interval_spec_milestones   = GreedyIntervalSpec( parent_trace = None, entity_name = ME._ENTITY_NAME) 

            self.interval_spec                  = interval_spec_milestones

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
            ME                              = MilestonesController._MilestonesConfig
            posted_cols                     = list(posted_content_df.columns)
            mandatory_cols                  = [ME._ENTITY_NAME]
            #mandatory_cols.extend(ME._SPLITTING_COLUMNS)
            missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})

        def entity_name(self):
            ME                      = MilestonesController._MilestonesConfig
            return ME._ENTITY_NAME

    class _MyPostingLabel(SkeletonController._MyPostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting modernization milestones. 
        '''
        _PRODUCT                    = "product"
        _JOURNEY                    = "journey"
        _SCENARIO                   = "scenario"
        _SCORING_CYCLE              = "scoringCycle"
        _SCORING_MATURITY           = "scoringMaturity"

        _ESTIMATED_BY               = "estimatedBy"
        _ESTIMATED_ON               = "estimatedOn"

        def __init__(self, parent_trace, controller):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,

                                mandatory_fields    = [ ME._PRODUCT,        ME._JOURNEY,            ME._SCENARIO,    # Determine name
                                                        ME._SCORING_CYCLE,  ME._SCORING_MATURITY,
                                                        ME._ESTIMATED_BY,   ME._ESTIMATED_ON],
                                date_fields         = [ME._ESTIMATED_ON])

        def product(self, parent_trace):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            return self._getField(parent_trace, ME._PRODUCT)

        def journey(self, parent_trace):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            return self._getField(parent_trace, ME._JOURNEY)

        def scenario(self, parent_trace):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            return self._getField(parent_trace, ME._SCENARIO)

        def scoring_cycle(self, parent_trace):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            return self._getField(parent_trace, ME._SCORING_CYCLE)

        def scoring_maturity(self, parent_trace):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            return self._getField(parent_trace, ME._SCORING_MATURITY)

        def estimated_by(self, parent_trace):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            return self._getField(parent_trace, ME._ESTIMATED_BY)

        def estimated_on(self, parent_trace):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            return self._getField(parent_trace, ME._ESTIMATED_ON)


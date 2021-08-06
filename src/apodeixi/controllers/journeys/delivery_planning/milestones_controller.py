from apodeixi.controllers.util.manifest_api                     import ManifestAPI
from apodeixi.util.a6i_error                                    import ApodeixiError
from apodeixi.util.formatting_utils                             import StringUtils

from apodeixi.controllers.util.skeleton_controller              import SkeletonController
from apodeixi.knowledge_base.filing_coordinates                 import JourneysFilingCoordinates
from apodeixi.xli.interval                                      import GreedyIntervalSpec

from apodeixi.xli.posting_controller_utils                      import PostingConfig, PostingController
from apodeixi.xli                                               import UpdatePolicy
from apodeixi.controllers.journeys.delivery_planning.big_rocks  import BigRocksEstimate_Controller

class MilestonesController(SkeletonController):
    '''
    Class to process an Excel posting journey milestiones. It produces one YAML manifests.

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)
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
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = ME._MilestonesConfig( update_policy       = update_policy, 
                                                                kind                = kind, 
                                                                manifest_nb         = manifest_nb,
                                                                controller          = self)
        elif kind == ME.REFERENCED_KIND:
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = BigRocksEstimate_Controller._BigRocksConfig(  update_policy       = update_policy, 
                                                                                        kind                = kind,
                                                                                        manifest_nb         = manifest_nb,
                                                                                        controller          = self)

        else:
            raise ApodeixiError(parent_trace, "Invalid domain object '" + kind + "' - should be one of "
                                                + ", ".join(self.SUPPORTED_KINDS),
                                                origination = {'signaled_from': __file__})

        return xlr_config 

    def getPostingLabel(self, parent_trace):
        '''
        Returns a PostingLabel, corresponding to the what is expected by this concrete controller class.
        '''
        ME                              = MilestonesController
        return ME._MyPostingLabel(parent_trace, controller = self)

    def _buildAllManifests(self, parent_trace, posting_label_handle):
        ME                              = MilestonesController
        all_manifests_dict, label       = super()._buildAllManifests(parent_trace, posting_label_handle)

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
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to MilestonesController") 

        product                         = label.product             (my_trace)
        journey                         = label.journey             (my_trace) 
        scenario                        = label.scenario            (my_trace)
        scoring_cycle                   = label.scoring_cycle       (my_trace)
        scoring_maturity                = label.scoring_maturity    (my_trace)  

        estimated_by                    = label.estimatedBy        (my_trace)
        estimated_on                    = label.estimatedOn        (my_trace)    


        my_trace                        = parent_trace.doing("Enriching generic manifest fields with additional fields "
                                                                + "specific to Milestone_Controller")
        
        if True:
            metadata                                    = manifest_dict['metadata']

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

            # These three settings replace the parent class's defaults. That ensures wwe read Excel by columns, 
            # not by rows, and that we realize a fair amount of rows in Excel are really a mapping to big rock, not
            # manifest entities' properties.
            self.horizontally                   = False 
            self.is_a_mapping                   = True
            self.kind_mapped_from               = 'big-rock'

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
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns. This often happens if "
                                                    + "ranges are wrong in Posting Label.",
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



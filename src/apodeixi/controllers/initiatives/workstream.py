from apodeixi.controllers.util.manifest_api         import ManifestAPI
from apodeixi.util.a6i_error                        import ApodeixiError
from apodeixi.util.formatting_utils                 import StringUtils

from apodeixi.controllers.util.skeleton_controller  import SkeletonController
from apodeixi.knowledge_base.filing_coordinates     import InitiativesFilingCoordinates
from apodeixi.xli.interval                          import IntervalUtils, GreedyIntervalSpec, ClosedOpenIntervalSpec

from apodeixi.xli.posting_controller_utils          import PostingConfig, PostingController, UpdatePolicy

class Workstream_Controller(SkeletonController):
    '''
    Class to process an Excel posting for initiative workstreams. It produces two YAML manifests:
    
    * The workstream's milestones
    * The workstream's metrics

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)

        self.MANIFEST_API = ManifestAPI(    parent_trace    = parent_trace,
                                            domain          = 'initiatives', 
                                            subdomain       = 'workstream', 
                                            api_publisher   = 'a6i',
                                            extension       = 'io')
        self.SUPPORTED_VERSIONS         = ['v1a']
        self.SUPPORTED_KINDS            = ['workstream-milestone', 'workstream-metric']

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
        ME                              = Workstream_Controller
        if kind == 'workstream-milestone':
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = ME._WorkstreamMilestoneConfig(    update_policy       = update_policy, 
                                                                            kind                = kind, 
                                                                            manifest_nb         = manifest_nb,
                                                                            controller          = self)
        elif kind == 'workstream-metric':
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = ME._WorkstreamMetricConfig(       update_policy       = update_policy, 
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
        ME                              = Workstream_Controller
        return ME._MyPostingLabel(parent_trace, controller = self)

    def _buildAllManifests(self, parent_trace, posting_label_handle):

        all_manifests_dict, label              = super()._buildAllManifests(parent_trace, posting_label_handle)

        return all_manifests_dict, label

    def subnamespaceFromLabel(self, parent_trace, label):
        '''
        Helper method that returns what the 'subnamespace' that is a portion of a manifest's name.
        It is inferred from a `label` that provides the posting details for a manifest that should be created.

        Returns a string corresponding to the subnamespace, if one applies to this `kind` of manifest.
        If no subnamespace applies, returns None.
        '''
        program                         = label.program             (parent_trace)
        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        return FMT(program)

    def manifestNameFromLabel(self, parent_trace, label, kind):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        label
        @param kind The kind of manifest for which the name is sought. This parameter can be ignored for controller
                    classes that use the same name for all supported kinds; it is meant to support controllers that
                    process multiple manifest kinds and do not use the same name for all of them. For example, controllers
                    that point to reference data in a different domain/sub-domain.
        '''
        program                         = label.program             (parent_trace)
        workstream_UID                  = label.workstream_UID      (parent_trace)
        initiative                      = label.initiative          (parent_trace)
        scenario                        = label.scenario            (parent_trace)
        scoring_cycle                   = label.scoring_cycle       (parent_trace)

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(program + '.' + scoring_cycle + '.' + initiative + '.' 
                                                + workstream_UID + '.' + scenario)

        return name

    def manifestNameFromCoords(self, parent_trace, subnamespace, coords, kind):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        filing coords, possibly complemented by the subnamespace.

        Usually used in the context of generating forms.

        Example: consider a manifest name like "modernization.dec-2020.fusionopus.default"
                in namespace "my-corp.production". 

                To build such a name, this method must receive "modernization" as the subnamespace, and
                filing coords from which to infer "dec-20220", "fusionopus", and "default".

        @param subnamespace A string, which is allowed to be None. If not null, this is a further partioning of
                        the namespace into finer slices, and a manifest's name is supposed to identify the slice
                        in which the manifest resides.

        @param coords A FilingCoords object corresponding to this controller. It is used, possibly along with the
                        `subnamespace` parameter, to build a manifest name.
        @param kind The kind of manifest for which the name is sought. This parameter can be ignored for controller
                    classes that use the same name for all supported kinds; it is meant to support controllers that
                    process multiple manifest kinds and do not use the same name for all of them. For example, controllers
                    that point to reference data in a different domain/sub-domain.
        '''
        if not type(coords) == InitiativesFilingCoordinates:
            raise ApodeixiError(parent_trace, "Can't build manifest name because received wrong type of filing coordinates",
                                                data = {"Type of coords received": str(type(coords)),
                                                        "Expected type of coords": "InitiativesFilingCoordinates"})


        workstream_UID                  = coords.workstream_UID
        program                         = subnamespace
        initiative                      = coords.initiative
        scenario                        = coords.scenario
        scoring_cycle                   = coords.scoring_cycle

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(program + '.' + scoring_cycle + '.' + initiative + '.' 
                                                + workstream_UID + '.' + scenario)

        return name

    def manifestLabelsFromCoords(self, parent_trace, subnamespace, coords):
        '''
        Helper method that returns what the a dict whose keys are label field names that should be populated
        inside a manifest based on the parameters, and the values are what the value should be for each label.

        Usually used in the context of generating forms.

        Example: consider a manifest name like "modernization.dec-2020.fusionopus.default"
                in namespace "my-corp.production", that arose from a posting for product "Fusion Opus",
                scoring cycle "Dec 2020" and scenario "Default".

                Then this method returns ["modernization", "Dec 2020", "Fusion Opus", and "Default"].

        @param subnamespace A string, which is allowed to be None. If not null, this is a further partioning of
                        the namespace into finer slices, and a manifest's name is supposed to identify the slice
                        in which the manifest resides.

        @param coords A FilingCoords object corresponding to this controller. It is used, possibly along with the
                        `subnamespace` parameter, to build a manifest name.
        '''
        if not type(coords) == InitiativesFilingCoordinates:
            raise ApodeixiError(parent_trace, "Can't build manifest name because received wrong type of filing coordinates",
                                                data = {"Type of coords received": str(type(coords)),
                                                        "Expected type of coords": "InitiativesFilingCoordinates"})

        workstream_UID                      = coords.workstream_UID
        initiative                          = subnamespace
        scenario                            = coords.scenario
        scoring_cycle                       = coords.scoring_cycle

        MY_PL                               = Workstream_Controller._MyPostingLabel # Abbreviation for readability
        result_dict                         = {}
        result_dict[MY_PL._WORKSTREAM_UID]  = workstream_UID
        result_dict[MY_PL._INITIATIVE]      = initiative
        result_dict[MY_PL._SCENARIO]        = scenario
        result_dict[MY_PL._SCORING_CYCLE]   = scoring_cycle

        return result_dict


    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, posting_data_handle, label)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to Workstream_Controller") 

        workstream_UID                  = label.workstream_UID      (my_trace)
        workstream_title                = label.workstream_title    (my_trace)
        program                         = label.program             (my_trace) 
        initiative                      = label.initiative          (my_trace)
        scenario                        = label.scenario            (my_trace)
        scoring_cycle                   = label.scoring_cycle       (my_trace)
        scoring_maturity                = label.scoring_maturity    (my_trace)

        my_trace                        = parent_trace.doing("Enriching generic manifest fields with additional fields "
                                                                + "specific to Workstream_Controller")
        
        if True:
            metadata                                    = manifest_dict['metadata']

            MY_PL                                       = Workstream_Controller._MyPostingLabel # Abbreviation for readability
            labels                                      = metadata['labels']
            labels[MY_PL._WORKSTREAM_UID]               = workstream_UID
            labels[MY_PL._WORKSTREAM_TITLE]             = workstream_title
            labels[MY_PL._PROGRAM]                      = program
            labels[MY_PL._INITIATIVE]                   = initiative
            labels[MY_PL._SCENARIO]                     = scenario
            labels[MY_PL._SCORING_CYCLE]                = scoring_cycle
            labels[MY_PL._SCORING_MATURITY]             = scoring_maturity

            assertion                                   = manifest_dict['assertion']

            assertion[MY_PL._WORKSTREAM_UID]            = workstream_UID
            assertion[MY_PL._WORKSTREAM_TITLE]          = workstream_title
            assertion[MY_PL._PROGRAM]                   = program
            assertion[MY_PL._INITIATIVE]                = initiative
            assertion[MY_PL._SCENARIO]                  = scenario
            assertion[MY_PL._SCORING_CYCLE]             = scoring_cycle
            assertion[MY_PL._SCORING_MATURITY]          = scoring_maturity
        
        return manifest_dict

    class _WorkstreamMilestoneConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for workstream's milestones
        '''

        _ENTITY_NAME                    = 'Theme'

        _SPLITTING_COLUMNS              = ['Milestone', 'Task', 'Dependency']

        def __init__(self, update_policy, kind, manifest_nb, controller):
            ME                          = Workstream_Controller._WorkstreamMilestoneConfig
            super().__init__(   kind            = kind, 
                                update_policy   = update_policy,
                                manifest_nb     = manifest_nb, 
                                controller      = controller)
        
            interval_spec_milestones    = ClosedOpenIntervalSpec(   parent_trace        = None, 
                                                                    splitting_columns   = ME._SPLITTING_COLUMNS,
                                                                    entity_name         = ME._ENTITY_NAME
                                                                    )

            self.interval_spec          = interval_spec_milestones

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
            ME                              = Workstream_Controller._WorkstreamMilestoneConfig
            posted_cols                     = list(posted_content_df.columns)
            mandatory_cols                  = [ME._ENTITY_NAME]
            mandatory_cols.extend(ME._SPLITTING_COLUMNS)
            missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns. This often happens if "
                                                    + "ranges are wrong in Posting Label.",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})

        def entity_name(self):
            ME                      = Workstream_Controller._WorkstreamMilestoneConfig
            return ME._ENTITY_NAME

    class _WorkstreamMetricConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for workstream's metrics
        '''

        _ENTITY_NAME                            = 'Metric'

        def __init__(self, update_policy, kind, manifest_nb, controller):
            ME                                  = Workstream_Controller._WorkstreamMetricConfig

            super().__init__(   kind            = kind, 
                                update_policy   = update_policy, 
                                manifest_nb     = manifest_nb,
                                controller      = controller)

            interval_spec_metrics               = GreedyIntervalSpec(parent_trace = None, entity_name = ME._ENTITY_NAME) 

            self.interval_spec                  = interval_spec_metrics

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
            ME                              = Workstream_Controller._WorkstreamMetricConfig
            posted_cols                     = list(posted_content_df.columns)
            mandatory_cols                  = [ME._ENTITY_NAME]

            missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns. This often happens if "
                                                    + "ranges are wrong in Posting Label.",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})

        def entity_name(self):
            ME                      = Workstream_Controller._WorkstreamMetricConfig
            return ME._ENTITY_NAME

    class _MyPostingLabel(SkeletonController._MyPostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting a workstream. 
        '''
        _WORKSTREAM_UID             = "workstreamUID"
        _WORKSTREAM_TITLE           = "workstreamTitle"
        _PROGRAM                    = "program"
        _INITIATIVE                 = "initiative"
        _SCENARIO                   = "scenario"
        _SCORING_CYCLE              = "scoringCycle"
        _SCORING_MATURITY           = "scoringMaturity"

        def __init__(self, parent_trace, controller):
            # Shortcut to reference class static variables
            ME = Workstream_Controller._MyPostingLabel

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,

                                mandatory_fields    = [ ME._PROGRAM,    ME._WORKSTREAM_UID, ME._INITIATIVE,  ME._SCENARIO,    # Determine name
                                                        ME._WORKSTREAM_TITLE,          
                                                        ME._SCORING_CYCLE,  ME._SCORING_MATURITY],
                                date_fields         = [])

        def program(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Workstream_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._PROGRAM)

        def workstream_UID(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Workstream_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._WORKSTREAM_UID)

        def workstream_title(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Workstream_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._WORKSTREAM_TITLE)

        def initiative(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Workstream_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._INITIATIVE)

        def scenario(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Workstream_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._SCENARIO)

        def scoring_cycle(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Workstream_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._SCORING_CYCLE)

        def scoring_maturity(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Workstream_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._SCORING_MATURITY)


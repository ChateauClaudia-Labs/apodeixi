
from apodeixi.util.a6i_error                                                import ApodeixiError

from apodeixi.controllers.journeys.delivery_planning.journeys_posting_label  import JourneysPostingLabel
from apodeixi.controllers.journeys.delivery_planning.journeys_controller     import JourneysController

from apodeixi.xli.interval                                                  import GreedyIntervalSpec

from apodeixi.xli.posting_controller_utils                                  import PostingConfig
from apodeixi.xli                                                           import UpdatePolicy
from apodeixi.controllers.journeys.delivery_planning.big_rocks              import BigRocksEstimate_Controller

class MilestonesController(JourneysController):
    '''
    Class to process an Excel posting journey milestiones. It produces one YAML manifests.

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)
        ME                              = MilestonesController

        self.SUPPORTED_VERSIONS         = ['v1']
        self.SUPPORTED_KINDS            = [ME.MY_KIND, ME.REFERENCED_KIND]

    MY_KIND                             = 'modernization-milestone'
    REFERENCED_KIND                     = 'big-rock'

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

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, posting_data_handle, label)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to MilestonesController") 

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

    class _MyPostingLabel(JourneysPostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting modernization milestones. 
        '''

        def __init__(self, parent_trace, controller):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,

                                mandatory_fields    = [],
                                date_fields         = [])

        def read(self, parent_trace, posting_label_handle):
            '''
            '''
            super().read(parent_trace, posting_label_handle)

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

            return editable_fields







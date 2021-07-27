from apodeixi.controllers.util.manifest_api         import ManifestAPI
from apodeixi.util.a6i_error                        import ApodeixiError
from apodeixi.util.formatting_utils                 import StringUtils

from apodeixi.controllers.util.skeleton_controller  import SkeletonController
from apodeixi.xli.interval                          import IntervalUtils, \
                                                            GreedyIntervalSpec, \
                                                            ClosedOpenIntervalSpec, \
                                                            MinimalistIntervalSpec

from apodeixi.xli.posting_controller_utils          import PostingConfig, PostingController, UpdatePolicy

class Mock_Controller(SkeletonController):
    '''
    Mock posting controller used by testing framework.

    Like all posting controllers, it processes and Excel posting, in this case for a fictitious domain "Account" 
    
    It produces several YAML manifests, to exercise the various IntervalSpec concrete classes.
    
    * The Account hierarchy, using the MinimalistIntervalSpec
    * The Account balances, using the GreedyIntervalSpec
    * The Account properties, using the ClosedOpenIntervalSpec

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    '''
    def __init__(self, parent_trace, store):
        super().__init__(parent_trace, store)

        self.MANIFEST_API = ManifestAPI(    parent_trace    = parent_trace,
                                            domain          = 'mock', 
                                            subdomain       = 'account', 
                                            api_publisher   = 'a6i',
                                            extension       = 'io')
        self.SUPPORTED_VERSIONS         = ['v1']
        self.SUPPORTED_KINDS            = ['hierarchy', 'balances', 'properties']

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
        ME                          = Mock_Controller
        if kind == 'hierarchy':
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            config                      = ME._AccountHierarchyConfig(       update_policy       = update_policy, 
                                                                            kind                = kind, 
                                                                            manifest_nb         = manifest_nb,
                                                                            controller          = self)
        elif kind == 'balances':
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            config                      = ME._AccountBalancesConfig(        update_policy       = update_policy, 
                                                                            kind                = kind, 
                                                                            manifest_nb         = manifest_nb,
                                                                            controller          = self)
        elif kind == 'properties':
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            config                      = ME._AccountPropertiesConfig(      update_policy       = update_policy, 
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
        ME                              = Mock_Controller
        return ME._MyPostingLabel(parent_trace, controller = self)

    def _buildAllManifests(self, parent_trace, posting_label_handle):

        all_manifests_dict, label              = super()._buildAllManifests(parent_trace, posting_label_handle)

        return all_manifests_dict, label

    def buildManifestName(self, parent_trace, posting_data_handle, label):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        posting_data_handle and label
        '''
        test_family                     = label.test_family         (parent_trace)
        test_case                       = label.test_case           (parent_trace)

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(test_family + '.' + test_case)

        return name

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, posting_data_handle, label)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to Mock_Controller") 

        test_family                     = label.test_family         (my_trace)
        test_case                       = label.test_case           (my_trace)
        test_description                = label.test_description    (my_trace)

        my_trace                        = parent_trace.doing("Enriching generic manifest fields with additional fields "
                                                                + "specific to Mock_Controller")
        if True:
            metadata                                    = manifest_dict['metadata']

            MY_PL                                       = Mock_Controller._MyPostingLabel # Abbreviation for readability
            labels                                      = metadata['labels']
            labels[MY_PL._TEST_FAMILY]                  = test_family
            labels[MY_PL._TEST_CASE]                    = test_case

            assertion                                   = manifest_dict['assertion']

            assertion[MY_PL._TEST_FAMILY]               = test_family
            assertion[MY_PL._TEST_CASE]                 = test_case
            assertion[MY_PL._TEST_DESCRIPTION]          = test_description
        
        return manifest_dict

    class _AccountHierarchyConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for an account balances
        '''

        _ENTITY_NAME                            = 'Asset Class'

        def __init__(self, update_policy, kind, manifest_nb, controller):
            ME                                  = Mock_Controller._AccountHierarchyConfig

            super().__init__(   kind            = kind, 
                                update_policy   = update_policy, 
                                manifest_nb     = manifest_nb,
                                controller      = controller)

            interval_spec_metrics               = MinimalistIntervalSpec(   parent_trace        = None, 
                                                                            entity_name         = ME._ENTITY_NAME,
                                                                            mandatory_columns   = ['Account']) 


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


        def entity_name(self):
            ME                      = Mock_Controller._AccountHierarchyConfig
            return ME._ENTITY_NAME

    class _AccountPropertiesConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for workstream's milestones
        '''

        _ENTITY_NAME                    = 'Asset Class'

        _SPLITTING_COLUMNS              = ['Institution', 'Account']

        def __init__(self, update_policy, kind, manifest_nb, controller):
            ME                          = Mock_Controller._AccountPropertiesConfig
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
            ME                              = Mock_Controller._AccountPropertiesConfig
            posted_cols                     = list(posted_content_df.columns)
            mandatory_cols                  = [ME._ENTITY_NAME]
            mandatory_cols.extend(ME._SPLITTING_COLUMNS)
            missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})

        def entity_name(self):
            ME                      = Mock_Controller._AccountPropertiesConfig
            return ME._ENTITY_NAME

    class _AccountBalancesConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for an account balances
        '''

        _ENTITY_NAME                            = 'Account'

        def __init__(self, update_policy, kind, manifest_nb, controller):
            ME                                  = Mock_Controller._AccountBalancesConfig

            super().__init__(   kind            = kind, 
                                update_policy   = update_policy, 
                                manifest_nb     = manifest_nb,
                                controller      = controller)

            interval_spec_metrics               = GreedyIntervalSpec(   parent_trace        = None, 
                                                                        entity_name         = ME._ENTITY_NAME,
                                                                        mandatory_columns   = ['Balance']) 


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


        def entity_name(self):
            ME                      = Mock_Controller._AccountBalancesConfig
            return ME._ENTITY_NAME

    class _MyPostingLabel(SkeletonController._MyPostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting a workstream. 
        '''
        _TEST_FAMILY                = "testFamily"
        _TEST_CASE                  = "testCase"
        _TEST_DESCRIPTION           = "testDescription"

        def __init__(self, parent_trace, controller):
            # Shortcut to reference class static variables
            ME = Mock_Controller._MyPostingLabel

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,

                                mandatory_fields    = [ ME._TEST_FAMILY,    ME._TEST_CASE,   # Determine name
                                                        ME._TEST_DESCRIPTION],
                                date_fields         = [])

        def test_family(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Mock_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._TEST_FAMILY)

        def test_case(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Mock_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._TEST_CASE)

        def test_description(self, parent_trace):
            # Shortcut to reference class static variables
            ME = Mock_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._TEST_DESCRIPTION)




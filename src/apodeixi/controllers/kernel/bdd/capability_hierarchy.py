from apodeixi.controllers.util.manifest_api         import ManifestAPI
from apodeixi.util.a6i_error                        import ApodeixiError
from apodeixi.util.formatting_utils                 import StringUtils

from apodeixi.controllers.util.skeleton_controller  import SkeletonController

from apodeixi.xli.update_policy                     import UpdatePolicy
from apodeixi.xli.posting_controller_utils          import PostingConfig
from apodeixi.xli.interval                          import ClosedOpenIntervalSpec

class CapabilityHierarchy_Controller(SkeletonController):
    '''
    Class to process an Excel posting for a BDD feature injection tree. It produces the YAML manifest for it
    and also creates the dolfer structure associated with the injection tree

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)

        self.MANIFEST_API = ManifestAPI(    parent_trace    = parent_trace,
                                            domain          = 'kernel', 
                                            subdomain       = 'bdd', 
                                            api_publisher   = 'a6i',
                                            extension       = 'io')
        self.SUPPORTED_VERSIONS         = ['v1a']
        self.SUPPORTED_KINDS            = ['capability-hierarchy']

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
        ME                          = CapabilityHierarchy_Controller
        update_policy               = UpdatePolicy(         reuse_uids      = True,            merge   = False)
        xlr_config                  = ME._MyPostingConfig(  update_policy   = update_policy,    
                                                            kind            = kind, 
                                                            manifest_nb     = manifest_nb,    
                                                            controller      = self)

        return xlr_config 

    def getPostingLabel(self, parent_trace):
        '''
        Returns a PostingLabel, corresponding to the what is expected by this concrete controller class.
        '''
        ME                              = CapabilityHierarchy_Controller
        return ME._MyPostingLabel(parent_trace, controller = self)

    def subnamespaceFromLabel(self, parent_trace, label):
        '''
        Helper method that returns what the 'subnamespace' that is a portion of a manifest's name.
        It is inferred from a `label` that provides the posting details for a manifest that should be created.

        Returns a string corresponding to the subnamespace, if one applies to this `kind` of manifest.
        If no subnamespace applies, returns None.
        '''
        scaffolding_purpose             = label.scaffoldingPurpose  (parent_trace)
        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        return FMT(scaffolding_purpose)

    def manifestNameFromLabel(self, parent_trace, label, kind):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        label
        @param kind The kind of manifest for which the name is sought. This parameter can be ignored for controller
                    classes that use the same name for all supported kinds; it is meant to support controllers that
                    process multiple manifest kinds and do not use the same name for all of them. For example, controllers
                    that point to reference data in a different domain/sub-domain.
        '''
        scaffolding_purpose             = label.scaffoldingPurpose  (parent_trace)
        project                         = label.project             (parent_trace) 

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(scaffolding_purpose + '.' + project)

        return name

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, posting_data_handle, label)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to CapabilityHierarchy_Controller") 
        scaffolding_purpose             = label.scaffoldingPurpose  (my_trace)
        project                         = label.project             (my_trace) 
        
        my_trace                        = parent_trace.doing("Enriching generic manifest fields with additional fields "
                                                                + "specific to CapabilityHierarchy_Controller")
        
        if True:
            metadata                                    = manifest_dict['metadata']

            MY_PL                                       = CapabilityHierarchy_Controller._MyPostingLabel # Abbreviation for readability
            labels                                      = metadata['labels']
            labels[MY_PL._PROJECT]                      = project
            assertion                                   = manifest_dict['assertion']

            assertion[MY_PL._SCAFFOLDING_PURPOSE]       = scaffolding_purpose
        
        return manifest_dict

    class _MyPostingConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for BDD capabiity hierarchy manifests
        '''

        _ENTITY_NAME                    = 'Jobs to be done'

        def __init__(self, kind, manifest_nb, update_policy, controller):
            ME                          = CapabilityHierarchy_Controller._MyPostingConfig
            super().__init__(   kind                = kind, 
                                update_policy       = update_policy, 
                                manifest_nb         = manifest_nb,
                                controller          = controller)

            interval_spec_milestones    = ClosedOpenIntervalSpec(   parent_trace        = None, 
                                                                    splitting_columns   = ['Capabilities', 'Feature', 'Story'],
                                                                    entity_name         = ME._ENTITY_NAME) 

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
            ME                              = CapabilityHierarchy_Controller._MyPostingConfig
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
            ME                      = CapabilityHierarchy_Controller._MyPostingConfig
            return ME._ENTITY_NAME

    class _MyPostingLabel(SkeletonController._MyPostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting BDD capability hierarchy content. 
        '''
        _SCAFFOLDING_PURPOSE        = "scaffoldingPurpose"
        _PROJECT                    = "project"
        def __init__(self, parent_trace, controller):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,

                                mandatory_fields    = [ ME._PROJECT,            ME._SCAFFOLDING_PURPOSE,    # Determine name
                                                        ],
                                date_fields         = [])

        def project(self, parent_trace):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._PROJECT)

        def scaffoldingPurpose(self, parent_trace):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._SCAFFOLDING_PURPOSE)

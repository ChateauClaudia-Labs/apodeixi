from apodeixi.controllers.util.manifest_api         import ManifestAPI
from apodeixi.util.a6i_error                        import ApodeixiError

from apodeixi.controllers.util.skeleton_controller  import SkeletonController

from apodeixi.xli                                   import UpdatePolicy, PostingController, PostingConfig, FixedIntervalSpec

class CapabilityHierarchy_Controller(SkeletonController):
    '''
    Class to process an Excel posting for a BDD feature injection tree. It produces the YAML manifest for it
    and also creates the dolfer structure associated with the injection tree
    '''
    def __init__(self, parent_trace):
        super().__init__(parent_trace)

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

    def getPostingConfig(self, parent_trace, kind):
        '''
        Return a PostingConfig, corresponding to the configuration that this concrete controller supports.
        '''
        ME                          = CapabilityHierarchy_Controller
        update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
        config                      = ME._MyPostingConfig(update_policy)

        return config 

    def getPostingLabel(self, parent_trace):
        '''
        Returns a PostingLabel, corresponding to the what is expected by this concrete controller class.
        '''
        ME                              = CapabilityHierarchy_Controller
        return ME._MyPostingLabel(parent_trace, controller = self)

    def _buildOneManifest(self, parent_trace, url, label, kind, excel_range):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, url, label, kind, excel_range)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to CapabilityHierarchy_Controller") 
        scaffolding_purpose             = label.scaffoldingPurpose  (my_trace)
        project                         = label.project             (my_trace) 
        
        my_trace                        = parent_trace.doing("Enriching generic manifest fields with additional fields "
                                                                + "specific to CapabilityHierarchy_Controller")
        
        if True:
            FMT                                         = PostingController.format_as_yaml_fieldname # Abbreviation for readability
            metadata                                    = manifest_dict['metadata']
            metadata['name']                            = FMT(scaffolding_purpose + '.' + project)

            MY_PL                                       = CapabilityHierarchy_Controller._MyPostingLabel # Abbreviation for readability
            labels                                      = metadata['labels']
            labels[MY_PL._PROJECT]                      = project
            assertion                                   = manifest_dict['assertion']

            assertion[MY_PL._SCAFFOLDING_PURPOSE]       = scaffolding_purpose
        
        return manifest_dict #, label

    def _genExcel(self, parent_trace, url, ctx_range, manifests_dir, manifest_file):
        '''
        Helper function that is amenable to unit testing (i.e., does not require a KnowledgeBase structure for I/O).

        Used to generate an Excel spreadsheet that represents the current state of the manifest, inclusive of UIDs.
        Such Excel spreadsheet is what the user would need to post in order to make changes to the manifest, since pre-existing
        UIDs must be repected.
        '''

    class _MyPostingConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for BDD capabiity hierarchy manifests
        '''

        _ENTITY_NAME                = 'Jobs to be done'

        def __init__(self, update_policy):
            ME                      = CapabilityHierarchy_Controller._MyPostingConfig
            super().__init__()
            self.update_policy      = update_policy

            interval_spec_jobs           = FixedIntervalSpec(None, [ME._ENTITY_NAME, 'Stakeholders']) 
            interval_spec_capabilities   = FixedIntervalSpec(None, ['Capabilities'])
            interval_spec_features       = FixedIntervalSpec(None, ['Feature'])
            interval_spec_stories        = FixedIntervalSpec(None, ['Story'])

            self.interval_specs          = [interval_spec_jobs,     interval_spec_capabilities, 
                                            interval_spec_features, interval_spec_stories]

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

import yaml                             as _yaml
from io                                 import StringIO

from apodeixi.util.a6i_error        import ApodeixiError

from apodeixi.xli                       import ExcelTableReader, \
                                                BreakdownTree, Interval, UID_Store, \
                                                PostingController, PostingLabel, PostingConfig, UpdatePolicy

class CapabilityHierarchy_Controller(PostingController):
    '''
    Class to process an Excel posting for a BDD feature injection tree. It produces the YAML manifest for it
    and also creates the dolfer structure associated with the injection tree
    '''
    def __init__(self):
        return

    def apply(self, parent_trace, knowledge_base_dir, relative_path, excel_filename, excel_sheet, ctx_range):
        '''
        Main entry point to the controller. Retrieves an Excel, parses its content, creates the YAML manifest and saves it.
        '''
        url                 = knowledge_base_dir + '/excel-postings/' + relative_path + '/' + excel_filename + ':' + excel_sheet
        root_trace          = parent_trace.doing("Applying Excel posting", data={'url'  : url})
        manifest_file       = excel_filename.replace('xlsx', 'yaml')
        manifests_dir       = knowledge_base_dir + '/manifests/' + relative_path
        self._genScaffoldingManifest(url, root_trace, ctx_range, manifests_dir, manifest_file)

    def _genScaffoldingManifest(self, parent_trace, url, ctx_range, manifests_dir, manifest_file):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        ME                              = CapabilityHierarchy_Controller
        _DOMAIN                     = "kernel"
        my_trace                        = parent_trace.doing("Parsing posting label", 
                                                                data = {'url': url, 'ctx_range': ctx_range, 
                                                                        'signaled_from': __file__})
        if True:            
            label                       = ME._MyPostingLabel()
            label.read(my_trace, url, ctx_range)    

            environment                 = label.environment         (my_trace)  
            scaffolding_purpose         = label.scaffoldingPurpose  (my_trace)
            project                     = label.project             (my_trace)
            organization                = label.organization        (my_trace)
            recorded_by                 = label.recordedBy          (my_trace)
            excel_range                 = label.dataRange           (my_trace)  

        my_trace                        = parent_trace.doing("Creating BreakoutTree from Excel", 
                                                                data = {'url': url, 'excel_range': excel_range, 
                                                                        'signaled_from': __file__})
        if True:
            update_policy               = UpdatePolicy(reuse_uids=False, merge=False)
            config                      = ME._MyPostingConfig(update_policy)
            tree                        = self._xl_2_tree(my_trace, url, excel_range, config)
            tree_dict                   = tree.as_dicts()
        
        my_trace                        = parent_trace.doing("Creating manifest from BreakoutTree", 
                                                                data = {'project': project, 'organization': organization, 
                                                                        'signaled_from': __file__})
        if True:
            FMT                         = PostingController.format_as_yaml_fieldname # Abbreviation for readability
            manifest_dict               = {}
            metadata                    = { 'namespace':    FMT(organization + '.' + environment), 
                                            'name':         FMT(scaffolding_purpose + '.' + project),
                                            'labels':       {'project': project, 'organization': organization}}

            manifest_dict['apiVersion'] = _DOMAIN + '.a6i.io/v1dev'
            manifest_dict['kind']       = 'ProjectScaffolding'
            manifest_dict['metadata']   = metadata

            manifest_dict['scaffolding'] = {label._RECORDED_BY: recorded_by , 'entity_type': tree.entity_type,
                                            FMT(tree.entity_type): tree_dict}
        
        my_trace                        = parent_trace.doing("Persisting manifest", 
                                                                data = {'manifests_dir': manifests_dir, 'manifest_file': manifest_file})
        if True:
            with open(manifests_dir + '/' + manifest_file, 'w') as file:
                _yaml.dump(manifest_dict, file)
        
        return manifest_dict

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

            interval_jobs           = Interval(None, [ME._ENTITY_NAME, 'Stakeholders']) 
            interval_capabilities   = Interval(None, ['Capabilities'])
            interval_features       = Interval(None, ['Feature'])
            interval_stories        = Interval(None, ['Story'])

            self.intervals               = [interval_jobs, interval_capabilities, interval_features, interval_stories]

        def entity_name(self):
            ME                      = CapabilityHierarchy_Controller._MyPostingConfig
            return ME._ENTITY_NAME

    class _MyPostingLabel(PostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting BDD capability hierarchy content. 
        '''
        _EXCEL_API                  = "excelAPI"
        _SCAFFOLDING_PURPOSE        = "scaffoldingPurpose"
        _PROJECT                    = "project"
        _ORGANIZATION               = 'organization'
        _DATA_RANGE                 = "dataRange"
        _ENVIRONMENT                = 'environment'
        _RECORDED_BY                = 'recordedBy'

        SUPPORTED_APIS              = ['capability-hierarchy.kernel.a6i.xlsx/v1a']

        def __init__(self):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            super().__init__(   mandatory_fields    = [ ME._EXCEL_API,          ME._ORGANIZATION,       ME._PROJECT, 
                                                        ME._SCAFFOLDING_PURPOSE,
                                                        ME._ENVIRONMENT,        ME._RECORDED_BY,        ME._DATA_RANGE],
                                date_fields         = [])

        def read(self, parent_trace, url, excel_range):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            super().read(parent_trace, url, excel_range)

            excel_api = self._getField(parent_trace, ME._EXCEL_API)
            if not excel_api in ME.SUPPORTED_APIS:
                raise ApodeixiError(parent_trace, "Non supported Excel API '" + excel_api + "'"
                                                + "\nShould be one of: " + ME.SUPPORTED_APIS)

        def environment(self, parent_trace):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._ENVIRONMENT)

        def organization(self, parent_trace):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._ORGANIZATION
            )
        def project(self, parent_trace):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._PROJECT)

        def scaffoldingPurpose(self, parent_trace):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._SCAFFOLDING_PURPOSE)

        def recordedBy(self, parent_trace):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._RECORDED_BY)

        def dataRange(self, parent_trace):
            # Shortcut to reference class static variables
            ME = CapabilityHierarchy_Controller._MyPostingLabel

            return self._getField(parent_trace, ME._DATA_RANGE)
        
        def _getField(self, parent_trace, fieldname):
            if self.ctx==None:
                raise ApodeixiError(parent_trace, "PostingLabel's context is not yet initialized, so can't read '" + fieldname + "'")
            
            if not fieldname in self.ctx.keys():
                raise ApodeixiError(parent_trace, "PostingLabel's context does not contain '" + fieldname + "'")
            
            return self.ctx[fieldname]

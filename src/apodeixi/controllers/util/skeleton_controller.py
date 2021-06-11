import yaml                                         as _yaml

from apodeixi.util.a6i_error                        import ApodeixiError

from apodeixi.xli.posting_controller_utils              import PostingController, PostingLabel, PostingConfig
from apodeixi.knowledge_base.knowledge_base_util        import PostResponse
from apodeixi.util.formatting_utils                     import StringUtils


class SkeletonController(PostingController):
    '''
    Abstract class intended to be implemented by classes that adhere to the most common conventions for Posting
    Controllers. It helps by implementing those conventions as a common skeleton that can be re-used by derived classes.

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    '''
    def __init__(self, parent_trace, store):
        super().__init__(parent_trace, store)

    def apply(self, parent_trace, excel_filename, excel_sheet, ctx_range, version=None):
        '''
        Main entry point to the controller. Retrieves an Excel, parses its content, creates the YAML manifest and saves it.

        Returns a PostingResponse.

        '''
        url                         = self.store.discoverPostingURL(parent_trace        = parent_trace, 
                                                                    excel_posting_path  = excel_filename, 
                                                                    sheet=excel_sheet)

        root_trace                  = parent_trace.doing("Applying Excel posting", 
                                                            data={'url'  : url}, 
                                                            origination = {'signaled_from' : __file__})
        manifest_file               = StringUtils().rreplace(excel_filename, 'xlsx', 'yaml')
        all_manifests_dicts, label  = self._buildAllManifests(root_trace, url, ctx_range)

        response                    = PostResponse()
        for manifest_nb in all_manifests_dicts.keys():
            loop_trace              = root_trace.doing("Persisting manifest in store",
                                                        data = {'manifest_nb': manifest_nb}, 
                                                        origination = {'signaled_from' : __file__})
            manifest_dict           = all_manifests_dicts[manifest_nb]
            self.store.persistManifest(root_trace, manifest_dict, version)
            response.recordCreation(parent_trace=loop_trace, manifest_dict=manifest_dict)

        # TODO - Finish the remaining phases of the controller, after creating the manifests. Namely:
        # TODO  1. Move the Excel spreadsheet to a "prior" area
        # TODO  2. Generate the Excel spreadsheet that can be used for updates. This probably must be in the derived controller class

        return response

    def getPostingConfig(self, parent_trace, kind):
        '''
        Implemented by concrete controller classes.
        Must return a PostingConfig, corresponding to the configuration that the concrete controller supports.
        '''
        raise NotImplementedError("Class " + str(self.__class__) + " forgot to implement method getPostingConfig") 

    def getPostingLabel(self, parent_trace):
        '''
        Implemented by concrete controller classes.
        Must return a PostingLabel, corresponding to the need of the concrete controller subclass.
        '''
        raise NotImplementedError("Class " + str(self.__class__) + " forgot to implement method getPostingLabel")

    def _buildAllManifests(self, parent_trace, url, ctx_range):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure.

        Returns 2 things:

        * a dictionary of dictionaries. The keys are integer ids for each manifest, as maintained in 
          the controller's show_your_work metadata for manifests. Values are the manifests themselves, as dictionaries.
        
        * the PostingLabel that was parsed in the process

        '''
        my_trace                            = parent_trace.doing("Parsing posting label", 
                                                                data = {'url': url, 'ctx_range': ctx_range}, 
                                                                origination = {'signaled_from': __file__})
        if True:            
            label                           = self.getPostingLabel(my_trace)
            label.read(my_trace, url, ctx_range)    

        MY_PL                               = SkeletonController._MyPostingLabel

        # Keys will be the manifest unique integer identifiers assigned by _MyPostingLabel._initialize_show_your_work
        all_manifests_dict                 = {} 
        
        for manifest_nb, kind, excel_range in self.show_your_work.manifest_metas():
            my_trace                        = parent_trace.doing("Parsing data for 1 manifest", 
                                                                    data = {'url': url, 'kind': kind, 'excel_range': excel_range},
                                                                    origination = {'signaled_from': __file__})
            manifest_dict                   = self._buildOneManifest(my_trace, url, label, kind, excel_range)
            all_manifests_dict[manifest_nb] = manifest_dict

        return all_manifests_dict, label

    def _buildOneManifest(self, parent_trace, url, label, kind, excel_range):
        '''
        Returns a  dictionary corresponding to the manifest that was built in this method
        '''
        organization                = label.organization        (parent_trace)
        environment                 = label.environment         (parent_trace)  
                    
        recorded_by                 = label.recordedBy          (parent_trace)

        my_trace                        = parent_trace.doing("Creating BreakoutTree from Excel", 
                                                                data = {'url': url, 'excel_range': excel_range}, 
                                                                origination = {'signaled_from': __file__})
        if True:
            config                      = self.getPostingConfig(my_trace, kind)
            tree                        = self._xl_2_tree(my_trace, url, excel_range, config)
            tree_dict                   = tree.as_dicts()
        
        my_trace                        = parent_trace.doing("Creating manifest from BreakoutTree", 
                                                                data = {'organization': organization},
                                                                origination = {'signaled_from': __file__})
        if True:
            FMT                         = PostingController.format_as_yaml_fieldname # Abbreviation for readability
            manifest_dict               = {}
            metadata                    = { 'namespace':    FMT(organization + '.' + environment), 
                                            'labels':       {'organization': organization}}

            manifest_dict['apiVersion'] = self.api_version(my_trace)
            manifest_dict['kind']       = kind
            manifest_dict['metadata']   = metadata

            manifest_dict['assertion']  = {label._RECORDED_BY:                 recorded_by , 
                                            'entity_type':                      tree.entity_type,
                                            FMT(tree.entity_type):              tree_dict}
        return manifest_dict

    def _genExcel(self, parent_trace, url, ctx_range, manifests_dir, manifest_file):
        '''
        Helper function that is amenable to unit testing (i.e., does not require a KnowledgeBase structure for I/O).

        Used to generate an Excel spreadsheet that represents the current state of the manifest, inclusive of UIDs.
        Such Excel spreadsheet is what the user would need to post in order to make changes to the manifest, since pre-existing
        UIDs must be repected.
        '''

    class _MyPostingLabel(PostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting BDD capability hierarchy content. 
        '''
        _EXCEL_API                  = "excelAPI"
        _DATA_KIND                  = "data.kind"
        _ORGANIZATION               = 'organization'
        _DATA_RANGE                 = "data.range"
        _ENVIRONMENT                = 'environment'
        _RECORDED_BY                = 'recordedBy'

        def __init__(self, parent_trace, controller, mandatory_fields, date_fields):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            combined_mandatory_fields               = [ ME._EXCEL_API,          ME._DATA_KIND,              # Determine apiVersion
                                                        ME._ORGANIZATION,       ME._ENVIRONMENT,            # Determine namespace
                                                        ME._RECORDED_BY,
                                                        ME._DATA_RANGE]
            combined_mandatory_fields.extend(mandatory_fields)

            combined_date_fields                    = []
            combined_date_fields.extend(date_fields)

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,
                                mandatory_fields    = combined_mandatory_fields,
                                date_fields         = combined_date_fields)

        def read(self, parent_trace, url, excel_range):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            super().read(parent_trace, url, excel_range)

            # Validate that Excel API in posting is one we know how to handle
            posted_xl_api_version       = self._getField(parent_trace, ME._EXCEL_API)
            required_xl_api             = StringUtils().rreplace(self.controller.getManifestAPI().apiName(), "io", "xlsx")
            supported_xl_api_versions   = [required_xl_api + "/" + version for version in self.controller.getSupportedVersions()]

            if not posted_xl_api_version in supported_xl_api_versions:
                raise ApodeixiError(parent_trace, "Non supported Excel API '" + posted_xl_api_version + "'"
                                                + "\nShould be one of: " + str(supported_xl_api_versions))

            # Validate that kind of domain object(s) in posting is(are) one that we know how to handle, 
            # and save the findings along the way in the controller's show_your_work for later use
            self._initialize_show_your_work(parent_trace)

            for manifest_nb, kind, excel_range in self.controller.show_your_work.manifest_metas():

                supported_data_kinds             = self.controller.getSupportedKinds()
                if not kind in supported_data_kinds:
                    raise ApodeixiError(parent_trace, "Non supported domain object kind '" + kind + "'"
                                                    + "\nShould be one of: " + str(supported_data_kinds))

        def environment(self, parent_trace):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            return self._getField(parent_trace, ME._ENVIRONMENT)

        def organization(self, parent_trace):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            return self._getField(parent_trace, ME._ORGANIZATION
            )

        def recordedBy(self, parent_trace):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            return self._getField(parent_trace, ME._RECORDED_BY)
        
        def _getField(self, parent_trace, fieldname):
            if self.ctx==None:
                raise ApodeixiError(parent_trace, "PostingLabel's context is not yet initialized, so can't read '" + fieldname + "'")
            
            if not fieldname in self.ctx.keys():
                raise ApodeixiError(parent_trace, "PostingLabel's context does not contain '" + fieldname + "'")
            
            return self.ctx[fieldname]

        def _initialize_show_your_work(self, parent_trace):
            '''
            Used to prepare the information needed to retrieve the data for each of the manifests (1 or more) that
            are being posted within the same Excel spreadsheet using a common PostingLabel.

            This method is expected to be called after super().read has been called, since super().read will cause self.sightings
            to be populated. 
            
            This method looks inside self.sightings['data.kind'] and self.sightings['data.range'], both of which should
            be arrays of the same size. For example, [] (if there is only one manifest) or [0, 1, 2] if there are three.

            Based on this it initializes self.controller.show_your_work:

            * Initializes the manifest-specific subdictionaries that are retrieved using kind (e.g., 
              self.controller.show_your_work[kind])

            * Remembers a list of metadata for all manifests, assigning a number to each manifest that can also
              be used as a numerical id of a manifest that is consistent throughout the lifetime of the controller
              object.

            '''

            def _keep_work(parent_trace, manifest_nb, kind_field, range_field): #, result):
                '''
                Helper function to avoid repetitive code in both branches of an if-else
                '''
                FMT                 = PostingController.format_as_yaml_fieldname # Abbreviation for readability
                kind_val            = FMT(self.ctx[kind_field])
                range_val           = self.ctx[range_field]
                my_trace            = parent_trace.doing("Initializing show-my-work memory for manifest of kind '" + kind_val + "'")
                self.controller.show_your_work.include(parent_trace=my_trace, manifest_kind=kind_val, posting_label_field=ME._DATA_KIND)

                my_trace            = parent_trace.doing("Saving manifest kind, range in show_my_work")
                self.controller.show_your_work.keep_manifest_meta(  parent_trace    = my_trace, 
                                                                    manifest_nb     = manifest_nb, 
                                                                    kind            = kind_val, 
                                                                    excel_range     = range_val)


            ME = SkeletonController._MyPostingLabel
            if self.sightings == None:
                raise ApodeixiError(parent_trace, "Can't determine data coordinates because self.sightings has not yet been computed")

            kind_list           = self.sightings[ME._DATA_KIND]
            range_list          = self.sightings[ME._DATA_RANGE]

            if kind_list==None or range_list==None or len(kind_list)!=len(range_list):
                raise ApodeixiError(parent_trace, "PostingLabel has inconsistent " + _DATA_KIND + " and " + _DATA_RANGE 
                                                    + " entries: they should both exist and have the same cardinality")
            if len(kind_list) == 0: # There is only one manifest to build in this case
                kind_field      = ME._DATA_KIND   # The field in the PostingLabel, like 'data.kind.2'
                range_field     = ME._DATA_RANGE
                _keep_work(parent_trace, 0, kind_field, range_field)
                
            else:                   # There are multiple manifests to build in this case
                
                for idx in range(len(kind_list)):
                    kind_field  = ME._DATA_KIND    + '.' + str(kind_list[idx])   # The field in the PostingLabel, like 'data.kind.2'
                    range_field = ME._DATA_RANGE   + '.' + str(range_list[idx])
                    _keep_work(parent_trace, idx, kind_field, range_field) 

import yaml                                     as _yaml
from io                                         import StringIO

from apodeixi.util.a6i_error                    import ApodeixiError

from apodeixi.xli                               import ExcelTableReader, \
                                                    BreakdownTree, Interval, UID_Store, \
                                                    PostingController, PostingLabel, PostingConfig, UpdatePolicy

class SkeletonController(PostingController):
    '''
    Abstract class intended to be implemented by classes that adhere to the most common conventions for Posting
    Controllers. It helps by implementing those conventions as a common skeleton that can be re-used by derived classes.
    '''
    def __init__(self, parent_trace):
        super().__init__()

    def apply(self, parent_trace, knowledge_base_dir, relative_path, excel_filename, excel_sheet, ctx_range):
        '''
        Main entry point to the controller. Retrieves an Excel, parses its content, creates the YAML manifest and saves it.

        '''
        url                         = knowledge_base_dir + '/excel-postings/' + relative_path + '/' + excel_filename \
                                                                                                        + ':' + excel_sheet
        root_trace                  = parent_trace.doing("Applying Excel posting", data={'url'  : url})
        manifest_file               = excel_filename.replace('xlsx', 'yaml')
        manifests_dir               = knowledge_base_dir + '/manifests/' + relative_path
        all_manifests_dicts, label  = self._buildAllManifests(root_trace, url, ctx_range)

        for manifest_dict in all_manifests_dicts:
            self._saveManifest(root_trace, manifest_dict, manifests_dir, manifest_file)

    def getPostingConfig(self):
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

        Returns two things:

        * a list of dictionaries, one per manifest, which can then be potentially enriched by parent classes, or persisted.
        * the PostingLabel that was parsed in the process
        '''
        my_trace                        = parent_trace.doing("Parsing posting label", 
                                                                data = {'url': url, 'ctx_range': ctx_range, 
                                                                        'signaled_from': __file__})
        if True:            
            label                       = self.getPostingLabel(my_trace)
            label.read(my_trace, url, ctx_range)    

        MY_PL                           = SkeletonController._MyPostingLabel

        all_manifests_dicts             = [] # Will be a list of dictionaries, one per manifest
        for kind_range_dict in label._kinds_and_ranges(parent_trace): # One per manifest to build
            kind                        = kind_range_dict[MY_PL._DATA_KIND]
            excel_range                 = kind_range_dict[MY_PL._DATA_RANGE]
            my_trace                        = parent_trace.doing("Parsing data for 1 manifest", 
                                                                    data = {'url': url, 'kind': kind, 'excel_range': excel_range,
                                                                            'signaled_from': __file__})
            manifest_dict                   = self._buildOneManifest(my_trace, url, label, kind, excel_range)
            all_manifests_dicts.append(manifest_dict)
        return all_manifests_dicts, label

    def _buildOneManifest(self, parent_trace, url, label, kind, excel_range):
        organization                = label.organization        (parent_trace)
        environment                 = label.environment         (parent_trace)  
                    
        recorded_by                 = label.recordedBy          (parent_trace)

        my_trace                        = parent_trace.doing("Creating BreakoutTree from Excel", 
                                                                data = {'url': url, 'excel_range': excel_range, 
                                                                        'signaled_from': __file__})
        if True:
            config                      = self.getPostingConfig()
            tree                        = self._xl_2_tree(my_trace, url, excel_range, config)
            tree_dict                   = tree.as_dicts()
        
        my_trace                        = parent_trace.doing("Creating manifest from BreakoutTree", 
                                                                data = {'organization': organization, 
                                                                        'signaled_from': __file__})
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


    def _saveManifest(self, parent_trace, manifest_dict, manifests_dir, manifest_file):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        my_trace                        = parent_trace.doing("Persisting manifest", 
                                                                data = {'manifests_dir': manifests_dir, 'manifest_file': manifest_file})
        if True:
            with open(manifests_dir + '/' + manifest_file, 'w') as file:
                _yaml.dump(manifest_dict, file)        


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
            required_xl_api             = self.controller.getManifestAPI().apiName().replace("io", "xlsx")
            supported_xl_api_versions   = [required_xl_api + "/" + version for version in self.controller.getSupportedVersions()]

            if not posted_xl_api_version in supported_xl_api_versions:
                raise ApodeixiError(parent_trace, "Non supported Excel API '" + posted_xl_api_version + "'"
                                                + "\nShould be one of: " + str(supported_xl_api_versions))

            # Validate that kind of domain object in posting is one we know how to handle
            kind                        = self._getField(parent_trace, ME._DATA_KIND)
            supported_DATA_KINDs             = self.controller.getSupportedKinds()
            if not kind in supported_DATA_KINDs:
                raise ApodeixiError(parent_trace, "Non supported domain object kind '" + kind + "'"
                                                + "\nShould be one of: " + str(supported_DATA_KINDs))

        def kind(self, parent_trace):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            return self._getField(parent_trace, ME._DATA_KIND)

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

        def dataRange(self, parent_trace):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            return self._getField(parent_trace, ME._DATA_RANGE)
        
        def _getField(self, parent_trace, fieldname):
            if self.ctx==None:
                raise ApodeixiError(parent_trace, "PostingLabel's context is not yet initialized, so can't read '" + fieldname + "'")
            
            if not fieldname in self.ctx.keys():
                raise ApodeixiError(parent_trace, "PostingLabel's context does not contain '" + fieldname + "'")
            
            return self.ctx[fieldname]

        def _kinds_and_ranges(self, parent_trace):
            '''
            Used to prepare the information needed to retrieve the data for each of the manifests (1 or more) that
            are being posted within the same Excel spreadsheet using a common PostingLabel.

            This method is expected to be called after self.read has been called, since self.read will cause self.sightings
            to be populated. 
            
            This method looks inside self.sightings['data.kind'] and self.sightings['data.range'], both of which should
            be arrays of the same size. For example, [] (if there is only one manifest) or [0, 1, 2] if there are three.
            based on this the right lookups are made into self.ctx and a list of dictionaries is assembled. There is
            one dictionary in the list for each manifest to be built, and each manifest's dictionary
            has two entries, with keys 'data.kind' and 'data.range', and the values for those
            entries are the Excel ranges for the manifest in question.

            This list of dictionaries is returned.
            '''
            ME = SkeletonController._MyPostingLabel
            if self.sightings == None:
                raise ApodeixiError(parent_trace, "Can't determine data coordinates because self.sightings has not yet been computed")

            kind_list           = self.sightings[ME._DATA_KIND]
            range_list          = self.sightings[ME._DATA_RANGE]

            if kind_list==None or range_list==None or len(kind_list)!=len(range_list):
                raise ApodeixiError(parent_trace, "PostingLabel has inconsistent " + _DATA_KIND + " and " + _DATA_RANGE 
                                                    + " entries: they should both exist and have the same cardinality")
            result              = []

            if len(kind_list) == 0: # There is only one manifest to build in this case
                result.append({ ME._DATA_KIND:  self.ctx[ME._DATA_KIND], 
                                ME._DATA_RANGE: self.ctx[ME._DATA_RANGE]})
                
            else:                   # There are multiple manifests to build in this case
                for idx in range(kind_list):
                    kind_field      = ME._DATA_KIND    + '.' + str(kind_list[idx])      # The field in the PostingLabel, like 'data.kind.2'
                    range_field     = ME._DATA_RANGE   + '.' + str(range_list[idx])
                    result.append({ ME._DATA_KIND:  self.ctx[kind_field], 
                                    ME._DATA_RANGE: self.ctx[range_field]})

            return result
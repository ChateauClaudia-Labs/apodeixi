import yaml                                         as _yaml

from apodeixi.util.a6i_error                        import ApodeixiError

from apodeixi.xli.posting_controller_utils              import PostingController, PostingLabel, PostingConfig
from apodeixi.knowledge_base.knowledge_base_util        import PostResponse, ManifestUtils
from apodeixi.util.formatting_utils                     import StringUtils


class SkeletonController(PostingController):
    '''
    Abstract class intended to be implemented by classes that adhere to the most common conventions for Posting
    Controllers. It helps by implementing those conventions as a common skeleton that can be re-used by derived classes.

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    '''
    def __init__(self, parent_trace, store):
        super().__init__(parent_trace, store)

    def apply(self, parent_trace, excel_filename, excel_sheet, ctx_range):
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
            self.store.persistManifest(root_trace, manifest_dict)
            response.recordCreation(parent_trace=loop_trace, manifest_dict=manifest_dict)

        # TODO - Finish the remaining phases of the controller, after creating the manifests. Namely:
        # TODO  1. Move the Excel spreadsheet to a "prior" area
        # TODO  2. Generate the Excel spreadsheet that can be used for updates. This probably must be in the derived controller class

        return response

    def nextVersion(self, parent_trade, manifest_nb):
        '''
        Returns an int, corresponding to the version number that should be used if the manifest identified by
        the int `manifest_nb` needs to be persisted.
        '''
        return 1 # Hard-coded for now. TODO - compute it based on a lookup in the store for the last version of the manifest

    def getPostingConfig(self, parent_trace, kind, manifest_nb):
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

    def _buildAllManifests(self, parent_trace, url, ctx_range="B2:C100"):
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
        
        for manifest_nb, kind, excel_range, excel_sheet in self.show_your_work.manifest_metas():
            my_trace                        = parent_trace.doing("Parsing data for 1 manifest", 
                                                                    data = {'url': url, 'kind': kind, 'excel_range': excel_range},
                                                                    origination = {'signaled_from': __file__})
            manifest_url                    = SkeletonController._build_manifest_url(   posting_url             = url, 
                                                                                        manifest_excel_sheet    = excel_sheet)
            manifest_dict                   = self._buildOneManifest(   parent_trace        = my_trace, 
                                                                        manifest_nb         = manifest_nb, 
                                                                        url                 = manifest_url, 
                                                                        label               = label, 
                                                                        kind                = kind, 
                                                                        excel_range         = excel_range)
                
            all_manifests_dict[manifest_nb] = manifest_dict

        return all_manifests_dict, label

    def _build_manifest_url(posting_url, manifest_excel_sheet):
        posting_excel_sheet                 = posting_url.split(":")[-1]
        excel_path_length                   = len(posting_url) - len(posting_excel_sheet) - 1 # Subtract 1 for the ":" delimeter
        excel_path                          = posting_url[0:excel_path_length]
        manifest_url                        = excel_path + ":" + manifest_excel_sheet
        return manifest_url

    def _buildOneManifest(self, parent_trace, manifest_nb, url, label, kind, excel_range):
        '''
        Returns a  dictionary corresponding to the manifest that was built in this method
        '''
        organization                = label.organization        (parent_trace)
        environment                 = label.environment         (parent_trace)  
                    
        recorded_by                 = label.recordedBy          (parent_trace)
        estimated_by                = label.estimatedBy         (parent_trace)
        estimated_on                = label.estimatedOn         (parent_trace)

        _VERSION                    = "version" # Refers to the version of the manifest, not of the posting
        my_trace                    = parent_trace.doing("Computing the version number to use for the manifest",
                                                            data = {    "manifest_nb":  str(manifest_nb),
                                                                        "kind":         str(kind)})
        next_version                = self.nextVersion(my_trace,manifest_nb)

        my_trace                        = parent_trace.doing("Creating BreakoutTree from Excel", 
                                                                data = {'url': url, 'excel_range': excel_range}, 
                                                                origination = {'signaled_from': __file__})
        if True:
            config                      = self.getPostingConfig(    parent_trace        = my_trace, 
                                                                    kind                = kind,
                                                                    manifest_nb         = manifest_nb)
            tree                        = self._xl_2_tree(my_trace, url, excel_range, config)
            tree_dict                   = tree.as_dicts()
        
        my_trace                        = parent_trace.doing("Creating manifest from BreakoutTree", 
                                                                data = {'organization': organization},
                                                                origination = {'signaled_from': __file__})
        if True:
            FMT                         = PostingController.format_as_yaml_fieldname # Abbreviation for readability
            manifest_dict               = {}
            metadata                    = { 'namespace':    FMT(organization + '.' + environment), 
                                            'labels':       {   label._ORGANIZATION:    organization,
                                                                label._ENVIRONMENT:     environment,
                                                                label._RECORDED_BY:     recorded_by,
                                                                label._ESTIMATED_BY:    estimated_by,
                                                                label._ESTIMATED_ON:    estimated_on,
                                                            }
                                            }

            manifest_dict['apiVersion'] = self.api_version(my_trace)
            manifest_dict['kind']       = kind
            manifest_dict['metadata']   = metadata

            manifest_dict['assertion']  = { label._RECORDED_BY:                 recorded_by ,
                                            label._ESTIMATED_BY:                estimated_by, 
                                            label._ESTIMATED_ON:                estimated_on,
                                            'entity_type':                      tree.entity_type,
                                            FMT(tree.entity_type):              tree_dict}
            
            ManifestUtils().set_manifest_version(   parent_trace        = parent_trace, 
                                                    manifest_dict       = manifest_dict, 
                                                    manifest_version    = next_version)
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
        _DATA_RANGE                 = "data.range"
        _DATA_SHEET                 = "data.sheet"
        _ORGANIZATION               = 'organization'
        _ENVIRONMENT                = 'environment'
        _RECORDED_BY                = 'recordedBy'
        _ESTIMATED_BY               = 'estimatedBy'
        _ESTIMATED_ON               = 'estimatedOn'

        _POSTING_VERSION            = "postingVersion"

        def __init__(self, parent_trace, controller, mandatory_fields, optional_fields = [], date_fields = []):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            combined_mandatory_fields               = [ ME._EXCEL_API,          ME._DATA_KIND,              # Determine apiVersion
                                                        ME._ORGANIZATION,       ME._ENVIRONMENT,            # Determine namespace
                                                        ME._RECORDED_BY,        ME._ESTIMATED_BY,       ME._ESTIMATED_ON,
                                                        ME._DATA_RANGE]
            combined_mandatory_fields.extend(mandatory_fields)

            combined_optional_fields                = [ME._DATA_SHEET]
            combined_optional_fields.extend(optional_fields)

            combined_date_fields                    = [ME._ESTIMATED_ON]
            combined_date_fields.extend(date_fields)

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,
                                mandatory_fields    = combined_mandatory_fields,
                                optional_fields     = combined_optional_fields,
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
            self._initialize_show_your_work(parent_trace, url)

            for manifest_nb, kind, excel_range, excel_sheet in self.controller.show_your_work.manifest_metas():

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
        
        def estimatedBy(self, parent_trace):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            return self._getField(parent_trace, ME._ESTIMATED_BY)

        def estimatedOn(self, parent_trace):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            dt  = self._getField(parent_trace, ME._ESTIMATED_ON)
            return dt

        def postingVersion(self, parent_trace):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            return self._getField(parent_trace, ME._POSTING_VERSION)

        def _getField(self, parent_trace, fieldname):
            if self.ctx==None:
                raise ApodeixiError(parent_trace, "PostingLabel's context is not yet initialized, so can't read '" + fieldname + "'")
            
            if not fieldname in self.ctx.keys():
                raise ApodeixiError(parent_trace, "PostingLabel's context does not contain '" + fieldname + "'")
            
            return self.ctx[fieldname]

        def _initialize_show_your_work(self, parent_trace, url):
            '''
            Used to prepare the information needed to retrieve the data for each of the manifests (1 or more) that
            are being posted within the same Excel spreadsheet using a common PostingLabel.

            This method is expected to be called after super().read has been called, since super().read will cause self.sightings
            to be populated. 
            
            This method looks inside self.sightings['data.kind'] and self.sightings['data.range'], both of which should
            be arrays of the same size. For example, [] (if there is only one manifest) or [0, 1, 2] if there are three.

            Optionally, the user may have specified 'data.sheet.0', 'data.sheet.1', 'data.sheet.2', say, if the data resides
            in a different Excel worksheet than the one containing this Posting Label. So this method also inquires on
            whether self.sightings['data.sheet'] exists and if so it will also process it just like the others.

            If the user did nost specify 'data.sheet.x' fields, then it will be defaulted to the same sheet containing
            this Posting Label by inferring it from the `url`

            Based on this it initializes self.controller.show_your_work:

            * Initializes the manifest-specific subdictionaries that are retrieved using kind (e.g., 
              self.controller.show_your_work[kind])

            * Remembers a list of metadata for all manifests, assigning a number to each manifest that can also
              be used as a numerical id of a manifest that is consistent throughout the lifetime of the controller
              object.

            '''

            def _keep_work(parent_trace, manifest_nb, kind_field, range_field, sheet_field):
                '''
                Helper function to avoid repetitive code in both branches of an if-else
                '''
                FMT                 = PostingController.format_as_yaml_fieldname # Abbreviation for readability
                kind_val            = FMT(self.ctx[kind_field])
                range_val           = self.ctx[range_field]
                sheet_val           = self.ctx[sheet_field]
                my_trace            = parent_trace.doing("Initializing show-my-work memory for manifest of kind '" + kind_val + "'")
                #self.controller.show_your_work.include(parent_trace=my_trace, manifest_kind=kind_val, posting_label_field=ME._DATA_KIND)

                my_trace            = parent_trace.doing("Saving manifest kind, range in show_my_work")
                self.controller.show_your_work.keep_manifest_meta(  parent_trace    = my_trace, 
                                                                    manifest_nb     = manifest_nb, 
                                                                    kind            = kind_val, 
                                                                    excel_range     = range_val,
                                                                    excel_sheet     = sheet_val)

            def _check_lists_match(parent_trace, list_dict):
                '''
                Helper method to raise an exception if a set of lists are not identical.
                The lists have names and passed in a dictionary with the names as keys. For example,
                for key 'kind' and list [1, 2, 3], this is passed by setting list_dict['kind'] = [1, 2, 3]
                '''
                missing_lists           = []
                different_lists         = False
                common_list            = None
                all_fields              = list(list_dict.keys())
                for key in all_fields:
                    a_list              = list_dict[key]
                    if a_list == None:
                        missing_lists.append(key)
                    if common_list == None and a_list != None: # First cycle in loop that has a list, so initialize common_list
                        common_list     = a_list
                    if a_list != common_list:
                        different_lists = True

                if len(missing_lists) > 0:
                    raise ApodeixieError(parent_trace, "Posting label lacks values for some fields",
                                                        data = {'missing fields': ','.join(missing_lists)})
                if different_lists:
                    msg_dict            = {}
                    for key in all_fields:
                        msg_dict[key]   = ",".join(list_dict[key])
                    raise ApodeixiError(parent_trace, "Posting label has inconsistent entries for " + ",".join(all_fields) 
                                                    + ": they should both exist and have the same suffixes",
                                                    data = msg_dict)

            ME                  = SkeletonController._MyPostingLabel
            if self.sightings == None:
                raise ApodeixiError(parent_trace, "Can't determine data coordinates because self.sightings has not yet been computed")

            kind_list           = self.sightings[ME._DATA_KIND]
            range_list          = self.sightings[ME._DATA_RANGE]

            sheet_list          = self._default_sheet_if_needed(parent_trace, kind_list, url)


            _check_lists_match(parent_trace, {  ME._DATA_KIND:          kind_list,
                                                ME._DATA_RANGE:         range_list,
                                                ME._DATA_SHEET:         sheet_list})

            if len(kind_list) == 0: # There is only one manifest to build in this case
                kind_field      = ME._DATA_KIND   # The field in the PostingLabel, like 'data.kind.2'
                range_field     = ME._DATA_RANGE
                sheet_field     = ME._DATA_SHEET
                _keep_work(parent_trace, 0, kind_field, range_field, sheet_field)
                
            else:                   # There are multiple manifests to build in this case
                
                for idx in range(len(kind_list)):
                    kind_field  = ME._DATA_KIND    + '.' + str(kind_list[idx])   # The field in the PostingLabel, like 'data.kind.2'
                    range_field = ME._DATA_RANGE   + '.' + str(range_list[idx])
                    sheet_field = ME._DATA_SHEET   + '.' + str(sheet_list[idx])
                    _keep_work(parent_trace, idx, kind_field, range_field, sheet_field) 

        def _default_sheet_if_needed(self, parent_trace, suffix_list, url):
            '''
            Helper method to default the Excel sheet to use for each manifest in situations where the user has not specified it.
            If the user has specified it, then it just returns the suffixes associated to it by the user.
            If not, then it defaults it inside self.ctx, and returns the suffix_list.
            '''
            ME                              = SkeletonController._MyPostingLabel
            sheet_field                     = ME._DATA_SHEET
            result                          = None
            if sheet_field in self.sightings.keys():
                result                      = self.sightings[ME._DATA_SHEET]
            else: # User did not specify any sheet fields, so must default them from the url
                default_sheet               = url.split(":")[-1]
                if len(suffix_list) == 0:
                    self.ctx[sheet_field]   = default_sheet
                else:
                    for idx in suffix_list:
                        self.ctx[sheet_field + "." + str(idx)]   = default_sheet
                result                      = suffix_list

            return result
import yaml                                             as _yaml
import os                                               as _os

from apodeixi.util.a6i_error                            import ApodeixiError

from apodeixi.xli.posting_controller_utils              import PostingController, PostingLabel, PostingConfig
from apodeixi.knowledge_base.knowledge_base_util        import PostResponse, ManifestUtils, PostingDataHandle, \
                                                                PostingLabelHandle, FormRequestResponse
from apodeixi.knowledge_base.filing_coordinates         import TBD_FilingCoordinates
from apodeixi.representers.as_dataframe                 import AsDataframe_Representer
from apodeixi.representers.as_excel                     import Manifest_Representer

from apodeixi.text_layout.excel_layout                  import AsExcel_Config_Table, ManifestXLConfig, PostingLabelXLConfig
from apodeixi.util.formatting_utils                     import StringUtils


class SkeletonController(PostingController):
    '''
    Abstract class intended to be implemented by classes that adhere to the most common conventions for Posting
    Controllers. It helps by implementing those conventions as a common skeleton that can be re-used by derived classes.

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    '''
    def __init__(self, parent_trace, store):
        super().__init__(parent_trace, store)

        # Internally computed data, maintained to assist with testing and debugging.
        self.log_txt                = None
        self.representer            = None

    GENERATED_FORM_WORKSHEET            = "Assertions"
    POSTING_LABEL_SHEET                 = "Posting Label"
    POSTING_LABEL_RANGE                 = "B2:C100"

    def apply(self, parent_trace, posting_label_handle):
        '''
        Main entry point to the controller. Retrieves an Excel, parses its content, creates the YAML manifest and saves it.

        Returns a PostResponse.

        '''
        excel_filename              = posting_label_handle.excel_filename

        root_trace                  = parent_trace.doing("Applying Excel posting", 
                                                            origination = {'signaled_from' : __file__})
        manifest_file               = StringUtils().rreplace(excel_filename, 'xlsx', 'yaml')
        all_manifests_dicts, label  = self._buildAllManifests(root_trace, posting_label_handle)

        response                    = PostResponse()
        for manifest_nb in all_manifests_dicts.keys():
            loop_trace              = root_trace.doing("Persisting manifest in store",
                                                        data = {'manifest_nb': manifest_nb}, 
                                                        origination = {'signaled_from' : __file__})
            manifest_dict           = all_manifests_dicts[manifest_nb]
            self.store.persistManifest(root_trace, manifest_dict)
            response.recordCreation(parent_trace=loop_trace, manifest_dict=manifest_dict)

        my_trace                    = parent_trace.doing("Archiving posting after successfully parsing it and "
                                                            + "creating manifests",
                                                            data = {"excel_filename": excel_filename})
        archival_handle             = self.store.archivePosting(my_trace, posting_label_handle)
        response.recordArchival(my_trace, posting_label_handle, archival_handle)

        manifest_handles            = [h for h in response.createdManifests() + response.updatedManifests()]
        form_request                = posting_label_handle.createUpdateForm(my_trace, manifest_handles)
        response.recordOptionalForm(my_trace, form_request)

        self.log_txt                = self.store.logPostEvent(my_trace, response)

        return response

    def generateForm(self, parent_trace, form_request):
        '''
        Generates and saves an Excel spreadsheet that the caller can complete and then submit
        as a posting

        Returns a FormRequestResponse object, as well as a string corresponding the log made during the processing.
        '''
        ME                                  = SkeletonController
        my_trace                            = parent_trace.doing("Loading manifests requested in the form")
        if True:
            manifest_handles_dict               = form_request.manifestHandles(my_trace)
            manifestInfo_dict                   = {}
            contents_df_dict                    = {} # needed for Manifest_Representer
            for key in manifest_handles_dict.keys():
                manifest_handle                 = manifest_handles_dict[key]
                loop_trace                      = my_trace.doing("Loading manifest",
                                                                    data = {"handle": manifest_handle.display(my_trace)})
                manifest_info                   = ME._ManifestInfo( parent_trace            = loop_trace,
                                                                    key                     = key,
                                                                    manifest_handle         = manifest_handle, 
                                                                    form_request            = form_request, 
                                                                    controller              = self)
                manifestInfo_dict[key]          = manifest_info
                # This other dictionary of dataframes is needed for Manifest_Representer
                data_df                         = manifest_info.getManifestContents(my_trace)
                contents_df_dict[key]           = data_df

        my_trace                            = parent_trace.doing("Creating Excel layouts for manifests")
        config_table                        = self._build_manifestsXLconfig(    parent_trace        = parent_trace, 
                                                                                manifestInfo_dict   = manifestInfo_dict)

        my_trace                            = parent_trace.doing("Creating Excel layouts for posting label")
        label, label_config                 = self._build_labelXLconfig(my_trace, manifestInfo_dict)
        config_table.setPostingLabelXLConfig(my_trace, label_config)

        my_trace                            = parent_trace.doing("Writing out the Excel spreadsheet requested")
        
        if True:
            rep                             = Manifest_Representer( config_table    = config_table,
                                                                    label_ctx       = label.ctx,
                                                                    content_df_dict = contents_df_dict,)
            filename                        = self.store.uploadForm(my_trace, 
                                                                    form_request    = form_request, 
                                                                    representer     = rep)

        my_trace                            = parent_trace.doing("Assembling FormRequest response")     
        if True:
            response_handle                     = PostingLabelHandle(   
                                                        parent_trace            = my_trace,
                                                        excel_filename          = filename,
                                                        excel_sheet             = SkeletonController.POSTING_LABEL_SHEET,
                                                        excel_range             = SkeletonController.POSTING_LABEL_RANGE,
                                                        posting_api             = form_request.getPostingAPI(my_trace), 
                                                        filing_coords           = form_request.getFilingCoords(my_trace), 
                                                        )

            env_config                          = self.store.current_environment(parent_trace).config(parent_trace)
            response                            = FormRequestResponse(self.store.getClientURL(my_trace),
                                                                        path_mask   = env_config.path_mask)
            response.recordClientURLCreation(parent_trace=my_trace, response_handle=response_handle)

            self.log_txt                        = self.store.logFormRequestEvent(my_trace, form_request, response)
            self.representer                    = rep

            return response

    def _build_manifestsXLconfig(self, parent_trace, manifestInfo_dict):
        '''
        Creates and returns an AsExcel_Config_Table containing the configuration data for how to lay out and format
        all the manifests of `manifestInfo_dict` onto an Excel spreadsheet
        '''
        config_table                        = AsExcel_Config_Table()
        x_offset                            = 1
        y_offset                            = 1
        for key in manifestInfo_dict:
            loop_trace                      = parent_trace.doing("Creating layout configurations for manifest '"
                                                                + str(key) + "'")
            manifest_info                   = manifestInfo_dict[key]
            data_df                         = manifest_info.getManifestContents(parent_trace)
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            config                          = ManifestXLConfig( sheet               = SkeletonController.GENERATED_FORM_WORKSHEET,
                                                                manifest_name       = key,    
                                                                viewport_width      = 100,  
                                                                viewport_height     = 40,   
                                                                max_word_length     = 20, 
                                                                editable_cols       = editable_cols,
                                                                hidden_cols         = [],
                                                                num_formats         = {},   
                                                                editable_headers    = [],   
                                                                x_offset            = x_offset,    
                                                                y_offset            = y_offset)
            # Put next manifest to the right of this one, separated by an empty column
            x_offset                        += data_df.shape[1] + 1 
            config_table.addManifestXLConfig(loop_trace, config)
        return config_table

    def _build_labelXLconfig(self, parent_trace, manifestInfo_dict):
        '''
        Helper method used as part of processing a FormRequest

        It creates a PostingLabelXLConfig object that should be used in the generation of the
        Excel spreadsheet (the "form") that was requested by the FormRequest. In the process it also creates a 
        PostingLabel object.

        It returns a pair: the PostingLabel, and the PostingLabelXLConfig
        '''
        label                               = self.getPostingLabel(parent_trace)
        label_editable_fields               = None
        for key in manifestInfo_dict.keys():
            loop_trace                      = parent_trace.doing("Checking label editable fields for manifest '" 
                                                                + str(key) + "'")
            manifest_info                   = manifestInfo_dict[key]
            manifest_dict                   = manifest_info.getManifestDict(loop_trace)
            proposed_editable_fields        = label.infer(loop_trace, manifest_dict)
            if label_editable_fields == None: # Initialize them
                label_editable_fields             = proposed_editable_fields
            elif proposed_editable_fields != label_editable_fields: 
                raise ApodeixiError(loop_trace, "Can't generate form since manifests disagree on which fields should be"
                                                + " editable in the PostingLabel of the form being requested") 

        my_trace                            = parent_trace.doing("Inferring posting label", 
                                                                origination = {'signaled_from': __file__})

        my_trace                            = parent_trace.doing("Creating Excel layout for Posting Label")
        
        label_config                        = PostingLabelXLConfig( sheet               = SkeletonController.POSTING_LABEL_SHEET,
                                                                    viewport_width      = 100,  
                                                                    viewport_height     = 40,   
                                                                    max_word_length     = 20, 
                                                                    editable_fields     = label_editable_fields, 
                                                                    date_fields         = label.date_fields,  
                                                                    x_offset            = 1,    
                                                                    y_offset            = 1)

        return label, label_config
    
    class _ManifestInfo():
        '''
        Helper data structure to group related information about a manifest that is gradually built or used in the process
        of handling a FormRequest that includes such manifest

        @param controller A an object of a class derived from SkeletonController, which contains this _Manifest_info
                class as an inner class
        '''
        def __init__(self, parent_trace, key, manifest_handle, form_request, controller):
            self._key                       = key
            self._manifest_handle           = manifest_handle  
            self._controller                = controller
            self._form_request              = form_request

            # These are build later 
            self._manifest_dict             = self._retrieveManifest(parent_trace)
            self._contents_df               = self._buildManifestContent(parent_trace)
            return

        def _retrieveManifest(self, parent_trace):
            '''
            Loads the YAML manifest and returns a dict representing it
            '''
            manifest_handles_dict           = self._form_request.manifestHandles(parent_trace)

            if self._key == None or not self._key in manifest_handles_dict.keys():
                raise ApodeixiError(parent_trace, "Key does not identify any ManifestHandle in the FormRequest",
                                                    data = {"key": self._key})

            manifest_handle                 = manifest_handles_dict[self._key]
            my_trace                        = parent_trace.doing("Loading manifest as a DataFrame",
                                                                 data = {"handle": manifest_handle.display(parent_trace)})
            manifest_dict, manifest_path    = self._controller.store.retrieveManifest(my_trace, manifest_handle)
            return manifest_dict
            
        def getManifestDict(self, parent_trace):
            self._abort_if_null_manifest(parent_trace)
            return self._manifest_dict

        def getManifestContents(self, parent_trace):
            self._abort_if_null_manifest(parent_trace)
            return self._contents_df

        def _buildManifestContent(self, parent_trace):
            '''
            Returns a DataFrame, corresponding to the manifest's contents of
            '''
            self._abort_if_null_manifest(parent_trace)

            kind                            = self._manifest_dict['kind']
            posting_config                  = self._controller.getPostingConfig(parent_trace, 
                                                                    kind, 
                                                                    self._form_request.manifest_nb(parent_trace, self._key)) 
            entity                          = posting_config.entity_as_yaml_fieldname()

            content_dict                    = self._manifest_dict['assertion'][entity]
            rep                             = AsDataframe_Representer()
            contents_path                   = 'assertion.' + entity
            contents_df                     = rep.dict_2_df(parent_trace, content_dict, contents_path)
        
            return contents_df

        def _abort_if_null_manifest(self, parent_trace):
            if self._manifest_dict == None:
                raise ApodeixiError(parent_trace, "_ManifestInfo has a null manifest - did you forget to retrieve it "
                                                + "ahead of this point in the processing?",
                                                data = {"manifest key": str(self._key)})


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

    def _buildAllManifests(self, parent_trace, posting_label_handle):
        '''
        Helper function, amenable to unit testing.
        Returns 2 things:

        * a dictionary of dictionaries. The keys are integer ids for each manifest, as maintained in 
          the controller's show_your_work metadata for manifests. Values are the manifests themselves, as dictionaries.
        
        * the PostingLabel that was parsed in the process

        '''
        my_trace                            = parent_trace.doing("Parsing posting label", 
                                                                origination = {'signaled_from': __file__})
        if True:            
            label                           = self.getPostingLabel(my_trace)
            label.read(my_trace, posting_label_handle)     

            # If we used a 'TBD' filing coordinates in the posting handle because the 'real' filing coordinates
            # were not known when the posting was submitted, this is the time to fill out that 'TBD' placeholder
            if type(posting_label_handle.filing_coords) == TBD_FilingCoordinates:
                posting_label_handle.filing_coords.inferFilingCoords( my_trace, label)

        MY_PL                               = SkeletonController._MyPostingLabel

        # Keys will be the manifest unique integer identifiers assigned by _MyPostingLabel._initialize_show_your_work
        all_manifests_dict                 = {} 
        
        for data_handle in self.getDataHandles(parent_trace, posting_label_handle):
            kind                            = data_handle.kind
            manifest_nb                     = data_handle.manifest_nb
            excel_range                     = data_handle.excel_range
            
            my_trace                        = parent_trace.doing("Parsing data for 1 manifest", 
                                                                    data = {'kind': kind, 'excel_range': excel_range},
                                                                    origination = {'signaled_from': __file__})

            manifest_dict                   = self._buildOneManifest(   parent_trace        = my_trace, 
                                                                        posting_data_handle = data_handle,
                                                                        label               = label)
                
            all_manifests_dict[manifest_nb] = manifest_dict

        return all_manifests_dict, label

    def getDataHandles(self, parent_trace, posting_label_handle):
        '''
        Returns a list of PostingDataHandle objects, one for each manifest whose posting needs to be processed
        '''
        result                  = []
        excel_filename          = posting_label_handle.excel_filename
        filing_coords           = posting_label_handle.filing_coords

        for manifest_nb, kind, excel_range, excel_sheet in self.show_your_work.manifest_metas():
            loop_trace          = parent_trace.doing("Creating PostingDataHandle for manifest " + str(manifest_nb),
                                                        data = {"kind": kind})

            data_handle         = posting_label_handle.buildDataHandle(    
                                                        parent_trace        = loop_trace,
                                                        manifest_nb         = manifest_nb,
                                                        kind                = kind,
                                                        excel_sheet         = excel_sheet,
                                                        excel_range         = excel_range)
            result.append(data_handle)
        return result

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Returns a  dictionary corresponding to the manifest that was built in this method
        '''
        manifest_nb                 = posting_data_handle.manifest_nb
        kind                        = posting_data_handle.kind

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
        
        relative_path                   = posting_data_handle.getRelativePath(my_trace)
        my_trace                        = parent_trace.doing("Creating BreakoutTree from Excel", 
                                                                data = {"relative_path": relative_path},
                                                                origination = {'signaled_from': __file__})
        if True:
            config                      = self.getPostingConfig(    parent_trace        = my_trace, 
                                                                    kind                = kind,
                                                                    manifest_nb         = manifest_nb)
            tree                        = self._xl_2_tree(my_trace, posting_data_handle, config)
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

    class _MyPostingLabel(PostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting BDD capability hierarchy content. 
        '''
        _MANIFEST_API               = "manifestAPI"
        _DATA_KIND                  = "data.kind"
        _DATA_RANGE                 = "data.range"
        _DATA_SHEET                 = "data.sheet"
        _ORGANIZATION               = 'organization'
        _ENVIRONMENT                = 'environment'
        _RECORDED_BY                = 'recordedBy'
        _ESTIMATED_BY               = 'estimatedBy'
        _ESTIMATED_ON               = 'estimatedOn'

        #_POSTING_VERSION            = "postingVersion"

        def __init__(self, parent_trace, controller, mandatory_fields, optional_fields = [], date_fields = []):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            combined_mandatory_fields               = [ ME._MANIFEST_API,       ME._DATA_KIND,              # Determine apiVersion
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

        def read(self, parent_trace, posting_label_handle):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            super().read(parent_trace, posting_label_handle)

            excel_range                 = posting_label_handle.excel_range

            # Validate that Manifest API in posting is one we know how to handle
            posted_manifest_api         = self._getField(parent_trace, ME._MANIFEST_API)
            #expected_manifest_api       = StringUtils().rreplace(self.controller.getManifestAPI().apiName(), "io", "xlsx")
            expected_manifest_api               = self.controller.getManifestAPI().apiName()
            manifest_api_supported_versions   = [expected_manifest_api + "/" + version for version in self.controller.getSupportedVersions()]

            if not posted_manifest_api in manifest_api_supported_versions:
                raise ApodeixiError(parent_trace, "Non supported Manifest API '" + posted_manifest_api + "'"
                                                + "\nShould be one of: " + str(manifest_api_supported_versions))

            # Validate that kind of domain object(s) in posting is(are) one that we know how to handle, 
            # and save the findings along the way in the controller's show_your_work for later use
            self._initialize_show_your_work(parent_trace, posting_label_handle)

            for manifest_nb, kind, excel_range, excel_sheet in self.controller.show_your_work.manifest_metas():

                supported_data_kinds             = self.controller.getSupportedKinds()
                if not kind in supported_data_kinds:
                    raise ApodeixiError(parent_trace, "Non supported domain object kind '" + kind + "'"
                                                    + "\nShould be one of: " + str(supported_data_kinds))

        def infer(self, parent_trace, manifest_dict):
            '''
            Builds out the properties of a PostingLabel so that it can be used in a post request to update a
            manifest given by the `manifest_dict`

            Returns a list of the fields that may be editable

            @param manifest_dict A dict object containing the information of a manifest (such as obtained after loading
                                a manifest YAML file into a dict)
            '''
            self.ctx                        = {}
            
            ME = SkeletonController._MyPostingLabel
            def _infer(fieldname, path_list):
                self._inferField(   parent_trace            = parent_trace, 
                                    fieldname               = fieldname, 
                                    path_list               = path_list, 
                                    manifest_dict           = manifest_dict)

            _infer(ME._MANIFEST_API,        ["apiVersion"                                       ])
            _infer(ME._ORGANIZATION,        ["metadata",    "labels",       ME._ORGANIZATION    ])
            _infer(ME._ENVIRONMENT,         ["metadata",    "labels",       ME._ENVIRONMENT     ])
            _infer(ME._RECORDED_BY,         ["assertion",                   ME._RECORDED_BY     ])
            _infer(ME._ESTIMATED_BY,        ["assertion",                   ME._ESTIMATED_BY    ])
            _infer(ME._ESTIMATED_ON,        ["assertion",                   ME._ESTIMATED_ON    ])

            editable_fields = [ME._RECORDED_BY, ME._ESTIMATED_BY, ME._ESTIMATED_ON]
            return editable_fields

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

        def _initialize_show_your_work(self, parent_trace, posting_label_handle):
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
            this Posting Label by inferring it from the `posting_label_handle`

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
                    raise ApodeixiError(parent_trace, "Posting label lacks values for some fields",
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

            sheet_list          = self._default_sheet_if_needed(parent_trace, kind_list, posting_label_handle)


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

        def _default_sheet_if_needed(self, parent_trace, suffix_list, posting_label_handle):
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
            else: # User did not specify any sheet fields, so must default them from the posting_label_handle
                default_sheet               = posting_label_handle.excel_sheet
                if len(suffix_list) == 0:
                    self.ctx[sheet_field]   = default_sheet
                else:
                    for idx in suffix_list:
                        self.ctx[sheet_field + "." + str(idx)]   = default_sheet
                result                      = suffix_list

            return result
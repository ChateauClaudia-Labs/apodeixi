import yaml                                             as _yaml
import os                                               as _os
import datetime                                         as _datetime
import pandas                                           as _pd

from apodeixi.util.a6i_error                            import ApodeixiError

from apodeixi.xli.posting_controller_utils              import PostingController, PostingLabel, PostingConfig
from apodeixi.xli.uid_store                             import UID_Store
from apodeixi.xli.xlimporter                            import ExcelTableReader, SchemaUtils

from apodeixi.controllers.util.manifest_api             import ManifestAPIVersion
from apodeixi.knowledge_base.knowledge_base_util        import PostResponse, ManifestUtils, PostingDataHandle, \
                                                                PostingLabelHandle, FormRequestResponse, ManifestHandle, \
                                                                FormRequest
from apodeixi.knowledge_base.filing_coordinates         import TBD_FilingCoordinates
from apodeixi.representers.as_dataframe                 import AsDataframe_Representer
from apodeixi.representers.as_excel                     import ManifestRepresenter

from apodeixi.text_layout.excel_layout                  import AsExcel_Config_Table, ManifestXLWriteConfig, PostingLabelXLWriteConfig
from apodeixi.util.formatting_utils                     import StringUtils
from apodeixi.util.dictionary_utils                     import DictionaryUtils


class SkeletonController(PostingController):
    '''
    Abstract class intended to be implemented by classes that adhere to the most common conventions for Posting
    Controllers. It helps by implementing those conventions as a common skeleton that can be re-used by derived classes.

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)

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
            read_only               = label.readOnly            (parent_trace, manifest_nb)
            if read_only == None or read_only == False:
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
        ME                      = SkeletonController
        my_trace                = parent_trace.doing("Loading manifests requested in the form")
        if True:
            manifests_in_scope_dict             = self._manifests_in_scope(parent_trace, form_request)
            manifestInfo_dict                   = {}
            contents_df_dict                    = {} # needed for ManifestRepresenter
            manifest_identifiers                = [] # needed for FormRequestResponse
            for key in manifests_in_scope_dict.keys():
                loop_trace                      = my_trace.doing("Extracting content for manifest",
                                                                    data = {"manifest identifier": str(key)})
                manifest_dict                   = manifests_in_scope_dict[key]
                if manifest_dict == None:
                    raise ApodeixiError(loop_trace, "Sorry, blind form requests are not yet supported") # TODO - Implement it!
                manifest_info                   = ME._ManifestInfo( parent_trace            = loop_trace,
                                                                    key                     = key,
                                                                    manifest_dict           = manifest_dict,
                                                                    controller              = self)
                manifestInfo_dict[key]          = manifest_info
                # This other dictionary of dataframes is needed for ManifestRepresenter
                data_df                         = manifest_info.getManifestContents(my_trace)
                contents_df_dict[key]           = data_df
                manifest_identifiers.append(key)

        my_trace                = parent_trace.doing("Creating Excel layouts for posting label")
        label, label_xlw_config = self._build_labelXLWriteconfig(my_trace, manifestInfo_dict)

        my_trace                = parent_trace.doing("Creating Excel layouts for manifests")
        xlw_config_table       = self._build_manifestsXLWriteconfig(    parent_trace        = parent_trace, 
                                                                    manifestInfo_dict   = manifestInfo_dict)

        xlw_config_table.setPostingLabelXLWriteConfig(my_trace, label_xlw_config)

        my_trace                = parent_trace.doing("Writing out the Excel spreadsheet requested")        
        if True:
            rep                 = ManifestRepresenter(  parent_trace        = my_trace,
                                                        xlw_config_table    = xlw_config_table,
                                                        label_ctx           = label.ctx,
                                                        content_df_dict     = contents_df_dict,)
            filename            = self.store.uploadForm(my_trace, 
                                                        form_request        = form_request, 
                                                        representer         = rep)

        my_trace                = parent_trace.doing("Assembling FormRequest response")     
        if True:
            response_handle     = PostingLabelHandle(   parent_trace            = my_trace,
                                                        excel_filename          = filename,
                                                        excel_sheet             = SkeletonController.POSTING_LABEL_SHEET,
                                                        excel_range             = SkeletonController.POSTING_LABEL_RANGE,
                                                        posting_api             = form_request.getPostingAPI(my_trace), 
                                                        filing_coords           = form_request.getFilingCoords(my_trace), 
                                            )

            env_config          = self.store.current_environment(parent_trace).config(parent_trace)
            response            = FormRequestResponse(  clientURL               = self.store.getClientURL(my_trace),
                                                        posting_api             = form_request.getPostingAPI(my_trace),
                                                        filing_coords           = form_request.getFilingCoords(my_trace),
                                                        path_mask               = env_config.path_mask,
                                                        manifest_identifiers    = manifest_identifiers)
            response.recordClientURLCreation(parent_trace=my_trace, response_handle=response_handle)

            self.log_txt                        = self.store.logFormRequestEvent(my_trace, form_request, response)
            self.representer                    = rep

            return response

    def _build_manifestsXLWriteconfig(self, parent_trace, manifestInfo_dict):
        '''
        Creates and returns an AsExcel_Config_Table containing the configuration data for how to lay out and format
        all the manifests of `manifestInfo_dict` onto an Excel spreadsheet
        '''
        xlw_config_table        = AsExcel_Config_Table()
        x_offset                = 1
        y_offset                = 1
        for key in manifestInfo_dict:
            loop_trace          = parent_trace.doing("Creating layout configurations for manifest '"
                                                                + str(key) + "'")
            manifest_info       = manifestInfo_dict[key]
            data_df             = manifest_info.getManifestContents(parent_trace)
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            xlw_config          = ManifestXLWriteConfig(sheet               = SkeletonController.GENERATED_FORM_WORKSHEET,
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
            xlw_config_table.addManifestXLWriteConfig(loop_trace, xlw_config)
        return xlw_config_table

    def _build_labelXLWriteconfig(self, parent_trace, manifestInfo_dict):
        '''
        Helper method used as part of processing a FormRequest

        It creates a PostingLabelXLWriteConfig object that should be used in the generation of the
        Excel spreadsheet (the "form") that was requested by the FormRequest. In the process it also creates a 
        PostingLabel object.

        It returns a pair: the PostingLabel, and the PostingLabelXLWriteConfig
        '''
        label                               = self.getPostingLabel(parent_trace)
        label.ctx                           = {} # It gest populated in the loop below, with each manifest contributing
        label_editable_fields               = None
        for key in manifestInfo_dict.keys():
            loop_trace                      = parent_trace.doing("Checking label editable fields for manifest '" 
                                                                + str(key) + "'")
            manifest_info                   = manifestInfo_dict[key]
            manifest_dict                   = manifest_info.getManifestDict(loop_trace)
            my_trace                        = loop_trace.doing("Inferring posting label", 
                                                                origination = {'signaled_from': __file__})
            proposed_editable_fields        = label.infer(loop_trace, manifest_dict, key)
            if label_editable_fields == None: # Initialize them
                label_editable_fields             = proposed_editable_fields
            elif proposed_editable_fields != label_editable_fields: 
                raise ApodeixiError(loop_trace, "Can't generate form since manifests disagree on which fields should be"
                                                + " editable in the PostingLabel of the form being requested") 

        my_trace                            = parent_trace.doing("Creating Excel layout for Posting Label")
        
        label_xlw_config    = PostingLabelXLWriteConfig(    sheet          = SkeletonController.POSTING_LABEL_SHEET,
                                                            viewport_width      = 100,  
                                                            viewport_height     = 40,   
                                                            max_word_length     = 20, 
                                                            editable_fields     = label_editable_fields, 
                                                            date_fields         = label.date_fields,  
                                                            x_offset            = 1,    
                                                            y_offset            = 1)

        return label, label_xlw_config
    
    class _ManifestInfo():
        '''
        Helper data structure to group related information about a manifest that is in scope for form (i.e.,
        Excel spreadsheet) being generated in response to a FormRequest.

        @param key A string, which is a unique identifier of this manifest among all manifests in the scope of
                    a form (i.e., of an Excel spreadsheet intended for postings).
                    Should be in the format of <kind>.<manifest number>
                    Example: "big-rock.0"
        @param manifest_dict A dict, representing the content of a manifest's YAML file. The manifest must be the
                    one identified by the `key` parameter.
        @param controller A an object of a class derived from SkeletonController, which contains this _Manifest_info
                class as an inner class
        '''
        def __init__(self, parent_trace, key, manifest_dict, controller): 
            self._key                       = key
            self._controller                = controller
            self._manifest_dict             = manifest_dict 
            self._contents_df               = self._buildManifestContent(parent_trace)  
            return

        TEMPLATE_DF                         = "TEMPLATE_DF" # Used when using a template DataFrame as the assertion

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
            manifest_nb                     = int(self._key.split('.')[1])
            
            assertion_dict                  = self._manifest_dict['assertion']
            DF_KEY                          = SkeletonController._ManifestInfo.TEMPLATE_DF
            if DF_KEY in assertion_dict.keys(): # This is not a real manifest - we have content as a DataFrame template
                contents_df                 = assertion_dict[DF_KEY]
            else: # This is a real manifest that we parsed, so need to convert parsed tree to a DataFrame
                posting_config                  = self._controller.getPostingConfig(parent_trace, 
                                                                        kind, 
                                                                        manifest_nb) 
                entity                          = posting_config.entity_as_yaml_fieldname()

                content_dict                    = assertion_dict[entity]
                rep                             = AsDataframe_Representer()
                contents_path                   = 'assertion.' + entity
                contents_df                     = rep.dict_2_df(parent_trace, content_dict, contents_path)
            
            return contents_df

        def _abort_if_null_manifest(self, parent_trace):
            if self._manifest_dict == None:
                raise ApodeixiError(parent_trace, "_ManifestInfo has a null manifest - did you forget to retrieve it "
                                                + "ahead of this point in the processing?",
                                                data = {"manifest key": str(self._key)})

    def _manifests_in_scope(self, parent_trace, form_request):
        '''
        Helper method that retrieves from the store the content needed to populate the requested form.
        It is used during processing of the controller's generateForm method.

        Specifically, based on the information in the `form_request` it constructs a dictionary
        whose keys are manifest identifiers (strings) and values are dictionaries representing the
        Manifest content per manifest identifier.
        For manifest identifiers corresponding to manifests that don't yet exist, the value in the
        returned dict is None

        @param form_request A FormRequest object
        '''
        manifests_in_scope_dict                 = {}
        scope                                   = form_request.getScope(parent_trace)
        if type(scope) == FormRequest.ExplicitScope:
            manifest_handles_dict               = scope.manifestHandles(parent_trace)
            for key in manifest_handles_dict.keys():
                manifest_handle                 = manifest_handles_dict[key]
                my_trace                        = parent_trace.doing("Loading manifest as a DataFrame",
                                                        data = {"handle": manifest_handle.display(parent_trace)})
                manifest_dict, manifest_path    = self.store.retrieveManifest(my_trace, manifest_handle)
                manifests_in_scope_dict[key]    = manifest_dict
        elif type(scope) == FormRequest.SearchScope:
            coords                              = form_request.getFilingCoords(parent_trace)
            namespace                           = scope.namespace
            subnamespace                        = scope.subnamespace
            name                                = self.manifestNameFromCoords(parent_trace, subnamespace, coords)
            manifest_nb                         = 0
            for kind in self.getSupportedKinds():
                loop_trace                      = parent_trace.doing("Searching for latest version of manifest",
                                                        data = {"kind":     str(kind),
                                                                "namespace":    str(namespace),
                                                                "name":         str(name)})
                manifest_identifier             = kind + "." + str(manifest_nb)
                manifest_api                    = self.getManifestAPI()
                manifest_dict, manifest_path    = self.store.findLatestVersionManifest( parent_trace    = loop_trace, 
                                                                                        manifest_api    = manifest_api,
                                                                                        namespace       = namespace, 
                                                                                        name            = name, 
                                                                                        kind            = kind)

                # If we did find something (i.e., manifest-dict isn't null), check this manifest is for an API version we support.
                # This call returns something like ("delivery-planning.journeys.a6i.io", "v1a")
                if manifest_dict != None:
                    api_found, api_suffix_found     = ManifestUtils().get_manifest_apiversion(loop_trace, manifest_dict)
                    if not api_suffix_found in self.getSupportedVersions():
                        raise ApodeixiError(loop_trace, "This distribution does not support the API version of the latest manifest",
                                                data = {"api in manifest":          str(api_found),
                                                        "api version in manifest":  str(api_suffix_found),
                                                        "supperted api versions":   str(self.getSupportedVersions())})
                else: # There is no manifest with these constraints, so create a template
                    template_dict, template_df  = self.createTemplate(  parent_trace        = loop_trace,
                                                                        form_request        = form_request,
                                                                        kind                = kind)
                    manifest_dict               = template_dict
                    DF_KEY                      = SkeletonController._ManifestInfo.TEMPLATE_DF
                    manifest_dict['assertion'][DF_KEY]   = template_df
                    
                manifests_in_scope_dict[manifest_identifier]    = manifest_dict # NB: may be none if it has to be created
                manifest_nb                         += 1
        else:
            raise ApodeixiError("Invalid type of scope in FormRequest",
                                data = {"type(scope)": str(type(scope)),
                                        "valid types": str["FormRequest.ExplicitScope", "FormRequest.SearchScope"]})

        return manifests_in_scope_dict

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
                tbd_coords                  = posting_label_handle.filing_coords
                tbd_coords.inferFilingCoords( my_trace, label)
                posted_coords               = tbd_coords.inferred_coords(my_trace)
            else:
                posted_coords               = posting_label_handle.filing_coords

            if self.a6i_config.enforce_referential_integrity:
                label.checkFilingCoordsConsistency(my_trace, posting_label_handle.posting_api, posted_coords)
                label.checkReferentialIntegrity(my_trace)

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

    def manifestNameFromLabel(self, parent_trace, label):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        label
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'manifestNameFromLabel' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})  

    def manifestNameFromCoords(self, parent_trace, subnamespace, coords):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        filing coords, possibly complemented by the subnamespace.

        Example: consider a manifest name like "modernization.default.dec-2020.fusionopus"
                in namespace "my-corp.production". 

                To build such a name, this method must receive "modernization" as the subnamespace, and
                filing coords from which to infer "default", "dec-20220", and "fusionopus".

        @param subnamespace A string, which is allowed to be None. If not null, this is a further partioning of
                        the namespace into finer slices, and a manifest's name is supposed to identify the slice
                        in which the manifest resides.

        @param coords A FilingCoords object corresponding to this controller. It is used, possibly along with the
                        `subnamespace` parameter, to build a manifest name.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'manifestNameFromCoords' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})        

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Returns a  dictionary corresponding to the manifest that was built in this method
        '''
        manifest_nb                 = posting_data_handle.manifest_nb
        kind                        = posting_data_handle.kind

        organization                = label.organization        (parent_trace)
        kb_area                     = label.knowledgeBaseArea         (parent_trace)  
                    
        recorded_by                 = label.recordedBy          (parent_trace)
        estimated_by                = label.estimatedBy         (parent_trace)
        estimated_on                = label.estimatedOn         (parent_trace)

        FMT                         = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        namespace                   = FMT(organization + '.' + kb_area)
        manifest_name               = self.manifestNameFromLabel(parent_trace, label)

        my_trace                    = parent_trace.doing("Checking if this is an update")
        if True:
            prior_version           = label.priorVersion        (parent_trace, manifest_nb)
            read_only               = label.readOnly            (parent_trace, manifest_nb)
            xlr_config              = self.getPostingConfig(    parent_trace        = my_trace, 
                                                                kind                = kind,
                                                                manifest_nb         = manifest_nb)
            # Set label in xlr_config. It is needed later but can only be set at this point in the coding
            # path, so it was left out of the self.getPostingConfig which is sometimes called in situations
            # where the label is not known or needed.
            xlr_config.posting_label    = label
            if prior_version != None and (read_only == None or read_only == False): # we are updating
                next_version        = prior_version + 1
            else:
                next_version        = 1

        relative_path                   = posting_data_handle.getRelativePath(my_trace)
        my_trace                        = parent_trace.doing("Creating BreakoutTree from Excel", 
                                                                data = {"relative_path": relative_path},
                                                                origination = {'signaled_from': __file__})
        if True:
            tree                        = self._xl_2_tree(my_trace, posting_data_handle, xlr_config)
            tree_dict                   = tree.as_dicts()
        
        my_trace                        = parent_trace.doing("Creating manifest from BreakoutTree", 
                                                                data = {'organization': organization},
                                                                origination = {'signaled_from': __file__})
        if True:
            
            manifest_dict               = {}
            metadata                    = { 'namespace':    namespace, 
                                            'name':         manifest_name,
                                            'labels':       {   label._ORGANIZATION:        organization,
                                                                label._KNOWLEDGE_BASE_AREA: kb_area,
                                                                label._RECORDED_BY:         recorded_by,
                                                                label._ESTIMATED_BY:        estimated_by,
                                                                label._ESTIMATED_ON:        estimated_on,
                                                            }
                                            }

            manifest_dict[ManifestAPIVersion.API_VERSION] = self.api_version(my_trace)
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

    def manifest_nb_from_kind(self, parent_trace, kind):
        '''
        Helper method for situations where there are not multiple manifests of the same kind. In such case
        this method will return the manifest number (an int) that uniquely corresponds to the
        manifest for kind `kind`.

        @param kind A string, representing the `kind` property of the manifest in question
        '''
        # Expect exactly 1 match
        matching_nbs                    = [manifest_nb 
                                            for manifest_nb, manifest_kind, excel_range, excel_sheet 
                                            in self.show_your_work.manifest_metas()
                                            if manifest_kind == kind]
        if len(matching_nbs)==0:
            raise ApodeixiError(parent_trace, "Unable to find metadata in controller's show_your_work for kind='" + kind + "'")
        if len(matching_nbs) > 1:
            raise ApodeixiError(parent_trace, "Too many matches in controller's show_your_work metadata for kind='" + kind 
                                            + "': expected exactly one match",
                                            data = {'kind': kind, 'matching_nbs': str(matching_nbs)})

        # After checks above, this is safe:
        manifest_nb                     = matching_nbs[0]
        return manifest_nb

    def linkReferenceManifest(self, parent_trace, manifest_dict, entity, linkField, refKind, many_to_one):
        '''
        Links the manifest_dict to the manifest of kind `refKind`, by inserting in manifest_dict a UID 
        in manifest_dict's entity `entity` that corresponds to a UID in the manifest for `refKind`.

        The association is done based on Excel rows: if the Excel row for the UID of manifest_dict's entity
        is the same Excel row containing a UID for the `refKind` manifest, these two will be linked.

        In situations where there are many-to-one relationships, the match is done on the "most recent Excel
        row": i.e., if a manifest_dict's entity is in row N, then it will be associated to a UID
        for the `refKind` list that lies in the biggest row that is less or equal to N.

        Example: suppose 
                        manifest_dict['kind']   =`big-rock-estimate` 
                        refKind                 =`big-rock`
                        entity                  =`effort`
                        linkField               = 'bigRock'

                    Then if big rock "BR5" is in the same row as effort "E9", this method will cause
                    the manifest_dict to add the following:

                    manifest_dict['assertion']['effort']['E9']['bigRock'] = 'BR5'

        @param manyToOne A boolean. If True, it is assumed that there are multiple entities in manifest_dict
                        reference the same UID in the `refKind` manifest, in which case the `refKind` UID is
                        assumed to potentially be in an earlier row than the manifest_dict entity that references
                        it
        '''
        kind                            = manifest_dict['kind']
        my_trace                        = parent_trace.doing("Linking " + str(kind) + " manifest to UIDs from "
                                                                + str(refKind) + " manifest ")
        entity_dict                     = manifest_dict['assertion'][entity]                                                        
        entity_uids                     = [e_uid for e_uid in entity_dict.keys() if not e_uid.endswith("-name")]
        UID_FINDER                      = self.link_table.find_foreign_uid # Abbreviation for readability

        for e_uid in entity_uids:
            ref_uid                     = UID_FINDER(   parent_trace            = my_trace, 
                                                        our_manifest_id         = kind, 
                                                        foreign_manifest_id     = refKind, 
                                                        our_manifest_uid        = e_uid,
                                                        many_to_one             = many_to_one)
            
            entity_dict[e_uid][linkField]   = ref_uid

    def linkMappedManifest(self, parent_trace, refKind, raw_df, first_row, last_row):
        '''
        '''
        if refKind == None:
            raise ApodeixiError(parent_trace, "Can't read mapping manifest information because the `kind` "
                                                + "of the manifest we map from was not set in the PostingConfig "
                                                + "ahead of time")
        
        my_trace                        = parent_trace.doing("Determining rows for reference manifest")
        if True:
            matches                     = [(excel_range, manifest_nb) 
                                                for manifest_nb, manifest_kind, excel_range, excel_sheet 
                                                in self.show_your_work.manifest_metas()
                                                if manifest_kind == refKind]
            if len(matches)==0:
                raise ApodeixiError(parent_trace, "Unable to find metadata in controller's show_your_work for kind='" 
                                                    + refKind + "'")
            if len(matches) > 1:
                raise ApodeixiError(parent_trace, "Too many matches in controller's show_your_work metadata for kind='" 
                                                + refKind 
                                                + "': expected exactly one match",
                                                data = {'kind': refKind, 'matching_nbs': str(matches)})
            # After checks above, this is safe:
            refRange, refManifest_nb    = matches[0]

            if not refKind in self.link_table.links_dict.keys():
                raise ApodeixiError(my_trace, "Unable to parse mappings from manifest '" 
                                                + str(refKind) + "." + str(refManifest_nb) + "' "
                                                + "because there are no entries in the link table for it. "
                                                + "Are you sure you listed it in the Posting Label before any "
                                                + "other manifest that is mapped from it?")

            first_refColumn, last_refColumn, first_refRow, last_refRow  \
                                            = ExcelTableReader.parse_range(my_trace, refRange)

        my_trace                        = parent_trace.doing("Split raw_df into dataset_df and mapping_df, "
                                                                + "indexed by Excel row numbers")
        if True:
            # Re-index raw_df so that its row indices are exactly the same as Excel row numbers.
            # We start at first_row+1 since first_row is the headers of raw_df
            working_df                  = raw_df.copy()
            working_df.index            = range(first_row + 1, first_row + 1 + len(working_df.index))

            # NB: loc is inclusive, so loc[3:5] includes rows 3, 4, and 5 (not just 3,4)
            mapping_df                  = working_df.loc[first_refRow + 1: last_refRow] 
            ds1_df                      = working_df.loc[:first_refRow] 
            ds2_df                      = working_df.loc[last_refRow + 1:]
            dataset_df                  = _pd.concat([ds1_df, ds2_df])

        my_trace                        = parent_trace.doing("Creating manifest DataFrame")
        if True:
            manifest_columns            = list(dataset_df.columns)[0] # These will be the manifest columns
            df2                         = SchemaUtils.drop_blanks(dataset_df, manifest_columns)
            df2                         = df2.set_index(manifest_columns) # That way when we transpose these become the columns
            df2.index.name              = None
            df2                         = df2.transpose()
            df2                         = df2.reset_index() # Ensures columns of dataset_df become the first column of df2
            renamed_columns             = ["Milestone"]
            renamed_columns.extend(df2.columns[1:])
            df2.columns                 = renamed_columns

            manifest_df                 = df2
            
        my_trace                        = parent_trace.doing("Create mapped vectors per milestone")
        if True:
            # The first column of mapping_df are the columns of manifest_df. But the rest correspond to milestones,
            # which are rows in manifest_df
            milestone_mappings          = {}
            for milestone in list(mapping_df.columns)[1:]:
                uid_list                = []
                
                for row_nb in mapping_df.index:
                    val                 = mapping_df[milestone].loc[row_nb]
                    # The link_table has *dataframe* row numbers for the reference manifest, so convert
                    # from the Excel row_nb to the dataframe row number ref_df_row_nb before the lookup
                    ref_df_row_nb       = row_nb - (first_refRow + 1)
                    cleaned_val         = StringUtils().strip(val)
                    if cleaned_val.strip().lower() == 'x': # There is a mapping
                        refUID          = self.link_table.uid_from_row( parent_trace            = my_trace,
                                                                        manifest_identifier     = refKind,
                                                                        row_number              = ref_df_row_nb)
                        if refUID != None:
                            uid_list.append(refUID)
                milestone_mappings[milestone] = uid_list

        my_trace                        = parent_trace.doing("Adding a column of mappings to manifest_df")
        if True:
            def assign_ref_uids(row):
                milestone               = row['Milestone']
                uid_list                = milestone_mappings[milestone]
                return uid_list

            manifest_df[refKind]        = manifest_df.apply(lambda row: assign_ref_uids(row), axis=1)

        return manifest_df

    def createTemplate(self, parent_trace, form_request, kind):
        '''
        Returns a "template" for a manifest, i.e., a dict that has the basic fields (with empty or mocked-up
        content) to support a ManifestRepresenter to create an Excel spreadsheet with that information.

        It is intended to support the processing of blind form requests.

        For reasons of convenience (to avoid going back and forth between DataFrames and YAML), it returns
        the template as a tuple of two data structures:

        * template_dict This is a dictionary of the non-assertion part of the "fake" manifest
        * template_df   This is a DataFrame for the assertion part of the "fake" manifest
        '''
        scope                       = form_request.getScope(parent_trace)
        label                       = self.getPostingLabel(parent_trace) 
        if type(scope) != FormRequest.SearchScope:
            raise ApodeixiError(parent_trace, "Can't create Excel template because FormRequest's scope is of wrong type",
                                                data = {"type of scope received":   str(type(scope)),
                                                        "type of scope required":   "FormRequest.SearchScope"},
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})

        coords                      = form_request.getFilingCoords(parent_trace)
        namespace                   = scope.namespace
        subnamespace                = scope.subnamespace
        manifest_name               = self.manifestNameFromCoords(parent_trace, subnamespace, coords)

        organization, environment   = namespace.split(".")
        recorded_by                 = "yourname.lastname@your_company.com"
        estimated_by                = "accountableowner.lastname@your_company.com"
        estimated_on                = _datetime.datetime(2021, 8, 4) # Random date just to make it deterministic

        template_dict               = {}   # Will be the non-assertions part of the template
        template_df                 = None # Will be the assertion part of the template. We leave it concrete classes to populate this
        metadata                    = { 'namespace':    namespace, 
                                        'name':         manifest_name,
                                        'labels':       {   label._ORGANIZATION:        organization,
                                                            label._KNOWLEDGE_BASE_AREA: environment,
                                                            label._RECORDED_BY:         recorded_by,
                                                            label._ESTIMATED_BY:        estimated_by,
                                                            label._ESTIMATED_ON:        estimated_on,
                                                        }
                                        }

        template_dict[ManifestAPIVersion.API_VERSION] = self.api_version(parent_trace)
        template_dict['kind']       = kind
        template_dict['metadata']   = metadata

        template_dict['assertion']  = { label._RECORDED_BY:                 recorded_by ,
                                        label._ESTIMATED_BY:                estimated_by, 
                                        label._ESTIMATED_ON:                estimated_on,
                                        #'entity_type':                      tree.entity_type,
                                        #FMT(tree.entity_type):              tree_dict
                                        }
        ''' DO NOT SET VERSION FOR A TEMPLATE - IT WILL LATER CAUSE ERRORS WHEN POSTING, THINKING ITS AN UPDATE
        ManifestUtils().set_manifest_version(   parent_trace        = parent_trace, 
                                                manifest_dict       = template_dict, 
                                                manifest_version    = -1) # Not a real manifest, so not a real version
        '''
        return template_dict, template_df

    def initialize_UID_Store(self, parent_trace, posting_data_handle, xlr_config):
        '''
        Creates and returns a UID_Store object.

        It also initializes it to contain all UIDs that might have been used previously by the preceding version
        of the manifest being updated by the posting referenced by `posting_data_handel`, if such a prior
        version exists and if `config`'s update policy is set to reuse UIDs.

        @xlr_config A PostingConfig object whose posting_label attribute has been previously set
        '''
        store                   = UID_Store(parent_trace)
        label                   = xlr_config.posting_label
        my_trace                = parent_trace.doing("Determining previously used UIDs to re-use")
        manifest_nb             = posting_data_handle.manifest_nb
        prior_version           = label.priorVersion        (parent_trace, manifest_nb)
        if xlr_config.update_policy.reuse_uids == True and prior_version != None:
            
            kind                    = posting_data_handle.kind

            organization            = label.organization        (parent_trace)
            kb_area                 = label.knowledgeBaseArea   (parent_trace)  
                        
            FMT                     = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
            namespace               = FMT(organization + '.' + kb_area)
            manifest_name           = self.manifestNameFromLabel(parent_trace, label)
            
            '''
            config                  = self.getPostingConfig(    parent_trace        = my_trace, 
                                                                kind                = kind,
                                                                manifest_nb         = manifest_nb)
            '''
            # Load the prior manifest, to determine which UIDs are already in use so that we don't
            # re-generate them for different data items
            prior_handle    = ManifestHandle(   apiVersion  = self.api_version(my_trace),
                                                namespace   = namespace, 
                                                name        = manifest_name, 
                                                kind        = kind,
                                                version     = prior_version)
            prior_manifest, prior_manifest_path     = self.store.retrieveManifest(my_trace, prior_handle) 

            if prior_manifest == None:
                raise ApodeixiError(my_trace, "Prior version of manifest does not exist, but it should",
                                            data = {"prior version":            prior_version,
                                                    "prior manifest handle":    prior_handle.display(my_trace)})                                                       
            
            store.initializeFromManifest(my_trace, prior_manifest)

        return store
        

    class _MyPostingLabel(PostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting BDD capability hierarchy content. 
        '''
        _MANIFEST_API               = "manifestAPI"
        
        _DATA_KIND                  = "data.kind"
        _DATA_RANGE                 = "data.range"
        _DATA_SHEET                 = "data.sheet"
        _PRIOR_VERSION              = "priorVersion"

        # True or False, per manifest. Read-only datasets won't be persisted when posted. For example, 
        # a posting may come from a form that includes multiple datasets from multiple manifests, and some
        # of them might be reference data used for "joins" with other datasets. If so the reference
        # datasets should not be persisted as new versions of the manifests from whence they came.
        _READ_ONLY                  = "readOnly" 
        
        
        _ORGANIZATION               = 'organization'
        _KNOWLEDGE_BASE_AREA        = 'knowledgeBase'
        _RECORDED_BY                = 'recordedBy'
        _ESTIMATED_BY               = 'estimatedBy'
        _ESTIMATED_ON               = 'estimatedOn'

        def __init__(self, parent_trace, controller, mandatory_fields, optional_fields = [], date_fields = []):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            combined_mandatory_fields               = [ ME._MANIFEST_API,       ME._DATA_KIND,           # Determine apiVersion
                                                        ME._ORGANIZATION,       ME._KNOWLEDGE_BASE_AREA, # Determine namespace
                                                        ME._RECORDED_BY,        ME._ESTIMATED_BY,       ME._ESTIMATED_ON,
                                                        ME._DATA_RANGE]
            combined_mandatory_fields.extend(mandatory_fields)

            combined_optional_fields                = [ME._DATA_SHEET, ME._PRIOR_VERSION, ME._READ_ONLY]
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

            excel_range                     = posting_label_handle.excel_range

            # Validate that Manifest API in posting is one we know how to handle
            posted_manifest_api             = self._getField(parent_trace, ME._MANIFEST_API)
            expected_manifest_api           = self.controller.getManifestAPI().apiName()
            manifest_api_supported_versions = [expected_manifest_api + "/" + version for version in self.controller.getSupportedVersions()]

            if not posted_manifest_api in manifest_api_supported_versions:
                raise ApodeixiError(parent_trace, "Non supported Manifest API '" + posted_manifest_api + "'"
                                                + "\nShould be one of: " + str(manifest_api_supported_versions))

            # Validate that kind of domain object(s) in posting is(are) one that we know how to handle, 
            # and save the findings along the way in the controller's show_your_work for later use
            self._initialize_show_your_work(parent_trace, posting_label_handle)

            for manifest_nb, kind, excel_range, excel_sheet in self.controller.show_your_work.manifest_metas():

                supported_data_kinds        = self.controller.getSupportedKinds()
                if not kind in supported_data_kinds:
                    raise ApodeixiError(parent_trace, "Non supported domain object kind '" + kind + "'"
                                                    + "\nShould be one of: " + str(supported_data_kinds))

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
            expected_organization           = self.controller.a6i_config.getOrganization(parent_trace)
            allowed_kb_areas                = self.controller.a6i_config.getKnowledgeBaseAreas(parent_trace)

            if self.organization(parent_trace) != expected_organization:
                raise ApodeixiError(parent_trace, "Invalid organization field in Posting Label",
                                data = {    "Expected":     str(expected_organization),
                                            "Submitted":    str(self.organization(parent_trace))})

            if not self.knowledgeBaseArea(parent_trace) in allowed_kb_areas:
                raise ApodeixiError(parent_trace, "Invalid knowledge base field in Posting Label",
                                data = {    "Allowed any of":   str(allowed_kb_areas),
                                            "Submitted":        str(self.knowledgeBaseArea(parent_trace))})

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
            #GOTCHA: This method is called several times, one per manifest. Usually most field names are identical
            #           and have identical values across the manifests, but some (like priorVersion) are manifest-dependent
            #           i.e., "priorVersion.0", "priorVersion.1", etc. are different fieldnames.
            #           For that reason we should not clear out the self.ctx when we enter this function, to avoid
            #           losing fields from prior cycles of the loop that calls this function
            #self.ctx                        = {} <======= DO NOT DO THIS
            
            try:
                kind, nb            = manifest_key.split(".")
            except ValueError as ex:
                raise ApodeixiError(parent_trace, "Unable to parse name of dataset. Expected something like <kind>.<number>",
                                                data = {"dataset name":     "'" + str(manifest_key) + "'",
                                                        "error":            str(ex)})

            ME = SkeletonController._MyPostingLabel
            def _infer(fieldname, path_list):
                self._inferField(   parent_trace            = parent_trace, 
                                    fieldname               = fieldname, 
                                    path_list               = path_list, 
                                    manifest_dict           = manifest_dict)

            _infer(ME._MANIFEST_API,        ["apiVersion"                                           ])
            _infer(ME._ORGANIZATION,        ["metadata",    "labels",       ME._ORGANIZATION        ])
            _infer(ME._KNOWLEDGE_BASE_AREA, ["metadata",    "labels",       ME._KNOWLEDGE_BASE_AREA ])
            _infer(ME._RECORDED_BY,         ["assertion",                   ME._RECORDED_BY         ])
            _infer(ME._ESTIMATED_BY,        ["assertion",                   ME._ESTIMATED_BY        ])
            _infer(ME._ESTIMATED_ON,        ["assertion",                   ME._ESTIMATED_ON        ])

            # Prior version is optional, since it would not apply for situations where manifests haven't
            # been created previously (and in that case the manifest_dict parameter given to this method
            # is really a "template", not the contents of a real manifest.)
            # In such cases we should not expect a prior version to exist, and if we insist on 
            # retrieving it from the manifest will get an error when nothing is really wrong. So extract
            # prior version only if it exists.
            check, explanations     = DictionaryUtils().validate_path(  parent_trace        = parent_trace, 
                                                                        root_dict           = manifest_dict, 
                                                                        root_dict_name      = str(manifest_key), 
                                                                        path_list           = ["metadata", "version"], 
                                                                        valid_types         = [int])
            if check:
                version_fieldname       = ME._PRIOR_VERSION + "." + str(nb)
                _infer(version_fieldname,   ["metadata",    "version"                               ])

            editable_fields = [ME._RECORDED_BY, ME._ESTIMATED_BY, ME._ESTIMATED_ON]
            return editable_fields

        def knowledgeBaseArea(self, parent_trace):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            return self._getField(parent_trace, ME._KNOWLEDGE_BASE_AREA)

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

        def priorVersion(self, parent_trace, manifest_nb):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            field_name      = ME._PRIOR_VERSION + "." + str(manifest_nb)
            if not field_name in self.ctx.keys():
                return None
            val  = self._getField(parent_trace, field_name)
            return val

        def readOnly(self, parent_trace, manifest_nb):
            # Shortcut to reference class static variables
            ME = SkeletonController._MyPostingLabel

            field_name      = ME._READ_ONLY + "." + str(manifest_nb)
            if not field_name in self.ctx.keys():
                return None
            val  = self._getField(parent_trace, field_name)
            return val

        def _initialize_show_your_work(self, parent_trace, posting_label_handle):
            '''
            Used to prepare the information needed to retrieve the data for each of the manifests (1 or more) that
            are being posted within the same Excel spreadsheet using a common PostingLabel.

            This method is expected to be called after super().read has been called, since super().read will cause 
            self.sightings to be populated. 
            
            This method looks inside self.sightings['data.kind'] and self.sightings['data.range'], both of which should
            be arrays of the same size. For example, [] (if there is only one manifest) or [0, 1, 2] if there are three.

            Optionally, the user may have specified 'data.sheet.0', 'data.sheet.1', 'data.sheet.2', say, if the data resides
            in a different Excel worksheet than the one containing this Posting Label. So this method also inquires on
            whether self.sightings['data.sheet'] exists and if so it will also process it just like the others.

            If the user did nost specify 'data.sheet.x' fields, then it will be defaulted to the same sheet containing
            this Posting Label by inferring it from the `posting_label_handle`

            Based on this it initializes self.controller.show_your_work:

            * Remembers a list of metadata for all manifests, assigning a number to each manifest that can also
              be used as a numerical id of a manifest that is consistent throughout the lifetime of the controller
              object.

            '''

            def _keep_work(parent_trace, manifest_nb, kind_field, range_field, sheet_field):
                '''
                Helper function to avoid repetitive code in both branches of an if-else
                '''
                FMT                 = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
                kind_val            = FMT(self.ctx[kind_field])
                range_val           = self.ctx[range_field]
                sheet_val           = self.ctx[sheet_field]
                my_trace            = parent_trace.doing("Initializing show-my-work memory for manifest of kind '" + kind_val + "'")

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
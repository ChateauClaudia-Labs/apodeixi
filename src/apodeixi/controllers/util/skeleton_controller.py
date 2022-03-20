import datetime                                         as _datetime
import pandas                                           as _pd

from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

from apodeixi.xli.posting_controller_utils              import PostingController, PostingLabel
from apodeixi.xli.update_policy                         import InferReferenceUIDsPolicy
from apodeixi.xli.uid_store                             import UID_Store
from apodeixi.xli.xlimporter                            import ExcelTableReader, SchemaUtils
from apodeixi.xli.interval                              import Interval
from apodeixi.xli.uid_acronym_schema                    import UID_Acronym_Schema

from apodeixi.controllers.util.manifest_api             import ManifestAPIVersion
from apodeixi.knowledge_base.knowledge_base_util        import PostResponse, \
                                                                PostingLabelHandle, FormRequestResponse, ManifestHandle, \
                                                                FormRequest
from apodeixi.knowledge_base.manifest_utils             import ManifestUtils
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

    # Key used in self.show_your_work.general_dict
    MANIFESTS_IN_SCOPE_DICT             = "MANIFESTS_IN_SCOPE_DICT"

    def getFilingClass(self):
        '''
        Abstract method, required to be implemented by concrete derived classes.
        It returns a class object, corresponding to the concrete subclass of FilingCoordinates
        that is supported by this controller
        '''
        root_trace                      = FunctionalTrace(parent_trace=None, path_mask=None)

        raise ApodeixiError(root_trace, "Someone forgot to implement abstract method 'getFilingClass' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})

    def apply(self, parent_trace, posting_label_handle):
        '''
        Main entry point to the controller. Retrieves an Excel, parses its content, creates the YAML manifest and saves it.

        Returns a PostResponse.

        '''
        excel_filename              = posting_label_handle.excel_filename

        my_trace                    = parent_trace.doing("Applying Excel posting", 
                                                            origination = {'signaled_from' : __file__})
        manifest_file               = StringUtils().rreplace(excel_filename, 'xlsx', 'yaml')
        all_manifests_dicts, label  = self._buildAllManifests(my_trace, posting_label_handle)

        response                    = PostResponse()
        for manifest_nb in all_manifests_dicts.keys():
            loop_trace              = my_trace.doing("Persisting manifest in store",
                                                        data = {'manifest_nb': manifest_nb}, 
                                                        origination = {'signaled_from' : __file__})
            manifest_dict           = all_manifests_dicts[manifest_nb]
            read_only               = label.readOnly            (loop_trace, manifest_nb)
            if read_only == True:
                response.recordUnchanged(parent_trace=loop_trace, manifest_dict=manifest_dict, manifest_nb=manifest_nb)
            else:
                self.store.persistManifest(loop_trace, manifest_dict)
                version             = ManifestUtils().get_manifest_version(loop_trace, manifest_dict)
                if version == 1:
                    response.recordCreation(parent_trace=loop_trace, manifest_dict=manifest_dict, manifest_nb=manifest_nb)
                else:
                    response.recordUpdate(parent_trace=loop_trace, manifest_dict=manifest_dict, manifest_nb=manifest_nb)

        my_trace                    = parent_trace.doing("Registering any foreign key constraints that should be honored "
                                                            + "in subsequent updates, if any")
        self.registerForeignKeyConstraints(my_trace, all_manifests_dicts)

        # Persistence happens later, during committing of the transaction- self.store.persistForeignKeyConstraints(my_trace)


        my_trace                    = parent_trace.doing("Archiving posting after successfully parsing it and "
                                                            + "creating manifests",
                                                            data = {"excel_filename": excel_filename})
        subnamespace                = self.subnamespaceFromLabel(my_trace, label)
        archival_handle             = self.store.archivePosting(my_trace, posting_label_handle, subnamespace)
        response.recordArchival(my_trace, posting_label_handle, archival_handle)

        manifest_handles            = response.allActiveManifests(my_trace)
        form_request                = posting_label_handle.createUpdateForm(my_trace, manifest_handles)
        response.recordOptionalForm(my_trace, form_request)

        self.log_txt                = self.store.logPostEvent(my_trace, response)

        return response

    def registerForeignKeyConstraints(self, parent_trace, all_manifests_dict):
        '''
        Intended as a hook for derived classes to register foreign key constraints.

        This method is used the the write flow (i.e., when processing postings) after all manifests pertinent
        to this controller are persisted, but before the transaction is committed.
        '''

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
                                                        manifestInfo_dict   = manifestInfo_dict,)
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
                                                        filename                = filename,
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
                                                        read_only           = False,
                                                        is_transposed       = False,     
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
            # We allow each manifest to contribute what it thinks should be editable, and we take the union.
            # A reason manfifests may differ on what is editable is because they might belong to different domains,
            # as when one manifests references another manifest from a different domain. Each domain may imply 
            # certain editable fields in the label.
            new_editable_fields             = [x for x in proposed_editable_fields if not x in label_editable_fields]
            label_editable_fields.extend(new_editable_fields)
            '''
            elif proposed_editable_fields != label_editable_fields: 
                raise ApodeixiError(loop_trace, "Can't generate form since manifests disagree on which fields should be"
                                                + " editable in the PostingLabel of the form being requested") 
            '''

        my_trace                            = parent_trace.doing("Checking referential integrity for inferred Posting Label")

        if self.a6i_config.enforce_referential_integrity:
            label.checkReferentialIntegrity(my_trace)

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
            
            assertion_dict                  = self._manifest_dict['assertion']
            DF_KEY                          = SkeletonController._ManifestInfo.TEMPLATE_DF
            if DF_KEY in assertion_dict.keys(): # This is not a real manifest - we have content as a DataFrame template
                contents_df                 = assertion_dict[DF_KEY]
            else: # This is a real manifest that we parsed, so need to convert parsed tree to a DataFrame
                contents_df                 = self._controller._loaded_manifest_dict_2_df(
                                                                                parent_trace, 
                                                                                manifest_dict       = self._manifest_dict, 
                                                                                manifest_id         = self._key)

            return contents_df

        def _abort_if_null_manifest(self, parent_trace):
            if self._manifest_dict == None:
                raise ApodeixiError(parent_trace, "_ManifestInfo has a null manifest - did you forget to retrieve it "
                                                + "ahead of this point in the processing?",
                                                data = {"manifest key": str(self._key)})

    def _loaded_manifest_dict_2_df(self, parent_trace, manifest_dict, manifest_id):
        '''
        Helper method invoked to construct and return a DataFrame out of a manifest dictionary that has been just loaded 
        from the store.

        This method is used in the context of generating forms, which requires retrieving previously saved manifest content 
        which will later be displayed in an Excel form.

        This method is a refactoring of a bit of logic inside _ManifestInfo's logic to build the manifest content.
        This refactoring was done so that concrete classes can overwrite this method if needed.

        A typical use case for why a concrete class may need to overwrite this method is "embedded reference columns":

        For example, the Excel display for an indicator actual's manifest becomes more user-friendly if, in addition to
        columns like 
        
                ("Q1 FY22", "Actual"), ("Q2 FY22", "Actual")

        it instead displayed "embedded" columns for the targets, read from some other manifest for indicator targets
        side-by-side with the actuals, aligning by timebucket.
        That means the display would have columns like 

                ("Q1 FY22", "Target"), ("Q1 FY22", "Actual"), ("Q2 FY22", "Target"), ("Q2 FY22", "Actual")

        The content under the "Target" columns is really owned by a different manifest, so even if the indicator actuals
        manifest has "field" for the "targets", they are just "copies" of what resides in the indicator target manifest.

        As a result of that, the "copy" may become stale if the reference manifest (e.g., indicator targets) is updated,
        so when generating a form for the referencing manifest (e.g., indicator actuals) we should "refresh" the targets
        copies that we retrieved from the store inside the indicator actual manifest.

        In the example, this means loading the indicator targets manifest and using its values to replace the values of
        the "Target" columns in the DataFrame returned by this method before returning it.

        The above was an example of the kind of logic that a concrete class might want to do when overwriting this method.

        For this parent-class default implementation, the logic is straightforward: the content DataFrame is simply built
        out of the manifest dictionary without any enrichments.

        @param manifest_dict A dict object, representing the full data of a manifest that has just been retrieved from
                                the KnowledgeStore
        @param manifest_id A string, that uniquely identifies a manifest within this controller object. For example,
                                'big-rock.0'. It is expected to be in the form of <kind>.<int>
        '''
        kind                            = manifest_dict['kind']
        manifest_nb                     = int(manifest_id.split('.')[1])
        posting_config                  = self.getPostingConfig(parent_trace, 
                                                                kind, 
                                                                manifest_nb) 
        entity                          = posting_config.entity_as_yaml_fieldname()

        content_dict                            = DictionaryUtils().get_val(
                                                                    parent_trace        = parent_trace, 
                                                                    root_dict           = manifest_dict,
                                                                    root_dict_name      = str(manifest_id),
                                                                    path_list           = ["assertion", str(entity)],
                                                                    valid_types         = [dict])

        rep                             = AsDataframe_Representer()
        contents_path                   = 'assertion.' + entity
        contents_df, uid_info_list      = rep.dict_2_df(parent_trace, content_dict, contents_path, 
                                                            sparse=True, abbreviate_uids=True)
        return contents_df
            

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

        # Some derived classes need access to some of the manifest data that is built in this method's loop
        # even before this method is returned. So to remember the data that is being built so that concrete classes
        # can access it, we will remember the manifests_in_scope_dict in self.show_your_work
        #
        self.show_your_work.general_dict[self.MANIFESTS_IN_SCOPE_DICT]   = manifests_in_scope_dict

        scope                                   = form_request.getScope(parent_trace)
        if type(scope) == FormRequest.ExplicitScope:
            manifest_handles_dict               = scope.manifestHandles(parent_trace, controller=self)
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
            
            manifest_nb                         = 0
            for kind in self.getSupportedKinds():
                loop_trace                      = parent_trace.doing("Searching for latest version of manifest",
                                                        data = {"kind":     str(kind),
                                                                "namespace":    str(namespace)})
                name                            = self.manifestNameFromCoords(parent_trace, subnamespace, coords, kind)
                manifest_identifier             = kind + "." + str(manifest_nb)
                manifest_api_name               = self.getManifestAPI().apiName()
                manifest_dict, manifest_path    = self.store.findLatestVersionManifest( 
                                                                            parent_trace        = loop_trace, 
                                                                            manifest_api_name   = manifest_api_name,
                                                                            namespace           = namespace, 
                                                                            name                = name, 
                                                                            kind                = kind)

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
                    my_trace                    = loop_trace.doing("Creating template for manifest",
                                                        data = {"kind":         str(kind),
                                                                "namespace":    str(namespace),
                                                                "name":         str(name)})
                    template_dict, template_df  = self.createTemplate(  parent_trace        = my_trace,
                                                                        form_request        = form_request,
                                                                        kind                = kind)
                    manifest_dict               = template_dict
                    DF_KEY                      = SkeletonController._ManifestInfo.TEMPLATE_DF

                    # At the discretion of the concrete controller class, it can decide that some 'kind' objects
                    # don't need to be in the template.
                    # Example: for the big-rocks controller, the 'investment' kind is not needed because the
                    # controller opted for a variant of "explained", where 'investment' is not needed
                    # That explains why we only add  data if self.createTemplate gave us non-nulls
                    if manifest_dict!= None:
                        manifest_dict['assertion'][DF_KEY]   = template_df
                    
                # As per the comment a few lines above, we allow self.createTemplate to give us null 
                # for some kinds, so we only add to the manifests in scope when there is something to add
                if manifest_dict != None:
                    manifests_in_scope_dict[manifest_identifier]    = manifest_dict 
                # Regardless of whether we added the kind in this loop to the manifests_in_scope, increase
                # the count since manifest_nb must match the kind index - lots of code assumes that.
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

            # GOTCHA
            #       We must process *ALL* manifests, even the read-only ones, because only by parsing them (through
            #       the call to self._buildOneManifest) would we know the Excel row numbers for aligning the various
            #       manifests in the same Excel posting (some might be read-only, others would be new manifests to be saved)
            #
            #       This has a suboptimal performance impact, since in the case of read-only manifests
            #       we effectively have to parse data from Excel that
            #       (other than for row numbers) we already have on disk. On a misguided attempt to make things faster,
            #       I tried skip processing for read-only manifests (loading them from disk instead), but that broke
            #       Apodeixi because the row linkage was not available to tell the parser for non-read-only manifests
            #       what UIDs to reference in the read-only manifest.

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

    def subnamespaceFromLabel(self, parent_trace, label):
        '''
        Helper method that returns what the 'subnamespace' that is a portion of a manifest's name.
        It is inferred from a `label` that provides the posting details for a manifest that should be created.

        Returns a string corresponding to the subnamespace, if one applies to this `kind` of manifest.
        If no subnamespace applies, returns None.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'subnamespaceFromLabel' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__}) 

    def manifestNameFromLabel(self, parent_trace, label, kind):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        label
        @param kind The kind of manifest for which the name is sought. This parameter can be ignored for controller
                    classes that use the same name for all supported kinds; it is meant to support controllers that
                    process multiple manifest kinds and do not use the same name for all of them. For example, controllers
                    that point to reference data in a different domain/sub-domain.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'manifestNameFromLabel' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})  

    def manifestNameFromCoords(self, parent_trace, subnamespace, coords, kind):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        filing coords, possibly complemented by the subnamespace.

        Usually used in the context of generating forms.

        Example: consider a manifest name like "modernization.dec-2020.fusionopus.default"
                in namespace "my-corp.production". 

                To build such a name, this method must receive "modernization" as the subnamespace, and
                filing coords from which to infer "dec-20220", "fusionopus", and "default".

        @param subnamespace A string, which is allowed to be None. If not null, this is a further partioning of
                        the namespace into finer slices, and a manifest's name is supposed to identify the slice
                        in which the manifest resides.

        @param coords A FilingCoords object corresponding to this controller. It is used, possibly along with the
                        `subnamespace` parameter, to build a manifest name.
        @param kind The kind of manifest for which the name is sought. This parameter can be ignored for controller
                    classes that use the same name for all supported kinds; it is meant to support controllers that
                    process multiple manifest kinds and do not use the same name for all of them. For example, controllers
                    that point to reference data in a different domain/sub-domain.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'manifestNameFromCoords' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__}) 

    def manifestLabelsFromCoords(self, parent_trace, subnamespace, coords):
        '''
        Helper method that returns what the a dict whose keys are label field names that should be populated
        inside a manifest based on the parameters, and the values are what the value should be for each label.

        Usually used in the context of generating forms.

        Example: consider a manifest name like "modernization.dec-2020.fusionopus.default"
                in namespace "my-corp.production", that arose from a posting for product "Fusion Opus",
                scoring cycle "Dec 2020" and scenario "Default".

                Then this method returns ["modernization", "Dec 2020", "Fusion Opus", and "Default"].

        @param subnamespace A string, which is allowed to be None. If not null, this is a further partioning of
                        the namespace into finer slices, and a manifest's name is supposed to identify the slice
                        in which the manifest resides.

        @param coords A FilingCoords object corresponding to this controller. It is used, possibly along with the
                        `subnamespace` parameter, to build a manifest name.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'manifestLabelsFromCoords' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})        

    def manifestAsDataFrame(self, parent_trace, kind, namespace, subnamespace, path_tokens):
        '''
        Returns three things:
        
        * DataFrame with the contents of the most recent manifest identified by the parameters.
        * A dict object for the full manifest (i.e., including metadata)
        * A list of UID_Info objects, one per row in the DataFrame returned

        This method is typically used in the context of reports, to get data sets that are input to the report.
        For that reason, the DataFrame that is returned is "not sparse" and has "unabbreviated" UIDs, so that joins
        can easily be done with other datasets also returned by this method.

        If no such manifest exists, it returns None, None

        @param kind A string, corresponding to the `kind` of manifest requested. Must be one of the kinds supported by this
                    controller class.

        @param namespace A string, corresponding to namespace within which the manifest in question is to be found.

        @param subnamespace A string, corresponding to the subnamespace for the manifest in question, if it is for a kind
                        of manifest that requires a subnamespace.

        @param path_tokens A list of strings, corresponding to the folder structure for the manifest under the namespace
                        and, if applicable, the subnamespace.
                        It should be the same list from which this controller's filing coordinates can be built for use in
                        method self.manifestFromCoords
        '''
        if not kind in self.getSupportedKinds():
            raise ApodeixiError(parent_trace, "Can't generate a DataFrame for manifest because the submitted `kind` is not valid",
                                                data = {"kind submitted":       str(kind),
                                                        "valid kinds":          str(self.getSupportedKinds())})

        filing_class                            = self.getFilingClass()
        coords                                  = filing_class()
        coords.build(parent_trace=parent_trace, path_tokens=path_tokens)
        name                                    = self.manifestNameFromCoords(
                                                                    parent_trace, 
                                                                    subnamespace        = subnamespace, 
                                                                    coords              = coords, 
                                                                    kind                = kind) 
        manifest_dict, manifest_path            = self.store.findLatestVersionManifest( 
                                                                    parent_trace        = parent_trace, 
                                                                    manifest_api_name   = self.getManifestAPI().apiName(),
                                                                    namespace           = namespace, 
                                                                    name                = name, 
                                                                    kind                = kind) 

        if manifest_dict == None:
            return None, None, None
            
        manifest_nickname                       = str(kind) + " manifest"
        manifest_entity                         = ManifestUtils().infer_entity(parent_trace, manifest_dict, manifest_nickname)
        rep                                     = AsDataframe_Representer()
        content_dict                            = DictionaryUtils().get_val(
                                                                    parent_trace        = parent_trace, 
                                                                    root_dict           = manifest_dict,
                                                                    root_dict_name      = manifest_nickname,
                                                                    path_list           = ["assertion", str(manifest_entity)],
                                                                    valid_types         = [dict])
        content_df, uid_info_list               = rep.dict_2_df(    parent_trace        = parent_trace, 
                                                                    content_dict        = content_dict,
                                                                    contents_path       = "assertion." + str(manifest_entity), 
                                                                    sparse              = False, 
                                                                    abbreviate_uids     = False)
        return content_df, manifest_dict, uid_info_list

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Returns a  dictionary corresponding to the manifest that was built in this method
        '''
        manifest_nb                 = posting_data_handle.manifest_nb
        kind                        = posting_data_handle.kind

        organization                = label.organization        (parent_trace)
        kb_area                     = label.knowledgeBaseArea   (parent_trace)  
                    
        recorded_by                 = label.recordedBy          (parent_trace)
        estimated_by                = label.estimatedBy         (parent_trace)
        estimated_on                = label.estimatedOn         (parent_trace)

        FMT                         = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        namespace                   = FMT(organization + '.' + kb_area)
        manifest_name               = self.manifestNameFromLabel(parent_trace, label, kind)

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
            if prior_version != None: 
                if read_only == True:
                    # This manifest won't be updated, and if the posting was not adultered by the user
                    # then the manifest in the posting must match exactly the manifest in the store.
                    # Still, we will parse the manifest content in the posting because the parsing
                    # activity will create metadata needed for joins, for example. We won't persist the
                    # manifest parsed, so we won't corrupt the store in the unlikely (but possible)
                    # event that the end user adultered the generated form's section for this manifest
                    # (which was generated to be read only).
                    # So we don't change the version number that we put in this parsed manifest
                    next_version        = prior_version 
                else:  # we are updating, so increase the version number
                    next_version        = prior_version + 1

                # Logic added on November 21, 2021. 
                # This also applies even for read-only manifests. For example,
                # a read-only manifest A may in turn be linked to another read-only manifest B, so
                # need A's prior version in the xlr_config.update_policy even though A is read-only.
                # 
                if type(xlr_config.update_policy) == InferReferenceUIDsPolicy and prior_version > 0:
                    prior_manifest_dict, path   = self.store.findLatestVersionManifest(
                                                            parent_trace            = my_trace,
                                                            manifest_api_name       = self.getManifestAPI().apiName(),
                                                            namespace               = namespace,
                                                            name                    = manifest_name,
                                                            kind                    = kind)
                    xlr_config.update_policy.prior_manifest_dict = prior_manifest_dict

            else: # There is no prior version, so this must be the first version
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

        @param many_to_one A boolean. If True, it is assumed that there are multiple entities in manifest_dict
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
            loop_trace                  = my_trace.doing("Aligning " + str(kind) + " " + str(e_uid) 
                                                            + " to a corresponding " + str(refKind))
            ref_uid                     = UID_FINDER(   parent_trace            = loop_trace, 
                                                        our_manifest_id         = kind, 
                                                        foreign_manifest_id     = refKind, 
                                                        our_manifest_uid        = e_uid,
                                                        many_to_one             = many_to_one)
            if ref_uid == None:
                row_nb                  = self.link_table.row_from_uid(loop_trace, kind, e_uid)

                # Try to get a more user-friendly message to the user, if possible
                try:
                    manifest_nb             = self.manifest_nb_from_kind(loop_trace, refKind)
                    excel_range             = self.show_your_work.get_excel_range(loop_trace, manifest_nb)
                    excel_row_nb            = ExcelTableReader.df_2_xl_row( parent_trace    = loop_trace, 
                                                                            df_row_nb       = row_nb, 
                                                                            excel_range     = excel_range) 
                    row_msg                 = " for Excel row #" + str(excel_row_nb)
                except ApodeixiError as ex:
                    row_msg                 = " for data item #" + str(row_nb + 1) + " (counting from the header)"

                msg                     = "Problem linking " + str(kind) + " to " + str(refKind) \
                                            + row_msg + " in the " + str(kind) + " content." \
                                            + "\nSeems like you didn't populate the corresponding " + str(refKind) \
                                            + " content? At least none could be found in that row"
                raise ApodeixiError(loop_trace, msg)
            
            entity_dict[e_uid][linkField]   = ref_uid

    def linkMappedManifest(self, parent_trace, refKind_list, my_entity, raw_df, first_row, last_row):
        '''
        Used while processing a posting for a manifest that has many-to-many mappings.
        In the Excel posting, the mapping is visually rendered by having the two mapped manifests laid out at
        90 degrees from each other, forming a shape like the letter "L", making them surround a 2-dimensional rectangle
        where the many-to-many mapping is unbundled into binary cells, one for each pair 
        <entity in referencing manifest, entity in referenced manifest>. In Excel, such cells have an "x" if there is
        a mapping between the two manifests' entities corresponding to that cell, and blank otherwise.

        @param refKind The `kind` attribute of the referenced manifest. For example, in the many-to-many mapping
                between milestones and big-rocks, this represents the kind `big-rock`
        @param my_entity The referencing entity. For example, "milestone" in the case of the many-to-many mapping
                between milestones and big rocks.
        @param raw_df A DataFrame, corresponding to DataFrame created by Pandas when reading the layout area corresponding
                to the referencing manifest. Thus, some rows in raw_df correspond to the columns of the referencing
                manifest, and other rows are for the unbundled many-to-many mappings.
        @param first_row An int, corresponding to the row number in Excel where the `raw_df` dataset starts
        @param last_row An int, corresponding to the last row number in Excel where the `raw_df` dataset appears
        '''
        referenced_boundary_dict                = {}
        for refKind in refKind_list:
            first_refRow, last_refRow           = self._get_referenced_manifest_boundaries(parent_trace, refKind)
            referenced_boundary_dict[refKind]   = [first_refRow, last_refRow]  

        non_mapping_df, mapping_df_dict         = self._split_referencing_manifest_raw_data(    
                                                                        parent_trace                = parent_trace, 
                                                                        referenced_boundary_dict    = referenced_boundary_dict, 
                                                                        my_entity                   = my_entity, 
                                                                        raw_df                      = raw_df, 
                                                                        first_row                   = first_row, 
                                                                        last_row                    = last_row)

        manifest_df, linkage_column             = self._rotate_referencing_manifest_properties(
                                                                        parent_trace                = parent_trace, 
                                                                        my_entity                   = my_entity, 
                                                                        non_mapping_raw_df          = non_mapping_df)
        referencing_entities_list               = list(manifest_df[linkage_column])
        for refKind in refKind_list:
            my_trace                            = parent_trace.doing("Adding a column of mappings to manifest_df for "
                                                                        + "the mappings for '" + str(refKind))
            refMapping_df                       = mapping_df_dict[refKind]
            first_refRow, last_refRow           = referenced_boundary_dict[refKind]
            referencing_mappings                = self._collect_referenced_uid_list(
                                                                        parent_trace                = parent_trace, 
                                                                        referencing_entities_list   = referencing_entities_list, 
                                                                        referencing_entity          = my_entity,
                                                                        refKind                     = refKind, 
                                                                        first_refRow                = first_refRow,
                                                                        refMapping_df               = refMapping_df)
            def assign_ref_uids(row):
                referencing_entity      = row[linkage_column]
                uid_list                = referencing_mappings[referencing_entity]
                return uid_list

            manifest_df[refKind]        = manifest_df.apply(lambda row: assign_ref_uids(row), axis=1)

        # Clean up any spurious Pandas suffixes in the raw column names that made it to the first column of 
        # manifest_df when it was created by rotating the raw DataFrame.
        #
        # GOTCHA: Don't do this earlier in the flow, as it could break the test made in self._collect_referenced_uid_list,
        #           which compares two lists one of which is the raw columns, with Pandas suffixes and all.
        manifest_df                     = self._remove_spurious_Pandas_column_suffixes(parent_trace, manifest_df)

        # If we are doing an update, we need to clear out spuriously named "UIDs" like "Unnamed: 8". This happens
        # if the user added additional milestones as part of the update. Since there is a "UID" already (being
        # an update), these new milestones will have a blank UID in Excel, and Pandas will convert into something
        # like "Unnamed: 8" (if it is column 8+1 in Excel), since Pandas DataFrame's require non-null columns.
        # But after the transpose that created manifest_df, in manifest_df these are values in the "UID" column, 
        # and we need to blank them so that the Apodeixi parser will not error out when it encounters strings like
        # "Unnamed: 8" that are not valid UIDs. Instead, we want them to be blank so that the Apodeixi parser
        # will generate a new valid UID for them.
        #
        # We had to wait until the end to do this cleanup since columns like "Unnamed: 8" are needed in prior-processing
        # to have a unique string identifier for raw columns and corresponding referencing (even if fake) entities
        if linkage_column == Interval.UID:
            def _clean_UIDs(row):
                raw_uid                 = row[Interval.UID]
                if raw_uid.startswith("Unnamed:"):
                    cleaned_uid         = ""
                else:
                    cleaned_uid         = raw_uid
                return cleaned_uid
            manifest_df[Interval.UID]   = manifest_df.apply(lambda row: _clean_UIDs(row), axis=1)

        return manifest_df

    def restoreReferenceManifestUIDs(self, parent_trace, xlr_config, row_number):
        '''
        Utility method that derived classes may choose to call.
        Intended to avoid "frivolous" diffs that can arise when referencing manifests are updated.

        Such "frivolous" diffs arise because reference manifests usually hide their UID field in Excel.
        Instead, they rely on a link field (usually also hidden) to align with the rows of a referenced
        manifest.

        For example, when the 'big-rock-estimate' referencing manifest is rendered on Excel, the manifest's
            'bigRock' field is used to align with Excel rows for a corresponding 'big-rock' entity.

        The problem with this is that when the Excel file is re-posted as an update, then the controller
        won't be receiving from Excel the UIDs for the 'big-rock-estimate' entities, so it will simply
        generate new ones.
        
        That gives the fall impression that all 'big-rock-estimate' entities changed, which is inaccurate.

        To avoid such situation, this (optional) method takes a referencing `manifest_dict` (for example, for
        'big-rock-estimate') and adds a UID column with the UIDs of the previuosly persisted 'big-rock-estimate'
        manifest.
        This "UID defaulting" is done for any entity in `manifest_dict` that was present in the previous version.
        This determination is made using the `linkField` to map entities in `manifest_dict` to the a referenced
        manifest and to entities in the prior versio of the referencing manifest.

        GOTCHA: This method must be called *after* self.linkReferenceManifest (usually done in 
            the concrete class's implementation of self._buildAllManifests()) since that link is relied upon.

        @param xlr_config   The PostingConfig we are using to process a posting to create a manifest.
        @param row_number An int, corresponding to the index in the DataFrame for the referencing manifest.
                Counts start at 0.
        '''
        referencing_uid                 = None
        if type(xlr_config.update_policy) == InferReferenceUIDsPolicy:
            try:

                referenced_kind             = xlr_config.update_policy.referenced_kind
                link_field                  = xlr_config.update_policy.link_field
                referenced_uid              = self.link_table.uid_from_row(parent_trace, referenced_kind, row_number)

                prior_manifest_dict         = xlr_config.update_policy.prior_manifest_dict

                entity                      = xlr_config.entity_as_yaml_fieldname()
                if prior_manifest_dict != None:

                    prior_content_dict      = DictionaryUtils().get_val(
                                                        parent_trace    = parent_trace,
                                                        root_dict       = prior_manifest_dict,
                                                        root_dict_name  = "Manifest dict for '" + str(referenced_kind) +"'",
                                                        path_list       = ["assertion", entity],
                                                        valid_types     = ["dict"])
                    rep                     = AsDataframe_Representer()
                    prior_manifest_df, uid_info_list    = rep.dict_2_df(
                                                                        parent_trace    = parent_trace,
                                                                        content_dict    = prior_content_dict,
                                                                        contents_path   = "assertion." + entity,
                                                                        sparse          = False,
                                                                        abbreviate_uids = False)
                                    

                    if not link_field in prior_manifest_df.columns:
                        raise ApodeixiError(parent_trace, "The link field provided is not a valid column in the "
                                                            + "DataFrame for the manifest's prior version",
                                                        data = {"link_field":       str(link_field),
                                                                "DataFrame columns": str(prior_manifest_df.columns),
                                                                "DataFrame row":    str(row_number),
                                                                "referenced_kind":  str(referenced_kind)})
                    filtered_df             = prior_manifest_df[prior_manifest_df[link_field]==referenced_uid]
                    if len(filtered_df.index) > 1:
                        raise ApodeixiError(parent_trace, "Corrupted referencing - should have at most one reference")
                    elif len(filtered_df.index) == 1:
                        referencing_uid     = filtered_df.iloc[0][Interval.UID]

            
            except Exception as ex:
                if type(ex) == ApodeixiError:
                    raise ex # Just propagate exception, retaining its friendly FunctionalTrace
                else:
                    raise ApodeixiError(parent_trace, "Found a problem retrieving UID from manifest's prior version",
                                                        data = {"error":    str(ex),
                                                        "DataFrame row":    str(row_number),
                                                        "referenced_kind":  str(referenced_kind),
                                                        "link_field":       str(link_field)})        
            return referencing_uid 

    def _get_referenced_manifest_boundaries(self, parent_trace, refKind):
        '''
        Helper method used by self.linkMappedManifest. Please refer to the documentation for that method.

        This method returns a pair of integers, corresponding to the Excel first and last row numbers for the referenced
        manifest `refKind`.

        For example, in the many-to-many relationship between milestones and big-rocks, this method returns the
        Excel row numbers for `big-rocks` content. This allows the coller to determine which are the rows where
        mapping information lies within the bigger set of rows in the `milestones` layout.

        @param refKind The `kind` attribute of the referenced manifest. For example, in the many-to-many mapping
                between milestones and big-rocks, this represents the kind `big-rock`
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
        return first_refRow, last_refRow

    def _split_referencing_manifest_raw_data(self, parent_trace, referenced_boundary_dict, my_entity, raw_df, 
                                            first_row, last_row):
        '''
        Helper method used by self.linkMappedManifest. Please refer to the documentation for that method

        This method does a subset of all the processing needed when parsing Excel content's for a referencing
        manifest in a many-to-many relationship to another manifest.
        
        This method splits the `raw_df` into multiple DataFrames, and returns that split in two data structures:

        * A DataFrame consisting of the rows in `raw_df` that are not mappings
        * A dictionary of DataFrames, where the keys are the referenced manifests and each value is a DataFrame
          consisting for the rows in `raw_df` for the mappings to that referenced manifest.

        For example, in the case of the many-to-many mapping between milestones and big-rocks, imagine a situation
        where the milestones are displayed in rows 2-32 in Excel, and the big rocks in rows 8-32.
        Then this method would return (approximately, see note below on re-indexing, and remembering that Excel
        row 2 correspond to index 0 in raw_df):

        * raw_df[0:5]                       (Excel rows 2-7     : the milestone's Excel area not used for mappings) 
        * {"big-rock": raw_df[6:26]}        (Excel rows 8-28    : the milestone's Excel area for mappings)

        This example is "approximate" in that the computation is against a copy of `raw_df` that is re-indexed so that 
        indices are exactly the same as Excel row number. The example "ignores" that by assuming that `raw_df` is already
        thus indexed, though normally that isn't the case when this method is called.

        *IMPORTANT* The referenced_boundary_dict must be *SORTED*.
            This means: if key1 appears before key2 in referenced_boundary_dict.keys(), then:
                    val1[0] <= val1[1] < val2[0] <= val2[1], where valx = referenced_boundary_dict[keyx]
            Otherwise it will raise an ApodeixiError
        
        @param referenced_boundary_dict A dctionary of lists, where the keys are the `kind` properties of each of
                the referenced manifests. For each key, its value is a list of 2 
                integers denoting the "row boundaries" of the referenced manifest in question, where the "row
                boundary" is expressed as the first and last Excel row numbers for the content of the referenced manifest.
                For example, in the many-to-many mapping between milestones and big-rocks, maybe the big-rocks
                is the only referenced manifest and it is displayed between Excel row 8 and 32, while the milestone
                mananifest uses more rows, from Excel row 2 to 28, say. 
                In that case, the parameter `referenced_boundary_list` should be {"big-rock": [8, 32]}
        @param my_entity The referencing entity. For example, "milestone" in the case of the many-to-many mapping
                between milestones and big rocks.
        @param raw_df A DataFrame, corresponding to DataFrame created by Pandas when reading the layout area corresponding
                to the referencing manifest. Thus, some rows in raw_df correspond to the columns of the referencing
                manifest, and other rows are for the unbundled many-to-many mappings.
        @param first_row An int, corresponding to the row number in Excel where the `raw_df` dataset starts
        @param last_row An int, corresponding to the last row number in Excel where the `raw_df` dataset appears
        '''
        my_trace                                    = parent_trace.doing("Checking that referenced boundaries are sorted")
        if True:
            last_boundary_row_nb                    = -1
            for refKind in referenced_boundary_dict.keys():
                loop_trace                              = my_trace.doing("Checking boundaries for mapping rows referencing '"
                                                                    + str(refKind) + "'")
                first_refRow, last_refRow           = referenced_boundary_dict[refKind]
                if first_refRow <= last_boundary_row_nb:
                    raise ApodeixiError(loop_trace, "Mapping boundaries are not properly sorted: expected first_refRow > " 
                                                        + str(last_boundary_row_nb),
                                                    data = {"first_refRow":     str(first_refRow)})
                if last_refRow < first_refRow:
                    raise ApodeixiError(loop_trace, "Mapping boundaries are not properly sorted: "
                                                        + "expected first_refRow <= last_refRow ",
                                                    data = {"first_refRow":     str(first_refRow),
                                                            "last_refRow":     str(last_refRow)})
            last_boundary_row_nb                    = last_refRow

        my_trace                                    = parent_trace.doing("Split raw_df into dataset_df and mapping_df, "
                                                                + "indexed by Excel row numbers")
        if True:
            # Re-index raw_df so that its row indices are exactly the same as Excel row numbers.
            # We start at first_row+1 since first_row is the headers of raw_df
            working_df                              = raw_df.copy()       
            
            working_df.index                        = range(first_row + 1, first_row + 1 + len(working_df.index))

            non_mapping_df_list                     = []
            mapping_df_dict                         = {}
            next_non_mapping_row_candidate          = first_row + 1
            for refKind in referenced_boundary_dict.keys():
                loop_trace                          = my_trace.doing("Splitting out mapping rows referencing '" 
                                                                            + str(refKind) + "'")
                first_refRow, last_refRow           = referenced_boundary_dict[refKind]

                # It should be the case that next_non_mapping_row_candidate <= first_refRow <= last_refRow
                # and that all of them are a valid index in working_df
                if not (next_non_mapping_row_candidate <= first_refRow and first_refRow <= last_refRow):
                    raise ApodeixiError(loop_trace, "Invalid mapping structure between '" + str(my_entity) + "' and '"
                                                    + str(refKind) + "': expected Excel rows to adhere to "
                                                    + "next_non_mapping_row_candidate <= first_refRow <= last_refRow",
                                                    data = {"next_non_mapping_row":     str(next_non_mapping_row_candidate),
                                                            "first_refRow":             str(first_refRow),
                                                            "last_refRow":              str(last_refRow)})
                if not next_non_mapping_row_candidate in working_df.index:
                    raise ApodeixiError(loop_trace, "Invalid mapping structure between '" + str(my_entity) + "' and '"
                                                    + str(refKind) + "': " + str(my_entity) + " should include row "
                                                    + str(next_non_mapping_row_candidate),
                                                    data = {"next_non_mapping_row":     str(next_non_mapping_row_candidate)})
                if not first_refRow in working_df.index:
                    raise ApodeixiError(loop_trace, "Invalid mapping structure between '" + str(my_entity) + "' and '"
                                                    + str(refKind) + "': " + str(my_entity) + " should include row "
                                                    + str(first_refRow)
                                                    + " Are your ranges for both datasets aligned in the Posting Label?",
                                                    data = {"first_refRow":             str(first_refRow)})
                if not last_refRow in working_df.index:
                    raise ApodeixiError(loop_trace, "Invalid mapping structure between '" + str(my_entity) + "' and '"
                                                    + str(refKind) + "': " + str(my_entity) + " should include row "
                                                    + str(last_refRow) 
                                                    + " Are your ranges for both datasets aligned in the Posting Label?",
                                                    data = {"last_refRow":              str(last_refRow)})

                # NB: loc is inclusive, so loc[3:5] includes rows 3, 4, and 5 (not just 3,4)
                mapping_df                          = working_df.loc[first_refRow + 1: last_refRow] 
                mapping_df_dict[refKind]            = mapping_df

                non_mapping_section_df              = working_df.loc[next_non_mapping_row_candidate:first_refRow]
                non_mapping_df_list.append(non_mapping_section_df)
                next_non_mapping_row_candidate      = last_refRow + 1
            # Consider a potential last section of non-mapping rows, if there is data in raw_df after the mappings
            # for the last referenced manifest. Take all remaining rows, if any
            non_mapping_section_df                  = working_df.loc[next_non_mapping_row_candidate:]
            non_mapping_df_list.append(non_mapping_section_df)

            non_mapping_df                          = _pd.concat(non_mapping_df_list)

            return non_mapping_df, mapping_df_dict

    def _rotate_referencing_manifest_properties(self, parent_trace, my_entity, non_mapping_raw_df):
        '''
        Helper method used by self.linkMappedManifest. Please refer to the documentation for that method

        This method does a subset of all the processing needed when parsing Excel content's for a referencing
        manifest in a many-to-many relationship to another manifest.
        
        This method focuses on creating the referencing manifest intrinsic properties, i.e., excludes the join
        information. A big part of that is doing a "rotation" of the raw information, since the referencing
        manifest is displayed in Excel at 90 degrees

        The intention is that the caller (method self.linkMappedManifest) will call this to build the "first draft"
        of the referencing manifest, and then other logic would enrich it with the list of UIDs for the referenced
        manifest (or manifests, if there are multiple many-to-many relatonships at play.)

        Returns two things:

        * A DataFrame, corresponding to the "first pass" manifest dataframe, properly rotated and cleaned up

        * The name of the column in the returned DataFrame containing the referenced manifest's entities.

        @param my_entity The referencing entity. For example, "milestone" in the case of the many-to-many mapping
                between milestones and big rocks.
        @param raw_df A DataFrame, corresponding to DataFrame created by Pandas when reading the layout area corresponding
                to the referencing manifest. Thus, some rows in raw_df correspond to the columns of the referencing
                manifest, and other rows are for the unbundled many-to-many mappings.
        @param first_row An int, corresponding to the row number in Excel where the `raw_df` dataset starts
        @param last_row An int, corresponding to the last row number in Excel where the `raw_df` dataset appears
        '''
        my_trace                            = parent_trace.doing("Creating manifest DataFrame")
        if True:
            manifest_columns                = list(non_mapping_raw_df.columns)[0] # These will be the manifest columns
            df2                             = SchemaUtils.drop_blanks(non_mapping_raw_df, manifest_columns)
            df2                             = df2.set_index(manifest_columns) # That way when we transpose these become the columns
            df2.index.name                  = None
            df2                             = df2.transpose()
            df2                             = df2.reset_index() # Ensures columns of dataset_df become the first column of df2

            # GOTCHA This is some tricky code. Various situations can happen, when one does an initial create
            #           and later does updates. Consider an entity called "Milestone"
            #   * In the manifest, that may be converted to lowercase: milestone. So we can't compare my_entity 
            #       ("Milestone") to the columns as-is, since "milestone != "Milestone"
            #   * On a create, there is no UID column (displayed as a row in Excel since we are at 90 degrees)
            #     In that case,the first column might be called "Milestone", but upon a rotation that label may go away
            #     So that makes it sound like we should forcefull force the first column after rotation to be 
            #     "Milestone"
            #   * However, that would be a mistake during an update, since the UID column protects the "Milestone"
            #     column during the rotation, so it is not lost. That means that the re-naming we should do on a create
            #     should not be done on an update
            #    * And in all this logic, comparisons must be done up to YAML equivalence.
            if not StringUtils().is_in_as_yaml(my_entity, list(df2.columns)):
                # In this case we need to rename the first column to be as the entity. This typically happens
                # in a create (as opposed to an update), since a create there is no UID column in dataset_df,
                # and the first column which was the entity (e.g., "Milestone" in our example) was "lost" during 
                # the transpose that created df_2, so now the first column of df_2 is probably something like "index".
                # So we re-name that column from "index" to "Milestone"
                # 
                renamed_columns             = [my_entity]
                renamed_columns.extend(df2.columns[1:])
                df2.columns                 = renamed_columns

                # This is the column in df_2 whose values are equal to (all but the first) columns in mapping_df.
                # This is used below to figure out the mapping, i.e., to build the list of uids in the
                # referenced manifest that our referencing manifest must reference.
                linkage_column               = my_entity
            else:
                # In this case, we are doing an update (as opposed to a create). Consider the example where
                # the entity is "Milestone". Had this been a create, then "Milestone" would have been the first
                # column of dataset_df and it woudl have been "lost" in the transpose that created df_2, turning itself
                # into "index". But since we did not lose it, it means that there must have been another column,
                # of necessity "UID", to the left of the "Milestone" column. But then this means that we "lost"
                # UID, so we need to restore it now
                renamed_columns             = [Interval.UID]
                renamed_columns.extend(df2.columns[1:])
                df2.columns                 = renamed_columns     

                # This is the column in df_2 whose values are equal to (all but the first) columns in mapping_df.
                # This is used below to figure out the mapping, i.e., to build the list of uids in the
                # referenced manifest that our referencing manifest must reference.
                linkage_column               = Interval.UID

            manifest_df                     = df2

        return manifest_df, linkage_column

    def _remove_spurious_Pandas_column_suffixes(self, parent_trace, rotated_df):
        '''
        This method does some cleanup on a DataFrame that arose from a rotation of a prior DataFrame
        read "raw" from Excel.

        The raw DataFrame might have had "duplicate columns" which were simply meant to be
        the same entity value for multiple entries in `rotated_df`'s first column.
        For example, perhaps multiple columns in Excel were labelled "Target State" by the user, which Pandas
        converted to "Target State", "Target State.1", "Target State.2", etc.
        
        Now that we rotated, the extra suffixes attached by Pandas (".1", ".2", etc) should be removed to
        restore the user's original intention
        '''
        restored_df                     = rotated_df.copy()
        FIRST_COL                       = restored_df.columns[0]
        raw_vals                        = list(restored_df[FIRST_COL])

        restored_vals                   = []
        for raw in raw_vals:
            tokens                      = raw.split(".")
            head                        = ".".join(tokens[:-1])
            tail                        = tokens[-1]
            if len(tokens) > 1 and tail.isdigit() and head in restored_vals:
                # This means this is something like "Target State.2" and we previously saw "Target State", so
                # it seems certain that Pandas added the ".2" suffix. So don't use it
                restored_vals.append(head)
            else:
                restored_vals.append(raw)
        
        restored_df[FIRST_COL]                  = restored_vals

        return restored_df
       

    def _collect_referenced_uid_list(self, parent_trace, referencing_entities_list, referencing_entity,
                                                    refKind, first_refRow, refMapping_df):
        '''
        Helper method used by self.linkMappedManifest. Please refer to the documentation for that method

        Returns a dictionary whose keys are the possible entity values for the referencing manifest, and each value
        is a list of UIDs of the referenced manifest that are pointed to by the referencing manifest's entity in the key.

        @param referencing_entities_list A list of strings, corresponding to the entities of the referencing manifest.
            For example: for the many-to-many mapping between Milestones and Big Rocks, this would be something like
            ["M1", "M2", "M3", ...]

        @referencing entity A string, corresponding to the top entity of the referencing manifest. For example, in the
                many-to-many mapping between Milestones and Big Rocks, that would be "Milestone"
        @refKind The kind of the referenced manifest. For example, in the many-to-many mapping between Milestones and
                Big Rocks, that would be "big-rock" 
        @param first_refRow An int, corresponding to the first Excel row number for the `refKind` manifest. For example, in 
                the many-to-many mapping between Milestones and Big Rocks, if Milestones occupy rows 2-32 in Excel and
                Big Rock occupies rows 8-32, then first_refRow = 8
        @param refMapping_df A DataFrame, which is a subset of the raw DataFrame rows after the Pandas reads the
                referencing manifest range. The subset correspond to the rows that are for mappings. For example, in 
                the many-to-many mapping between Milestones and Big Rocks, if Milestones occupy rows 2-32 in Excel and
                Big Rock occupies rows 8-32, then refMapping_df is raw_df[8:28], where raw_df is the DataFrame loaded
                by Pandas for the Milestones area (ie., "raw" in that it has not be rotated or cleaned up yet)               
        '''
        # Test we correctly chose linkage_column
        list1                       = list(refMapping_df.columns)[1:]

        if list1 != referencing_entities_list:
            raise ApodeixiError(parent_trace, "Problem establishing linkage when processing mapping of manifests: lists "
                                            "should match",
                                        data = {"list1": str(list1), "list2": str(referencing_entities_list), 
                                                    "referenced Kind": str(refKind),
                                                    "referencing entity": referencing_entity})
            
        my_trace                        = parent_trace.doing("Create mapped vectors per referencing entity")
        if True:
            # refMapping_df is "only mappings" - we filtered out the rows that were properties or our entity ("Milestones"
            # in the example), so refMapping_df'w rows have "x"s expressing a mapping (e.g., big rocks linked to milestone)
            referencing_mappings          = {}

            for referencing_entity in list(refMapping_df.columns)[1:]: # This list is the same as manifest_df[linkage_column]
                uid_list                = []
                
                for row_nb in refMapping_df.index:
                    val                 = refMapping_df[referencing_entity].loc[row_nb]
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
                referencing_mappings[referencing_entity] = uid_list

        return referencing_mappings

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
        manifest_name               = self.manifestNameFromCoords(parent_trace, subnamespace, coords, kind)

        if namespace == None:
            raise ApodeixiError(parent_trace, "Can't create Excel template because namespace was not set")
        if type(namespace) != str:
            raise ApodeixiError(parent_trace, "Can't create Excel template because namespace is a '"
                                                + str(type(namespace)) + "'; a string was expected instead")

        tokens                      = namespace.split(".")
        if len(tokens) != 2:
            raise ApodeixiError(parent_trace, "Can't create Excel template because namespace is in the wrong format",
                                        data = {"expected": "<organization>.<Knowledge Base area>",
                                                "received": str(namespace)})

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
            manifest_name           = self.manifestNameFromLabel(parent_trace, label, kind)
            
            # Load the prior manifest, to determine which UIDs are already in use so that we don't
            # re-generate them for different data items
            prior_handle    = ManifestHandle(   manifest_api    = self.getManifestAPI().apiName(),
                                                namespace       = namespace, 
                                                name            = manifest_name, 
                                                kind            = kind,
                                                version         = prior_version)
            prior_manifest, prior_manifest_path     = self.store.retrieveManifest(my_trace, prior_handle) 

            if prior_manifest == None:
                raise ApodeixiError(my_trace, "Prior version of manifest does not exist, but it should",
                                            data = {"prior version":            prior_version,
                                                    "prior manifest handle":    prior_handle.display(my_trace)})                                                       
            
            acronym_schema  = UID_Acronym_Schema()
            acronym_schema.build_schema_from_manifest(parent_trace, prior_manifest) 
            store.set_acronym_schema(parent_trace, acronym_schema) 

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
            my_trace                        = parent_trace.doing("Checking referential integrity")
            expected_organization           = self.controller.a6i_config.getOrganization(my_trace)
            allowed_kb_areas                = self.controller.a6i_config.getKnowledgeBaseAreas(my_trace)

            if not StringUtils().equal_as_yaml(self.organization(my_trace), expected_organization):
                raise ApodeixiError(my_trace, "Invalid organization field in Posting Label",
                                data = {    "Expected":     str(expected_organization),
                                            "Submitted":    str(self.organization(my_trace))})

            if not StringUtils().is_in_as_yaml(txt = self.knowledgeBaseArea(my_trace), a_list = allowed_kb_areas):
                raise ApodeixiError(my_trace, "Invalid knowledge base field in Posting Label",
                                data = {    "Allowed any of":   str(allowed_kb_areas),
                                            "Submitted":        str(self.knowledgeBaseArea(my_trace))})

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

            # Ensure val is an int. If it is a blank, treat it as null (so no prior version - caller must do a "Create"). 
            # Otherwise, that's an error
            if StringUtils().is_blank(val):
                val         = None
            elif val != None and type(val) != int:
                raise ApodeixiError(parent_trace, "Invalid priorVersion: expected an integer, and instead found a '"
                                                    + str(type(val)) + "'",
                                                    data = {"priorVersion": str(val)})

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
                    manifest_nb = int(kind_list[idx])
                    kind_field  = ME._DATA_KIND    + '.' + str(manifest_nb)   # The field in the PostingLabel, like 'data.kind.2'
                    range_field = ME._DATA_RANGE   + '.' + str(manifest_nb)
                    sheet_field = ME._DATA_SHEET   + '.' + str(manifest_nb)
                    _keep_work(parent_trace, manifest_nb, kind_field, range_field, sheet_field) 

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
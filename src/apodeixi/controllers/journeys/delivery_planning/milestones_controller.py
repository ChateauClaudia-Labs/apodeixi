import pandas as                                                            _pd

from apodeixi.util.a6i_error                                                import ApodeixiError
from apodeixi.util.formatting_utils                                         import StringUtils

from apodeixi.controllers.util.skeleton_controller                          import SkeletonController
from apodeixi.controllers.journeys.delivery_planning.journeys_posting_label import JourneysPostingLabel
from apodeixi.controllers.journeys.delivery_planning.journeys_controller    import JourneysController

from apodeixi.knowledge_base.knowledge_base_util                            import FormRequest
from apodeixi.knowledge_base.manifest_utils                                 import ManifestUtils

from apodeixi.text_layout.excel_layout                                      import AsExcel_Config_Table, \
                                                                                ManifestXLWriteConfig, \
                                                                                MappedManifestXLWriteConfig, \
                                                                                NumFormats

from apodeixi.xli.interval                                                  import GreedyIntervalSpec

from apodeixi.xli.posting_controller_utils                                  import PostingConfig
from apodeixi.xli                                                           import UpdatePolicy
from apodeixi.controllers.journeys.delivery_planning.big_rocks              import BigRocksEstimate_Controller

class MilestonesController(JourneysController):
    '''
    Class to process an Excel posting journey milestiones. It produces one YAML manifests.

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)
        ME                              = MilestonesController

        self.SUPPORTED_VERSIONS         = ['v1a']

        # GOTCHA: 
        # These must be listed in the order in which they are later processed in _build_manifestsXLWriteconfig
        # For example, since _build_manifestsXLWriteconfig assumes a key like 'big-rock.0', we must have
        # 'big-rock' as the first member of the list. 
        # Otherwise, self.generateForm(-) might fail for a blind form request because when it searches for manifests,
        # it doe so by kind in the order they appear here, and imputs a key like "big-rock.0" based on the order
        # here, and that key is later assumed in the _build_manifestsXLWriteconfig. If instead we put big-rock second end
        # of the list, the key would be 'big-rock.1' and _build_manifestsXLWriteconfig would error out as an
        # unrecognized key
        self.SUPPORTED_KINDS            = [ME.REFERENCED_KIND, ME.MY_KIND] # Process referenced dependency first

    MY_KIND                             = 'modernization-milestone'
    REFERENCED_KIND                     = 'big-rock'

    def getSupportedVersions(self):
        return self.SUPPORTED_VERSIONS 

    def getSupportedKinds(self):
        return self.SUPPORTED_KINDS

    def getPostingConfig(self, parent_trace, kind, manifest_nb):
        '''
        Return a PostingConfig, corresponding to the configuration that this concrete controller supports.
        '''
        ME                              = MilestonesController
        if kind == ME.MY_KIND:
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = ME._MilestonesConfig( update_policy       = update_policy, 
                                                                kind                = kind, 
                                                                manifest_nb         = manifest_nb,
                                                                controller          = self)
        elif kind == ME.REFERENCED_KIND:
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = BigRocksEstimate_Controller._BigRocksConfig(  update_policy       = update_policy, 
                                                                                        kind                = kind,
                                                                                        manifest_nb         = manifest_nb,
                                                                                        controller          = self)

        else:
            raise ApodeixiError(parent_trace, "Invalid domain object '" + kind + "' - should be one of "
                                                + ", ".join(self.SUPPORTED_KINDS),
                                                origination = {'signaled_from': __file__})

        return xlr_config 

    def getPostingLabel(self, parent_trace):
        '''
        Returns a PostingLabel, corresponding to the what is expected by this concrete controller class.
        '''
        ME                              = MilestonesController
        return ME._MyPostingLabel(parent_trace, controller = self)

    def _build_manifestsXLWriteconfig(self, parent_trace, manifestInfo_dict):
        '''
        Overwrites parent's implementation

        Creates and returns an AsExcel_Config_Table containing the configuration data for how to lay out and format
        all the manifests of `manifestInfo_dict` onto an Excel spreadsheet
        '''
        ME                                  = BigRocksEstimate_Controller
        xlw_config_table                    = AsExcel_Config_Table()
        x_offset                            = 1
        #y_offset                            = 1
        for key in manifestInfo_dict:
            loop_trace                      = parent_trace.doing("Creating layout configurations for manifest '"
                                                                + str(key) + "'")
            manifest_info                   = manifestInfo_dict[key]
            data_df                         = manifest_info.getManifestContents(parent_trace)
            
            if key == 'big-rock.0':
                editable_cols               = [] # Nothing is editable for big-rocks, since it is reference data
                hidden_cols                 = []
                right_margin                = 0
                num_formats                 = {}
                excel_formulas              = None
                df_xy_2_excel_xy_mapper   = None
                is_transposed               = False

                # We must leave some rows above empty for the other manifest (the modernization-milestone.1) that will
                # appear transposed. So we shift y_offset by the number of columns in the other manifest
                other_manifest_df           = manifestInfo_dict['modernization-milestone.1']._contents_df
                y_offset                    = 1 + len(other_manifest_df.columns)

                xlw_config  = ManifestXLWriteConfig( 
                                            sheet                       = SkeletonController.GENERATED_FORM_WORKSHEET,
                                            manifest_name               = key, 
                                            read_only                   = True,
                                            is_transposed               = is_transposed,    
                                            viewport_width              = 100,  
                                            viewport_height             = 40,   
                                            max_word_length             = 20, 
                                            editable_cols               = editable_cols,
                                            hidden_cols                 = hidden_cols,  
                                            num_formats                 = num_formats, 
                                            excel_formulas              = excel_formulas,
                                            df_xy_2_excel_xy_mapper   = df_xy_2_excel_xy_mapper,
                                            editable_headers            = [],   
                                            x_offset                    = x_offset,    
                                            y_offset                    = y_offset)
            elif key == 'modernization-milestone.1':
                editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
                hidden_cols                 = ['big-rock'] # These are list values, so can't be displayed in a cell. Will instead display in enriched mapping rows.
                right_margin                = 0
                num_formats                 = {}
                excel_formulas              = None
                df_xy_2_excel_xy_mapper   = None

                # We display milestones rotated 90 degrees, so we set the transposed flag and also exchange
                # the x and y offsets (so here the value of x is vertical and y is horizontal, and right
                # values have x being horizontal and y being vertical)
                is_transposed               = True
                original_x_offset           = x_offset
                original_y_offset           = y_offset
                x_offset                    = 1
                y_offset                    = original_x_offset

                # We use a specialized XL Write Config class, one that understands mappings
                xlw_config  = MappedManifestXLWriteConfig( 
                                            sheet                       = SkeletonController.GENERATED_FORM_WORKSHEET,
                                            manifest_name               = key, 
                                            read_only                   = False,
                                            referenced_manifest_name    = 'big-rock.0',
                                            my_entity                   = "milestone", 
                                            mapped_entity               = "big-rock",
                                            is_transposed               = is_transposed,    
                                            viewport_width              = 100,  
                                            viewport_height             = 40,   
                                            max_word_length             = 20, 
                                            editable_cols               = editable_cols,
                                            hidden_cols                 = hidden_cols,  
                                            num_formats                 = num_formats, 
                                            excel_formulas              = excel_formulas,
                                            df_xy_2_excel_xy_mapper   = df_xy_2_excel_xy_mapper,
                                            editable_headers            = [],   
                                            x_offset                    = x_offset,    
                                            y_offset                    = y_offset)

            else:
                raise ApodeixiError(loop_trace, "Invalid manifest key: '" + str(key) + "'")

            # Put next manifest to the right of this one, separated by an empty column
            x_offset                        += data_df.shape[1] -len(hidden_cols) + right_margin
            xlw_config_table.addManifestXLWriteConfig(loop_trace, xlw_config)
        return xlw_config_table

    def _buildAllManifests(self, parent_trace, posting_label_handle):
        ME                              = MilestonesController
        all_manifests_dict, label       = super()._buildAllManifests(parent_trace, posting_label_handle)

        return all_manifests_dict, label

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, posting_data_handle, label)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to MilestonesController") 

        return manifest_dict

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
        template_dict, template_df      = super().createTemplate(parent_trace, form_request, kind)

        ME                              = MilestonesController
        
        scope                                   = form_request.getScope(parent_trace)
        if type(scope) != FormRequest.SearchScope:
            raise ApodeixiError(parent_trace, "Can't create template for because request form is invalid: it should "
                                    + "have a scope of type FormRequest.SearchScope",
                                    data = {"form_request": form_request.display(parent_trace)})
        
        coords                          = form_request.getFilingCoords(parent_trace)
        namespace                       = scope.namespace
        subnamespace                    = scope.subnamespace
        name                            = self.manifestNameFromCoords(parent_trace, subnamespace, coords)

        manifest_api                    = self.getManifestAPI()

        if kind == ME.REFERENCED_KIND:
            posting_api                 = form_request.getPostingAPI(parent_trace)
            raise ApodeixiError(parent_trace, "Can't create template for posting API '" + str(posting_api) + "' "
                                        + "because this API requires pre-existence of a '" + str(kind) + "' manifest, and "
                                        + "no '" + str(kind) + "' manifest was not found at the expected location:"
                                        + "\n\tmanifest_api         = " + str(manifest_api.apiName())
                                        + "\n\tnamespace            = " + str(namespace)
                                        + "\n\tname                 = " + str(name)
                                        + "\n\tkind                 = " + str(kind))
        elif kind == ME.MY_KIND:
            m_list                      = ["SME market", "SME market", "New UX", "Cloud"]
            t_list                      = ["CAM expansion", "Margin improvement", "New UX", "Cloud Native"]
            d_list                      = ["Q3 FY20", "Q1 FY21", "Q4 FY21", "Q4 FY22"]

            template_df                 = _pd.DataFrame({"Milestone": m_list, "Theme": t_list, 'Date': d_list})
        else:
            raise ApodeixiError(parent_trace, "Invalid domain object '" + kind + "' - should be one of "
                                                + ", ".join(self.SUPPORTED_KINDS),
                                                origination = {'signaled_from': __file__})

        return template_dict, template_df

    class _MilestonesConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for modernization milestones
        '''

        _ENTITY_NAME                            = 'Milestone'

        def __init__(self, update_policy, kind, manifest_nb, controller):
            ME                                  = MilestonesController._MilestonesConfig

            super().__init__(   kind            = kind, 
                                update_policy   = update_policy, 
                                manifest_nb     = manifest_nb,
                                controller      = controller)

            # These three settings replace the parent class's defaults. That ensures we read Excel by columns, 
            # not by rows, and that we realize a fair amount of rows in Excel are really a mapping to big rock, not
            # manifest entities' properties.
            self.horizontally                   = False 
            self.is_a_mapping                   = True
            self.kind_mapped_from               = 'big-rock'

            interval_spec_milestones   = GreedyIntervalSpec( parent_trace = None, entity_name = ME._ENTITY_NAME) 

            self.interval_spec                  = interval_spec_milestones

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
            ME                              = MilestonesController._MilestonesConfig
            posted_cols                     = list(posted_content_df.columns)
            mandatory_cols                  = [ME._ENTITY_NAME]
            #mandatory_cols.extend(ME._SPLITTING_COLUMNS)
            #missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]

            missing_cols                    = [col for col in mandatory_cols 
                                                if not StringUtils().is_in_as_yaml(col, posted_cols)]
        
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns. This often happens if "
                                                    + "ranges are wrong in Posting Label.",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})

        def entity_name(self):
            ME                      = MilestonesController._MilestonesConfig
            return ME._ENTITY_NAME

        def entity_as_yaml_fieldname(self):
            ME                          = MilestonesController._MilestonesConfig
            return StringUtils().format_as_yaml_fieldname(ME._ENTITY_NAME)

    class _MyPostingLabel(JourneysPostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting modernization milestones. 
        '''

        def __init__(self, parent_trace, controller):
            # Shortcut to reference class static variables
            ME = MilestonesController._MyPostingLabel

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,

                                mandatory_fields    = [],
                                date_fields         = [])

        def read(self, parent_trace, posting_label_handle):
            '''
            '''
            super().read(parent_trace, posting_label_handle)

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
            super().checkReferentialIntegrity(parent_trace)

            # In addition to checks made by the parent class, we want to check that references to read-only manifests
            # are correct. Specifically, we want to make sure that milestones manifest references the most recent version
            # of the big-rocks manifest, before we accept the submitted Excel for the milestones manifest.
            #
            # So we check that the version of the big-rocks in the Posting Label is indeed the most recent version of the
            # big-rocks.
            my_trace                        = parent_trace.doing("Checking milestones reference most recent big-rocks")
            ME                              = MilestonesController
            manifest_api_name               = self.controller.getManifestAPI().apiName()
            organization                    = self.organization(my_trace)
            kb_area                         = self.knowledgeBaseArea(my_trace)
            FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
            namespace                       = FMT(organization + '.' + kb_area)
            manifest_name                   = self.controller.manifestNameFromLabel(my_trace, label=self)

            manifest_dict, manifest_path    = self.controller.store.findLatestVersionManifest( 
                                                                        parent_trace        = my_trace, 
                                                                        manifest_api_name   = manifest_api_name,
                                                                        namespace           = namespace, 
                                                                        name                = manifest_name, 
                                                                        kind                = ME.REFERENCED_KIND)

            BIG_ROCKS_MANIFEST_NB           = 0
            referenced_manifest_nb          = BIG_ROCKS_MANIFEST_NB
            last_version_nb                 = ManifestUtils().get_manifest_version(my_trace, manifest_dict)

            submitted_version_nb            = self.priorVersion(my_trace, referenced_manifest_nb)

            if submitted_version_nb < last_version_nb:
                raise ApodeixiError(my_trace, "Excel form needs to be refreshed and re-submitted because it does not reference "
                                    + "the most recent version of the '" + ME.REFERENCED_KIND + "'. Request a new form "
                                    + "for '" + ME.MY_KIND + "' to reflect the correct version for '" 
                                    + ME.REFERENCED_KIND + "' and re-apply your changes to that form, and re-submit",
                                    data = {"version submitted": str(submitted_version_nb),
                                            "latest version":   str(last_version_nb)})
            if submitted_version_nb > last_version_nb:
                raise ApodeixiError(my_trace, "Excel form needs to be refreshed and re-submitted because it references "
                                    + "a non-existent version of the '" + ME.REFERENCED_KIND + "'. Request a new form "
                                    + "for '" + ME.MY_KIND + "' to reflect the correct version for '" 
                                    + ME.REFERENCED_KIND + "' and re-apply your changes to that form, and re-submit",
                                    data = {"version submitted": str(submitted_version_nb),
                                            "latest version":   str(last_version_nb)})

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
            editable_fields     = super().infer(parent_trace, manifest_dict, manifest_key)

            return editable_fields







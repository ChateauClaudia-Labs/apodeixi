import pandas                                                   as _pd
from apodeixi.util.a6i_error                                    import ApodeixiError

from apodeixi.controllers.util.skeleton_controller              import SkeletonController
from apodeixi.controllers.admin.static_data.static_data         import StaticData_Controller

from apodeixi.text_layout.excel_layout                          import AsExcel_Config_Table, ManifestXLWriteConfig

from apodeixi.xli.posting_controller_utils                      import UpdatePolicy
from apodeixi.xli.interval                                      import ClosedOpenIntervalSpec

class ScoringCyclesController(StaticData_Controller):
    '''
    Class to process an Excel posting for the scoring cycle static data objec. It produces one YAML manifest:
    
    * scoring-cycle

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)

        self.SUPPORTED_VERSIONS         = ['v1a']
        self.SUPPORTED_KINDS            = ['scoring-cycle']

        self.POSTING_API                = 'scoring-cycle.static-data.admin.a6i'

    def getSupportedVersions(self):
        return self.SUPPORTED_VERSIONS 

    def getSupportedKinds(self):
        return self.SUPPORTED_KINDS

    def getPostingAPI(self):
        '''
        Implemented by concrete classes.
        Must return a string corresponding to the posting API supported by this controller.
        '''
        return self.POSTING_API

    def getPostingConfig(self, parent_trace, kind, manifest_nb):
        '''
        Return a PostingConfig, corresponding to the configuration that this concrete controller supports.
        '''
        ME                              = ScoringCyclesController
        if kind in self.SUPPORTED_KINDS:
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = ME._ScoringCycleConfig(   kind            = kind, 
                                                                    update_policy   = update_policy,
                                                                    manifest_nb     = manifest_nb, 
                                                                    controller      = self)
        else:
            raise ApodeixiError(parent_trace, "Invalid domain object '" + kind + "' - should be one of "
                                                + ", ".join(self.SUPPORTED_KINDS),
                                                origination = {'signaled_from': __file__})

        return xlr_config 

    def _buildAllManifests(self, parent_trace, posting_label_handle):

        all_manifests_dict, label              = super()._buildAllManifests(parent_trace, posting_label_handle)

        return all_manifests_dict, label

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

        # Discard whatever the parent class did for the templated content. Here we decide how we want it to look

        if kind == "scoring-cycle":
            a_list                          = ["Modernization"]
            a_list.extend([""] * 4)
            a_list.append('Migration')
            a_list.extend([""] * 5)
            
            b_list                          = ["FY 20"]
            b_list.extend([""] * 2)
            b_list.append('FY 21')
            b_list.append('FY 22')
            b_list.append('FY 21')
            b_list.extend([""] * 5)



            c_list                         = ["Official"]
            c_list.append("New investment")
            c_list.append("Retail focus")
            c_list.append("Official")
            c_list.append("Official")
            c_list.append("Official")
            c_list.extend([""] * 5)

            d_list                         = ["Execution of plan approved by CEO on April 19, 2019"]
            d_list.append("What-if scenario assuming $10m of new investment")
            d_list.append("What-if scenario if all modernization headcount is moved to retail from other BUs, "
                                + "whose modernization is stopped")
            d_list.append("Execution on plan approved by Transformation Office on June 14, 2020")
            d_list.append("Plan approved by BoD on May 25, 2021")
            d_list.append("Migration of 100 Infinity clients to FusionOpus")
            d_list.extend([""] * 5)

            template_df                     = _pd.DataFrame({   "Journey":          a_list,
                                                                "Scoring Cycle":    b_list,
                                                                "Scenario":         c_list,
                                                                "Description":      d_list})
        else:
            raise ApodeixiError(parent_trace, "Invalid kind was provided: '" + str(kind) + "'",
                                                origination = { 'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})

        return template_dict, template_df

    def _build_manifestsXLWriteconfig(self, parent_trace, manifestInfo_dict):
        '''
        Overwrites parent's implementation

        Creates and returns an AsExcel_Config_Table containing the configuration data for how to lay out and format
        all the manifests of `manifestInfo_dict` onto an Excel spreadsheet
        '''
        xlw_config_table                    = AsExcel_Config_Table()
        x_offset                            = 1
        y_offset                            = 1
        for key in manifestInfo_dict:
            loop_trace                      = parent_trace.doing("Creating layout configurations for manifest '"
                                                                + str(key) + "'")
            manifest_info                   = manifestInfo_dict[key]
            data_df                         = manifest_info.getManifestContents(parent_trace)
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            if key == 'scoring-cycle.0':
                hidden_cols                 = []
                right_margin                = 0
                num_formats                 = {}
                excel_formulas              = None
                df_xy_2_excel_xy_mapper   = None
            else:
                raise ApodeixiError(loop_trace, "Invalid manifest key: '" + str(key) + "'")
            xlw_config  = ManifestXLWriteConfig(sheet                       = SkeletonController.GENERATED_FORM_WORKSHEET,
                                                manifest_name               = key,
                                                read_only                   = False,
                                                is_transposed               = False,     
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
            
            x_offset                        += data_df.shape[1] -len(hidden_cols) + right_margin
            xlw_config_table.addManifestXLWriteConfig(loop_trace, xlw_config)
        return xlw_config_table

    class _ScoringCycleConfig(StaticData_Controller._StaticDataConfig):
        '''
        Codifies the schema and integrity expectations for scoring cycle static datasets.
        '''
        def __init__(self, kind, manifest_nb, update_policy, controller):
            ME                          = StaticData_Controller._StaticDataConfig
            super().__init__(   kind                = kind, 
                                update_policy       = update_policy, 
                                manifest_nb         = manifest_nb,
                                controller          = controller)
        
            interval_spec    = ClosedOpenIntervalSpec(  parent_trace        = None, 
                                                        splitting_columns   = ['Scoring Cycle', 'Scenario'],
                                                        entity_name         = kind) 

            self.interval_spec  = interval_spec
            self._entity_name    = 'Journey'

        def entity_name(self):
            return self._entity_name











import pandas                                                   as _pd
from apodeixi.util.a6i_error                                    import ApodeixiError

from apodeixi.controllers.util.skeleton_controller              import SkeletonController
from apodeixi.controllers.admin.static_data.static_data         import StaticData_Controller

from apodeixi.text_layout.excel_layout                          import AsExcel_Config_Table, ManifestXLConfig


class ProductsController(StaticData_Controller):
    '''
    Class to process an Excel posting for the products static data objec. It produces two YAML manifest:
    
    * products
    * line-of-business

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)

        self.SUPPORTED_VERSIONS         = ['v1a']
        self.SUPPORTED_KINDS            = ['product', 'line-of-business']

        self.POSTING_API                = 'products.static-data.admin.a6i'

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
        list_of_blanks                   = [""] *15
        if kind == "product":
            p_list                          = ["MYPROD"]
            p_list.extend(list_of_blanks)
            an_list                         = ["My Product, My product, myprod"]
            an_list.extend(list_of_blanks)
            template_df                     = _pd.DataFrame({   "Product":      p_list,
                                                                "Alias names":  an_list})
        elif kind == "line-of-business":
            lob_list                        = ["My business unit"]
            lob_list.extend(list_of_blanks)
            template_df                     = _pd.DataFrame({   "LOB":          lob_list})
        else:
            raise ApodeixiError(parent_trace, "Invalid kind was provided: '" + str(kind) + "'",
                                                origination = { 'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})

        return template_dict, template_df

    def _build_manifestsXLconfig(self, parent_trace, manifestInfo_dict):
        '''
        Overwrites parent's implementation

        Creates and returns an AsExcel_Config_Table containing the configuration data for how to lay out and format
        all the manifests of `manifestInfo_dict` onto an Excel spreadsheet
        '''
        config_table                        = AsExcel_Config_Table()
        #x_offset                            = 1
        y_offset                            = 1
        for key in manifestInfo_dict:
            loop_trace                      = parent_trace.doing("Creating layout configurations for manifest '"
                                                                + str(key) + "'")
            manifest_info                   = manifestInfo_dict[key]
            data_df                         = manifest_info.getManifestContents(parent_trace)
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            if key == 'product.1':
                x_offset                    = 2 # Start 2 columns over so that line of business can go to the left
                hidden_cols                 = []
                right_margin                = 0
                num_formats                 = {}
                excel_formulas              = None
                df_row_2_excel_row_mapper   = None
            elif key == 'line-of-business.2':
                x_offset                    = 1 # Lay LOB column to the left of product
                hidden_cols                 = []
                right_margin                = 0
                num_formats                 = {}
                excel_formulas              = None
                df_row_2_excel_row_mapper   = None
            else:
                raise ApodeixiError(loop_trace, "Invalid manifest key: '" + str(key) + "'")
            config      = ManifestXLConfig( sheet                       = SkeletonController.GENERATED_FORM_WORKSHEET,
                                            manifest_name               = key,    
                                            viewport_width              = 100,  
                                            viewport_height             = 40,   
                                            max_word_length             = 20, 
                                            editable_cols               = editable_cols,
                                            hidden_cols                 = hidden_cols,  
                                            num_formats                 = num_formats, 
                                            excel_formulas              = excel_formulas,
                                            df_row_2_excel_row_mapper   = df_row_2_excel_row_mapper,
                                            editable_headers            = [],   
                                            x_offset                    = x_offset,    
                                            y_offset                    = y_offset)
            # Put next manifest to the right of this one, separated by an empty column
            x_offset                        += data_df.shape[1] -len(hidden_cols) + right_margin
            config_table.addManifestXLConfig(loop_trace, config)
        return config_table















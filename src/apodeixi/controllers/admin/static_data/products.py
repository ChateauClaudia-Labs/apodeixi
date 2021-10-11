import pandas                                                   as _pd

from apodeixi.controllers.util.skeleton_controller              import SkeletonController
from apodeixi.controllers.admin.static_data.static_data         import StaticData_Controller

from apodeixi.knowledge_base.manifest_utils                     import ManifestUtils

from apodeixi.util.a6i_error                                    import ApodeixiError
from apodeixi.util.formatting_utils                             import StringUtils

from apodeixi.text_layout.excel_layout                          import AsExcel_Config_Table, ManifestXLWriteConfig
from apodeixi.xli.posting_controller_utils                      import UpdatePolicy
from apodeixi.xli.interval                                      import ClosedOpenIntervalSpec, Interval


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

    PRODUCT_COL                 = 'product'
    ALIAS_COL                   = 'Alias names'
    SUB_PRODUCT_COL             = 'Sub Product'
    SUB_PRODUCT_ALIAS_COL       = 'Sub product aliases'

    MULTIPLE_JOURNEYS           = "Multiple"

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
        ME                              = ProductsController
        if kind == 'product':
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = ME._ProductConfig(    kind            = kind, 
                                                                update_policy   = update_policy,
                                                                manifest_nb     = manifest_nb, 
                                                                controller      = self)
        elif kind == 'line-of-business':
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            xlr_config                  = StaticData_Controller._StaticDataConfig(  kind            = kind, 
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

        # Link product entities of products manifest to the line of business they correspond to
        bre_manifest_nb                 = self.manifest_nb_from_kind(parent_trace, 'product')
        bre_manifest_dict               = all_manifests_dict[bre_manifest_nb]
        self.linkReferenceManifest(parent_trace, bre_manifest_dict,     entity      = 'product', 
                                                                        linkField   = 'lineOfBusiness', 
                                                                        refKind     = 'line-of-business',
                                                                        many_to_one = True)
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

        ME                              = ProductsController
        # Discard whatever the parent class did for the templated content. Here we decide how we want it to look
        if kind == "product":
            columns                     = [ME.PRODUCT_COL,  ME.ALIAS_COL,                               
                                                                ME.SUB_PRODUCT_COL,     ME.SUB_PRODUCT_ALIAS_COL]

            data                        = [
                ["MYPROD_A",    "My Product A, My product A, myprod A",     "Prod A Enterprise",    "Prod A enterprise, A enterprise"],
                ["",            "",                                         "Prod A Express",       "Prod A express, A express"],
                ["",            "",                                         "", ""],
                ["",            "",                                         "", ""],
                ["",            "",                                         "", ""],
                ["",            "",                                         "", ""],
                ["",            "",                                         "", ""],
                ["MYPROD_B",    "My Product B, My product B, myprod B",     "", ""],
                ["MYPROD_C",    "My Product C, My product C, myprod C",     "Prod C Premium",       ""],
                ["",            "",                                         "Prod C Basic",         ""],
                ["",            "",                                         "", ""],
                ["",            "",                                         "", ""],
                ["",            "",                                         "", ""],
                ["",            "",                                         "", ""],
                ["",            "",                                         "", ""],
            ]

            template_df                     = _pd.DataFrame(columns=columns, data=data)

        elif kind == "line-of-business":
            list_of_blanks                  = [""] *6
            lob_list                        = ["My business unit"]
            lob_list.extend(list_of_blanks)
            lob_list.append("The other business unit")
            lob_list.append("")
            lob_list.extend(list_of_blanks)
            template_df                     = _pd.DataFrame({   "Line of Business":          lob_list})
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
        #x_offset                            = 3 
        y_offset                            = 1

        # Products need to be grouped by line of business, and then displayed in that order. So we do a bit
        # of pandas manipulation for that
        products_df                         = manifestInfo_dict['product.0'].getManifestContents(parent_trace)
        if "lineOfBusiness" in products_df.columns:
            # In this case, products have already been mapped to LOBs, so we will need to display products
            # grouped by LOB. First step: sort products by LOB so that they are grouped by LOB, and make
            # this the order how we display them (see below the definition of my_prod_mapper lambda, that uses
            # this sorted DataFrame)
            sorted_products_df          = ManifestUtils().sort_manifest_df_by_foreign_uid(
                                                                        parent_trace        = parent_trace, 
                                                                        manifest_df         = products_df, 
                                                                        foreign_uid_column  = "lineOfBusiness")
            ORIGINAL_INDEX_COL          = "index"     
            # Pad a UID top-level column, so that it is never blank, since that is how we will map rows
            # Reason UID might be blank is that a product may have sub-products, so product_df['UID'] would be blank
            # for the sub-product rows, since they "inherit" the UID from a prior row.
            sorted_products_df          = ManifestUtils().pad_manifest_dataframe(   parent_trace        = parent_trace, 
                                                                                    manifest_df         = sorted_products_df, 
                                                                                    padding_column      = Interval.UID)
                     
        else:
            # In this case, we must be displaying a template, so mapping isn't established yet. So
            # display in the same order
            sorted_products_df              = products_df

        for key in manifestInfo_dict:
            loop_trace                      = parent_trace.doing("Creating layout configurations for manifest '"
                                                                + str(key) + "'")
            manifest_info                   = manifestInfo_dict[key]
            data_df                         = manifest_info.getManifestContents(parent_trace)
            editable_cols = [col for col in data_df.columns if not col.startswith('UID')]
            if key == 'product.0':
                x_offset                    = 3 # Start 3 columns over so that line of business can go to the left
                hidden_cols                 = ["lineOfBusiness"]
                right_margin                = 0
                num_formats                 = {}
                excel_formulas              = None

                def my_prod_mapper(manifest_df, manifest_df_row_number, representer):
                    if not "UID" in manifest_df.columns:
                        # Implement vanilla behavior - no UID means this must be a template
                        excel_row           = y_offset + 1 + manifest_df_row_number # An extra '1' because of the headers
                        final_excel_row     = y_offset + len(manifest_df.index) # Don't do len(index)-1 since headers add a row
                        return excel_row, final_excel_row
                    else:
                        # This is the tricky case: we must not display products in the order the are listed in the manifest,
                        # but in an order that segments them into groups based on line-of-business, i.e.,
                        # in the order in which they appear in sorted_products_df
                        # So algorithm is:
                        #   1. Get the UID of the product for this manifest_df_row_number
                        #   2. Find the idx in sorted_products_df where that product UID appears
                        #   3. Drive the excel row number from that idx
                        if len(manifest_df.index) != len(sorted_products_df.index):
                            raise ApodeixiError(loop_trace, "Misalignment problem: two supposedly equivalent DataFrames "
                                                                + "(up to sorting) have different number of rows",
                                                                data = {"Number of rows": str(manifest_df.index) +
                                                                            " vs " + str(sorted_products_df.index)})

                        # Pad a UID top-level column, so that it is never blank, since that is how we will map rows
                        # Reason UID might be blank is that a product may have sub-products, so manifest_df['UID'] would be blank
                        # for the sub-product rows, since they "inherit" the UID from a prior row.
                        '''
                        padded_manifest_df  = ManifestUtils().pad_manifest_dataframe(   
                                                                                    parent_trace        = loop_trace, 
                                                                                    manifest_df         = manifest_df, 
                                                                                    padding_column      = Interval.UID)
                        PADDED_UID_COL      = Interval.UID + "_PADDED"

                        prod_uid            = padded_manifest_df[PADDED_UID_COL].iloc[manifest_df_row_number] 
                        sorted_idx_list     = sorted_products_df.index[sorted_products_df[Interval.UID] == prod_uid].tolist()
                        '''
                        sorted_idx_list     = sorted_products_df.index[sorted_products_df[ORIGINAL_INDEX_COL] == manifest_df_row_number].tolist()

                        if len(sorted_idx_list) != 1:
                            raise ApodeixiError(loop_trace, "Misalignment problem: not a unique entry in product manifest for "
                                                                + "a given UID",
                                                                data = {"manifest": key, 
                                                                        "manifest_df_row_number": str(manifest_df_row_number),
                                                                        "number of entries": str(len(sorted_idx_list))})
                        sorted_idx          = sorted_idx_list[0]
                        excel_row           = y_offset + 1 + sorted_idx # An extra '1' because of the headers
                        final_excel_row     = y_offset + len(manifest_df.index) # Don't do len(index)-1 since headers add a row
                        return excel_row, final_excel_row

                df_xy_2_excel_xy_mapper   = my_prod_mapper
            elif key == 'line-of-business.1':
                x_offset                    = 1 # Lay LOB column to the left of product
                hidden_cols                 = []
                right_margin                = 0
                num_formats                 = {}
                excel_formulas              = None

                def my_lob_mapper(manifest_df, manifest_df_row_number, representer):
                    if not "UID" in manifest_df.columns:
                        # Implement vanilla behavior - no UID means this must be a template
                        excel_row           = y_offset + 1 + manifest_df_row_number # An extra '1' because of the headers
                        final_excel_row     = y_offset + len(manifest_df.index) # Don't do len(index)-1 since headers add a row
                        return excel_row, final_excel_row
                    else:
                        # This is the tricky case: we must not display products in the order the are listed in the manifest,
                        # but in an order that segments them into groups based on line-of-business, i.e.,
                        # in the order in which they appear in sorted_products_df
                        # So algorithm is:
                        #   1. Get the UID of the product for this manifest_df_row_number
                        #   2. Find the idx in sorted_products_df where that product UID appears
                        #   3. Drive the excel row number from that idx
                        lob_uid             = manifest_df['UID'].iloc[manifest_df_row_number] 
                        sorted_idx_list     = sorted_products_df.index[sorted_products_df['lineOfBusiness'] == lob_uid].tolist()

                        if len(sorted_idx_list) == 0:
                            raise ApodeixiError(loop_trace, "Misalignment problem: an LOB is not associated to any product",
                                                                data = {"manifest": key, "LOB UID": str(lob_uid)})
                        # Display the LOB on the first product that is associated with it
                        sorted_idx          = sorted_idx_list[0]
                        excel_row           = y_offset + 1 + sorted_idx # An extra '1' because of the headers
                        final_excel_row     = y_offset + len(sorted_products_df.index) # Don't do len(index)-1 since headers add a row
                        return excel_row, final_excel_row

                df_xy_2_excel_xy_mapper     = my_lob_mapper
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
            
            #x_offset                        += data_df.shape[1] -len(hidden_cols) + right_margin
            xlw_config_table.addManifestXLWriteConfig(loop_trace, xlw_config)
        return xlw_config_table



    class _ProductConfig(StaticData_Controller._StaticDataConfig):
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
                                                        splitting_columns   = ['Sub Product'],
                                                        entity_name         = kind,
                                                        may_ignore_tail     = True) 

            self.interval_spec  = interval_spec
            self._entity_name    = 'product'

        def entity_name(self):
            return self._entity_name











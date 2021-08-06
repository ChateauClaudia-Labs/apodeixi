import os                                               as _os

from apodeixi.controllers.admin.static_data.products    import ProductsController
from apodeixi.representers.as_dataframe                 import AsDataframe_Representer

from apodeixi.util.a6i_error                            import ApodeixiError
from apodeixi.util.dictionary_utils                     import DictionaryUtils
from apodeixi.util.formatting_utils                     import StringUtils

class StaticDataValidator():
    '''
    Utility class that provides services to validate static data. 
    A typical use case for leveraging these services is when validating referential integrity.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        self.store              = store
        self.a6i_config         = a6i_config

    def validateProduct(self, parent_trace, label, namespace):
        '''
        Validates the the product in the label is for a product static data that is known to exist in the 
        KnowledgeBase store for the given namespace.

        @param label    An object inheriting from PostingLabel with property called "product"

        '''
        try:
            my_trace                = parent_trace.doing("Checking product referential integrity")
            if True:
                alleged_product     = label.product(my_trace)

                prod_code           = self.getProductCode(my_trace, namespace, alleged_product)
                if prod_code == None:
                    all_product_codes   = self.allProductCodes(my_trace, namespace)
                    raise ApodeixiError(my_trace, "Invalid product field in Posting Label",
                                    data = {    "Expected one of":  str(all_product_codes),
                                                "Submitted":        str(alleged_product)})
        except ApodeixiError as ex:
            raise ex
        except Exception as ex:
            raise ApodeixiError("Found a problem while validating referential integrity for product field",
                                data = {    "alleged product":  alleged_product, 
                                            "error":             str(ex)})
    
    def getProductCode(self, parent_trace, namespace, alleged_product):
        '''
        Checks if `alleged_product` is a valid product in the given `namespace`, i.e., if the products manifest for
        the namespaces includes the alleged_product, either as the name of an official product mame or as an alias
        for an official product.

        If the check passes, it returns the official product name corresponding to the alleged_product. Otherwise,
        it returns None.

        @param namespace A string. Corresponds to a namespace in the manifest's section of the KnowledgeBase store.
                            For example, "my-corp.production"

        @param allged_product A string that is claimed represents the name of a product or an known alias for a
                            valid product.
        '''
        PRODUCT_COL                 = 'product'
        ALIAS_COL                   = 'Alias names'

        my_trace                    = parent_trace.doing("Retrieving product static data")
        contents_df                 = self._loadProducts(my_trace, namespace)

        my_trace                    = parent_trace.doing("Checking if '" + str(alleged_product) 
                                                            + "' appears in product static data")
        for row in contents_df.iterrows():
            prod_code               = row[1][PRODUCT_COL]
            alias_list              = row[1][ALIAS_COL]
            if alleged_product == prod_code or alleged_product in alias_list:
                return prod_code

        # If we get this far, then we didn't find it, so return None
        return None

    def allProductCodes(self, parent_trace, namespace):
        '''
        Returns a list of all official product codes for the given namespace.

        @param namespace A string. Corresponds to a namespace in the manifest's section of the KnowledgeBase store.
                            For example, "my-corp.production"
        '''
        PRODUCT_COL                 = 'product'

        my_trace                    = parent_trace.doing("Retrieving product static data")
        contents_df                 = self._loadProducts(my_trace, namespace)
        all_product_codes           = list(contents_df[PRODUCT_COL])
        return all_product_codes

    def _loadProducts(self, parent_trace, namespace):
        '''
        Helper method. Returns a DataFrame of the latest version of the products static data manifest.
        '''
        prod_ctrl           = ProductsController(parent_trace, self.store, self.a6i_config)
        PROD_API            = 'static-data.admin.a6i.io' 

        PRODUCT_COL         = 'product'
        ALIAS_COL           = 'Alias names'

        prod_manifest_dict, prod_manifest_path  = self.store.findLatestVersionManifest(
                                                                        parent_trace    = parent_trace, 
                                                                        manifest_api    = PROD_API, 
                                                                        namespace       = namespace, 
                                                                        name            = 'static-data', 
                                                                        kind            = 'product')

        if prod_manifest_dict == None:
            raise ApodeixiError(parent_trace, "Product static data is not configured for namespace '" + str(namespace) + "'")
        rep                             = AsDataframe_Representer()
        contents_path                   = 'assertion.' + 'product'
        filename                        = _os.path.split(prod_manifest_path)[1]
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = parent_trace, 
                                                                root_dict       = prod_manifest_dict, 
                                                                root_dict_name  = filename,
                                                                path_list       = ['assertion', 'product'],
                                                                valid_types     = [dict])

        if check == False:
            raise ApodeixiError(parent_trace, "Manifest is corrupted: ['assertion']['product'] is not a dict",
                                                data        = { "manifest path":    prod_manifest_path},
                                                origination = { 'concrete class':   str(self.__class__.__name__), 
                                                                'signaled_from':    __file__})

        content_dict                    = prod_manifest_dict['assertion']['product']
        contents_df                     = rep.dict_2_df(parent_trace, content_dict, contents_path)

        return contents_df
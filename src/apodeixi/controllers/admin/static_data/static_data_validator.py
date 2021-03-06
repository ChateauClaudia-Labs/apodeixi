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
        Validates that the product in the label is for a product static data that is known to exist in the 
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
            raise ApodeixiError(parent_trace, "Found a problem while validating referential integrity for product field",
                                data = {    "alleged product":  alleged_product, 
                                            "error":             str(ex)})

    def validateScoringCycle(self, parent_trace, label, namespace):
        '''
        Validates that the scoringCycle and related data (the journey and the scenario)
        in the label are for static data that is known to exist in the 
        KnowledgeBase store for the given namespace.

        @param label    An object inheriting from PostingLabel with properties called 'journey',
                        'Scoring Cycle', and 'Scenario'

        '''
        JOURNEY_COL                         = 'journey'
        SCORING_CYCLE_COL                   = 'Scoring Cycle'
        SCENARIO_COL                        = 'Scenario'
        submitted                           = None
        try:
            my_trace                        = parent_trace.doing("Checking scoring cycle referential integrity")
            if True:
                alleged_journey, subproduct = self._split_subnamespace(my_trace, label, namespace)
                alleged_scoring_cycle       = label.scoring_cycle(my_trace)
                alleged_scenario            = label.scenario(my_trace)

                submitted                   = [alleged_journey, alleged_scoring_cycle, alleged_scenario]

                contents_df                 = self._loadStaticData( my_trace, 
                                                                    namespace, 
                                                                    kind            = 'scoring-cycle', 
                                                                    entity          = 'journey')


                valid_options               = []

                for row in contents_df.iterrows():
                    journey                 = row[1][JOURNEY_COL]
                    scoring_cycle           = row[1][SCORING_CYCLE_COL]
                    scenario                = row[1][SCENARIO_COL]

                    EQ                      = StringUtils().equal_as_yaml

                    if EQ(alleged_journey, journey) and EQ(alleged_scoring_cycle, scoring_cycle) \
                                                    and EQ(alleged_scenario, scenario):
                        # Good, we have a match so that Posting Label is referencing things that exist.
                        # So just return, validation is a success
                        return
                    elif EQ(alleged_journey, ProductsController.MULTIPLE_JOURNEYS) and EQ(alleged_scoring_cycle, scoring_cycle) \
                                                    and EQ(alleged_scenario, scenario):
                        # This is also a "match", in the sense that sometimes (e.g., for products with subproducts)
                        # there might be different journeys for different subproducts, say, and Apodeixi
                        # semantics are that the user should enter "Multiple" as the journey. So this is
                        # also considered vaid
                        return
                    # Remember this in case we need to error out and provide this feedback to the user
                    valid_options.append([journey, scoring_cycle, scenario])
                    valid_options.append([ProductsController.MULTIPLE_JOURNEYS, scoring_cycle, scenario])

                # If we get this far then there has been no match. 
                raise ApodeixiError(my_trace, "Invalid combination of [journey, scoring cycle, scenario] in Posting Label",
                                    data = {    "Expected one of":  str(valid_options),
                                                "Submitted":        str(submitted)})
        except ApodeixiError as ex:
            raise ex
        except Exception as ex:
            if submitted == None:
                submitted = "<Couldn't figure this out>"
            raise ApodeixiError(parent_trace, "Found a problem while validating referential integrity for "
                                + " [journey, scoring cycle, scenario] in Posting Label",
                                data = {    "in posting label": submitted, 
                                            "error":            str(ex)})

    def _split_subnamespace(self, parent_trace, label, namespace):
        '''
        Helper method to self.validateScoringCycle. It determines whether the subnamespace provided by the user in the
        posting request (i.e., label.journey) is really a journey like "Cloud" or, in situations where subproducts
        exist, a composite like "Cloud.PTG", which would indicate that it is the "Cloud" journey for the
        subproduct "PTG".

        Returns two strings: the journey the subproduct, if it exists.

        Example 1: if label.journey is "Cloud.PTG", then it returns ("Cloud", "PTG")

        Example 2: if label.journey is "Cloud" then it returns ("Cloud", None)

        It does some validation: in the case of composite subnamespaces like "Cloud.PTG", then it 
        validates that "PTG" is a real subproduct of label.product (which should be something like "GPP")
        '''
        subnamespace                = label.journey(parent_trace)
        tokens                      = subnamespace.split(".")
        if len(tokens) == 1:
            alleged_journey         = tokens[0]
            subproduct      = None
        elif len(tokens) == 2:
            alleged_journey         = tokens[0]
            subproduct              = tokens[1]
        else:
            raise ApodeixiError(parent_trace, "'" + str(subnamespace) +"' is invalid subnamespace. "
                                "Should have at most token separated by '.', like 'Cloud' or 'Cloud.PTG'")
        if subproduct != None:
            # Check it is a valid subproduct
            alleged_product         = label.product(parent_trace)
            valid_subproducts       = self.getSubProducts(parent_trace, namespace, alleged_product)
            if not StringUtils().is_in_as_yaml(subproduct, valid_subproducts):
                raise ApodeixiError(parent_trace, "'" + str(subproduct) + " is not a valid subproduct for '"
                                    + str(alleged_product) + "'",
                                    data = {"valid subproducts":    str(valid_subproducts)})

        # If we get this far then the subproduct (if it exists) seems legit, so return
        return alleged_journey, subproduct

    def getScoringCycles(self, parent_trace, namespace):
        '''
        Gets a list of all scoring cycles in the namespace, as a DataFrames
        '''
        my_trace                    = parent_trace.doing("Checking scoring cycle referential integrity")
        contents_df                 = self._loadStaticData( my_trace, 
                                                            namespace, 
                                                            kind            = 'scoring-cycle', 
                                                            entity          = 'journey')
        return contents_df
  
    
    def getProductCode(self, parent_trace, namespace, alleged_product):
        '''
        Checks if `alleged_product` is a valid product in the given `namespace`, i.e., if the products manifest for
        the namespaces includes the alleged_product, either as the name of an official product mame or as an alias
        for an official product.

        If the check passes, it returns the official product name corresponding to the alleged_product. Otherwise,
        it returns None.

        @param namespace A string. Corresponds to a namespace in the manifest's section of the KnowledgeBase store.
                            For example, "my-corp.production"

        @param alleged_product A string that is claimed represents the name of a product or an known alias for a
                            valid product.
        '''
        my_trace                    = parent_trace.doing("Retrieving product static data")
        contents_df                 = self._loadStaticData(my_trace, namespace, kind='product', entity='product') 

        my_trace                    = parent_trace.doing("Checking if '" + str(alleged_product) 
                                                            + "' appears in product static data")
        for row in contents_df.iterrows():
            prod_code               = row[1][ProductsController.PRODUCT_COL].strip()
            alias_list              = [alias.strip() for alias in row[1][ProductsController.ALIAS_COL].split(",")]
            if alleged_product == prod_code or alleged_product in alias_list:
                return prod_code

        # If we get this far, then we didn't find it, so return None
        return None

    def getSubProducts(self, parent_trace, namespace, alleged_product):
        '''
        Returns a list, consisting of the sub products for the given product, if any.
        If none exists then it returns an empty list.

        If the `alleged_product` is not a valid product (or at least an alias for a valid product), it raises an ApodeixiError

        @param namespace A string. Corresponds to a namespace in the manifest's section of the KnowledgeBase store.
                            For example, "my-corp.production"

        @param alleged_product A string that is claimed represents the name of a product or an known alias for a
                            valid product.
        '''
        PRODUCT_COL                 = 'product'
        SUB_PRODUCT_COL             = 'Sub Product'

        ALIAS_COL                   = 'Alias names'

        my_trace                    = parent_trace.doing("Retrieving product static data")
        contents_df                 = self._loadStaticData(my_trace, namespace, kind='product', entity='product') 

        my_trace                    = parent_trace.doing("Checking if '" + str(alleged_product) 
                                                            + "' appears in product static data")
        def _is_a_match(row):
            prod_code               = row[PRODUCT_COL].strip()
            alias_list              = [alias.strip() for alias in row[ALIAS_COL].split(",")]
            if alleged_product == prod_code or alleged_product in alias_list:
                return True
            else:
                return False

        alleged_product_df          = contents_df[contents_df.apply(_is_a_match, axis=1) == True]

        if len(alleged_product_df.index) == 0:
            raise ApodeixiError(my_trace, "'" + str(alleged_product) + "' is not a valid product or alias of a valid product")


        if SUB_PRODUCT_COL in alleged_product_df.columns:
            # Because of the way how content_df is built (with sparse=False in self._loadStaticData), 
            # it probably has a dedicated row for the product and additional
            # rows for each subproduct. In other words, there like is a row (the one for the product) that has a blank
            # subproduct field.
            # So we must not pick up the row where the product lies is the subproduct field is
            # blank - otherwise we would be erroreously returning a spurious "blank" subproduct. Hence the filter we do here
            candidates              = list(alleged_product_df[SUB_PRODUCT_COL].unique())
            real_subproducts        = [prod for prod in candidates if not StringUtils().is_blank(prod)]
            return real_subproducts
        else:
            return []

    def allProductCodes(self, parent_trace, namespace):
        '''
        Returns a list of all official product codes for the given namespace.

        @param namespace A string. Corresponds to a namespace in the manifest's section of the KnowledgeBase store.
                            For example, "my-corp.production"
        '''
        PRODUCT_COL                 = 'product'

        my_trace                    = parent_trace.doing("Retrieving product static data")
        contents_df                 = self._loadStaticData(my_trace, namespace, kind='product', entity='product')
        
        # GOTCHA: due to subproducts, some products may appear in multiple rows in contents_df, so make sure to
        # remove duplicates
        all_product_codes           = list(contents_df[PRODUCT_COL].unique())
        return all_product_codes

    def _loadStaticData(self, parent_trace, namespace, kind, entity):
        '''
        Helper method. Returns a DataFrame of the latest version of the static data manifest for the `kind`

        @param kind A string, representing the `kind` of static data to load
        @param entity A string, representing the field in the manifest under 'assertions' that is the root
                        of the content for the manifest.
        '''
        STATIC_DATA_API     = self.a6i_config.get_static_data_api(parent_trace)

        manifest_dict, manifest_path  = self.store.findLatestVersionManifest(
                                                                        parent_trace        = parent_trace, 
                                                                        manifest_api_name   = STATIC_DATA_API, 
                                                                        namespace           = namespace, 
                                                                        name                = 'static-data', 
                                                                        kind                = kind)

        if manifest_dict == None:
            raise ApodeixiError(parent_trace, "Static data of type '" + str(kind) 
                                                + "' is not configured for namespace '" + str(namespace) + "'")
        rep                             = AsDataframe_Representer()
        contents_path                   = 'assertion.' + str(entity)
        filename                        = _os.path.split(manifest_path)[1]
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = parent_trace, 
                                                                root_dict       = manifest_dict, 
                                                                root_dict_name  = filename,
                                                                path_list       = ['assertion', entity],
                                                                valid_types     = [dict])

        if check == False:
            raise ApodeixiError(parent_trace, "Manifest is corrupted: ['assertion']['" + str(entity) + "'] is not a dict",
                                                data        = { "manifest path":    manifest_path},
                                                origination = { 'concrete class':   str(self.__class__.__name__), 
                                                                'signaled_from':    __file__})

        content_dict                    = manifest_dict['assertion'][str(entity)]
        contents_df, uid_info_list      = rep.dict_2_df(parent_trace, content_dict, contents_path, 
                                                                sparse=False, abbreviate_uids=True)

        return contents_df
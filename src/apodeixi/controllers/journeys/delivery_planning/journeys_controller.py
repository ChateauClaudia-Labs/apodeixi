import itertools                                                            as _itertools

from apodeixi.controllers.util.manifest_api                                 import ManifestAPI
from apodeixi.controllers.journeys.delivery_planning.journeys_posting_label  import JourneysPostingLabel
from apodeixi.controllers.util.skeleton_controller                          import SkeletonController
from apodeixi.controllers.admin.static_data.static_data_validator           import StaticDataValidator

from apodeixi.knowledge_base.filing_coordinates                             import JourneysFilingCoordinates
from apodeixi.knowledge_base.knowledge_base_util                            import FormRequest

from apodeixi.util.a6i_error                                                import ApodeixiError
from apodeixi.util.formatting_utils                                         import StringUtils
from apodeixi.util.dictionary_utils                                         import DictionaryUtils
from apodeixi.util.dataframe_utils                                          import DataFrameUtils

class JourneysController(SkeletonController):
    '''
    Abstrac class to with common properties for posting controllers in the Journey domain.

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        super().__init__(parent_trace, store, a6i_config)

        self.MANIFEST_API = ManifestAPI(    parent_trace    = parent_trace,
                                            subdomain       = 'delivery-planning', 
                                            domain          = 'journeys', 
                                            api_publisher   = 'a6i',
                                            extension       = 'io')

    def getFilingClass(self):
        '''
        Returns a class object, corresponding to the concrete subclass of FilingCoordinates
        that is supported by this controller
        '''
        return JourneysFilingCoordinates
        
    def getManifestAPI(self):
        return self.MANIFEST_API

    def manifestNameFromLabel(self, parent_trace, label, kind):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        label
        @param kind The kind of manifest for which the name is sought. This parameter can be ignored for controller
                    classes that use the same name for all supported kinds; it is meant to support controllers that
                    process multiple manifest kinds and do not use the same name for all of them. For example, controllers
                    that point to reference data in a different domain/sub-domain.
        '''
        product                         = label.product             (parent_trace)
        journey                         = label.journey             (parent_trace) 
        scenario                        = label.scenario            (parent_trace)
        scoring_cycle                   = label.scoring_cycle       (parent_trace)

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(journey + '.' + scoring_cycle + '.' + product + '.' + scenario)
        return name

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
        if not type(coords) == self.getFilingClass():
            raise ApodeixiError(parent_trace, "Can't build manifest name because received wrong type of filing coordinates",
                                                data = {"Type of coords received": str(type(coords)),
                                                        "Expected type of coords": str(self.getFilingClass())})

        if subnamespace == None:
            raise ApodeixiError(parent_trace, "Can't build manifest name becase subnamespace is null. Should be "
                                                + "set to a kind of journey. Example: 'modernization'")

        product                         = coords.product
        journey                         = subnamespace
        scenario                        = coords.scenario
        scoring_cycle                   = coords.scoringCycle

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(journey + '.' + scoring_cycle + '.' + product + '.' + scenario)

        return name

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
        if not type(coords) == self.getFilingClass():
            raise ApodeixiError(parent_trace, "Can't build manifest name because received wrong type of filing coordinates",
                                                data = {"Type of coords received": str(type(coords)),
                                                        "Expected type of coords": str(self.getFilingClass())})

        if subnamespace == None:
            raise ApodeixiError(parent_trace, "Can't build manifest name becase subnamespace is null. Should be "
                                                + "set to a kind of journey. Example: 'modernization'")

        product                                 = coords.product
        journey                                 = subnamespace
        scenario                                = coords.scenario
        scoring_cycle                           = coords.scoringCycle 

        MY_PL                                   = JourneysPostingLabel # Abbreviation for readability
        result_dict                             = {}
        result_dict[MY_PL._PRODUCT]             = product
        result_dict[MY_PL._JOURNEY]             = journey
        result_dict[MY_PL._SCENARIO]            = scenario
        result_dict[MY_PL._SCORING_CYCLE]       = scoring_cycle
        result_dict[MY_PL._SCORING_MATURITY]    = ""

        return result_dict

    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a knowledge base
        structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, posting_data_handle, label)
           
        my_trace                        = parent_trace.doing("Getting PostingLabel fields specific to BigRocksEstimate_Controller") 

        product                         = label.product             (my_trace)
        journey                         = label.journey             (my_trace) 
        scenario                        = label.scenario            (my_trace)
        scoring_cycle                   = label.scoring_cycle       (my_trace)
        scoring_maturity                = label.scoring_maturity    (my_trace)

        
        my_trace                        = parent_trace.doing("Enriching generic manifest fields with additional fields "
                                                                + "specific to BigRocksEstimate_Controller")
        
        if True:
            metadata                                    = manifest_dict['metadata']

            MY_PL                                       = JourneysPostingLabel # Abbreviation for readability
            labels                                      = metadata['labels']
            labels[MY_PL._PRODUCT]                      = product
            labels[MY_PL._JOURNEY]                      = journey
            labels[MY_PL._SCENARIO]                     = scenario
            labels[MY_PL._SCORING_CYCLE]                = scoring_cycle
            labels[MY_PL._SCORING_MATURITY]             = scoring_maturity

            assertion                                   = manifest_dict['assertion']

            assertion[MY_PL._SCENARIO]                  = scenario
            assertion[MY_PL._SCORING_CYCLE]             = scoring_cycle
            assertion[MY_PL._SCORING_MATURITY]          = scoring_maturity
        
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
        template_dict, template_df              = super().createTemplate(parent_trace, form_request, kind)

        MY_PL                                   = JourneysPostingLabel # Abbreviation for readability

        scope                                   = form_request.getScope(parent_trace)
        if type(scope) != FormRequest.SearchScope:
            raise ApodeixiError(parent_trace, "Can't create template for because request form is invalid: it should "
                                    + "have a scope of type FormRequest.SearchScope",
                                    data = {"form_request": form_request.display(parent_trace)})
        
        coords                                  = form_request.getFilingCoords(parent_trace)
        namespace                               = scope.namespace
        subnamespace                            = scope.subnamespace
        mlfc_dict                               = self.manifestLabelsFromCoords(parent_trace, subnamespace, coords)

        labels_dict                             = template_dict['metadata']['labels']

        labels_dict                             = labels_dict | mlfc_dict
        template_dict['metadata']['labels']     = labels_dict

        labels_dict[MY_PL._SCORING_MATURITY]    = ""

        return template_dict, template_df

    def apply_subproducts_to_df(self, parent_trace, template_dict, template_df):
        '''
        Helper method that derived classes may use when creating templates for manifests that should be replicated
        per subproduct.

        This method creates and returns a DataFrame that the caller (a derived class) can use as a template, by 
        replicating `template_df` for each subproduct that exists for the product of `template_dict`.
        It also adds an extra level to the columns of the returned value (i.e., columns are a MultiIndex of tuples)
        where the top level is the subproduct.

        If the product in question has no subproducts, then it just returns `template_df` without changes.
        '''
        subproducts                     = self.get_subproducts(parent_trace, template_dict)
        if subproducts == None:
            return template_df
        else:
            template_per_subproduct_df  = DataFrameUtils().replicate_dataframe( parent_trace, 
                                                                                seed_df         = template_df, 
                                                                                categories_list = subproducts)
            return template_per_subproduct_df

    def apply_subproducts_to_list(self, parent_trace, a_list, subproducts):
        '''
        Creates and returns a list of tuples, based on the given list `a_list`, "duplicating" it (kind of) for each subproduct

        For each element X in `a_list` and each sub-product P in `subproducts`, the returned list has a tuple (P, X)

        If subproducts is None, then it just returns `a_list`

        @param a_list A list, typically of strings
        @param suproducts A list, typically of strings
        '''
        if subproducts == None:
            return a_list
        else:
            result                          = [(x,y) for (x, y) in _itertools.product(*[subproducts, a_list])]
            return result

    def apply_subproducts_to_dict(self, parent_trace, a_dict, subproducts):
        '''
        Creates and returns a dict whose keys are tuples, based on the given dict `a_dict`, "duplicating keys" (kind of)
        for each subproduct

        For each key X in `a_dict` and each sub-product P in `subproducts`, the returned dict R has a key (P, X)
        such that R[(P, X)] = a_dict[X]

        If subproducts is None, then it just returns `a_dict`

        @param a_dict A dict, typically of strings
        @param suproducts A list, typically of strings
        '''
        if subproducts == None:
            return a_dict
        else:
            result                          = {}
            for (x, y) in _itertools.product(*[subproducts, a_dict.keys()]):
                result[(x,y)]               = a_dict[y]

            return result

    def get_foreign_uid(self, parent_trace, foreign_key, manifest_df, manifest_df_row_number, subproducts):
        '''
        Helper function for derived classes to retrieve the UID of a referenced manifest that corresponds
        to a given row number in the referencing manifest `manifest_df`.

        Typical use case: when creating a form that involves aligning row-by-row a referencing manifest's content
        to that of a referenced manifest. For example, aligning big-rock-estimates with big-rocks.

        This method handles the case where subproducts may exist, and if so will ensure that all subproducts
        agree on the referenced UID to use for the given row
        '''
        if subproducts == None:
            # If there are no subproduct, the columns are strings, not tuples
            referenced_uid          = manifest_df[foreign_key].iloc[manifest_df_row_number] 
        else:
            ref_columns             = [(subprod, foreign_key) for subprod in subproducts]
            ref_uid_list            = [manifest_df[col].iloc[manifest_df_row_number] for col in ref_columns]
            # Remove duplites by going to set and back
            br_uid_list             = list(set(ref_uid_list))
            if len(br_uid_list) != 1:
                raise ApodeixiError(parent_trace, "Can't link to " +str(foreign_key) + "' for DataFrame row "
                                                + str(manifest_df_row_number) 
                                                + " because expected exacly 1 foreign UID, and instead found "
                                                + str(len(br_uid_list)),
                                                data = {"Referenced UIDs": str(br_uid_list)})
            referenced_uid          = br_uid_list[0]

        return referenced_uid

    def get_subproducts(self, parent_trace, manifest_dict):
        '''
        Helper method intended to be used by derived classes when dealing with a manifest for a product that has
        subproducts.

        This method returns a list, consisting of the subproducts of the manifest's product.
        '''
        validator                       = StaticDataValidator(parent_trace, self.store, self.a6i_config)
        product                         = DictionaryUtils().get_val(parent_trace, 
                                                                    root_dict       = manifest_dict,
                                                                    root_dict_name  = "Sub Product Scope",
                                                                    path_list       = ["metadata", "labels", "product"],
                                                                    valid_types     = [str])
        namespace                         = DictionaryUtils().get_val(parent_trace, 
                                                                    root_dict       = manifest_dict,
                                                                    root_dict_name  = "Sub Product Scope",
                                                                    path_list       = ["metadata", "namespace"],
                                                                    valid_types     = [str])
        subproducts                     = validator.getSubProducts(parent_trace, namespace, product)
        return subproducts

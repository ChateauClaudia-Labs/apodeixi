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
from apodeixi.util.time_buckets                                             import TimebucketStandardizer, FY_Quarter
from apodeixi.util.rollover_utils                                           import RolloverUtils
from numpy import product

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

        self.using_subproducts          = None # This will be set in self._buildOneManifest
        self.subproducts                = None # This will be set in self._buildOneManifest

    def getFilingClass(self):
        '''
        Returns a class object, corresponding to the concrete subclass of FilingCoordinates
        that is supported by this controller
        '''
        return JourneysFilingCoordinates
        
    def getManifestAPI(self):
        return self.MANIFEST_API

    def subnamespaceFromLabel(self, parent_trace, label):
        '''
        Helper method that returns what the 'subnamespace' that is a portion of a manifest's name.
        It is inferred from a `label` that provides the posting details for a manifest that should be created.

        Returns a string corresponding to the subnamespace, if one applies to this `kind` of manifest.
        If no subnamespace applies, returns None.
        '''
        journey                         = label.journey             (parent_trace) 
        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        return FMT(journey)

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

    def _manifestRolloverNameFromCoords(self, parent_trace, roll_to_name, subnamespace, coords, kind):
        '''
        Helper method used in rollover situations, usually used in the context of generating forms. 
        
        This is when we are switching fiscal years, such as from FY22 to FY23,
        and need the name of the previous fiscal year's manifest consistent with the parameters.
        
        So in this example, while the method `self.manifestNameFromCoords` would return (among other things)
        a FY23 name for the manifest this other method would return the FY22 equivalent.

        This makes it possible that when callers ask for "the most recent manifest to update in FY23", and no such manifests
        exists in FY23, then the get "the last manifest from FY 22" so that their first FY23 update is a continuation of
        the history of changes in FY22.

        More specifically, it returns three strings, which in the example would be:

        * Something like "modernization.fy-22.astrea.official" - the "roll-from name"
        * "FY 22" - the "roll-from scoring cycle"
        * "FY 23" - the "roll-to scoring cycle"

        If rollover functionality is not supported, then a triple of None's is returned. It is up to each concrete controller class
        to determine whether it supports rollover

        Example: consider a manifest name like "modernization.fy-22.fusionopus.default"
                in namespace "my-corp.production". 

                To build such a name, this method must receive "modernization" as the subnamespace, and
                filing coords from which to infer "fy-23" (as opposed to "fy-22", since we are rolling over), 
                "fusionopus", and "default".
        @param roll_to_name A string, with the manifest name we would be rolling to. E.g. "modernization.fy-23.astrea.official"
                when rolling from FY 22 to FY 23

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
            raise ApodeixiError(parent_trace, "Can't build manifest rollover name because received wrong type of filing coordinates",
                                                data = {"Type of coords received": str(type(coords)),
                                                        "Expected type of coords": str(self.getFilingClass())})

        if subnamespace == None:
            raise ApodeixiError(parent_trace, "Can't build manifest rollover name becase subnamespace is null. Should be "
                                                + "set to a kind of journey. Example: 'modernization'")

        product                         = coords.product
        journey                         = subnamespace
        scenario                        = coords.scenario
        scoring_cycle                   = coords.scoringCycle

        # Check if the scoring_cycle is a timebucket
        standardizer                    = TimebucketStandardizer()
        if not standardizer.is_a_timebucket_column(parent_trace, scoring_cycle, self.a6i_config):
            # Rollover functionality is not supported unless scoring_cycle is a timebucket
            return None, None, None
        else:
            month_fiscal_year_starts    = self.a6i_config.getMonthFiscalYearStarts(parent_trace)
            roll_to_timebucket          = FY_Quarter.build_FY_Quarter(parent_trace, str(scoring_cycle), month_fiscal_year_starts)
            roll_from_timebucket        = FY_Quarter(   fiscal_year                 = roll_to_timebucket.fiscal_year-1, 
                                                        quarter                     = roll_to_timebucket.quarter,
                                                        month_fiscal_year_starts    = month_fiscal_year_starts)
            # We use spacing because in this concrete class we make it a policy that scoring cycles should be like "FY 22" and 
            # not "FY22". That way when formatted by `StringUtils().format_as_yaml_fieldname` we get "fy-22" instead of "fy22"
            roll_from_scoring_cycle     = roll_from_timebucket.displayFY(spacing= " ")

            FMT                         = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
            roll_from_name              = FMT(journey + '.' + roll_from_scoring_cycle + '.' + product + '.' + scenario)

            roll_to_scoring_cycle       = scoring_cycle

            return roll_from_name, roll_from_scoring_cycle, roll_to_scoring_cycle

    def subspace_from_name(self, parent_trace, namespace, name, product, kind):
        '''
        Helper method used by self.rollover. Extracts the subspace from a manifest name, taking into account
        whether there are subproducts or not.

        For example, if there are no subproducts, then we expect to be given names like

                cloud.fy-23.opus.official

        and then the subspace is "cloud".

        However, if there are subproducts and product OPUS has a subproduct called MDI, then we expect names like

                cloud.mdi.fy-23.opus.official

        and then the subspace is "cloud.mdi"
        '''


        # GOTCHA: Normally this is called during "get form" as opposed than during a "post", so the function
        #       that normally determines if there are subproducts (self._buildOneManifest) might not have been called.
        #       So in case, we duplicate that logic here
        validator                   = StaticDataValidator(parent_trace, self.store, self.a6i_config)
        subproducts                 = validator.getSubProducts(parent_trace, namespace, product)
        if len(subproducts) == 0:
            self.using_subproducts  = False
        else:
            self.using_subproducts  = True # Derived classes can use this in self.getPostingConfig to ensure multiple headers are on
            self.subproducts        = subproducts

        if self.using_subproducts:
            # Then name is something like "cloud.mdi.fy-23.opus.official", and we want to extract "cloud.mdi"
            subnamespace                            = ".".join(name.split(".")[:2])
        else:
            # Then name is something like "cloud.fy-23.opus.official", and we want to extract "cloud"
            subnamespace                            = name.split(".")[0]
        return subnamespace


    def rollover(self, parent_trace, manifest_api_name, namespace, roll_to_name, coords, kind):
        '''
        Returns a dictionary corresponding to the most recent manifest meeting the given characteristics, except
        that its scoring cycle is the previous fiscal year.

        If no such exists, or if scoring cycles are not represented as fiscal years in the format "FY 22", for example,
        then it returns None
        '''
        # We expect roll_to_name to be something like "cloud.fy-23.opus.official", so we can extract the subnamespace
        # (which this Journeys controller requires) by taking the first substring of roll_from_name before the first "."
        #
        # First step is to get a product
        try:
            product                             = coords.product
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Can't do a rollover because coordinates don't have a product",
                                data = {"manifest_api_name": manifest_api_name,
                                            "namespace":    namespace,
                                            "roll_to_name": roll_to_name,
                                            "coords":       str(coords),
                                            "kind":         kind})
        subnamespace                            = self.subspace_from_name(parent_trace, 
                                                                                        namespace, 
                                                                                        roll_to_name, 
                                                                                        product, 
                                                                                        kind)
        roll_from_name, roll_from_scoring_cycle, roll_to_scoring_cycle   = self._manifestRolloverNameFromCoords(
                                                                                        parent_trace, 
                                                                                        roll_to_name, 
                                                                                        subnamespace, 
                                                                                        coords, 
                                                                                        kind)
        manifest_dict                           = None
        if roll_from_name != None:
            manifest_dict, manifest_path        = self.store.findLatestVersionManifest( 
                                                                parent_trace        = parent_trace, 
                                                                manifest_api_name   = manifest_api_name,
                                                                namespace           = namespace, 
                                                                name                = roll_from_name, 
                                                                kind                = kind)

        if manifest_dict != None:
            # GOTCHA: need to add hints for later use
            # 
            # Since manifest_dict != None, that means that the prior year's last manifest can be used 
            # as the basis for the next year's
            # 
            # Problem is: 
            #       the metadata in the manifest_dict, while correct, would cause any Excel form built from it to
            # have a scoring cycle for the past year, not the next year as we intend in a rollover.
            # To fix this we add an additional label as a "hint" for later use in journeys_posting_label::infer, so that it knows
            # not to take the scoring cycle from manifest_dict's scoring_cycle label (since that is prior year's)
            # but from this additional label we are adding: RolloverUtils.ROLL_TO_SCORING_CYCLE
            #
            # Likewise, we remember the "roll-from name" (i.e., "modernization.fy-22.astrea.official" instead of 
            # "modernization.fy-23.astrea.official" when rolling from "FY 22" to "FY 23"). This is remembered so that we
            # don't get errors when checking integrity versions when we post manifests: if we post version 5 of a manifest, say,
            # Apodeixi will check if version 4 exists. But if Apodeixi looks in the "new year's" name, then it won't find 
            # a prior manifest for version 4 and error out. To pre-empt this, we remember the "last year's" name so that
            # Apodeixi can use it to find the prior version 4 of the manifest, and pass the version integrity check.
            #
            # The reverence integrity check is dones in skeleton_controller::initialize_UID_Store
            #
            manifest_dict['metadata']['labels'][RolloverUtils.ROLL_TO_SCORING_CYCLE]   = roll_to_scoring_cycle
            manifest_dict['metadata']['labels'][RolloverUtils.ROLL_FROM_NAME]           = roll_from_name


            

        return manifest_dict

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
        # Determine if we have subproducts, because in that case we need to remember that since it may affect how some
        # derived classes create their posting configuration. For example, for kind `big-rock-estimate` the posting configuration
        # needs to record that there will be 2 headers (a MultiLevel index in Pandas), not 1
        #
        # GOTCHA: This determination must be done *before* calling super()._buildOneManifest, since super will lead to the
        #   actual loading of the Excel, which requires having the posting configuration aware of how many headers are expected
        #   in Excel (i.e., whether Pandas shuold build a MultiLevel index for the columns, or not)
        #   It is for that reason that his code duplicates some things that the call to super() will redo, like determining
        #   the namespace
        my_trace                        = parent_trace.doing("Determining if subproducts exist")
        if True:
            organization                = label.organization        (parent_trace)
            kb_area                     = label.knowledgeBaseArea   (parent_trace) 
            FMT                         = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
            namespace                   = FMT(organization + '.' + kb_area)
            product                     = label.product             (my_trace)
            validator                   = StaticDataValidator(parent_trace, self.store, self.a6i_config)
            subproducts                 = validator.getSubProducts(parent_trace, namespace, product)
            if len(subproducts) == 0:
                self.using_subproducts  = False
            else:
                self.using_subproducts  = True # Derived classes can use this in self.getPostingConfig to ensure multiple headers are on
                self.subproducts        = subproducts

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

    def rollOverIsSupported(self, kind):
        '''
        Returns a boolean, depending on whether rollover functionality is supported for the `kind` in question.
        This is used when posting an Excel file in a "immediately after rollover" context, e.g., when  
        we just did a "get form" for FY 23 and it gave us an Excel that points to a prior version in FY 22 through 
        its "rollFromName" label field.

        In those situations it may happen that the Excel file leads to the creation of multiple manifests,
        and possibly for only some of them the prior version should be sought in the prior fiscal year
        (for example, some manifests may be static data or may not use the same manifest name as the main manifests posted,
        so the "rollFromName" field in the posting label should not be used for that `kind` of manifest).
        
        In those cases, this function allows the concrete controller class to state which kinds support rollover
        logic, i.e., for which ones it makes sense to look in a prior fiscal yea
        '''
        return True

    def apply_subproducts_to_df(self, parent_trace, template_dict, template_df):
        '''
        Helper method that derived classes may use when creating templates for manifests that should be replicated
        per subproduct.

        This method creates and returns a DataFrame that the caller (a derived class) can use as a template, by 
        replicating `template_df` for each subproduct that exists for the product of `template_dict`.
        It also adds an extra level to the columns of the returned value (i.e., columns are a MultiIndex of tuples)
        where the top level is the subproduct.

        If the product in question has no subproducts, or if it is an empty list, 
        then it just returns `template_df` without changes.
        '''
        subproducts                     = self.get_subproducts(parent_trace, template_dict)
        if subproducts == None or len(subproducts) == 0:
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

        If subproducts is None, or if it is an empty list, then it just returns `a_list`

        @param a_list A list, typically of strings
        @param suproducts A list, typically of strings
        '''
        if subproducts == None or len(subproducts) == 0:
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

        If subproducts is None, or if it is an empty list, then it just returns `a_dict`

        @param a_dict A dict, typically of strings
        @param suproducts A list, typically of strings
        '''
        if subproducts == None or len(subproducts) == 0:
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
        if subproducts == None or foreign_key in manifest_df.columns:
            # If there are no subproduct, the columns are strings, not tuples.
            # And even in cases where there are subproducts, sometimes the foreign_key is not tied to subproducts,
            # so that particular column wouldn't be a tuple but simply a string.
            # In either case we can just use foreign_key as the column to search for the referenced_uid
            referenced_uid          = manifest_df[foreign_key].iloc[manifest_df_row_number] 
        else:
            # In this case we are looking for columns that is a tuple, whose first entry is a subproduct and the
            # second is the foreign_key.
            # There might be multiple such, but they should all agree on what is the referenced_uid
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

        If there are no subprodcuts, it returns an empty list
        '''
        validator                       = StaticDataValidator(parent_trace, self.store, self.a6i_config)
        product                         = DictionaryUtils().get_val(parent_trace, 
                                                                    root_dict       = manifest_dict,
                                                                    root_dict_name  = "A Manifest",
                                                                    path_list       = ["metadata", "labels", "product"],
                                                                    valid_types     = [str])
        namespace                         = DictionaryUtils().get_val(parent_trace, 
                                                                    root_dict       = manifest_dict,
                                                                    root_dict_name  = "A Manifest",
                                                                    path_list       = ["metadata", "namespace"],
                                                                    valid_types     = [str])
        subproducts                     = validator.getSubProducts(parent_trace, namespace, product)
        return subproducts

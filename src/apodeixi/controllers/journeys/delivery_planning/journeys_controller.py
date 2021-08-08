import pandas                                                               as _pd

from apodeixi.controllers.util.manifest_api                                 import ManifestAPI
from apodeixi.controllers.journeys.delivery_planning.journeys_posting_label  import JourneysPostingLabel
from apodeixi.controllers.util.skeleton_controller                          import SkeletonController

from apodeixi.knowledge_base.filing_coordinates                             import JourneysFilingCoordinates
from apodeixi.knowledge_base.knowledge_base_util                            import FormRequest

from apodeixi.util.a6i_error                                                import ApodeixiError
from apodeixi.util.formatting_utils                                         import StringUtils

from apodeixi.knowledge_base.filing_coordinates                             import JourneysFilingCoordinates


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

    def getManifestAPI(self):
        return self.MANIFEST_API

    def manifestNameFromLabel(self, parent_trace, label):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        label
        '''
        product                         = label.product             (parent_trace)
        journey                         = label.journey             (parent_trace) 
        scenario                        = label.scenario            (parent_trace)
        scoring_cycle                   = label.scoring_cycle       (parent_trace)

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(journey + '.' + scenario + '.' + scoring_cycle + '.' + product)
        return name

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
        if not type(coords) == JourneysFilingCoordinates:
            raise ApodeixiError(parent_trace, "Can't build manifest name because received wrong type of filing coordinates",
                                                data = {"Type of coords received": str(type(coords)),
                                                        "Expected type of coords": "JourneysFilingCoordinates"})

        if subnamespace == None:
            raise ApodeixiError(parent_trace, "Can't build manifest name becase subnamespace is null. Should be "
                                                + "set to a kind of journey. Example: 'modernization'")

        product                         = coords.product
        journey                         = subnamespace
        scenario                        = coords.scenario
        scoring_cycle                   = coords.scoringCycle

        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(journey + '.' + scenario + '.' + scoring_cycle + '.' + product)
        return name

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
        name                                    = self.manifestNameFromCoords(parent_trace, subnamespace, coords)

        journey, scoring_cycle, product, scenario = name.split(".")

        labels_dict                             = template_dict['metadata']['labels']

        labels_dict[MY_PL._JOURNEY]             = journey
        labels_dict[MY_PL._SCORING_CYCLE]       = scoring_cycle
        labels_dict[MY_PL._PRODUCT]             = product
        labels_dict[MY_PL._SCENARIO]            = scenario
        labels_dict[MY_PL._SCORING_MATURITY]    = ""

        return template_dict, template_df


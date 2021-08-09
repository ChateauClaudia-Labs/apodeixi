from apodeixi.controllers.admin.static_data.static_data_validator   import StaticDataValidator
from apodeixi.controllers.util.skeleton_controller                  import SkeletonController
from apodeixi.util.formatting_utils                                 import StringUtils

class JourneysPostingLabel(SkeletonController._MyPostingLabel):
    '''
    Parent class for the concrete Posting Label class used by controllers in the Journeys domain
    Codifies the schema expectations for the posting label when posting big rocks estimates. 
    '''
    _PRODUCT                    = "product"
    _JOURNEY                    = "journey"
    _SCENARIO                   = "scenario"
    _SCORING_CYCLE              = "scoringCycle"
    _SCORING_MATURITY           = "scoringMaturity"

    def __init__(self, parent_trace, controller, mandatory_fields, optional_fields = [], date_fields = []):
        # Shortcut to reference class static variables
        ME = JourneysPostingLabel

        combined_mandatory_fields               = [ ME._PRODUCT,        ME._JOURNEY,            ME._SCENARIO,    # Determine name  
                                                    ME._SCORING_CYCLE,  ]
        combined_mandatory_fields.extend(mandatory_fields)

        combined_optional_fields                = [ME._SCORING_MATURITY]
        combined_optional_fields.extend(optional_fields)

        combined_date_fields                    = []
        combined_date_fields.extend(date_fields)

        super().__init__(   parent_trace        = parent_trace,
                            controller          = controller,
                            mandatory_fields    = combined_mandatory_fields,
                            optional_fields     = combined_optional_fields,
                            date_fields         = combined_date_fields)

    def read(self, parent_trace, posting_label_handle):
        '''
        '''
        super().read(parent_trace, posting_label_handle)

        # The product field is allowed to be submitted with aliases. Therefore, replace its value if the user
        # submitted an alias. Only applies when we enforce referential integrity, since otherwise we allow the
        # product field to be "anything". 
        # Example: avoid an attempt to replace alias for unit tests, since they use a mock-up store that lacks
        # reference data, so they'll fail if we attempted to determine if a product has alias. That's why
        # referential integrity checks are turned off for unit tests.
        ME = JourneysPostingLabel
        if self.controller.a6i_config.enforce_referential_integrity:
            submitted_product                   = self.product(parent_trace)
            validator                           = StaticDataValidator(  parent_trace    = parent_trace, 
                                                                        store           = self.controller.store, 
                                                                        a6i_config      = self.controller.a6i_config)
            namespace                           = self.determineNamespace(parent_trace)
            product_code                        = validator.getProductCode(parent_trace, namespace, submitted_product)
            if submitted_product != product_code:
                self.ctx[ME._PRODUCT] = product_code

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

        validator           = StaticDataValidator(parent_trace, self.controller.store, self.controller.a6i_config)

        namespace           = self.determineNamespace(parent_trace)

        validator.validateProduct(          parent_trace, self, namespace)
        validator.validateScoringCycle(     parent_trace, self, namespace)

    def determineNamespace(self, parent_trace):
        '''
        Returns the namespace implied by the fields of this posting label
        '''
        raw_namespace       = self.organization(parent_trace) + "." + self.knowledgeBaseArea(parent_trace)
        namespace           = StringUtils().format_as_yaml_fieldname(raw_namespace)
        return namespace


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

        ME = JourneysPostingLabel
        def _infer(fieldname, path_list):
            self._inferField(   parent_trace            = parent_trace, 
                                fieldname               = fieldname, 
                                path_list               = path_list, 
                                manifest_dict           = manifest_dict)

        _infer(ME._PRODUCT,             ["metadata",    "labels",       ME._PRODUCT             ])
        _infer(ME._JOURNEY,             ["metadata",    "labels",       ME._JOURNEY,            ])
        _infer(ME._SCENARIO,            ["metadata",    "labels",       ME._SCENARIO,           ])
        _infer(ME._SCORING_CYCLE,       ["metadata",    "labels",       ME._SCORING_CYCLE,      ])
        _infer(ME._SCORING_MATURITY,    ["metadata",    "labels",       ME._SCORING_MATURITY,   ])

        editable_fields.extend([ME._SCORING_MATURITY])

        return editable_fields

    def product(self, parent_trace):
        # Shortcut to reference class static variables
        ME = JourneysPostingLabel

        return self._getField(parent_trace, ME._PRODUCT)

    def journey(self, parent_trace):
        # Shortcut to reference class static variables
        ME = JourneysPostingLabel

        return self._getField(parent_trace, ME._JOURNEY)

    def scenario(self, parent_trace):
        # Shortcut to reference class static variables
        ME = JourneysPostingLabel

        return self._getField(parent_trace, ME._SCENARIO)

    def scoring_cycle(self, parent_trace):
        # Shortcut to reference class static variables
        ME = JourneysPostingLabel

        return self._getField(parent_trace, ME._SCORING_CYCLE)

    def scoring_maturity(self, parent_trace):
        # Shortcut to reference class static variables
        ME = JourneysPostingLabel

        return self._getField(parent_trace, ME._SCORING_MATURITY)

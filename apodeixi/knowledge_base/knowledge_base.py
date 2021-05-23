from apodeixi.util.a6i_error                                    import ApodeixiError

from apodeixi.controllers.kernel.bdd.capability_hierarchy       import CapabilityHierarchy_Controller
from apodeixi.controllers.journeys.delivery_planning.big_rocks  import BigRocksEstimate_Controller

class KnowledgeBase():
    '''
    @param store A KnowledgeBaseStore instance. Handles all I/O for this KnowledgeBase.
    '''
    def __init__(self, store):
        self.store              = store
        self.processing_rules   = KB_ProcessingRules()
        return

    def post(self, parent_trace, posting_type):
        if not posting_type in self.processing_rules.keys():
            raise ApodeixiError("Invalid posting type '" + posting_type + "': must be one of " + ", ".join(self.processsing_rules.keys()))

        ctrl                    = self.processing_rules[posting_type](parent_trace, self.store)

        #    def apply(self, parent_trace, knowledge_base_dir, relative_path, excel_filename, excel_sheet, ctx_range):
        ctrl.apply()

class KB_ProcessingRules():
    '''
    Configuration class to represent the processing that the KnowledgeBase must take in response to an "event". For example,
    what concrete posting controller to use in response to an Excel posting.
    '''
    def __init__(self):
        # Keys are strings for each kind of Excel posting known to the knowledge base, and values are controller classes to handle them
        self.posting_handlers = {} 
        self._initPostingHandlers()

    def _initPostingHanders(self):
        ME                                                                  = KB_ProcessingRules
        self.posting_handlers[ME.POSTING_CAPABILITY_HIERARCHY]              = CapabilityHierarchy_Controller 

        rule_dict                                                           = {}
        rule_dict[_CONTROLLER_CLASS]                                        = BigRocksEstimate_Controller
        # Example: ["modernization", "default", "Dec 2020", "FusionOpus"]. This, plus posting type, uniquely identifies location
        # of a posting in the knowledge base. These are fields that the PostingLabel for the controller must have.
        rule_dict[_POSTINGS_FILING_SCHEME]                                  = ["journey", "scenario", "scoringCycle", "product"]

        self.posting_handlers[ME.POSTING_BIG_ROCKS]                         = BigRocksEstimate_Controller  

    # Possible keys in a rule dictionary for a given posting type
    _CONTROLLER_CLASS               = "_CONTROLLER_CLASS" 
    _POSTINGS_FILING_SCHEME         = "_POSTINGS_FILING_SCHEME"    

    # Static strings used for the string users are expected to provide to expresss what type
    #  of posting a user is doing
    POSTING_CAPABILITY_HIERARCHY    = "capability-hierarchy"
    POSTING_BIG_ROCKS               = "big-rocks"
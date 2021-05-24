from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace

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

    '''
    Returns a PostResponse
    '''
    def post(self, parent_trace, path_of_file_being_posted, posting_type, excel_sheet="Sheet1", ctx_range="B2:C1000", version=None):
        root_trace              = parent_trace.doing("Posting excel spreadsheet to knowledge base",
                                                                data = {    'posting_type'  : posting_type,
                                                                            'path'          : path_of_file_being_posted,
                                                                            'excel_sheet'   : excel_sheet,
                                                                            'ctx_range'     : ctx_range,
                                                                            'version'       : version,
                                                                            'signaled_from' : __file__
                                                                            })
        handlers                = self.processing_rules.posting_handlers
        
        if not posting_type in handlers.keys():
            raise ApodeixiError("Invalid posting type '" + posting_type + "': must be one of " + ", ".join(handlers.keys()))

        ctrl                    = handlers[posting_type][KB_ProcessingRules._CONTROLLER_CLASS](root_trace, self.store)

        response                = ctrl.apply(   parent_trace        = root_trace, 
                                                excel_filename      = path_of_file_being_posted, 
                                                excel_sheet         = excel_sheet, 
                                                ctx_range           = ctx_range, 
                                                version             = version)

        return response

class KB_ProcessingRules():
    '''
    Configuration class to represent the processing that the KnowledgeBase must take in response to an "event". For example,
    what concrete posting controller to use in response to an Excel posting.
    '''
    def __init__(self):
        # Keys are strings for each kind of Excel posting known to the knowledge base, and values are controller classes to handle them
        self.posting_handlers = {} 
        self._initPostingHandlers()

    def _initPostingHandlers(self):
        ME                                                                  = KB_ProcessingRules

        # Init processing rules for the CapabilityHierarchy controller
        rule_dict                                                           = {}
        rule_dict[ME._CONTROLLER_CLASS]                                     = CapabilityHierarchy_Controller
        rule_dict[ME._POSTINGS_FILING_SCHEME]                               = ["scaffoldingPurpose", "project"]
        self.posting_handlers[ME.POSTING_CAPABILITY_HIERARCHY]              = rule_dict 

        # Init processing rules for the Big Rocks controller
        rule_dict                                                           = {}
        rule_dict[ME._CONTROLLER_CLASS]                                     = BigRocksEstimate_Controller
        # Example: ["modernization", "default", "Dec 2020", "FusionOpus"]. This, plus posting type, uniquely identifies location
        # of a posting in the knowledge base. These are fields that the PostingLabel for the controller must have.
        rule_dict[ME._POSTINGS_FILING_SCHEME]                                  = ["journey", "scenario", "scoringCycle", "product"]
        self.posting_handlers[ME.POSTING_BIG_ROCKS]                         = rule_dict  

    # Possible keys in a rule dictionary for a given posting type
    _CONTROLLER_CLASS               = "_CONTROLLER_CLASS" 
    _POSTINGS_FILING_SCHEME         = "_POSTINGS_FILING_SCHEME"    

    # Static strings used for the string users are expected to provide to expresss what type
    #  of posting a user is doing
    POSTING_CAPABILITY_HIERARCHY    = "capability-hierarchy"
    POSTING_BIG_ROCKS               = "big-rocks"


    
        
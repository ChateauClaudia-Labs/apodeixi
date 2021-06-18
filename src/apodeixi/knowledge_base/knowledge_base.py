from apodeixi.util.a6i_error                                                import ApodeixiError, FunctionalTrace

from apodeixi.controllers.kernel.bdd.capability_hierarchy                   import CapabilityHierarchy_Controller
from apodeixi.controllers.journeys.delivery_planning.big_rocks              import BigRocksEstimate_Controller
from apodeixi.controllers.journeys.delivery_planning.milestones_controller  import MilestonesController

class KnowledgeBase():
    '''
    @param store A KnowledgeBaseStore instance. Handles all I/O for this KnowledgeBase.
    '''
    def __init__(self, store):
        self.store              = store
        
        self.controllers           = { #List of associations of posting API => dict of kind=> PostingController class to use 
                                        # for such posting API
            'delivery-planning.journeys.a6i':       {   "big-rocks":                        BigRocksEstimate_Controller,
                                                        'modernization-milestone':          MilestonesController},
            'bdd.kernel.a6i':                       {   "capability-hierarchy":             CapabilityHierarchy_Controller},
            'milestone.journeys.a6i':               None, # TODO
            'milestone.journeys.a6i':               None, # TODO
            'milestones.initiative.a6i':            None, # TODO
            'charter.initiative.a6i':               None, # TODO
        }

        return

    '''
    Returns a PostResponse
    '''
    def post(self, parent_trace, path_of_file_being_posted, posted_kind, excel_sheet="Sheet1", ctx_range="B2:C1000", version=None):
        root_trace              = parent_trace.doing("Posting excel spreadsheet to knowledge base",
                                                                data = {    'posted_kind'   : posted_kind,
                                                                            'path'          : path_of_file_being_posted,
                                                                            'excel_sheet'   : excel_sheet,
                                                                            'ctx_range'     : ctx_range,
                                                                            'version'       : version},
                                                                origination = {'signaled_from' : __file__
                                                                            })

        my_trace                = parent_trace.doing("Inferring the posting API from filename",
                                                        data = {'filename': path_of_file_being_posted})
        posting_api             = self.store.infer_posting_api(my_trace, path_of_file_being_posted)

        my_trace                = parent_trace.doing("Checking if posting API for this file is supported")
        supported_apis          = list(self.controllers.keys())
        if not posting_api in supported_apis:
            raise ApodeixiError(my_trace, "The posting API for this file is not supported by the Knowledge Base",
                                            data = {    'posting_api':                      posting_api,
                                                        'filename':                         path_of_file_being_posted,
                                                        'supported apis':                   str(supported_apis)})
        
        my_trace                = parent_trace.doing("Checking if posted_kind is supported by posting_api",
                                                        data = {    'posted_kind':         posted_kind,
                                                                    'posting_api':          posting_api})
        controllers_sub_dict    = self.controllers[posting_api]
        supported_kinds         = list(controllers_sub_dict.keys())
        if not posted_kind in supported_kinds:
            raise ApodeixiError(my_trace, "The posted kind is not supported by the posting API",
                                            data = {    'posted_kind':         posted_kind,
                                                        'posting_api':          posting_api})

        ctrl                    = controllers_sub_dict[posted_kind](root_trace, self.store)

        response                = ctrl.apply(   parent_trace        = root_trace, 
                                                excel_filename      = path_of_file_being_posted, 
                                                excel_sheet         = excel_sheet, 
                                                ctx_range           = ctx_range, 
                                                version             = version)

        return response

    
        
from apodeixi.util.a6i_error                                                import ApodeixiError, FunctionalTrace

from apodeixi.controllers.kernel.bdd.capability_hierarchy                   import CapabilityHierarchy_Controller
from apodeixi.controllers.journeys.delivery_planning.big_rocks              import BigRocksEstimate_Controller
from apodeixi.controllers.journeys.delivery_planning.milestones_controller  import MilestonesController
from apodeixi.util.dictionary_utils                                         import DictionaryUtils

class KnowledgeBase():
    '''
    @param store A KnowledgeBaseStore instance. Handles all I/O for this KnowledgeBase.
    '''
    def __init__(self, parent_trace, store):
        self.store              = store
        
        self.controllers           = { #List of associations of posting API => dict of kind=> PostingController class to use 
                                        # for such posting API
            'delivery-planning.journeys.a6i':       {   "big-rocks":                        BigRocksEstimate_Controller,
                                                        'modernization-milestone':          MilestonesController},
            'bdd.kernel.a6i':                       {   "capability-hierarchy":             CapabilityHierarchy_Controller},
            'milestone.journeys.a6i':               None, # TODO

            'workstream.initiatives.a6i':           None, # TODO
            'charter.initiatives.a6i':              None, # TODO
        }

        return

    '''
    Returns a PostResponse
    '''
    def post(self, parent_trace, path_of_file_being_posted, posted_kind, excel_sheet="Posting Label", ctx_range="B2:C1000"):
        root_trace              = parent_trace.doing("Posting excel spreadsheet to knowledge base",
                                                                data = {    'posted_kind'   : posted_kind,
                                                                            'path'          : path_of_file_being_posted,
                                                                            'excel_sheet'   : excel_sheet,
                                                                            'ctx_range'     : ctx_range},
                                                                origination = {'signaled_from' : __file__
                                                                            })

        my_trace                = parent_trace.doing("Inferring the posting API from filename",
                                                        data = {'filename': path_of_file_being_posted})

        label_handle            = self.store.buildPostingHandle(    parent_trace        = my_trace,
                                                                    excel_posting_path  = path_of_file_being_posted, 
                                                                    sheet               = excel_sheet, 
                                                                    excel_range         = ctx_range)

        posting_api             = label_handle.getPostingAPI(my_trace)

        my_trace                = parent_trace.doing("Retrieving a PostingController to process the posting")
        ctrl                    = self.findController(  parent_trace        = my_trace,
                                                        posting_api         = posting_api, 
                                                        kind                = posted_kind)

        response                = ctrl.apply(   parent_trace                = root_trace, 
                                                posting_label_handle        = label_handle)

        return response

    
    def findController(self, parent_trace, posting_api, kind):
        '''
        Retrieves and returns a PostingController object that knows how to process postings for objects
        of the given `kind` belonging to the given `posting_api`.

        If the Knowledge Base or its store is not configured to support such postings, it raises an ApodeixiError.
        '''
        my_trace            = parent_trace.doing("Validating that KnowledgeBase supports the given posting api and kind",
                                                    data = {    'posting_api':      posting_api,
                                                                'kind':             kind})
                                                                
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = parent_trace, 
                                                                root_dict       = self.controllers, 
                                                                root_dict_name  = 'Knowledge Base supported controllers',
                                                                path_list       = [posting_api, kind],
                                                                valid_types     = [type])
                                                       
        if not check:
            raise ApodeixiError(my_trace, "Knowledge Base does not support the given posting api and kind",
                                                data = {    'posting_api':      posting_api,
                                                            'kind':             kind})

        my_trace            = parent_trace.doing("Validating that KnowledgeBase's store supports the given posting api",
                                                    data = {    'posting_api':      posting_api})
        store_supported_apis    = self.store.supported_apis(my_trace)
        if not posting_api in store_supported_apis:
            raise ApodeixiError(my_trace, "Unable to instantiate a controller from given class. Is it the right type?",
                                                data = {    'posting_api':                      str(posting_api),
                                                            'store_supported_apis found':       str(store_supported_apis)})

        klass           = self.controllers[posting_api][kind]
        my_trace            = parent_trace.doing("Instantiating a PostingController class",
                                                    data = {    'class':      str(klass)})
        
        try:
            
            ctrl            = klass(my_trace, self.store)
        except Exception as ex:
            raise ApodeixiError(my_trace, "Unable to instantiate a controller from given class. Is it the right type?",
                                                data = {    'controller_class':     str(klass),
                                                            'exception found':      str(ex)})

        return ctrl
from apodeixi.util.a6i_error                                                import ApodeixiError, FunctionalTrace

from apodeixi.controllers.admin.static_data.products                        import ProductsController
from apodeixi.controllers.kernel.bdd.capability_hierarchy                   import CapabilityHierarchy_Controller
from apodeixi.controllers.journeys.delivery_planning.big_rocks              import BigRocksEstimate_Controller
from apodeixi.controllers.journeys.delivery_planning.milestones_controller  import MilestonesController
from apodeixi.controllers.initiatives.workstream                            import Workstream_Controller
from apodeixi.util.dictionary_utils                                         import DictionaryUtils

class KnowledgeBase():
    '''
    @param store A KnowledgeBaseStore instance. Handles all I/O for this KnowledgeBase.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        self.store              = store
        self.a6i_config         = a6i_config
        
        self.controllers           = { #List of associations of posting API => dict of kind=> PostingController class to use 
                                        # for such posting API
            'big-rocks.journeys.a6i':                   BigRocksEstimate_Controller,
            'milestone.journeys.a6i':                   MilestonesController,

            'products.static-data.admin.a6i':           ProductsController,

            'capability-hierarchy.bdd.kernel.a6i':      CapabilityHierarchy_Controller,

            'workstream.initiatives.a6i':               Workstream_Controller,
            'charter.initiatives.a6i':                  None, # TODO
        }

        return

    def postByFile(self, parent_trace, path_of_file_being_posted, excel_sheet="Posting Label", ctx_range="B2:C1000"):
        '''
        Part of the KnowledgeBase's API, i.e., this method is transactional (to the extent that the
        store used by the KnowledgeBase supports it).

        Handles a posting request expressed as an Excel file, with optional information on the worksheet and cells
        where the posting label can be found within the Excel file.

        Returns a PostResponse object, as well as a string corresponding the log made for this posting
        '''
        self.store.beginTransaction(parent_trace)
        try:
            root_trace              = parent_trace.doing("Posting excel spreadsheet to knowledge base",
                                                                    data = {    'path'          : path_of_file_being_posted,
                                                                                'excel_sheet'   : excel_sheet,
                                                                                'ctx_range'     : ctx_range},
                                                                    origination = {'signaled_from' : __file__
                                                                                })
            my_trace                = root_trace.doing("Inferring the posting handle from filename",
                                                            data = {'filename': path_of_file_being_posted})

            label_handle            = self.store.buildPostingHandle(    parent_trace        = my_trace,
                                                                        excel_posting_path  = path_of_file_being_posted, 
                                                                        sheet               = excel_sheet, 
                                                                        excel_range         = ctx_range)

            my_trace                = root_trace.doing("Posting by label")
            response, log_txt       = self.postByLabel(my_trace, label_handle)

            self.store.commitTransaction(parent_trace)

            return response, log_txt

        except Exception as ex:
            self.store.abortTransaction(parent_trace) # Clean up the transactional isolation area before erroring out
            if type(ex) == ApodeixiError:
                raise ex # Just propagate exception, retaining its friendly FunctionalTrace
            else:
                raise ApodeixiError(parent_trace, "Transaction aborted due to error found in processing",
                                                    data = {"error": str(ex)})

    def postByLabel(self, parent_trace, label_handle):
        '''
        Part of the KnowledgeBase's API, i.e., this method is transactional (to the extent that the
        store used by the KnowledgeBase supports it).
        
        Handles a posting request expressed as an Posting Label handle.

        Returns a PostResponse object, as well as a string corresponding the log made for this posting
        '''
        self.store.beginTransaction(parent_trace)
        try:
            my_trace                = parent_trace.doing("Posting by label",
                                                data = {'relativePath': label_handle.getRelativePath(parent_trace)})

            posting_api             = label_handle.getPostingAPI(my_trace)

            ctrl                    = self.findController(  parent_trace        = my_trace,
                                                                posting_api     = posting_api)
            # Reset the LinkTable, in case the same controller was previouly used to process another Excel file 
            # since that implies that any previously stored links are for a different scope of UIDs
            ctrl.init_link_table(parent_trace)
            my_trace                = parent_trace.doing("Applying controller to process the posting")
            response                = ctrl.apply(   parent_trace                = my_trace, 
                                                        posting_label_handle    = label_handle)

            log_txt                 = ctrl.log_txt

            self.store.commitTransaction(parent_trace)

            return response, log_txt

        except Exception as ex:
            self.store.abortTransaction(parent_trace) # Clean up the transactional isolation area before erroring out
            if type(ex) == ApodeixiError:
                raise ex # Just propagate exception, retaining its friendly FunctionalTrace
            else:
                raise ApodeixiError(parent_trace, "Transaction aborted due to error found in processing",
                                                    data = {"error": str(ex)})

    def postInBatch(self, parent_trace, label_handle_list):
        '''
        Part of the KnowledgeBase's API, i.e., this method is transactional (to the extent that the
        store used by the KnowledgeBase supports it).
        
        Handles a barch of posting request expressed as a list of PostingLabelHandle objects.

        Returns two dictionaries, one for successes and one for errors. 
        Both are indexed with the integer index of a PostingLabelHandle in `label_handle_list`.

        For the success dictionary, the values are the PostResponse objects obtained from processing the
        corresponding PostingLabelHandle.
        
        For the success dictionary, the values are the ApodeixiError raised whhile processing the
        correspoding PostingLabelHandle.
        '''
        self.store.beginTransaction(parent_trace)

        try:
            successes               = {}
            errors                  = {}
            for idx in range(len(label_handle_list)):
                handle              = label_handle_list[idx]
                loop_trace          = parent_trace.doing("Doing a cycle of loop to process one of " 
                                                            + str(len(label_handle_list)) 
                                                            + " label handles",
                                                        data = {'idx'               : idx,
                                                                'excel_filename'    : handle.getRelativePath(parent_trace)})
                                                                
                
                try:
                    response, log   = self.postByLabel(loop_trace, handle)
                    successes[idx]  = response
                except ApodeixiError as ex:
                    errors[idx]     = ex

            self.store.commitTransaction(parent_trace)

            return successes, errors

        except Exception as ex:
            self.store.abortTransaction(parent_trace) # Clean up the transactional isolation area before erroring out
            if type(ex) == ApodeixiError:
                raise ex # Just propagate exception, retaining its friendly FunctionalTrace
            else:
                raise ApodeixiError(parent_trace, "Transaction aborted due to error found in processing",
                                                    data = {"error": str(ex)})

    def requestForm(self, parent_trace, form_request):
        '''
        Part of the KnowledgeBase's API, i.e., this method is transactional (to the extent that the
        store used by the KnowledgeBase supports it).
        
        Handles the request for getting a form (i.e., an Excel spreadsheet) that the caller can complete
        and later submit in a post request to the Knowledge Base.
        
        Therefore, this method will create and save an Excel spreadsheet in a location in the KnowledgeBase
        postings' area determined by the `form_request` parameter.

        It then returns a FormRequestResponse object, as well as a couple of objects to help with debugging or
        regression testing:
        
        * a string corresponding the log made during the processing
        * the ManifestRepresenter object that was used to create the form

        '''
        self.store.beginTransaction(parent_trace)

        try:
            my_trace                = parent_trace.doing("Requestiong a form",
                                                    data = {'posting_api':     form_request.getPostingAPI(parent_trace)})

            posting_api             = form_request.getPostingAPI(my_trace)

            ctrl                    = self.findController(  parent_trace        = my_trace,
                                                            posting_api         = posting_api)

            my_trace                = parent_trace.doing("Applying controller to process the posting")
            response                = ctrl.generateForm(    parent_trace            = my_trace, 
                                                            form_request            = form_request)

            log_txt                 = ctrl.log_txt
            representer             = ctrl.representer

            self.store.commitTransaction(parent_trace)

            return response, log_txt, representer

        except Exception as ex:
            self.store.abortTransaction(parent_trace) # Clean up the transactional isolation area before erroring out
            if type(ex) == ApodeixiError:
                raise ex # Just propagate exception, retaining its friendly FunctionalTrace
            else:
                raise ApodeixiError(parent_trace, "Transaction aborted due to error found in processing",
                                                    data = {"error": str(ex)})
 
    def findController(self, parent_trace, posting_api):
        '''
        Retrieves and returns a PostingController object that knows how to process postings for objects
        belonging to the given `posting_api`.

        If the Knowledge Base or its store is not configured to support such postings, it raises an ApodeixiError.
        '''
        my_trace            = parent_trace.doing("Validating that KnowledgeBase supports the given posting api",
                                                    data = {    'posting_api':      posting_api})
                                                                
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = parent_trace, 
                                                                root_dict       = self.controllers, 
                                                                root_dict_name  = 'Knowledge Base supported controllers',
                                                                path_list       = [posting_api],
                                                                valid_types     = [type])
                                                       
        if not check:
            raise ApodeixiError(my_trace, "Knowledge Base does not support the given posting api and kind",
                                                data = {    'posting_api':      posting_api})

        my_trace            = parent_trace.doing("Validating that KnowledgeBase's store supports the given posting api",
                                                    data = {    'posting_api':      posting_api})
        store_supported_apis    = self.store.supported_apis(my_trace)
        if not posting_api in store_supported_apis:
            raise ApodeixiError(my_trace, "Unable to instantiate a controller from given class. Is it the right type?",
                                                data = {    'posting_api':                      str(posting_api),
                                                            'store_supported_apis found':       str(store_supported_apis)})

        klass           = self.controllers[posting_api]
        my_trace            = parent_trace.doing("Instantiating a PostingController class",
                                                    data = {    'class':        str(klass),
                                                                'posting_api':  str(posting_api)})
        
        try:
            ctrl            = klass(my_trace, self.store, a6i_config=self.a6i_config)
        except Exception as ex:
            raise ApodeixiError(my_trace, "Unable to instantiate a controller from given class. Is it the right type?",
                                                data = {    'controller_class':     str(klass),
                                                            'exception found':      str(ex)})

        return ctrl
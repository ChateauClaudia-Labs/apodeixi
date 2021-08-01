
from apodeixi.util.a6i_error                                    import ApodeixiError

from apodeixi.controllers.admin.static_data.static_data         import StaticData_Controller


class ProductsController(StaticData_Controller):
    '''
    Class to process an Excel posting for the products static data objec. It produces two YAML manifest:
    
    * products
    * line-of-business

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    '''
    def __init__(self, parent_trace, store):
        super().__init__(parent_trace, store)

        self.SUPPORTED_VERSIONS         = ['v1a']
        self.SUPPORTED_KINDS            = ['product', 'line-of-business']

        self.POSTING_API                = 'products.static-data.admin.a6i'

    def getSupportedVersions(self):
        return self.SUPPORTED_VERSIONS 

    def getSupportedKinds(self):
        return self.SUPPORTED_KINDS

    def getPostingAPI(self):
        '''
        Implemented by concrete classes.
        Must return a string corresponding to the posting API supported by this controller.
        '''
        return self.POSTING_API















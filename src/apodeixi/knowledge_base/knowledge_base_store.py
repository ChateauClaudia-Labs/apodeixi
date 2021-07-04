import os                                           as _os
import yaml                                         as _yaml

from apodeixi.knowledge_base.knowledge_base_util    import ManifestHandle, PostingLabelHandle
from apodeixi.knowledge_base.filing_coordinates     import TBD_FilingCoordinates
from apodeixi.util.path_utils                       import PathUtils
from apodeixi.util.a6i_error                        import ApodeixiError

class KnowledgeBaseStore():
    '''
    Abstract class used to encapsulate the common services that a KnowledgeBase depends on from a "store" in which the
    KnowledgeBase can persist and retrieve manifests, postings, and any other persistent Apodeixi domain object.
    '''
    def __init__(self):
        return

    def supported_apis(self, parent_trace):
        '''
        Abstract method. Returns a list of the posting APIs that this KnowledgeStore knows about.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'supported_apis' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def getFilingClass(self, parent_trace, posting_api):
        '''
        Abstract method. 
        
        Returns a class object, derived from FilingCoordinates, that this store uses to structure postings for 
        the giving posting api. Used to build the posting handle.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'getFilingClass' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def getPostingsURL(self, parent_trace):
        '''
        Abstract method.

        Returns a string that can be used to locate the postings area in the Knowledge Base store's current environment
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'getPostingsURL' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def buildPostingHandle(self, parent_trace, excel_posting_path, sheet="Posting Label", excel_range="B2:C100"):
        '''
        Returns an PostingLabelHandle for the posting label embedded within the Excel spreadsheet that resides in 
        the path provided.
        '''
        kb_postings_url                     = self.getPostingsURL(parent_trace)
        if PathUtils().is_parent(           parent_trace                = parent_trace,
                                            parent_dir                  = kb_postings_url, 
                                            path                        = excel_posting_path):

            relative_path, filename         = PathUtils().relativize(   parent_trace    = parent_trace, 
                                                                        root_dir        = kb_postings_url,
                                                                        full_path       = excel_posting_path)

            posting_api                     = self._filename_2_api(parent_trace, filename)
                                   
            my_trace                        = parent_trace.doing("Building the filing coordinates",
                                                                    data = {"relative_path": str(relative_path)})
            filing_coords                   = self._buildFilingCoords(  parent_trace        = my_trace, 
                                                                        posting_api         = posting_api, 
                                                                        relative_path       = relative_path)
        else: # Posting wasn't submitted from the "right" folder, so coordinates will have be inferred later when label is read
            filename                        = PathUtils().tokenizePath(parent_trace, excel_posting_path)[-1]
            posting_api                     = self._filename_2_api(parent_trace, filename)
            filing_coords                   = TBD_FilingCoordinates( fullpath            = excel_posting_path,
                                                                    posting_api         = posting_api)

        # Now build the posting label handle
        posting_handle                  = PostingLabelHandle(       parent_trace        = parent_trace,
                                                                    posting_api         = posting_api,
                                                                    kb_postings_url     = kb_postings_url, 
                                                                    filing_coords       = filing_coords,
                                                                    excel_filename      = filename, 
                                                                    excel_sheet         = sheet, 
                                                                    excel_range         = excel_range)

        return posting_handle

    def searchPostings(self, parent_trace, posting_api, filing_coordinates_filter=None, posting_version_filter=None):
        '''
        Abstract method

        Returns a list of PostingLabelHandle objects, one for each posting in the Knowledge Base that matches
        the given criteria:

        * They are all postings for the `posting_api`
        * They pass the given filters

        @param posting_api A string that identifies the type of posting represented by an Excel file. For example,
                            'milestone.modernization.a6i' is a recognized posting API and files that end with that suffix,
                            such as 'opus_milestone.modernization.a6i.xlsx' will be located by this method.
        @param filing_coordinates_filter A function that takes a FilingCoordinates instance as a parameter and returns a boolean. 
                            Any FilingCoordinates instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        @param posting_version_filter A function that takes a PostingVersion instance as a parameter and returns a boolean. 
                            Any PostingVersion instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.n.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'searchPostings' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def _filename_2_api(self, parent_trace, filename):
        '''
        Helper method that can be used by derived classes to infer the posting api from a filename.

        Returns a string: the posting api. Raises an ApodeixiError if none of the store's supported apis matches the filename.
        '''
        posting_api                                 = None
        supported_apis                              = self.supported_apis(parent_trace=parent_trace)
        for api in supported_apis:
            if filename.endswith(api + ".xlsx"):
                posting_api          = api
                break
        if posting_api == None:
            raise ApodeixiError(parent_trace, "Filename is not for an API supported by the Knowledge Base store",
                                            data    = {    'filename':             filename,
                                                            'supported apis':       str(supported_apis)})
        return posting_api

    def _buildFilingCoords(self, parent_trace, posting_api, relative_path):
        '''
        Helper method that concrete derived classes may choose to use as part of implementing `buildPostingHandle`,
        to determine the FilingCoordinates to put into the posting handle.
        '''
        path_tokens                     = PathUtils().tokenizePath( parent_trace    = parent_trace,
                                                                    path   = relative_path) 

        my_trace                        = parent_trace.doing("Looking up filing class for given posting API",
                                                                data = {'posting_api': posting_api})               
        filing_class                    = self.getFilingClass(parent_trace, posting_api)
        if filing_class == None:
            raise ApodeixiError(my_trace, "Can't build filing coordinates from a null filing class")
        my_trace                        = parent_trace.doing("Validating that posting is in the right folder structure "
                                                                + "within the Knowledge Base")
        filing_coords                   = filing_class().build(parent_trace = my_trace, path_tokens = path_tokens)
        if filing_coords == None:
            raise ApodeixiError(my_trace, "Posting is not in the right folder within the Knowledge Base for this kind of API",
                                            data = {'posting relative path tokens':         path_tokens,
                                                    'posting api':                          posting_api,
                                                    'relative path expected by api':        filing_coords.expected_tokens(my_trace)})
        return filing_coords

    def persistManifest(self, parent_trace, manifest_dict):
        '''
        Abstract method implemented by concrete classes.

        It persists a manifest object whose content is given by `manifest_dict`, and returns a 
        ManifestHandle that uniquely identifies it.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'persistManifest' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def retrieveManifest(self, parent_trace, manifest_handle):
        '''
        Returns a dict and a string.
        
        The dict represents the unique manifest in the store that is identified by the `manifest handle`.

        The string represents the full path for the manifest.

        If none exists, it returns None.

        @param manifest_handle A ManifestHandle instance that uniquely identifies the manifest we seek to retrieve.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'retrieveManifest' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def searchManifests(self, parent_trace, manifest_api, labels_filter=None, manifest_version_filter=None):
        '''
        Abstract method

        Returns a list of ManifestHandle objects, one for each manifest in the Knowledge Base that matches
        the given criteria:

        * They are all manifests for the `manifest_api`
        * They pass the given filters

        @param manifest_api A string that identifies the type of manifest supported by the store. For example,
                            'milestone.modernization.a6i' is a recognized manifest API and store manifest objects
                            for such an api will be retrieved by this method.
        @param labels_filter A function that takes aa dict as a parameter and returns a boolean. The dict represents the content
                            of a manifest.
                            Any store mmanifest for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        @param manifest_version_filter A function that takes a ManifestVersion instance as a parameter and returns a boolean. 
                            Any ManifestVersion instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'searchManifests' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})


    def archivePosting(self, parent_trace, posting_label_handle):
        '''
        Abstract methods.

        Used after a posting Excel file has been processed. It moves the Excel file to a newly created folder dedicated 
        to this posting event and returns a FilingCoordinates object to identify that folder.       
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'archivePosting' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})
        
    def logPostEvent(self, parent_trace, controller_response):
        '''
        Abstract methods.

        Used to record in the store information about a posting event that has been completed.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'logPostEvent' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})
        
 
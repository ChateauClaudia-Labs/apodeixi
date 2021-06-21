import os                                           as _os
import yaml                                         as _yaml

from apodeixi.knowledge_base.knowledge_base_util    import ManifestHandle
from apodeixi.util.a6i_error                        import ApodeixiError

class KnowledgeBaseStore():
    '''
    Abstract class used to encapsulate the common services that a KnowledgeBase depends on from a "store" in which the
    KnowledgeBase can persist and retrieve manifests, postings, and any other persistent Apodeixi domain object.
    '''
    def __init__(self):
        return

    def supported_apis(self, parent_trace, manifest_handle=None, version = None):
        '''
        Abstract method. Returns a list of the posting APIs that this KnowledgeStore knows about.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'supported_apis' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def buildPostingHandle(self, parent_trace, excel_posting_path, sheet="Posting Label", excel_range="B2:C100"):
        '''
        Returns an Apodeixi Excel URL for the posting label embedded within the Excel spreadsheet that resides in the path provided.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'buildPostingHandle' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})


    def locatePostings(self, parent_trace, posting_api, filing_coordinates_filter=None, posting_version_filter=None):
        '''
        Returns a dictionary with the information of all postings that satisfy the criteria.

        The keys are FilingCoordinates instances, and the values are lists with the file name of each posting that lies
        at those coordinates.

        @param posting_api A string that identifies the type of posting represented by an Excel file. For example,
                            'milestone.modernization.a6i' is a recognized posting API and files that end with that suffix,
                            such as 'opus_milestone.modernization.a6i.xlsx' will be located by this method.
        @param filing_coordinates_filter A function that takes a FilingCoordinates instance as a parameter and returns a boolean. 
                            Any FilingCoordinates instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        @param posting_version_filter A function that takes a PostingVersion instance as a parameter and returns a boolean. 
                            Any PostingVersion instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'locatePostings' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})



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
        Returns a dict representing the unique manifest in the store that is identified by the `manifest handle`.
        If none exists, it returns None.

        @param manifest_handle A ManifestHandle instance that uniquely identifies the manifest we seek to retrieve.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'retrieveManifest' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def searchManifests(self, parent_trace, manifest_api, labels_filter=None, manifest_version_filter=None):
        '''
        Used to retrieve all manifests in the store for a given `manifest_api` provided they match the
        given conditions.

        Returns a dictionary where the keys are ManifestHandle instances and the values are dictionaries
        representing the data of the manifest corresponding to that ManifestHandle.

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



        
 
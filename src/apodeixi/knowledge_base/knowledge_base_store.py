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

    def discoverPostingURL(self, parent_trace, excel_posting_path, sheet="Posting Label"):
        '''
        Returns an Apodeixi Excel URL for the posting label embedded within the Excel spreadsheet that resides in the path provided.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'discoverPostingURL' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def locatePostings(self, parent_trace, posting_api, filing_coordinates_filter=None, posting_version_filter=None):
        '''
        @param posting_api A string that identifies the type of posting represented by an Excel file. For example,
                            'milestone.modernization.a6i' is a recognized posting API and files that end with that suffix,
                            such as 'opus_milestione.modernization.a6i.xlsx' will be located by this method.
        @param filing_coordinates_filter A function that takes a JourneysFilingCoordinates instance as a parameter and returns a boolean. 
                            Any JourneysFilingCoordinates instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        @param posting_version An instance of a posting version.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'locatePostings' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def persistManifest(self, parent_trace, manifest_dict, version = None):
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'persistManifest' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def retrieveManifest(self, parent_trace, manifest_handle, version = None):
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'retrieveManifest' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def supported_apis(self, parent_trace, manifest_handle=None, version = None):
        '''
        Abstract method. Returns a list of the posting APIs that this KnowledgeStore knows about.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'supported_apis' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def infer_posting_api(self, parent_trace, filename):
        '''
        '''
        for api in self.supported_apis(parent_trace=parent_trace, manifest_handle=None, version = None):
            if filename.endswith(api + ".xlsx"):
                return api
        # If we get this far then the filename does not correspond to a supported API. Raise an exception
        raise ApodeixiError(parent_trace, "Filename is not for a supported API",
                                            data = {    'filename':             filename,
                                                        'supported apis':       str(list(self.filing_rules.keys()))})

    def _getMatchingManifests(self, parent_trace, folder, manifest_handle, suffix):
        '''
        Returns two lists of the same length:

        * A list of dictionaries, one per manifest that matches the given manifest handle
        * A list of filenames, which is where each of those manifests was retrieved from
        '''
        matching_manifests = [] # List of dictionaries, one per manifest
        matching_filenames = [] # List of filename strings. Will be 1-1 lined up with matching_manifests

        # Two areas where to search for manifests: input area, and output area. First the input area
        for filename in self._getFilenames(parent_trace, folder, suffix):
            my_trace            = parent_trace.doing("Loading manifest from file",
                                                        data = {'filename':         filename,
                                                                'folder':           folder},
                                                        origination = {
                                                                'concrete class':   str(self.__class__.__name__), 
                                                                'signaled_from':    __file__})
            with open(folder + '/' + filename, 'r') as file:
                manifest_dict   = _yaml.load(file, Loader=_yaml.FullLoader)
            #manifest_dict       = _yaml.load(filename, Loader=_yaml.FullLoader)
            inferred_handle     = ManifestHandle.inferHandle(my_trace, manifest_dict)
            if inferred_handle == manifest_handle:
                matching_filenames.append(filename)
                matching_manifests.append(manifest_dict)

        return matching_manifests, matching_filenames

    def _getFilenames(self, parent_trace, folder, suffix):
        '''
        Helper method that looks at all yaml files in the given folder and returns their filenames
        '''
        return [filename for filename in _os.listdir(folder) if filename.endswith(suffix)]
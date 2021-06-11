import os                                               as _os

from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore
from apodeixi.util.a6i_error                            import ApodeixiError

class File_KnowledgeBaseStore(KnowledgeBaseStore):
    '''
    File-system-based implementation of the KnowledgeBaseStore. The entire knowledge base is held under a two root folders
    (one for postings and one for all derived data, including manifests)
    and follows a structure based on filing schemes of the KB_ProcessingRules.
    '''
    def __init__(self, postings_rootdir, derived_data_rootdir):
        super().__init__()

        self.postings_rootdir       = postings_rootdir
        self.derived_data_rootdir   = derived_data_rootdir

        self.filing_rules           = { #List of associations of posting API => FilingCoordinate class to use for such posting API
            'marathon-investment.modernization.ea':         JourneysFilingCoordinates,
            'milestone.modernization.ea':                   JourneysFilingCoordinates,

        }


    def locatePostings(self, parent_trace, posting_api, filing_coordinates_filter=None, posting_version_filter=None):
        '''
        @param posting_api A string that identifies the type of posting represented by an Excel file. For example,
                            'milestone.modernization.ea' is a recognized posting API and files that end with that suffix,
                            such as 'opus_milestione.modernization.ea.xlsx' will be located by this method.
        @param filing_coordinates_filter A function that takes a JourneysFilingCoordinates instance as a parameter and returns a boolean. 
                            Any JourneysFilingCoordinates instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        @param posting_version An instance of a posting version.
        '''
        def _tokenizePath(parent_trace, relative_path):
            '''
            Helper method suggested in  https://stackoverflow.com/questions/3167154/how-to-split-a-dos-path-into-its-components-in-python.
            It tokenizes relative paths to make it easier to construct FilingCoordinates from them
            For example, given a relative path like

                    \FY 22\LIQ\MTP

            it returns a list

                    ['FY 22', 'LIQ', 'MTP']
            '''
            folders         = []
            SPURIOUS_FOLDER = "\\" # This is added in Windows by some _os / split manipulations. If so, ignore it
            LIMIT           = 1000 # Maximum path length to handle. Precaution to avoid infinte loops
            idx             = 0
            path            = relative_path
            while idx < LIMIT: # This could have been "while True", but placed a limit out of caution
                path, folder = _os.path.split(path)

                if folder   != "": 
                    folders.append(folder)
                elif path   != "":
                    folders.append(path)
                    break
                idx         += 1

            folders.reverse()
            if folders[0]   == SPURIOUS_FOLDER:
                folders     = folders[1:]
            return folders


        my_trace                    = parent_trace.doing("Scanning existing filing coordinates")
        if True:
            scanned_coords              = []
            filing_class                = self.filing_rules[posting_api]
            for currentdir, dirs, files in _os.walk(self.postings_rootdir):
                for subdir in dirs:
                    loop_trace          = my_trace.doing("Tokenzing  path", data = {'currentdir': currentdir, 'subdir': subdir})
                    path_tokens         = _tokenizePath(parent_trace    = loop_trace,
                                                        relative_path   = _os.path.join(currentdir, subdir).split(self.postings_rootdir)[1]) 
                    filing_coords       = filing_class().build(parent_trace = loop_trace, path_tokens = path_tokens)
                    if filing_coords    != None:
                        if filing_coordinates_filter == None or filing_coordinates_filter(filing_coords): # Passed the filter, if any
                            scanned_coords.append(filing_coords)

        my_trace                    = parent_trace.doing("Collecting matching files for scanned coordinates")
        if True:
            result                  = {}
            for coords in scanned_coords:
                files               = self._findMatchingFiles(my_trace, coords, posting_api)
                result[coords]      = files

        return result

    def _findMatchingFiles(self, parent_trace, filing_coordinates, posting_api):
        path_tokens                 = filing_coordinates.path_tokens(parent_trace)
        full_path                   = self.postings_rootdir + "/" + "/".join(path_tokens)

        result                      = []
        for file in _os.listdir(full_path): # This picks up both directories and files
            d = _os.path.join(full_path, file)
            if not _os.path.isdir(d) and file.endswith(posting_api + ".xlsx"):
                result.append(file)
        return result
 

class FilingCoordinates():
    '''
    Abstract class used to identify how Excel postings are organized in a KnowledgeBaseStore.
    '''
    def __init__(self):
        return

    '''
    Implemented by concrete classes derived from this abstract class.

    This method "finishes up" the construction of a FilingCoordinates object, a construction that could not be completely carried out
    by the constructor since it is dependent on a path that may not necessarily lead to success. Determination of success or failure
    is up to each concrete class.

    @path_tokens: a list of strings that make up a "path" in a KnowledgeBaseStore, i.e., viewing a KnowledgeBaseStore as a logical tree,
                    these are the tokens of a path that goes from the root of such tree to some descendent node.
                    Concrete classes would know how to instantiate themselves from such a "path".
    '''
    def build(self, parent_trace, path_tokens):
        return  

    def path_tokens(self, parent_trace):
        '''
        Abstract method. Returns a list of strings, corresponding to the path tokens implicit by this FilingCoordinates instance.
        '''

    def to_dict(self, parent_trace):
        '''
        Abstract method. Returns a dictionary representation of self built only from scalars. Useful to display in test output files.
        '''

class JourneysFilingCoordinates(FilingCoordinates):
    '''
    Helper class to hold the properties that are used to organize Excel postings for Journeys domain in a KnowledgeBaseStore. An instance of this class
    has the filing information for one such Excel posting.
    '''
    def __init__(self):
        super().__init__()

        # These will be set later, by the build(-) method
        self.scoringCycle           = None
        self.product                = None
        self.scenario               = None
        return

    '''
    This method "finishes up" the construction of a JourneysFilingCoordinates object. IT successful, it returns 'self' fully built,
    and else it returns None.

    For construction to succeed, the JourneysFilingCoordinates expects the path to include exactly 3 tokens, corresponding to
    the scoringCycle, the product, and the scenario, in that order.

    @path_tokens: List of strings in a path from the root for a KnowledgeBase. Expected to be a list of string tokens [scoringCycle, product, scenario]. 
    '''
    def build(self, parent_trace, path_tokens):
        if type(path_tokens)        != list:
            raise ApodeixiError(parent_trace, "Invalid type for path_tokens: expected a list, instead received a " + str(type(path_tokens)))
        if len(path_tokens)         != 3:
            return None
        non_strings                 = [token for token in path_tokens if type(token) != str]
        if len(non_strings) > 0:
            return None

        self.scoringCycle           = path_tokens[0]
        self.product                = path_tokens[1]
        self.scenario               = path_tokens[2]
        return self

    def path_tokens(self, parent_trace):
        '''
        Returns a list of strings, corresponding to the path tokens implicit by this FilingCoordinates instance.
        '''
        if self.scoringCycle==None or self.product==None or self.scenario==None:
            raise ApodeixiError(parent_trace, "Can't provide path_tokens because JourneysFilingCoordinates is not fully built",
                                    data = {"scoringCycle": self.scoringCycle, "product" : self.product, "scenario" : self.scenario})

        return [self.scoringCycle, self.product, self.scenario ]

    def to_dict(self, parent_trace):
        '''
        Returns a dictionary representation of self built only from scalars. Useful to display in test output files.
        '''
        return {'scoringCycle': self.scoringCycle, 'product': self.product, 'scenario': self.scenario}

    def __format__(self, format_spec):
        msg     = "scoringCycle: " + self.scoringCycle + "; product: " + self.product + "; scenario: " + self.scenario

        return msg

    def __str__(self):
        msg     = str(self.scoringCycle) + "." + str(self.product) + "." + str(self.scenario)
        return msg


class PostingVersion():
    '''
    Helper class to represent different versions of the same posting
    '''
    def __init__(self, version_nb = 0):
        self.version_nb         = version_nb
        return
    
    def nextVersion(self, posting_version):
        return PostingVersion(posting_version.version_nb + 1)


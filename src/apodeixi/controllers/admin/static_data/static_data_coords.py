from apodeixi.util.a6i_error                        import ApodeixiError
from apodeixi.knowledge_base.filing_coordinates     import FilingCoordinates

class StaticDataFilingCoordinates(FilingCoordinates):
    '''
    Helper class to hold the properties that are used to organize Excel postings for Journeys domain in a KnowledgeBaseStore. 
    An instance of this class has the filing information for one such Excel posting.
    '''
    def __init__(self):
        super().__init__()

        return
    
    ADMIN                           = "admin"
    STATIC_DATA                     = "static-data"

    '''
    This method is mandated by abstract parent classes, and is intended to "finish up" the construction of a 
    StaticDataFilingCoordinates object. If successful, it returns 'self' fully built, and else it returns None.

    In this case the implemenation is straight forward, because there is nothing to build for the filing
    coords of static data. So this method just returns self.

    @path_tokens: List of strings in a path from the root for a KnowledgeBase. Expected to be the list of string tokens 
                    ["static_data"]. 
    '''
    def build(self, parent_trace, path_tokens):
        return self

    def infer_from_label(self, parent_trace, posting_label):
        '''
        In situations where the FilingCoordinates are not known until after the PostingLabel is constructed,
        this is used to infer the properties of the FilingCoords from the PostingLabel
        '''
        return self        

    def path_tokens(self, parent_trace):
        '''
        Returns a list of strings, corresponding to the path tokens implicit by this FilingCoordinates instance.
        '''
        ME                  = StaticDataFilingCoordinates
        return [ME.ADMIN, ME.STATIC_DATA]

    def to_dict(self, parent_trace):
        '''
        Returns a dictionary representation of self built only from scalars. Useful to display in test output files.
        '''
        return {}

    def __format__(self, format_spec):
        ME                  = StaticDataFilingCoordinates
        msg     = ''
        return msg

    def __str__(self):
        msg     = ""
        return msg

    def expected_tokens(self, parent_trace):
        '''
        Returns a string that describes (as a template) the kind of relative path that is required
        for this FilingCoordinates concrete class. Used in error messages to educate the caller on what should have been
        the right input to provide.
        '''
        ME                  = StaticDataFilingCoordinates
        return "['"+ ME.ADMIN + ", " + ME.STATIC_DATA + "]"

    def getTag(self, parent_trace):
        '''
        Returns a string, which is possibly empty. This string is a "tag" that would be appended to the
        filename of any generated form (i.e., any Excel spreadsheet created by Apodeixi that adheres
        to these filing coordinates object).

        The Excel filenames created would typically be <tag>.<posting API>.xlsx

        The purpose of such a "tag" is to improve usability by giving the end-user a bit more clarity on
        what the Excel file contains, expecially in situations where there are multiple Excel spreadsheets
        for the same posting API. 
        
        Example: for posting API 'big-rocks.journeys.a6i', there can be many Excel spreadsheets across all
        products, scenarios, etc. A product-based tag would help have filenames that differ per product so the
        user can more easily tell which is which, and also allows the user to simultaneously open more than one 
        in Excel since they have different filenames (Excel won't allow opening two files with the same
        filename, even if they are in different folders)
        '''
        return ''
import datetime                                         as _datetime
import apodeixi.knowledge_base.knowledge_base_util      as kb_util
from apodeixi.util.a6i_error                            import ApodeixiError

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
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'build' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__}) 

    def infer_from_label(self, parent_trace, posting_label):
        '''
        In situations where the FilingCoordinates are not known until after the PostingLabel is constructed,
        this is used to infer the properties of the FilingCoords from the PostingLabel
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'infer_from_label' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__}) 
    def path_tokens(self, parent_trace):
        '''
        Abstract method. Returns a list of strings, corresponding to the path tokens implicit by this FilingCoordinates instance.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'path_tokens' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__}) 
    def to_dict(self, parent_trace):
        '''
        Abstract method. Returns a dictionary representation of self built only from scalars. Useful to display in test output files.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'to_dict' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__}) 

    def expected_tokens(self, parent_trace):
        '''
        Abstract method. Returns a string that describes (as a template) the kind of relative path that is required
        for this FilingCoordinates concrete class. Used in error messages to educate the caller on what should have been
        the right input to provide.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'expected_tokens' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__}) 
    def getTag(self, parent_trace):
        '''
        Abstract method.

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
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'getTag' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

class JourneysFilingCoordinates(FilingCoordinates):
    '''
    Helper class to hold the properties that are used to organize Excel postings for Journeys domain in a KnowledgeBaseStore. 
    An instance of this class has the filing information for one such Excel posting.
    '''
    def __init__(self):
        super().__init__()

        # These will be set later, by the build(-) method
        self.scoringCycle           = None
        self.product                = None
        self.scenario               = None
        return
    JOURNEYS                        = "journeys"

    '''
    This method "finishes up" the construction of a JourneysFilingCoordinates object. If successful, it returns 'self' fully built,
    and else it returns None.

    For construction to succeed, the JourneysFilingCoordinates expects the path to include exactly 4 tokens, corresponding to
    the domain, the scoringCycle, the product, and the scenario, in that order.

    The domain is required to be identical to "journeys"

    @path_tokens: List of strings in a path from the root for a KnowledgeBase. Expected to be a list of string tokens 
                    ["journeys", scoringCycle, product, scenario]. 
    '''
    def build(self, parent_trace, path_tokens):
        ME                          = JourneysFilingCoordinates
        if type(path_tokens)        != list:
            raise ApodeixiError(parent_trace, "Invalid type for path_tokens: expected a list, instead received a " + str(type(path_tokens)))
        if len(path_tokens)         != 4:
            raise ApodeixiError(parent_trace, "Expected exactly 4 path tokens",
                                                data = {'path_tokens': str(path_tokens)})
        if path_tokens[0]           != ME.JOURNEYS:
            raise ApodeixiError(parent_trace, "The first path token is required to be '" + ME.JOURNEYS + "'",
                                                data = {'path_tokens': str(path_tokens)})

        non_strings                 = [token for token in path_tokens if type(token) != str]
        if len(non_strings) > 0:
            raise ApodeixiError(parent_trace, "Some tokens are not strings",
                                                data = {'non-string types found': str([type(x) for x in non_strings])})

        self.scoringCycle           = path_tokens[1]
        self.product                = path_tokens[2]
        self.scenario               = path_tokens[3]
        return self

    def infer_from_label(self, parent_trace, posting_label):
        '''
        In situations where the FilingCoordinates are not known until after the PostingLabel is constructed,
        this is used to infer the properties of the FilingCoords from the PostingLabel
        '''
        _PRODUCT                    = "product"
        _SCENARIO                   = "scenario"
        _SCORING_CYCLE              = "scoringCycle"

        self.scoringCycle           = posting_label._getField(parent_trace, _SCORING_CYCLE)
        self.product                = posting_label._getField(parent_trace, _PRODUCT)
        self.scenario               = posting_label._getField(parent_trace, _SCENARIO)
        return self        

    def path_tokens(self, parent_trace):
        '''
        Returns a list of strings, corresponding to the path tokens implicit by this FilingCoordinates instance.
        '''
        if self.scoringCycle==None or self.product==None or self.scenario==None:
            raise ApodeixiError(parent_trace, "Can't provide path_tokens because JourneysFilingCoordinates is not fully built",
                                    data = {"scoringCycle": self.scoringCycle, "product" : self.product, "scenario" : self.scenario})

        return [JourneysFilingCoordinates.JOURNEYS, self.scoringCycle, self.product, self.scenario ]

    def to_dict(self, parent_trace):
        '''
        Returns a dictionary representation of self built only from scalars. Useful to display in test output files.
        '''
        return {'scoringCycle': self.scoringCycle, 'product': self.product, 'scenario': self.scenario}

    def __format__(self, format_spec):
        msg     = "scoringCycle: "      + str(self.scoringCycle) \
                    + "; product: "     + str(self.product) \
                    + "; scenario: "    + str(self.scenario)

        return msg

    def __str__(self):
        msg     = str(self.scoringCycle) + "." + str(self.product) + "." + str(self.scenario)
        return msg

    def expected_tokens(self, parent_trace):
        '''
        Returns a string that describes (as a template) the kind of relative path that is required
        for this FilingCoordinates concrete class. Used in error messages to educate the caller on what should have been
        the right input to provide.
        '''
        return "['"+ JourneysFilingCoordinates.JOURNEYS + "', <scoringCycle>, <product>, <scenario>]"

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
        return self.product

class InitiativesFilingCoordinates(FilingCoordinates):
    '''
    Helper class to hold the properties that are used to organize Excel postings for Initiatives domain in a KnowledgeBaseStore. 
    An instance of this class has the filing information for one such Excel posting.
    '''
    def __init__(self):
        super().__init__()

        # These will be set later, by the build(-) method
        self.scoringCycle           = None
        self.workstream_UID         = None
        self.scenario               = None
        return

    INITIATIVES                     = "initiatives"

    '''
    This method "finishes up" the construction of a InitiativesFilingCoordinates object. If successful, it returns 'self' fully built,
    and else it returns None.

    For construction to succeed, the InitiativesFilingCoordinates expects the path to include exactly 3 or 4 tokens.
    The first 3 tokens must correspond to
    the domain, the scoringCycle, the workstream_UID, in that order. The optional 3rd token is for the scenario, if any.

    The domain is required to be identical to "initiatives"

    @path_tokens: List of strings in a path from the root for a KnowledgeBase. Expected to be a list of string tokens 
    ["initiatives", scoringCycle, workstream_UID] or ["initiatives", scoringCycle, workstream_UID, scenario]. 
    '''
    def build(self, parent_trace, path_tokens):
        if type(path_tokens)        != list:
            raise ApodeixiError(parent_trace, "Invalid type for path_tokens: expected a list, instead received a " + str(type(path_tokens)))
        if len(path_tokens)         != 3 and len(path_tokens)         != 4:
            return None
        if path_tokens[0]           != InitiativesFilingCoordinates.INITIATIVES:
            return None

        non_strings                 = [token for token in path_tokens if type(token) != str]
        if len(non_strings) > 0:
            return None

        self.scoringCycle           = path_tokens[1]
        self.workstream_UID         = path_tokens[2]
        if len(path_tokens) == 4:
            self.scenario           = path_tokens[3]
        else:
            self.scenario           = None

        return self

    def infer_from_label(self, parent_trace, posting_label):
        '''
        In situations where the FilingCoordinates are not known until after the PostingLabel is constructed,
        this is used to infer the properties of the FilingCoords from the PostingLabel
        '''
        _WORKSTREAM_UID             = "workstreamUID"
        _SCENARIO                   = "scenario"
        _SCORING_CYCLE              = "scoringCycle"

        self.scoringCycle           = posting_label._getField(parent_trace, _SCORING_CYCLE)
        self.workstream_UID         = posting_label._getField(parent_trace, _WORKSTREAM_UID)
        scenario               = posting_label._getField(parent_trace, _SCENARIO)

        if len(scenario.strip(' ')) == 0:
            self.scenario           = None
        else:
            self.scenario           = scenario
        
        return self 

    def path_tokens(self, parent_trace):
        '''
        Returns a list of strings, corresponding to the path tokens implicit by this FilingCoordinates instance.
        '''
        if self.scoringCycle==None or self.workstream_UID==None:
            raise ApodeixiError(parent_trace, "Can't provide path_tokens because InitiativesFilingCoordinates is not fully built",
                                    data = {    "scoringCycle":     self.scoringCycle, 
                                                "workstream_UID" :  self.workstream_UID, 
                                                "scenario" :        self.scenario})

        if self.scenario != None:
            result          = [InitiativesFilingCoordinates.INITIATIVES, self.scoringCycle, self.workstream_UID, self.scenario]
        else:
            result          = [InitiativesFilingCoordinates.INITIATIVES, self.scoringCycle, self.workstream_UID]

        return result

    def to_dict(self, parent_trace):
        '''
        Returns a dictionary representation of self built only from scalars. Useful to display in test output files.
        '''
        return {'scoringCycle': self.scoringCycle, 'workstream_UID': self.workstream_UID, 'scenario': self.scenario}

    def __format__(self, format_spec):
        msg     = "scoringCycle: "          + str(self.scoringCycle) \
                    + "; workstream_UID: "  + str(self.workstream_UID) \
                    + "; scenario: "        + str(self.scenario)

        return msg

    def __str__(self):
        msg     = str(self.scoringCycle) + "." + str(self.workstream_UID) + "." + str(self.scenario)
        return msg

    def expected_tokens(self, parent_trace):
        '''
        Returns a string that describes (as a template) the kind of relative path that is required
        for this FilingCoordinates concrete class. Used in error messages to educate the caller on what should have been
        the right input to provide.
        '''
        output_txt = "Either \n\t['"+ InitiativesFilingCoordinates.INITIATIVES + "', <scoringCycle>, <workstream_UID>]"

        output_txt += "\nor \n\t['"+ InitiativesFilingCoordinates.INITIATIVES + "', <scoringCycle>, <workstream_UID>, <scenario>]"

        return output_txt

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
        return self.workstream_UID

class TBD_FilingCoordinates(FilingCoordinates):
    '''
    FilingCoordinates class used temporarily in situations where the real FilingCoordinates class to use
    is meant to be inferred from the data in a PostingLabel (i.e., it can only be set *after* reading
    a PostingLabel, not before, so before reading the PostingLabel this "TBD" coordinates are used
    as a place holder)
    '''
    def __init__(self, fullpath, posting_api, path_mask):
        super().__init__()

        self._fullpath              = fullpath
        self._posting_api           = posting_api
        self._path_mask             = path_mask

        # This will be set later, by the inferFilingCoords methods
        self._inferred_coords       = None
        return

    def getFullPath(self):
        return self._fullpath

    def inferred_coords(self, parent_trace):
        '''
        Returns the inferred coordinates, if they have already been inferred. Otherwise raises an ApodeixiError
        '''
        if self._inferred_coords != None:
            return self._inferred_coords
        else:
            raise ApodeixiError(parent_trace, "Coordinates have not yet been inferred - they are still TBD."
                                                + " Possibly this is being called too early in the processing?",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__}) 

    def inferFilingCoords(self, parent_trace, posting_label):
        '''
        After a PostingLabel is read with self as the posting handle, we can read from the Posting Label
        what the "real" FilingCoords should have been, and the caller can use this method to get
        such "inferred" FilingCoordinates and replace self (a "TBD" FilingCoords) with the "real" one
        '''
        my_trace                        = parent_trace.doing("Looking up filing class for given posting API",
                                                                data = {'posting_api': self._posting_api})               
        filing_class                    = posting_label.controller.store.getFilingClass(parent_trace, self._posting_api)
        if filing_class == None:
            raise ApodeixiError(my_trace, "Can't build filing coordinates from a null filing class")
        my_trace                        = parent_trace.doing("Validating that posting is in the right folder structure "
                                                                + "within the Knowledge Base")
        filing_coords                   = filing_class().infer_from_label(  parent_trace    = my_trace, 
                                                                            posting_label   = posting_label)
        self._inferred_coords           = filing_coords

    def path_tokens(self, parent_trace):
        '''
        Returns a list of strings, corresponding to the path tokens implicit by this FilingCoordinates instance.
        '''
        if self._inferred_coords != None:
            return self._inferred_coords.path_tokens(parent_trace)
        else:
            raise ApodeixiError(parent_trace, "Path tokens are not available because coordinate haven't yet been inferred",
                                            origination = {'concrete class': str(self.__class__.__name__), 
                                                            'signaled_from': __file__}) 

    def __str__(self):
        path            = str(self._fullpath)
        if self._path_mask != None:
            path        = self._path_mask(path)
        msg             = "TBD - Submitted from: " + str(path)
        return msg

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
        if self._inferred_coords != None:
            return self._inferred_coords.getTag(parent_trace)
        else:
            raise ApodeixiError(parent_trace, "Filename tag is not available because coordinate haven't yet been inferred",
                                            origination = {'concrete class': str(self.__class__.__name__), 
                                                            'signaled_from': __file__}) 

class ArchiveFilingCoordinates(FilingCoordinates):
    '''
    Helper class to hold the properties that are used to organize archived Excel postings in a KnowledgeBaseStore. 

    It wraps the original FilingCoordinates object that was used to post the Excel posting, adding additional
    coordinates. In effect, this means archived filing structures are a sub-structure of the original 
    posting structure. Additionally, the archival coordinates are unique to a posting event. For example,
    repeately posting the same Excel file would result in different archived coordinates even if the
    original posting's coordinates are the same.

    In "file system" language, the equivalent way to say the above is: the archived file resides in a folder
    dedicated to the posting event as a subfolder of some subfolder of the folder containing the original posting.

    @param posting_label_handle A PostingLabelHandle object that uniquely identifies the submitted posting that 
                    we are supposed to archive. 
    '''
    def __init__(self, parent_trace, posting_label_handle, use_timestamps):
        super().__init__()
        
        if posting_label_handle == None or type(posting_label_handle) != kb_util.PostingLabelHandle:
            raise ApodeixiError(parent_trace, "Need the submitted posting's PostingLabelHandle in order to archive" 
                                                + " posting, but instead got a '" + str(type(posting_label_handle)) + "'")
        original_coords                  = posting_label_handle.filing_coords
        
        if original_coords == None or not issubclass(type(original_coords), FilingCoordinates):
            raise ApodeixiError(parent_trace, "Need the submitted posting's FilingCoordinates in order to archive" 
                                                + " posting, but instead got a '" + str(type(original_coords)) + "'")

        if type(original_coords) == TBD_FilingCoordinates:
            original_coords         = original_coords.inferred_coords(parent_trace)

        self.original_coords        = original_coords

        dt                          = _datetime.datetime.today()
        # This will look like '210703.102746 Posting' for a posting done on the 3rd of July of 2021 at 10:27 am (and 46 sec)
        # Intention is for this folder name to be unique for this posting event, even if other postings (for the same
        # or different Excel files) happen the same day with the same filing coords
        if use_timestamps:
            self.archive_folder         = dt.strftime("%y%m%d.%H%M%S") + " Posting"
        else:
            self.archive_folder         = "(Timestamp omitted)" + " Posting"
        return

    ARCHIVED_POSTINGS               = "_ARCHIVE"


    def path_tokens(self, parent_trace):
        '''
        Returns a list of strings, corresponding to the path tokens implicit by this FilingCoordinates instance.
        '''
        ME                          = ArchiveFilingCoordinates
        original_tokens             = self.original_coords.path_tokens(parent_trace)
        archival_tokens             = original_tokens.copy()
        archival_tokens.extend([ME.ARCHIVED_POSTINGS, self.archive_folder])

        return archival_tokens

    def to_dict(self, parent_trace):
        '''
        Returns a dictionary representation of self built only from scalars. Useful to display in test output files.
        '''
        original_dict                       = self.original_coords.to_dict(parent_trace)
        archival_dict                       = original_dict.copy()
        archival_dict["archive_folder"]     = self.archive_folder

        return archival_dict

    def __format__(self, format_spec):
        msg     = self.original_coords.__format(format_spec)
        msg     += "archive_folder: "      + str(self.archive_folder) 

        return msg

    def __str__(self):
        msg     = self.original_coords.__str__()
        msg     += "." + ArchiveFilingCoordinates.ARCHIVED_POSTINGS + "." + str(self.archive_folder)
        return msg


class LogFilingCoordinates(FilingCoordinates):
    '''
    Helper class to hold the properties that are used to organize archived Excel postings in a KnowledgeBaseStore. 

    It wraps the original FilingCoordinates object that was used to post the Excel posting, adding additional
    coordinates. In effect, this means log filing structures are a sub-structure of the original 
    posting structure. Additionally, the log coordinates are unique to an event. For example,
    repeately posting the same Excel file would result in different archived coordinates even if the
    original posting's coordinates are the same.

    In "file system" language, the equivalent way to say the above is: the log file resides in a folder
    dedicated to the event as a subfolder of some subfolder of the folder where the original event's posting
    is to reside.

    @param form_request A FormRequest object that uniquely identifies the submitted posting that 
                    we are supposed to archive. 
    '''
    def __init__(self, parent_trace, form_request, use_timestamps):
        super().__init__()
        
        if form_request == None or type(form_request) != kb_util.FormRequest:
            raise ApodeixiError(parent_trace, "Need the submitted posting's FormRequest in order to archive" 
                                                + " posting, but instead got a '" + str(type(form_request)) + "'")
        original_coords                  = form_request.getFilingCoords(parent_trace)
        
        if original_coords == None or not issubclass(type(original_coords), FilingCoordinates):
            raise ApodeixiError(parent_trace, "Need the submitted posting's FilingCoordinates in order to archive" 
                                                + " posting, but instead got a '" + str(type(original_coords)) + "'")

        if type(original_coords) == TBD_FilingCoordinates:
            original_coords         = original_coords.inferred_coords(parent_trace)

        self.original_coords        = original_coords

        dt                          = _datetime.datetime.today()
        # This will look like '210703.102746 Posting' for a posting done on the 3rd of July of 2021 at 10:27 am (and 46 sec)
        # Intention is for this folder name to be unique for this posting event, even if other postings (for the same
        # or different Excel files) happen the same day with the same filing coords
        if use_timestamps:
            self.archive_folder         = dt.strftime("%y%m%d.%H%M%S") + " Posting"
        else:
            self.archive_folder         = "(Timestamp omitted)" + " Posting"
        return

    ARCHIVED_POSTINGS               = "_ARCHIVE"


    def path_tokens(self, parent_trace):
        '''
        Returns a list of strings, corresponding to the path tokens implicit by this FilingCoordinates instance.
        '''
        ME                          = LogFilingCoordinates
        original_tokens             = self.original_coords.path_tokens(parent_trace)
        archival_tokens             = original_tokens.copy()
        archival_tokens.extend([ME.ARCHIVED_POSTINGS, self.archive_folder])

        return archival_tokens

    def to_dict(self, parent_trace):
        '''
        Returns a dictionary representation of self built only from scalars. Useful to display in test output files.
        '''
        original_dict                       = self.original_coords.to_dict(parent_trace)
        archival_dict                       = original_dict.copy()
        archival_dict["archive_folder"]     = self.archive_folder

        return archival_dict

    def __format__(self, format_spec):
        msg     = self.original_coords.__format(format_spec)
        msg     += "archive_folder: "      + str(self.archive_folder) 

        return msg

    def __str__(self):
        msg     = self.original_coords.__str__()
        msg     += "." + LogFilingCoordinates.ARCHIVED_POSTINGS + "." + str(self.archive_folder)
        return msg
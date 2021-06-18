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
        if type(path_tokens)        != list:
            raise ApodeixiError(parent_trace, "Invalid type for path_tokens: expected a list, instead received a " + str(type(path_tokens)))
        if len(path_tokens)         != 4:
            return None
        if path_tokens[0]           != JourneysFilingCoordinates.JOURNEYS:
            return None

        non_strings                 = [token for token in path_tokens if type(token) != str]
        if len(non_strings) > 0:
            return None

        self.scoringCycle           = path_tokens[1]
        self.product                = path_tokens[2]
        self.scenario               = path_tokens[3]
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
            self.scenarion          = None

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
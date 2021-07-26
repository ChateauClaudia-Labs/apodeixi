import re                                       as _re

from apodeixi.util.a6i_error                    import ApodeixiError
from apodeixi.xli.interval                      import Interval

class UID_Store:
    '''
    Stores UIDs like 'P12.AC3.E45', and is able to generate the next UID for a given prefix.
    For example, if the store contains P12.AC3.E45 but not P12.AC3.E46, then the next UID for prefix
    P12.AC3.E would be P12.AC3.E46. If there is no pre-existing UID for that prefix, then the next prefix
    would be P12.AC3.E1
    
    '''
    class _TokenTree:
        '''
        Represents a tree for which the top level of nodes correspond to tokens, 
        e.g., AV1, AV2, AV3, ...FRA1, FRA2, ..
        So for each prefix like 'AV' or 'FRA' there is a unique set of integers used in the tokens for
        that prefix.
        The children of such top nodes are other _TokenTree objects.

        To avoid accidental infinite loops, a _TokenTree has a maximum height of 100 levels.
        '''
        def __init__(self, parent_trace, level):
            
            if level > UID_Store._TokenTree.MAX_LEVELS:
                raise ApodeixiError(parent_trace, 'Illegal attempt to create a _TokenTree at a level exceeding ' 
                                 + str( UID_Store._TokenTree.MAX_LEVELS))
            self.level     = level
            
            # Keys are acronyms like 'P', and values are arrays of non-negative integers like [1, 2, 3]
            # indicating that this _TokenTree contains 'P1', 'P2', and P3
            self.vals      = {} 
            
            # A dictionary where the key is a string like 'P12' where 12 belongs to array self.vals['P']
            # Value for that key 'P12' is another _TokenTree
            self.children  = {} 
            
            
        MAX_LEVELS = 100
        
        def addToken(self, parent_trace, token):
            '''
            Given a string `token` such as P4, it adds it to this tree
            '''
            acronym, nb     = self.parseToken(parent_trace, token) #TODO Finish this up
            if not acronym in self.vals.keys():
                self.vals[acronym] = []
            nb_list         = self.vals[acronym]
            if not nb in nb_list:
                nb_list.append(nb)
            if not token in self.children.keys():
                self.children[token] = UID_Store._TokenTree(parent_trace, self.level + 1)           
        
        def _generateHere(self, parent_trace, acronym):
            if acronym not in self.vals.keys():
                self.vals[acronym] = []
            
            used_numbers           = self.vals[acronym]
            
            if len(used_numbers) ==0:
                nextVal            = 1 # Start at 1, not 0. Though parent might have 0's
            else:
                nextVal            = max(used_numbers) + 1
                
            used_numbers.append(nextVal)
            uid                    = acronym + str(nextVal)
            self.children[uid]     = UID_Store._TokenTree(parent_trace = parent_trace, level = self.level + 1)
            return uid
    
        def generateNextUID(self, parent_trace, branch, acronym):
            '''
            @param branch A list of pairs that specify a branch in the _TokenTree. For example:
                          [['P', 12], ['AC', 3], ['E', 45]]. If the acronym is 'W', it will add a node
                          [['W', 5]], say, if P12.AC3.E45.W1,2,3,4 already exist.
                          Returns two uids: a full UID P12.AC3.E45.W5 and the leaf UID W5
            '''                
            # Validate acronym is valid
            REGEX         = '^([a-zA-Z]+)$'
            m             = _re.match(REGEX, acronym)
            if m == None or len(m.groups()) != 1:
                raise ApodeixiError(parent_trace, "Invalid acronym='" + acronym + "': expected something like 'P' or 'AV'.  "
                                + "Level=" + str(self.level))                
            
            if len(branch)==0:
                # We hit bottom
                leaf_uid           = self._generateHere(parent_trace, acronym)
                full_uid           = leaf_uid
                
            else:
                head               = branch[0]
                tail               = branch[1:]
                child              = self._findChild(parent_trace, head)
                tail_uid, leaf_uid = child.generateNextUID(parent_trace, tail, acronym)
                full_uid           = head + '.' + tail_uid
                
            return full_uid, leaf_uid
                
        def _findChild(self, parent_trace, head):
            '''
            @param head A string like 'PR56'. If it exists in this _TokenTree as a top node return it.
                        Else raises an error.
            '''
            acronym, val  = self.parseToken(parent_trace, head)

            # Some of these checks are theoretically duplicate if the inner state of this object
            # is consistent as in theory it should be. But being paranoid, we do duplicate
            # checks since that might also catch bugs with inconsistent state
            if acronym not in self.vals.keys():
                raise ApodeixiError(parent_trace, 'Acronym ' + acronym + ' corresponds to no valid child. Level=' 
                                 + str(self.level) + ". Happened while doing _findChild(" + head + ')')
            if val not in self.vals[acronym]:
                raise ApodeixiError(parent_trace, 'Value ' + str(val) + ' corresponds to no valid child. Level=' 
                                 + str(self.level) + ". Happened while doing _findChild(" + head + ')',
                                 data = {'acronym': acronym, 'level': str(self.level),
                                            'self.vals[' + acronym + ']': self.vals[acronym]})
            if head not in self.children.keys():
                raise ApodeixiError(parent_trace, 'Token ' + head + ' corresponds to no valid child. Level=' 
                                 + str(self.level) + ". Happened while doing _findChild(" + head + ')')

            # We got past the checks, so this should not crash
            return self.children[head]
            
        def display(self, parent_trace):
            '''
            Used for debugging, to return a dictionary representation of the tree
            '''
            result_dict = {}
            for uid in self.children.keys():
                child   = self.children[uid]
                result_dict[uid] = child.display()
            return result_dict
        
        def parseToken(self, parent_trace, token):
            '''
            Given a token like 'PR34', it returns the acronym 'PR' and the value 34
            '''
            REGEX         = '^([a-zA-Z]+)([0-9]+)$'
            m             = _re.match(REGEX, token)
            if m == None or len(m.groups())!= 2:
                raise ApodeixiError(parent_trace, "Invalid token='" + token + "': expected something like 'P3' or 'AV45'.  "
                                + "Level=" + str(self.level))
            acronym       = m.group(1)
            val           = int(m.group(2))
            return acronym, val
        
    
    def __init__(self, parent_trace):
        self.tree     = UID_Store._TokenTree(parent_trace, level=0)
        return
    
    def generateUID(self, parent_trace, parent_UID, acronym):
        branch        = self._tokenize(parent_trace, parent_UID)
        return self.tree.generateNextUID(parent_trace, branch, acronym)
    
    def initializeFromManifest(self, parent_trace, manifest_dict):
        '''
        Given a dictionary `manifest_dict`, it recursively searches in the manifest for any node called
        "UID", expecting a value like "JTBD1.C1.F1.S1". It then tokenizes it like [JTBD1, C1, F1, S1]
        and adds it as a branch of this token tree.

        @param manifest_dict A dict object representing a manifest
        '''
        for key in manifest_dict.keys():
            val             = manifest_dict[key]
            if key == Interval.UID:
                self.add_known_uid(parent_trace, val)
            elif type(val) == dict: #Recursive call
                self.initializeFromManifest(parent_trace, val)

    def add_known_uid(self, parent_trace, uid):
        '''
        Records that the `uid` is already used, and therefore no generated UID should be like it.

        Use with caution: normally this method should not be used, since normally a user's posting
        should normally include a UID that was generated previously during processing of an earlier posting
        that gave rise to a manifest being persisted. That manifest would have the UID and normally if the
        user makes an update to the posting, that update controller logic would call the method
        `initializeFromManifest` on the UID Store to seed the UID Store with such previously generated
        UIDs.

        So it rare when we need to *forcefully* tell the UID store that a UID is already reserved,
        and mainly in internal Apodeix low-level code, not by application code.

        @param uid A string such as "JTBD1.C1.F1.S1"
        '''
        self._mark_uid_as_used(parent_trace, uid, self.tree)

    def _mark_uid_as_used(self, parent_trace, uid, token_tree):
        '''
        Recursive implementation of `add_known_uid`
        '''
        tokens              = self._tokenize(parent_trace, uid)
        if len(tokens) == 0:
            return # Nothing to do

        head                = tokens[0]
        tail                = tokens[1:]
        token_tree.addToken(parent_trace, head)
        if len(tail) > 0: #recurse
            subtree         = token_tree.children[head]
            sub_uid         = '.'.join(tail)
            self._mark_uid_as_used(self, parent_trace, sub_uid, subtree)


            



    def _tokenize(self, parent_trace, uid):
        if uid==None:
            return []
        tokens        = uid.split('.')
        # Something like P3 pr AV456. 
        REGEX         = '^[a-zA-Z]+[0-9]+$' 
        for t in tokens:
            m         = _re.match(REGEX, t)
            if m == None:
                raise ApodeixiError(parent_trace, "Invalid uid='" + uid + "': expected something like P3 or AV45.P1.E12")
        return tokens

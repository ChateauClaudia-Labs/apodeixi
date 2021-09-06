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

        @level an int, recording how many levels this _TokenTree is from the root, since a _TokenTree
                        might be a sub-tree of a larget _TokenTree.
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
            acronym, nb     = UID_Utils().parseToken(parent_trace, token) 
            if not acronym in self.vals.keys():
                self.vals[acronym] = []
            nb_list         = self.vals[acronym]
            if not nb in nb_list:
                nb_list.append(nb)
            if not token in self.children.keys():
                self.children[token] = UID_Store._TokenTree(parent_trace, self.level + 1)           
        
        def genAcronymList(self, parent_trace):
            '''
            Many _TokenTree objects have a unique acronym at each level of the tree.
            If so, this returns that list, as a list of strings ordered from the top of the tree
            to the leaves.

            In situations where there are multiple acronyms at a given level, it returns the a random
            "longest" path of acronyms through the tree
            '''
            result                          = []
            if len(self.vals.keys()) > 1:
                raise ApodeixiError(parent_trace, "Can't figure out acronyms for a UID Token Tree because there "
                                                     + "is not a unique acronyms at the top of this tree",
                                                     data = {"acronyms": str(list(self.vals.keys()))})
            elif len(self.vals.keys()) == 0:
                return []

            top_level_acronym               = next(iter(self.vals))
            result.append(top_level_acronym)

            # idx_list is something like [10, 11, 2, 3, 4] if top_level_acronym is BR and UIDs are
            # BR10, BR11, BR2, BR3, and BR4
            idx_list                        = self.vals[top_level_acronym]

            # We will loop through the children and select the child for which its sublist of acronyms is the longest
            # That way we don't inadvertently miss out on some acronyms, as we used to in a prior buggy implementation
            # that chose the "first" path, not the "longest" path
            longest_sub_result              = []
            for idx in idx_list:
                child_uid                   = top_level_acronym + str(idx)
                loop_trace                  = parent_trace.doing("Getting acronym list below uid '" + child_uid + "'")
                child                       = self.children[child_uid]
                candidate_sub_result        = child.genAcronymList(loop_trace)
                if len(candidate_sub_result) > len(longest_sub_result):
                    longest_sub_result      = candidate_sub_result

            result.extend(longest_sub_result)

            return result


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
            acronym, val  = UID_Utils().parseToken(parent_trace, head)

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
           
    def __init__(self, parent_trace):
        self.tree     = UID_Store._TokenTree(parent_trace, level=0)
        return
    
    def generateUID(self, parent_trace, parent_UID, acronym):
        branch        = UID_Utils()._tokenize(parent_trace, parent_UID)
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

    def add_known_uid(self, parent_trace, uid, last_acronym=None):
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
        @param last_acronym A string for the entity of the leaf UID. In the example "JTBD1.C1.F1.S1",
                    perhaps "S" stands for "Story", and "S" would be the last_acronym passed.
                    The reason for needing this parameter is that for usability reasons the user may
                    abbreviate the UID to something like "1.1.1.1", and the system needs to infer 
                    the acronyms. The UID Store would already now about the ancestors (JTBD, C, F) but
                    might not yet know about the leaf UID acronym ("S"), which is therefore passed
                    by the caller (the caller typically is the BreakdownTree class that would know
                    how to get such "last acronym")
        '''
        # Path of the acronyms the store knows about so far. May not yet include the entity, if we
        # are adding a uid for that entity for the first time
        known_acronym_list  = self.tree.genAcronymList(parent_trace) 

        if last_acronym != None and not last_acronym in known_acronym_list:
            known_acronym_list.append(last_acronym)
        
        self._mark_uid_as_used(parent_trace, uid, known_acronym_list, self.tree)

    def _mark_uid_as_used(self, parent_trace, uid, acronym_list, token_tree):
        '''
        Recursive implementation of `add_known_uid`
        '''
        tokens              = UID_Utils()._tokenize(parent_trace, uid, acronym_list)
        if len(tokens) == 0:
            return # Nothing to do

        head                = tokens[0]
        tail                = tokens[1:]
        token_tree.addToken(parent_trace, head)
        if len(tail) > 0: #recurse
            subtree         = token_tree.children[head]
            sub_uid         = '.'.join(tail)
            self._mark_uid_as_used(parent_trace, sub_uid, acronym_list[1:], subtree)
       
    def remember_acronym(self, parent_trace, last_acronym):
        '''
        Used in cases when the caller wants this store to remember one more acronym
                    at the end of its list of known acronyms

        @last_acronym Acronym to remember. If set to None, it is ignored. 
        '''
        # Path of the acronyms the store knows about so far. May not yet include the entity, if we
        # are adding a uid for that entity for the first time
        known_acronym_list  = self.tree.genAcronymList(parent_trace) 

        if last_acronym != None and not last_acronym in known_acronym_list:
            known_acronym_list.append(last_acronym)



class UID_Utils():
    '''
    '''
    def __init__(self):
        return

    def parseToken(self, parent_trace, token):
        '''
        Given a token like 'PR34', it returns the acronym 'PR' and the value 34
        '''
        REGEX         = '^([a-zA-Z]+)([0-9]+)$'
        m             = _re.match(REGEX, token)
        if m == None or len(m.groups())!= 2:
            raise ApodeixiError(parent_trace, "Invalid token='" + token + "': expected something like 'P3' or 'AV45'.  ")
        acronym       = m.group(1)
        val           = int(m.group(2))
        return acronym, val

    def abbreviate_uid(self, parent_trace, uid, acronym_schema):
        '''
        Abbreviates the uid by stripping all acronyms except the first, and returns it.

        For example, a uid like "P4.C3.AC2" is abbreviated to "P4.3.2".

        It handles cases where an entity is skipped. For example, if the acronym schema is logically
        like 
                [A, I, SI, AS]

        but the 3rd entity is "skipped" so that the caller submits a `uid` with just 3 tokens like

                A4.I2.AS1

        this method will detect that and return an abbreviated UID with 4 tokens, not 3, putting a 0
        for the gap:

                A4.2.0.1,   as oppose to A4.2.1, which would be "buggy" since the last token is for the wrong entity.
        '''
        tokens                      = self._tokenize(parent_trace, uid=uid, acronym_list=None)
        if len(tokens)<= 1:
            return uid

        # GOTCHA: 
        # We very deliberately keep the first acronym, and only abbreviate the rest. For example, we
        # don't want to abbreviate BR7.B10 as 7.10. Instead the correct abbreviation should be BR7.10
        # This is to avoid bugs, because if we abbreviated to 7.10 then the various conversions across Excel and
        # Pandas will treat it as a number, equal to 7.1. This will cause two UIDs to collide (BR7.B1 and BR7.B10)
        # and one will overwrite the contents of the other, losing data from a manifest.
        abbreviated_uid_tokens          = []                 
        abbreviated_uid_tokens.append(tokens[0])

        prior_acronym                   = self.parseToken(parent_trace, tokens[0])[0]
        acronym_list                    = [acronyminfo.acronym for acronyminfo in acronym_schema.acronym_infos()]
        for idx in range(1, len(tokens)):
            token                       = tokens[idx]
            acronym, val                = self.parseToken(parent_trace, token)
            if not acronym in acronym_list:
                raise ApodeixiError(parent_trace, "Can't abbreviate an invalid UID that has an acronym not in the schema",
                                                data = {"uid":                  str(uid),
                                                        "invalid acronym":      str(acronym),
                                                        "schema":               str(acronym_schema)})
            acronym_schema_idx          = acronym_list.index(acronym)
            prior_acronym_schema_idx    = acronym_list.index(prior_acronym) 
            if prior_acronym_schema_idx != len(abbreviated_uid_tokens) -1:
                raise ApodeixiError(parent_trace, "Algorithm for abbreviating UID is flawed - please report a bug",
                                                    data = {"uid":              str(uid),
                                                            "schema":           str(acronym_schema),
                                                            "problem":          "Length of abbreviated uid does not match expectation",
                                                            "abbreviated UID tokens":  str(abbreviated_uid_tokens),
                                                            "acronym":          str(acronym),
                                                            "prior acronym":    str(prior_acronym),
                                                            "prior_acronym_schema_idx": str(prior_acronym_schema_idx)})
            if acronym_schema_idx <= prior_acronym_schema_idx:
                raise ApodeixiError(parent_trace, "Can't abbreviate an invalid UID because two acronyms are in the wrong "
                                                    + "order: '" + str(acronym) + "' appears after '" + str(prior_acronym) + "' "
                                                    + "but in the schema that order is reversed",
                                                    data = {"uid":                      str(uid),
                                                            "schema":                   str(acronym_schema)})
            if idx > acronym_schema_idx:
                raise ApodeixiError(parent_trace, "Can't abbreviate an invalid UID because its acronym '" + str(acronym) + "' "
                                                    + "is not at a legal position in the schema",
                                                    data = {"uid":                      str(uid),
                                                            "max position allowed":     str(acronym_schema_idx),
                                                            "acronym position":         str(idx),
                                                            "schema":                   str(acronym_schema)})
            
            # Pad with 0's for any acronyms that might have been skipped
            for gap_idx in range(prior_acronym_schema_idx+1, acronym_schema_idx):
                abbreviated_uid_tokens.append("0")

            # Now add this acronym's value
            abbreviated_uid_tokens.append(str(val))

            # Initialize for next cycle of loop
            prior_acronym        = acronym
        
        abbreviated_uid         = ".".join(abbreviated_uid_tokens)
        return abbreviated_uid

    def unabbreviate_uid(self, parent_trace, uid, acronym_schema):
        '''
        Returns a possibly modified UID. For example, a UID like "P4.3" might be replaced by "P4.C3".
        In other words, if the uid is one of those "abbreviated UIDs" that lacks acronyms (they arise
        for usability reasons in user-provided UIDs), attempt to infer the acronyms that are missing and
        return the full UID ("P4.C3" in the example)

        Potentially, if a UID skipped an entity, it relies on 0 digit to determine that. For example, if the
        entity schema is logically like  [A, I, SI, AS], if a full UID is A4.I3.AS2, then the SI entity
        was skipped.
        In that case, the correct abbreviated UID should be A4.3.0.2, instead of A4.3.2.

        That makes it possible for this method to line up 1-1 the tokens of the abbreviated UID to the
        acronym schema, to infer the correct unabbreviated UID. In the example, that would be inferring that
        A4.3.0.2 corresponds to A4.I3.AS2. Without the "0" digit, if we had A4.3.2, we would have 
        incorrectly inferred A4.I3.I2

        @acronym_schema Used to determine what acronyms to use in the full UID that is returned.
        '''
        # Path of the acronyms the store knows about so far. May not yet include the entity, if we
        # are adding a uid for that entity for the first time

        acronym_list        = [acronyminfo.acronym for acronyminfo in acronym_schema.acronym_infos()]

        # Calling self._tokenize produces "unabbreviated" tokens
        tokens              = UID_Utils()._tokenize(parent_trace, uid, acronym_list)
        if len(tokens) == 0:
            raise ApodeixiError(parent_trace, "Unable to parse and unabbreviate uid '" + str(uid) + "'")
            
        full_uid = ".".join(tokens)
        return full_uid

    def _tokenize(self, parent_trace, uid, acronym_list=None):
        '''
        Returns a list of strings which are the individual tokens of the uid. It disabbreviates them if 
        necessary.

        For example, if the uid is "M3.T2" this method returns ["M3", "T2"].

        On the other hand, if the uid is an abbreviation like "3.2", this method will attempt to 
        figure out what were the acronyms, and if a successful guess (i.e., a valid acronym list as judged
        by what the UI store knows) it returns something like ["M3", "T2"]. It never returns abbreviated
        tokens, i.e., rather than returning ["3", "2"] when unabbreviation is not possible, this method
        will raise an ApodeixiError.

        @param acronym_list Optional parameter, used only when the caller wants to have a recovery behavior
                            if the UID is things like "3.2" instead of "M3.T2". The acronym list would
                            be a list of strings, such as ["M", "T"] in this example
        '''
        if uid==None:
            return []
        raw_tokens                          = uid.split('.')
        result                              = []
        # Something like P3 pr AV456. 
        REGEX                               = '^[a-zA-Z]+[0-9]+$' 
        for idx in range(len(raw_tokens)):
            t                               = raw_tokens[idx]
            m                               = _re.match(REGEX, t)
            if m == None:
                # Before we fail, let's try to recover. It may be that the user entered something like
                # "AV45.1.12" for usability reasons, expecting us to infer that the user meant "AV45.P1.E12".
                # This kind of "abbreviated UIDs" are expected when doing joins, for example, since the user
                # needs to type the UIDs and it is more user-friendly to type abbreviated UIDs than the full thing.
                ABBREVIATED_REGEX           = '^[0-9]+$'
                m2                          = _re.match(ABBREVIATED_REGEX, t)
                if m2 == None: # Recovery attempt did not work, so abort
                    raise ApodeixiError(parent_trace, "Invalid uid='" + uid 
                            + "': expected something like P3 or AV45.P1.E12, or abbreviations like AV45.1.12")
                else: # t is something like 12
                    if t == "0":
                        # We don't add a token for 0's in the abbreviation. See documentation of
                        # self.unabbreviate_uid
                        continue 
                    if acronym_list != None and len(acronym_list) <= idx:
                        raise ApodeixiError(parent_trace, "Too few known acronyms to infer them for uid='" + uid  + "'",
                                                    data = {"known acronyms": str(acronym_list)})
                    full_t                  = acronym_list[idx] + str(t)
            else: # t is someting like E12
                full_t                      = t 
            result.append(full_t)

        return result


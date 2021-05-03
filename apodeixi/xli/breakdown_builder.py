#import pandas      as _pd
import yaml        as _yaml
import re          as _re
import sys         as _sys
import os          as _os
import math        as _math
import datetime    as _datetime
from io import StringIO
import pandas

from .xlimporter import ExcelTableReader
from apodeixi.util.ApodeixiError    import *

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
        def __init__(self, level):
            
            if level > UID_Store._TokenTree.MAX_LEVELS:
                raise ValueError('Illegal attempt to create a _TokenTree at a level exceeding ' 
                                 + str( UID_Store._TokenTree.MAX_LEVELS))
            self.level     = level
            
            # Keys are acronyms like 'P', and values are arrays of non-negative integers like [1, 2, 3]
            # indicating that this _TokenTree contains 'P1', 'P2', and P3
            self.vals      = {} 
            
            # A dictionary where the key is a string like 'P12' where 12 belongs to array self.vals['P']
            # Value for that key 'P12' is another _TokenTree
            self.children  = {} 
            
            
        MAX_LEVELS = 100
        
        def initialize(self, tokens):
            '''
            Used in cases where the top level is determined externally
            '''
            for t in tokens:
                acronym, val           = self.parseToken(t)
                if acronym not in self.vals.keys():
                    self.vals[acronym] = []
                self.vals[acronym].append(val)
                self.children[t]       = UID_Store._TokenTree(self.level + 1)             
        
        def _generateHere(self, acronym):
            if acronym not in self.vals.keys():
                self.vals[acronym] = []
            
            used_numbers           = self.vals[acronym]
            
            if len(used_numbers) ==0:
                nextVal            = 1 # Start at 1, not 0. Though parent might have 0's
            else:
                nextVal            = max(used_numbers) + 1
                
            used_numbers.append(nextVal)
            uid                    = acronym + str(nextVal)
            self.children[uid]     = UID_Store._TokenTree(self.level + 1)
            return uid
    
        def generateNextUID(self, branch, acronym):
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
                raise ValueError("Invalid acronym='" + acronym + "': expected something like 'P' or 'AV'.  "
                                + "Level=" + str(self.level))                
            
            if len(branch)==0:
                # We hit bottom
                leaf_uid           = self._generateHere(acronym)
                full_uid           = leaf_uid
                
            else:
                head               = branch[0]
                tail               = branch[1:]
                child              = self._findChild(head)
                tail_uid, leaf_uid = child.generateNextUID(tail, acronym)
                full_uid           = head + '.' + tail_uid
                
            return full_uid, leaf_uid
                
        def _findChild(self, head):
            '''
            @param head A string like 'PR56'. If it exists in this _TokenTree as a top node return it.
                        Else raises an error.
            '''
            acronym, val  = self.parseToken(head)

            # Some of these checks are theoretically duplicate if the inner state of this object
            # is consistent as in theory it should be. But being paranoid, we do duplicate
            # checks since that might also catch bugs with inconsistent state
            if acronym not in self.vals.keys():
                raise ValueError('Acronym ' + acronym + ' corresponds to no valid child. Level=' 
                                 + str(self.level) + ". Happened while doing _findChild(" + head + ')')
            if val not in self.vals[acronym]:
                raise ValueError('Value ' + str(val) + ' corresponds to no valid child. Level=' 
                                 + str(self.level) + ". Happened while doing _findChild(" + head + ')')
            if head not in self.children.keys():
                raise ValueError('Token ' + head + ' corresponds to no valid child. Level=' 
                                 + str(self.level) + ". Happened while doing _findChild(" + head + ')')

            # We got past the checks, so this should not crash
            return self.children[head]
            
        def display(self):
            '''
            Used for debugging, to return a dictionary representation of the tree
            '''
            result_dict = {}
            for uid in self.children.keys():
                child   = self.children[uid]
                result_dict[uid] = child.display()
            return result_dict
        
        def parseToken(self, token):
            '''
            Given a token like 'PR34', it returns the acronym 'PR' and the value 34
            '''
            REGEX         = '^([a-zA-Z]+)([0-9]+)$'
            m             = _re.match(REGEX, token)
            if m == None or len(m.groups())!= 2:
                raise ValueError("Invalid token='" + token + "': expected something like 'P3' or 'AV45'.  "
                                + "Level=" + str(self.level))
            acronym       = m.group(1)
            val           = int(m.group(2))
            return acronym, val
        
    
    def __init__(self):
        self.tree     = UID_Store._TokenTree(level=0)
        return
    
    def generateUID(self, parent_UID, acronym):
        branch        = self._tokenize(parent_UID)
        return self.tree.generateNextUID(branch, acronym)
    
    def initialize(self, tokens):
        self.tree.initialize(tokens)
    
    def _tokenize(self, uid):
        if uid==None:
            return []
        tokens        = uid.split('.')
        REGEX         = '^[a-zA-Z]+[0-9]+$' # Something like P3 pr AV456
        for t in tokens:
            m         = _re.match(REGEX, t)
            if m == None:
                raise ValueError("Invalid uid='" + uid + "': expected something like P3 or AV45.P1.E12")
        return tokens


class DEPRECATED_UID_Store:
    '''
    @param start_at_0 Boolean. If True, UIDs start at 0 (i.e., for acronym X the first UID is X.00). False
                      by default, so UIDs start at 1 (e.g., X.01)
    '''
    def __init__(self, start_at_0=False):
        self.start_at_0   = True
        self.UID_dict     = {}
        return
    
    def _parseParent(self, parentUID):
        if parentUID == None:
            # We are starting a new branch from the root
            parent_acronym         = None
            parent_nb              = ''
        else:
            REGEX                  = r"^([a-zA-Z]+).(([0-9]{2})(.[0-9]{2})*)$" # Match eg P.03 or SD.04.12 or C.03.10.11

            m                      = _re.match(REGEX, parentUID) 
            if m==None or len(m.groups()) != 4:
                raise ValueError('Badly given parentUID. Should be something like "P.03" or "SD.02.11". Instead it was "' 
                                    + parentUID + '"')
            parent_acronym         = m.group(1)
            parent_nb              = m.group(2)   
            
        return parent_acronym, parent_nb
    
    def _add(self, acronym, nb):
        '''
        Adds a new UID to the internal store and returns it
        '''
        if acronym not in self.UID_dict.keys():
            self.UID_dict[acronym] = [nb] 
        else:
            self.UID_dict[acronym].append(nb)
            
        return acronym + '.' + nb
            
    def _already_used(self, acronym, parent_nb):
        '''
        Returns a list of the existing entries in the store that begin with acronym + parent_nb.
        These entries are the numerical part of the UID, i.e., strings consisting only of digits
        If there are none, it returns an empty list
        '''
        if acronym not in self.UID_dict.keys():
            return []
        # By this time we can safely assume that UID_dict has acronym as a key
        else:
            return [x for x in self.UID_dict[acronym] if x.startswith(parent_nb)]
        
    def _next_code(self, number_codes):
        '''
        For a list of strings representing N-digit number codes only differing in the last 2 digits, 
        it returns a new 2-digit number code that is 1 larger than the largest number code in the input. 
        As a side effect, it might sort the 'number_codes'
        
        Since only 99 2-digit codes are supported, will raise an exception if the largest number code in the 
        input is 99
        '''
        if len(number_codes)==0:
            if self.start_at_0:
                return '00'
            else:
                return '01'
        number_codes.sort()
        last_code     = number_codes[len(number_codes)-1]
        if len(last_code) < 2:
            raise ValueError('Require all number codes to have at least 2 digits. Instead was given this:\n'
                             + 'number_codes=' + number_codes)
        a             = int(last_code[len(last_code)-2]) 
        b             = int(last_code[len(last_code)-1])
        if a==9 and b==9:
            raise ValueError('UID generation of children UIDs only support 2-digit extensions of a parent UID, '
                                + 'ranging from 01 to 99, so there is hard limit of 99 children and that has been exceeded.')
        if b<9:
            b_new = b+1
            a_new = a
        else: # We have a carry
            b_new = 0
            a_new = a+1
        new_code    = str(a_new) + str(b_new)
        return new_code

    def generateUID(self, acronym, parent_UID):

        parent_acronym, parent_nb    = self._parseParent(parent_UID)
                    
        already_used_codes           = self._already_used(acronym, parent_nb)
                    
        next_suffix                  = self._next_code(already_used_codes)
        
        if parent_nb == None or len(parent_nb)==0:
            new_nb = next_suffix
        else:
            new_nb = parent_nb + '.' + next_suffix
        
        return self._add(acronym, new_nb)

class L1L2_Link:
    def __init__(self, L1_UID, L2_URL, L2_excel_range):
        self.L1_UID             = L1_UID
        self.L2_URL             = L2_URL
        self.L2_excel_range     = L2_excel_range
        return

_SCENARIO             = 'scenario'
_ENVIRONMENT          = 'environment'
_SCORING_CYCLE        = 'scoringCycle'
_SCORING_MATURITY     = 'scoringMaturity'
_ESTIMATED_BY         = 'estimatedBy'
_ESTIMATED_ON         = 'estimatedOn'
_RECORDED_BY          = 'recordedBy'
_PURSUIT              = 'pursuit'
_BREAKDOWN_TYPE       = 'breakdownType'

class BreakdownBuilder:
    '''
    Creates a Breakdown domain resource by aggregating data from multiple Excel sheets within the same 
    Excel spreadsheet.
    A Breakdown is basically a tree.
    One sheet contains the top-level breakdown, for the root of the tree (level 0) and its immediate children (level 1).
    For each children in level 1, there is a sheet that contains a breakdown into level 2 and level 3 for a 
    particular "relationship type" between level 1 and level 2. Different relationship types would be on different sheets.
    
    @ param uid_store A UID_Store, used to generate unique identifiers for each node in the Breakdown tree.
    '''
    def __init__(self, ctx, links, l0_url, l0_excel_range, manifests_repo_dir, uid_store):
        self.ctx                  = ctx
        self.links                = links
        self.l0_url               = l0_url
        self.l0_excel_range       = l0_excel_range
        self.manifests_repo_dir   = manifests_repo_dir
        self.uid_store            = uid_store
        return


    
    def build(self):
        user                            = self.ctx[_RECORDED_BY]
        pursuit                         = self.ctx[_PURSUIT]
        scoring_cycle                   = self.ctx[_SCORING_CYCLE]
        plan_maturity                   = self.ctx[_SCORING_MATURITY]
        environment                     = self.ctx[_ENVIRONMENT]
        planning_scenario               = self.ctx[_SCENARIO]
        breakdown_type                  = self.ctx[_BREAKDOWN_TYPE]
        
        estimation_date                 = self.ctx[_ESTIMATED_ON]
        
        manifest_dict                   = {}

        metadata                        = {'namespace': environment + '.' + scoring_cycle,
                                           'name':      pursuit     + '.' + planning_scenario, 
                                           'labels': {'scoringCycle': scoring_cycle,
                                                      'scenario': planning_scenario,
                                                      'pursuit': pursuit}}

        manifest_dict['apiVersion']     = 'breakdown.a6i.io/v1dev'
        manifest_dict['kind']           = 'Breakdown'
        manifest_dict['metadata']       = metadata
        
        # Plan maturity can be one of: 'Not done', 'Drafted', 'Checked', 'Published'
        manifest_dict['planMaturity']   = plan_maturity
        
        l0_dict                         = self._buildLevel1Breakdown()
        
        manifest_dict['breakdown']      = {'type': breakdown_type,  #'estimated_by': estimating_mgr,
                                           'defined_on': estimation_date,
                                           'defined_by': user,
                                          'streams': l0_dict}    
        
        
        streams_dict                    = manifest_dict['breakdown']['streams'] 
        
        for link in self.links:
            l2_key, l2_children                      = self._buildLevel2Breakdown(link) 

            l1_key                      = link.L1_UID + '-detail' # For example, 'W.03-detail'
            '''
            if l1_key not in streams_dict.keys():
                streams_dict[l1_key]    = {}
            streams_dict[l1_key][l2_key] = l2_children
            '''

            self._dock( parent                 = streams_dict[l1_key],
                        docking_key             = l2_key, 
                        children_to_dock        = l2_children, 
                        concatenate_previous    = False)
            

        #_yaml.dump(manifest_dict, _sys.stdout)
        output = StringIO()
        _yaml.dump(manifest_dict, output)
        

        with open(self.manifests_repo_dir + '/' + pursuit + '-breakdown.yaml', 'w') as file:
            _yaml.dump(manifest_dict, file)

        return output.getvalue()

    def _dock(self, parent, docking_key, children_to_dock, concatenate_previous):
        '''
        Results in this outcome being `True`: `parent[docking_key] == children_to_dock`. It creates any missing references
        (e.g., if `docking_key` is not a key in `parent`, it creates it). 
        An exception to the above outcome is when the `docking_key` already existed and previously existing childen
        were docked at it.
        In such a case, previously existing children are either removed or concated to, depending on the `concatenate_previous`
        flag. If concatenation results in conflicts the new children win.

        If the docking key is None, the children are docked at the root (1 level higher than otherwise)

        Example 1: suppose

        .. code::

            parent = {'a', {'b': [1, 2],  
                            'c': [3, 4]}, 
                      'x' : {'y': [5, 6]}}

            docking_key = 'a'

            children_to_dock = {'p': [7, 8], 
                                'c': [9, 10]}

        In such a case, when not concatenating then the result is:

        .. code::

             parent = {'a', {'p': [7, 8],  
                             'c': [9, 10]}, 
                      'x' : {'y': [5, 6]}}

        If concatenating, then the result is:

        .. code::

             parent = {'a', {'b': [1, 2],
                             'p': [7, 8],  
                             'c': [9, 10]}, 
                      'x' : {'y': [5, 6]}}

        Example 2: suppose

        .. code::

            parent = {'a', {'b': [1, 2],  
                            'c': [3, 4]}, 
                      'x' : {'y': [5, 6]}}

            docking_key = None

            children_to_dock = {'p': [7, 8], 
                                'c': [9, 10]}

        In such a case, when not concatenating then the result is:

        .. code::

            parent = {'a', {'b': [1, 2],  
                            'c': [3, 4]}, 
                      'x' : {'y': [5, 6]},
                      'p': [7, 8],
                      'c': [9, 10]}


        @param children_to_dock       A dictionary
        @param parent                 A dictionary
        @param docking_key            A string
        @param concatenate_previous   A boolean to determine whether to replace or concatenate pre-existing children
        '''
        if docking_key == None:
            for k in children_to_dock:
                parent[k] = children_to_dock[k]
        else:
            if docking_key not in parent.keys():
                parent[docking_key] = {}

            if concatenate_previous==False:
                parent[docking_key] = children_to_dock
            else:
                previous_children   = parent[docking_key]
                for k in children_to_dock:
                    previous_children[k] = children_to_dock[k]
    
    
    def _nice(txt):
        return txt.strip().lower().replace(' ', '-')
    

        
    def _strip(txt):
        '''
        Removes any whitespace or other "noise" from txt and return sit
        '''
        if type(txt)==float and _math.isnan(txt):
            return ''
        stripped_txt = str(txt).replace('\n', '').strip(' ')
        return stripped_txt
    
    '''
    def _cleanup_UID(txt):
        
        #If the 'txt' finishes in a number but lacks a dot required for UIDs (e.g., txt="W4" or "W-4" instead of "W.04")
        #it will return the correctly formatted txt ("W.04")
        
        REGEX = '^[a-zA-Z -\._]*([0-9]+)$'
        m     = _re.match(REGEX, txt.strip(' \n'))
        if m==None or len(m.groups()) != 1:
            raise ValueError("Unable to parse '" + txt + "': expected all digits to be in a contiguous suffix.")
        nb    = int(m.group(1))
        if nb > 100:
            raise ValueError("Invalid UID '" + txt + "':' the numerical value " + str(nb) + " should not exceed 99")
        prefix = txt.split(str(nb))[0]
        prefix = prefix.strip(' \n-_.')
        if nb < 10:
            nb_txt = '0' + str(nb) # From '00' to '09'
        else:
            nb_txt = str(nb) # From '10' to '99'
        return prefix + "." + nb_txt
    '''

    def _buildLevel1Breakdown(self):
        reader                           = ExcelTableReader(url=self.l0_url, excel_range=self.l0_excel_range)
        l0_df                            = reader.read()
        columns                          = l0_df.columns

        if len(columns) < 2:
            raise ValueError("Too few columns: need at least two columns, the first two of which should the "\
                                + "UID and the Title for a Level 1 breakout. Happened for url=" + self.l0_url)
        UID                              = columns[0]
        TITLE                            = columns[1]        
        l0_dict                          = {}
        for row in l0_df.iterrows():
            l1_data                      = row[1]
            l1_uid                       = l1_data[UID] #BreakdownBuilder._cleanup_UID(l1_data[UID])
            l0_dict[l1_uid]              = l1_data[TITLE]
            l0_dict[l1_uid + '-detail']  = {}
            for idx in range(2, len(columns)):
                col                      = columns[idx]
                l1_details_dict          = l0_dict[l1_uid + '-detail']
                l1_details_dict[col]     = l1_data[col]
                l1_details_dict['UID']   = l1_uid

        return l0_dict
    
    def _buildLevel2Breakdown(self, link):
        '''
        Returns a pair of a key and a sub-dictionary for a portion of the YAML to be built by this class.
        
        Below is an example of the YAML fragment that callers can build from the sub-dictionary created in this function.
        The example correspond to an Excel spreadsheet block that has columns called: 
        'UID', 'Expectation', 'Description', 'Acceptance Criteria Artifact', 'Evidence of correctness'

        expectations:
            E1: Analyze segmentation
            E1-detail:
            UID: W0.E1
            acceptance-criteria-artifacts:
                A1:
                UID: W0.E1.A1
                description: 'Segmentation tree: consolidated tree of segments (verticals,
                    geos, tiers, and breakouts for either) '
                A2:
                UID: W0.E1.A2
                description: Size at each leaf in the segmentation tree
                A3:
                UID: W0.E1.A3
                description: Quantification of how much of that could be cloud
            description: Break Finastra's space into segments and for each measure the
                appetite for cloud
            E2: Analyze "Jobs to be done" / Personas
            E2-detail:
            UID: W0.E2
            '''    
        url                 = link.L2_URL
        excel_range         = link.L2_excel_range
        reader              = ExcelTableReader(url, excel_range)

        l2l3_df             = reader.read()


        if len(l2l3_df.columns) != 5:
            raise ValueError ("Badly formatted breakdown: should have exactly five columns, corresponding to: " \
                              + "'UID', name of the L1-L2 relationship, descriptive attribute of L2, "\
                              + "name of the L2-L3 relationship, descriptive attribute of L3." \
                              + "  Error whiln processing range= '" + excel_range + "' and url=\n\t" + url)
        
        # Column names in CAPs
        columns             = l2l3_df.columns
        L2                  = columns[1]
        L2_DESC             = columns[2]
        L3                  = columns[3]
        L3_DESC             = columns[4]
        
        # Data that is different for each ith cycle of loop
        l2_dict_i           = {}
        l3_fill_UID_i       = None
        l3_leaf_UID_i       = None
        
        # Data that changes on the nth time a new Level 2 is entered
        l3_children_n       = {}
        l2_full_UID_n       = None
        l2_leaf_UID__n      = None

        # Data constructed in subsequent cycles of loop
        all_l2s_dict        = {}
        
        # YAML-friendly keys derived from the columns (e.g., "Acceptance Criteria" becomes "acceptance-criteria")
        Y_L2                = BreakdownBuilder._nice(L2) + "s" # Plural, as we have multiple level 2 things
        Y_L2_DESC           = BreakdownBuilder._nice(L2_DESC)
        Y_L3                = BreakdownBuilder._nice(L3) + "s" # Plural, as we have multiple level 3 things
        Y_L3_DESC           = BreakdownBuilder._nice(L3_DESC)

        for row in l2l3_df.iterrows(): # nth cycle of loop
            data_i                              = row[1]
            l2_i                                = data_i[L2]
            l2_desc_i                           = BreakdownBuilder._strip(data_i[L2_DESC])
            l3_i                                = data_i[L3]
            l3_desc_i                           = BreakdownBuilder._strip(data_i[L3_DESC])
            
            if _is_blank(l2_i): # We are within the same Level 2 as in prior cycle of the loop
                l3_full_UID_i, l3_leaf_UID_i    = self.uid_store.generateUID(acronym=L3[0], parent_UID=l2_full_UID_n)
                l3_children_n[l3_leaf_UID_i]    = {'description': l3_i, 'UID': l3_full_UID_i}

            elif (type(l2_i)==str and len(l2_i)>0): # We just entered a new Level 2
                l2_full_UID_n, l2_leaf_UID_n    = self.uid_store.generateUID(acronym    = _acronym(L2[0]), 
                                                             parent_UID = link.L1_UID)
                l3_full_UID_i, l3_leaf_UID_i    = self.uid_store.generateUID(acronym    = _acronym(L3[0]), 
                                                             parent_UID = l2_full_UID_n)
                # Dock level 3                                             
                l3_children_n                     = {}
                self._dock( parent                = l3_children_n,
                            docking_key           = l3_leaf_UID_i, 
                            children_to_dock      = {'description': l3_i, 'UID': l3_full_UID_i}, 
                            concatenate_previous  = False)

                # Dock level 2
                l2_dict_n                         = {}
                self._dock( parent                = l2_dict_n,
                            docking_key           = Y_L3, 
                            children_to_dock      = l3_children_n, 
                            concatenate_previous  = False)
                l2_desc_n                         = l2_desc_i
                self._dock( parent                = l2_dict_n,
                            docking_key           = None, 
                            children_to_dock      = {Y_L2_DESC: l2_desc_n, 'UID': l2_full_UID_n}, 
                            concatenate_previous  = False)

                # Dock level 1  
                l2_n                              = l2_i            
                self._dock( parent                = all_l2s_dict,
                            docking_key           = l2_leaf_UID_n + '-detail', 
                            children_to_dock      = l2_dict_n, 
                            concatenate_previous  = False)
                self._dock( parent                = all_l2s_dict,
                            docking_key           = None,
                            children_to_dock      = {l2_leaf_UID_n: l2_n}, 
                            concatenate_previous  = False)





            else:
                raise ValueError("Expected a string or a blank, not a '" + str(type(l2_i)) 
                                 + '(row=' + str(row[0]) + " and text is '" + str(l2_i) + "')")
            

        return Y_L2, all_l2s_dict


    '''
    def _process_row(self, row, intervals, tree_fragments):
        for interval in metadata: # loops from the more granular to the higher level
            if interval.not_blank(row): # We just entered a new section for this interval, so post
                tree_fragments.dock(to=interval, row=
                row)
            else:
                break # By convention, if an interval is blank for a row, all other intervals to the left of it are also blank
    '''

class BreakdownTree():
    '''
    The intuition behind this class is that it represents `1:N` entity relationships. Consider an `entity A` with a `1:N` relationship
    to an `entity B`. Then an instance `a` of `A` may "link" to instances `b1, b2, ..., bN` of `B`. A `BreakdownTree` is
    a way to capture these links, which "breaks down" `a` into `b1, ..., bN`.

    Each of these "linked" objects `b1,...bN` are described based on their named properties, which might be "simple" (a scalar),
    or "complex" (another `1:N` link from entity `B` to yet another entity `C`). This introduces a natural tree-like
    structure as one navigates entity relationships.

    A final observation is that since we are talking entities (i.e., domain constructs that have an autonomous existence), 
    each entity instance should have a unique UID identifying it.

    To represent this domain model, a BreakdownTree is a tree with these characteristics:

    1. Every immedidate child of the root is a node of kind "_EntityInstance". All these immediate children are for a common
       "entity type" and each child represents an "entity instance" identified with a unique UID.
    2. Every "_EntityInstance" node has one of four kinds of children: 
        * A unique child called "UID" that has a scalar value uniquely identifying the _EntityInstance within the "global BreakdownTree"
            (see below for what is the "global BreakdownTree) 
        * A unique string-valued child that provides a "name" for the "entity instance" represented by the _EntityInstance. The
            string value for this child is unique among all _EntityInstances of its immediate parent.
        * Zero or more scalars "properties"
        * Zero or more BreakdownTree children (each representing references from the _EntityIntance to yet another entity)
    3.  Two BreakdownTree objects are "connected" if one is a descendent of the other or if both descend from a common
        BreakdownTree. For any BreakdownTree T, all other BreakdownTree objects it is connected to descend from a unique, maximal
        BreakdownTree G, that we call the "global BreakdownTree".
    4. The unique UIDs are as created by the UID_Store class in this module. The instance of the UID_Store used is common
        across all nodes in a BreakdownTree
    4. All children are identified by a unique string. In the case of the _EntityInstance child, the uique string is "UID"
    '''
    def __init__(self, uid_store, entity_type, parent_UID):
        self.uid_store              = uid_store
        self.entity_type            = entity_type # Common entity type for all the nodes under root
        self.parent_UID             = parent_UID
        self.children               = {} # Dictionary of _EntityInstance's, keyed by UID
        self.last_path              = {} # Keys are entity types, and value is an _EntityInstance
        self.acronyms               = {} # Keys are entity types, and value is the acronym used for it

    def as_dicts(self):
        '''
        Returns a dictionary of dictionaries representing this BreakdownTree. The keys are the leaf UIDs for the
        _EntityInstance objects comprising this BreakdownTree
        '''
        result                                  = {}

        for k in self.children.keys():
            entity_instance                     = self.children[k]
            entity_instance_dict                = {}
            entity_instance_dict['UID']         = entity_instance.UID
            entity_instance_dict['name']        = entity_instance.name

            for prop_k in entity_instance.scalar_children.keys():
                entity_instance_dict[prop_k]    = entity_instance.scalar_children[prop_k]

            for tree_k in entity_instance.breakdown_children.keys():
                entity_instance_dict[tree_k + "s"]    = entity_instance.breakdown_children[tree_k].as_dicts()

            result[entity_instance.leaf_UID]         = entity_instance_dict
            #result.append(entity_instance_dict)
        return result
        

    def readDataframeFragment(self, interval, row, parent_trace): 
        '''
        Used to attach or enrich an immediate child to the root of this BreakdownTree based on information in a row
        in a Pandas DataFrame.

        The idea is that end-used used something like Excel to capture both the entity relationships and the properties
        of the entities themselves. As one looks at Excel columns left to right, they partition into
        intervals, one for each entity. Within an interval, the columns provide the properties of the entity for that
        row.

        The trick lies in how 1:N entity relationships are represented in Excel. The idea is that if entity `A`'s instance `a` references
        entity `B`'s instances `b1, ...., bn` this is represented in Excel by n rows and two intervals of columns:
        `intervalA` on the left and `intervalB` on the right. `b1, ..., bn`'s properties are in the `n` rows under the 
        `intervalB` columns. The properties of `a` are in the **first row only** under the `intervalA` columns, with all other
        rows under `intervalA` being blank. That is the convention for how the user easily capture properties for `a`, `b1, ..., bn`
        and their linkage in a single worksheet in Excel: blank columns under `interval A` indicates that the `B` instances
        are linked to the same `A` instance for the last row that wasn't blank under `interval A`.

        The above pattern may be repeated across multiple entity depths, e.g., entity `A` having `1:n` linkage to entity `B`, 
        and `B` in turn having `1:n` linkage to entity `C`, and so on, all within a single worksheet in Excel.

        This Excel is then programmatically loaded into a Pandas Dataframe, and processed row by row in order to produce
        the inner representation of all these entity representations as an Apodeixi domain model YAML manifest. When a row
        is processed, it is processed entity by entity, from most general to the more granular, following the order
        how entity relationships point.

        To explain this, consider again the case of entity `A`'s instance `a` references entity `B`'s instances `b1, ...., bn`,
        and imagine we are processing a row `i`.

        We first process the columns in `interval A`, and there are two possibilities: we may find them to
        be blank, or not.

        If `interval A` columns are not blank this means that the user captured `a` in that row (that only happens if `i=0`
        in this example).
        In that case, we create a new `_EntityInstance` object to capture `a`, and attach it to the BreakdownTree
        for the interval before `Interval A` (if any), possible since we process the row from left to right, so such BreakdownTree
        exists already unless there is no interval to the left of `Interval A`, in which case we are at the root.

        On the other hand, if `interval A` columns are blank (only happens if `i>0` in this example), that means we already processed
        `a` in a previous row, and so we get that previously constructed instance of `a`'s _EntityInstance, using
        self.last_path which keeps track of such previously constructed things.

        Either way, we now have `a`'s _EntityInstance. That makes it now possible to process `Interval B` and
        attach `b1, ..., bn` to `a`'s _EntityInstance as a breakdown child (i.e., a sub-BreakdownTree)
        

        @param interval     List of strings, corresponding to the columns in `row` that pertain to an entity being processed
        @param row          A tuple `(idx, series)` representing a row in a larger Pandas Dataframe as yielded by
                            the Dataframe `iterrows()` iterator.
        @param parent_trace A apodeixi.util.ApodeixiError.FunctionalTrace object. It contains human-friendly information 
                            for humans to troubleshoot problems when error are raised.
        '''
        encountered_new_entity              = False
        entity_column_idx                   = None
        known_entity_types                  = list(self.last_path.keys())
        my_trace                            = parent_trace.doing("Validating inputs are well-formed",
                                                    data = {'known_entity_types': known_entity_types})
        if True:
            # Check against nulls
            if interval==None or len(interval)==0:
                raise ApodeixiError(my_trace, "Empty interval of columns was given.")

            # Check it's the right entity type  ### LOOKS LIKE AN INCORRECT CHECK - Level 2 intervals WON'T MATCH ROOT TREE ENTITY
            #if interval[0] != self.entity_type:
            #    raise ApodeixiError(my_trace, "Wrong entity type '" + interval[0] + "'. Should be '" + self.entity_type  + "'.")

            # Check we got a real Dataframe row
            if row==None or type(row)!=tuple or len(row)!=2 or type(row[1])!=pandas.core.series.Series:
                raise ApodeixiError(my_trace, "Didn't get a real Pandas row")   

            # Check interval and row are consistent
            columns                     = list(row[1].index)
            if not set(interval).issubset(set(columns)):
                raise ApodeixiError(my_trace, "Interval is not a subset of the row's columns.")

            # Check entity appears in exactly one column. From above know it appears at least once. 
            idxs                        = [idx for idx in range(len(columns)) if columns[idx]==interval[0]]
            if len(idxs)>1:
                raise ApodeixiError(my_trace, "Entity '" + interval[0] + "' appears in multiple columns. Should appear only once.")
            entity_column_idx           = idxs[0]

            # Check that if interval's entity is blank, all of interval is bank
            blank_cols                  = [col for col in interval if _is_blank(row[1][col])]
            encountered_new_entity      = not interval[0] in blank_cols
            if not encountered_new_entity and len(blank_cols) < len(interval):
                raise ApodeixiError(my_trace, "Row has a blank '" + interval[0] 
                                    + "' so rest of row's interval should be blank, but isn't")

            # Check that interval itself has no subentities (as any subentity should be *after* the interval)
            # Remember to not count interval[0] as "illegal", since it is clearly an entity and not a sub-entity/
            # That's why we intersect the known_entity_types with interval[1:] (as opposed to intersecting with interval)
            illegal_sub_entities        = set(known_entity_types).intersection(set(interval[1:])) 
            if len(illegal_sub_entities) > 0:
                raise ApodeixiError(my_trace, "There shouldn't be subentities inside the interval, but found some: " 
                                                + str(illegal_sub_entities))

        columns                             = list(row[1].index)            
        parent_entity                       = None
        my_trace                            = parent_trace.doing("Discovering parent entity")
        if True:
            ancestor_entities_idxs      = [idx for idx in range(len(columns)) if columns[idx] in known_entity_types 
                                                                                    and idx < entity_column_idx]
            if len(ancestor_entities_idxs) == 0:
                my_trace                = my_trace.doing("Validating we are the root entity", 
                                                data={'self.entity_type': self.entity_type,
                                                        'entity_column_idx': entity_column_idx})
                if interval[0] != self.entity_type:
                    raise ApodeixiError(my_trace, "Could not find a parent entity for '" + interval[0] + "'") 
            else:
                parent_entity           = columns[max(ancestor_entities_idxs)]

        if encountered_new_entity: 
            my_trace                        = parent_trace.doing("Figuring out docking coordinates for '" + interval[0] + "'.")
            if True:
                if parent_entity == None: # Attach to the root
                    docking_uid             = self.parent_UID
                else:
                    my_trace                = my_trace.doing("Validating we previously created a node for '" 
                                                                    + parent_entity + "' to which to attach '" + interval[0] + "'.")
                    if parent_entity not in self.last_path.keys():
                        raise ApodeixiError(my_trace, "No prior node found for  '" + parent_entity + "'") 
                    
                    parent_entity_instance  = self.last_path[parent_entity]
                    docking_uid             = parent_entity_instance.UID

            my_trace                        = parent_trace.doing("Docking a new '" + interval[0] 
                                                                    + "' below docking_uid '" + str(docking_uid) + "'")
            self.dockEntityData(    full_docking_uid    = docking_uid, 
                                    #tree_to_attach_to   = tree_to_attach_to, 
                                    entity_type         = interval[0], 
                                    data_to_attach      = row[1][interval], 
                                    parent_trace        = my_trace)
            
        else: # Didn't encounter a new entity - so nothing to do for this interval
            return
        
    def dockEntityData(self, full_docking_uid, entity_type, data_to_attach, parent_trace):
        '''
        Method to attach a descendent to the tree. When an entity A links 1:n with an entity B,
        this method can be used to "attach" an instance 'bi' of B to an instance 'a' of A.
        We call this "docking" because we look at the BreakdownTree as already having a node of 'a' with
        UID given by the `full_docking_uid`. Below that a subtree exists (or will be created by this method)
        for all the instances `b1, b2, ..., bn` of `B` that should link to that particular `a`.

        This method creates a new _EntityInstance node for `bi` based on the `data_to_attach`, and then links 
        that node to the subtree under `a` for `entity_type`, thereby increasing the size of this BreakdownTree. 

        @param full_docking_uid A string like 'A23.BW2.C2' identifying uniquely an _EntityInstance node in this tree
                                If null we assume we are docking at the top of this tree
        @param entity_type      A string for the kind of entity to be added under the full_docking_uid
        @param data_to_attach: A Pandas Series   
        '''
        acronym_for_attachment  = self.getAcronym(entity_type)
        my_trace                = parent_trace.doing("Identifying sub tree to attach to")
        if full_docking_uid==self.parent_UID: # We are attaching at the root
            tree_to_attach_to   = self

        else:
            parent_entity_instance  = self.find(full_docking_uid, my_trace)
            if parent_entity_instance == None:
                raise ApodeixiError(my_trace, "No node exists for UID '" + full_docking_uid + "'")

            tree_to_attach_to       = self._get_tree_to_attach_to(parent_entity_instance, entity_type, my_trace)

            sub_trace           = my_trace.doing("Validating acronym is not used by another entity")
            if tree_to_attach_to.entity_type != entity_type:
                raise ApodeixiError(sub_trace, "Can't add entity '" + entity_type 
                                    + "' because its acronym conflicts with acronym of previously used entity '"
                                    + tree_to_attach_to.entity_type + "'")

        
        full_uid, leaf_uid      = self.uid_store.generateUID(   acronym         = acronym_for_attachment, 
                                                                parent_UID      = full_docking_uid)
        new_node                = BreakdownTree._EntityInstance(    uid_store   = self.uid_store, 
                                                                    name        = data_to_attach[entity_type],
                                                                    uid         = full_uid,
                                                                    leaf_uid    = leaf_uid)

        for idx in data_to_attach.index:
            if idx != entity_type: # Don't attach entity_type as a property, since we already put it in as 'name
                new_node.setProperty(idx, data_to_attach[idx])

        tree_to_attach_to.children[leaf_uid]    = new_node
        self.last_path[entity_type]             = new_node

    def _get_tree_to_attach_to(self, containing_entity_instance, entity_type_to_attach, parent_trace):
        acronym_for_attachment  = self.getAcronym(entity_type_to_attach)

        tree_to_attach_to       = containing_entity_instance.find_subtree(acronym_for_attachment, self, parent_trace)

        if tree_to_attach_to==None: # This is first time we attach for this acronym, so create tree
            tree_to_attach_to   = BreakdownTree(self.uid_store, entity_type_to_attach, containing_entity_instance.UID)
            containing_entity_instance.breakdown_children[entity_type_to_attach]      = tree_to_attach_to

        return tree_to_attach_to


    #def dock_subtree(self, full_docking_uid, entity_type, subtree_to_attach, parent_trace):
    def dock_subtree(self, entity_type, subtree_to_attach, parent_trace):

        my_trace                        = parent_trace.doing("Finding where to dock in containing tree")
        containing_equity_instance      = self.find(subtree_to_attach.parent_UID, my_trace)

        containing_equity_instance.breakdown_children[entity_type + 's']    = subtree_to_attach



    def find(self, descendent_uid, parent_trace):
        '''
        Returns an _EntityInstance that descends from the root of this tree, and identified by `descendent_uid`
        as the unique UID identifying this _EntityInstance in the global BreakdownTree we belong to.
        '''
        if descendent_uid == None:
                raise ApodeixiError(parent_trace, "Can't find with a null descendent_uid")  

        relative_uid                        = descendent_uid
        my_trace                            = parent_trace.doing('Computing relative uid', data = {'parent_UID': self.parent_UID})
        if self.parent_UID != None:
            prefix                          = self.parent_UID + '.'
            if not descendent_uid.startswith(prefix):
                raise ApodeixiError(my_trace, "Bad  uid '" + descendent_uid + "': it should have started with '" + prefix + "'")  
            relative_uid                    = descendent_uid.lstrip (prefix)   

        my_trace                            = parent_trace.doing('Traversing uid path', data = {'relative_uid': relative_uid})
        uid_path                            = relative_uid.split('.')

        #previous_entity_instance            = None
        entity_instance                     = None # At start of loop, the entity instance for parth of uid_path already processed
        for idx in range(len(uid_path)):
            leaf_uid                        = uid_path[idx]
            loop_trace                      = my_trace.doing("Doing loop cycle for leaf_uid '" + leaf_uid + "'")

            if entity_instance == None: # First cycle in loop, so search in root tree
                next_tree                   = self
            else:
                uid_acronym, uid_nb         = _parse_leaf_uid(leaf_uid, loop_trace)
                sub_trace                   = loop_trace.doing("Looking for a subtree for the '" + uid_acronym + "' acronym")
                next_tree                   = entity_instance.find_subtree(uid_acronym, self, sub_trace) 
                if next_tree == None:
                    raise ApodeixiError(sub_trace, "Can't a subtree for acronym '" + uid_acronym + "'")

            # Set for next cycle of loop, or final value if we are in the last cycle
            entity_instance                 = next_tree.children[leaf_uid]

        # Return the last entity instance we got into
        return entity_instance
        
    def getAcronym(self, entity_type):
        '''
        Returns the entity's acronym. If none exists, it will generate a new one to ensure it does not conflict with
        the previously used acronyms
        '''
        if entity_type not in self.acronyms.keys():
            already_used        = [self.acronyms[e] for e in self.acronyms.keys()]
            nb_letters          = 1
            candidate           = _acronym(entity_type, nb_letters=nb_letters)
            while candidate in already_used:
                nb_letters      += 1
                new_candidate   = _acronym(entity_type, nb_letters=nb_letters)

                if len(candidate)==len(new_candidate):
                    # We ran out of letters. Just keep adding letters. Ugly, but should happen very, very rarely
                    new_candidate = new_candidate + new_candidate[0]
                candidate = new_candidate

            self.acronyms[entity_type]  = candidate 

        acronym                 = self.acronyms[entity_type] 
        return acronym

    class _EntityInstance():
        '''
        Represents an immediate child of the root of a BreakdownTree
        '''
        def __init__(self, uid_store, name, uid, leaf_uid):
            self.uid_store           = uid_store
            #self.entity_type         = entity_type

            # The four kinds of possible "children"
            self.name                = name
            self.UID                 = uid
            self.leaf_UID            = leaf_uid
            self.scalar_children     = {}
            self.breakdown_children  = {}
            
        def setProperty(self, name, value):
            self.scalar_children[name] = value

        def linkAnotherEntity(self, name, breakdown_tree):
            self.breakdown_children[name]     = breakdown_tree

        def find_subtree(self, uid_acronym, containing_tree, parent_trace):
            '''
            Searches among this `entity_instance`'s breakout children, looking for a unique BreakdownTree for the given
            uid_acronym, and returns it. If there are none, returns None. Raises an error if there are more than one. 
            '''
            all_subtrees                    = self.breakdown_children
            all_subtree_roots               = list(all_subtrees.keys())
            my_trace                        = parent_trace.doing("Searching a path for acronym '" + uid_acronym + "'",
                                                            data = {'breakdown keys': all_subtree_roots}) 
            potential_subtree_roots         = [root for root in all_subtree_roots if containing_tree.getAcronym(root)== uid_acronym]
            if len(potential_subtree_roots) > 1:
                raise ApodeixiError(my_trace, "Ambiguous paths for '" + uid_acronym + "': could be any of " + potential_subtree_roots)

            elif len(potential_subtree_roots) == 0:
                result_tree                 = None
            else: 
                found_root                  = potential_subtree_roots[0]
                result_tree                 = all_subtrees[found_root]
            return result_tree


def _is_blank(txt):
    '''
    Returns True if 'txt' is NaN or just spaces
    '''
    if type(txt)==float and _math.isnan(txt):
        return True
    elif type(txt)==str:
        stripped_txt = BreakdownBuilder._strip(txt)
        return len(stripped_txt)==0
    else:
        return False


def _acronym(txt, nb_letters=1):
    '''
    Returns a string of initials for 'txt', in uppercase
    '''
    stripped_txt = BreakdownBuilder._strip(txt)
    tokens       = stripped_txt.split(' ')
    acronym      = ''.join([token[0:min(nb_letters, len(token))].upper() for token in tokens])
    return acronym

def _parse_leaf_uid(leaf_uid, parent_trace):
    '''
    Parses a string like 'AC43' and returns two things: the acronym string 'AC' and the int 43
    '''
    REGEX               = '([a-zA-Z]+)([0-9])+'
    m                   = _re.match(REGEX, leaf_uid)
    my_trace            = parent_trace.doing("Parsing leaf_uid into acronym and number")
    if m == None or len(m.groups()) != 2:
        raise ApodeixiError(parent_trace, "Couldn't parse leaf_uid '" + leaf_uid + "'")
    acronym             = m.group(1)
    nb                  = int(m.group(2))
    return acronym, nb


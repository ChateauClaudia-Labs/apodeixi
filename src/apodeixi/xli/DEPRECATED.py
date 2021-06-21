import pandas      as _pd
import yaml        as _yaml
import re          as _re
import sys         as _sys
import os          as _os
import math        as _math
import datetime    as _datetime

from io import StringIO

from apodeixi.util.a6i_error            import ApodeixiError, FunctionalTrace

from apodeixi.xli.xlimporter import SchemaUtils, ExcelTableReader

def _parse_url(url):
    '''
    Given a url of form "<some string A, maybe with colons>:<some string B without colons>"
    it returns the two substrings separated by the last colon
    '''
    parent_trace              = FunctionalTrace(None).doing("Parsing url")
    s = _re.split(':', url)
    if len(s) < 2:
        raise ApodeixiError (parent_trace, "Incorrectly formatted url was given: '" + url
                            +"'. Should instead be formmated like this example: "
                            + "'C:/MyDocuments/MySpreadsheets/Wonderful.xlsx:SheetName'")
    sheet = s[len(s)-1]
    path = url.split(':' + sheet)[0]
    if len(path) == 0 or len(sheet) ==0:
        raise ApodeixiError (parent_trace, "Incorrectly formatted url was given: \n\t'" + url
                            + "'\nShould instead be formmated like this example, with a non-empty path and a non-empty"
                            + " sheet name separated by the last colon in the url: \n"
                            + "\t'C:/My Documents/My Spreadsheets/Wonderful.xlsx:SheetName'")
    return path, sheet

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

class L1L2_Link:
    def __init__(self, L1_UID, L2_URL, L2_excel_range):
        self.L1_UID             = L1_UID
        self.L2_URL             = L2_URL
        self.L2_excel_range     = L2_excel_range
        return

_SCENARIO               = 'scenario'
_ENVIRONMENT            = 'environment'
_SCORING_CYCLE          = 'scoringCycle'
_SCORING_MATURITY       = 'scoringMaturity'
_ESTIMATED_BY           = 'estimatedBy'
_ESTIMATED_ON           = 'estimatedOn'
_RECORDED_BY            = 'recordedBy'
_PURSUIT                = 'pursuit'
_BREAKDOWN_TYPE         = 'breakdownType'

_UID                    = 'UID'  # Field name for anything that is a UID

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
        path, sheet                     = _parse_url(self.l0_url)
        #reader                           = ExcelTableReader(url=self.l0_url, excel_range=self.l0_excel_range)
        reader                           = ExcelTableReader(path, sheet, excel_range=self.l0_excel_range)
        root_trace                       = FunctionalTrace(None).doing("About to read Excel into a dataframe",
                                                                data = {'url': self.l0_url, 'excel_range': self.l0_excel_range})
        l0_df                            = reader.read(root_trace)
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
        path, sheet         = _parse_url(url)
        #reader              = ExcelTableReader(url, excel_range)
        reader              = ExcelTableReader(path, sheet, excel_range)

        root_trace                       = FunctionalTrace(None).doing("About to read Excel into a dataframe",
                                                                data = {'url': url, 'excel_range': excel_range})
        l2l3_df             = reader.read(root_trace)
        root_trace          = FunctionalTrace(None).doing("Building level 2 breakdown")

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
                l3_full_UID_i, l3_leaf_UID_i    = self.uid_store.generateUID(   parent_trace = root_trace,
                                                                                acronym=L3[0], 
                                                                                parent_UID=l2_full_UID_n)
                l3_children_n[l3_leaf_UID_i]    = {'description': l3_i, 'UID': l3_full_UID_i}

            elif (type(l2_i)==str and len(l2_i)>0): # We just entered a new Level 2
                l2_full_UID_n, l2_leaf_UID_n    = self.uid_store.generateUID(   parent_trace = root_trace,
                                                                                acronym    = _acronym(L2[0]), 
                                                                                parent_UID = link.L1_UID)
                l3_full_UID_i, l3_leaf_UID_i    = self.uid_store.generateUID(   parent_trace = root_trace,
                                                                                acronym    = _acronym(L3[0]), 
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


_PRODUCT              = 'product'
_JOURNEY              = 'journey'
_PLAN_TYPE            = 'planType'
_SCENARIO             = 'scenario'
_ENVIRONMENT          = 'environment'
_SCORING_CYCLE        = 'scoringCycle'
_SCORING_MATURITY     = 'scoringMaturity'
_ESTIMATED_BY         = 'estimatedBy'
_ESTIMATED_ON         = 'estimatedOn'
_RECORDED_BY          = 'recordedBy'

_CONTEXT_FIELDS = [_PRODUCT, _JOURNEY, _PLAN_TYPE, _SCENARIO, _ENVIRONMENT,
                  _SCORING_CYCLE, _SCORING_MATURITY, 
                  _ESTIMATED_BY, _ESTIMATED_ON, _RECORDED_BY]


def DEPRECATEDapplyMarathonJourneyPlan(ctx, url, excel_range, repo_root_dir):
    product             = ctx[_PRODUCT]
    scoring_cycle       = ctx[_SCORING_CYCLE]
    plan_maturity       = ctx[_SCORING_MATURITY]
    environment         = ctx[_ENVIRONMENT]
    planning_scenario   = ctx[_SCENARIO]
    estimating_mgr      = ctx[_ESTIMATED_BY]
    user                = ctx[_RECORDED_BY]
    plan_type           = ctx[_PLAN_TYPE]
    journey             = ctx[_JOURNEY]
    
    BAD_SCHEMA_MSG      = "Bad estimation date provided in context"
    estimation_date     = SchemaUtils.to_yaml_date(ctx[_ESTIMATED_ON], BAD_SCHEMA_MSG)
    
    path, sheet         = _parse_url(url)
    #reader              = ExcelTableReader(url, excel_range)
    reader              = ExcelTableReader(path, sheet, excel_range)
    
    root_trace          = FunctionalTrace(None).doing("About to read Excel into a dataframe",
                                                                data = {'url': self.l0_url, 'excel_range': self.l0_excel_range})
    plan_df             = reader.read(root_trace)
    if len(plan_df.columns) != 2:
        raise ValueError ("Badly formatted Marathon Plan: should have exactly two columns, ideally called: 'Workstream' and "
                         + "'Effort'. Error when processing range= '" + excel_range + "' and url=\n\t" + url)
    plan_df.columns     = ['Workstream', 'Effort']
    
    # Drop workstreams that were not defined
    plan_df             = SchemaUtils.drop_blanks(plan_df, 'Workstream')
   
    
    manifest_dict       = {}
    workstreams         = []
    WORKSTREAM_ID       = 1
    
    BAD_SCHEMA_MSG      = "Incorrect schema for a Marathon Plan in range '" + excel_range + "'."
    M                   = SchemaUtils.ValidationMonad(BAD_SCHEMA_MSG)
    
    for row in plan_df.iterrows():
        workstream      = row[1]['Workstream']
        effort          = row[1]['Effort']
        effort          = M.validate(effort).is_of_type([float, int])
        
        workstreams.append({'workstream'   : workstream, 
                            'effort'       : effort, 
                            'workstream-id': 'ws-' + str(WORKSTREAM_ID)})
        WORKSTREAM_ID += 1

    # Namespae would typically be something like 'Development' or 'Production'
    metadata      = {'namespace': environment + '.' + scoring_cycle, 
                     'name': product + '.' + journey + '.' + planning_scenario,
                     'labels': {'product': product, 'scoringCycle': scoring_cycle, 'scenario': planning_scenario,
                                                  'journey': journey}}

    manifest_dict['apiVersion']     = 'journeys.inbound.a6i.io/v1dev'
    manifest_dict['kind']           = 'JourneyPlan'
    manifest_dict['metadata']       = metadata
    # Plan maturity can be one of: 'Not done', 'Drafted', 'Checked', 'Published'
    manifest_dict['planMaturity']   = plan_maturity
    manifest_dict['plan']           = {'type': plan_type, 
                                       'estimated_by': estimating_mgr, 
                                        'estimated_on': estimation_date,
                                        'recorded_by': user,
                                       'workstreams': workstreams}    
    
    _yaml.dump(manifest_dict, _sys.stdout)
    
    with open(repo_root_dir + '/' + product + '-marathon-plan.yaml', 'w') as file:
        _yaml.dump(manifest_dict, file)


def DEPRECATEDapplyInvestmentCommittment(ctx, url, excel_range, repo_root_dir):
    
    product             = ctx[_PRODUCT]
    scoring_cycle       = ctx[_SCORING_CYCLE]
    plan_maturity       = ctx[_SCORING_MATURITY]
    environment         = ctx[_ENVIRONMENT]
    planning_scenario   = ctx[_SCENARIO]
    committing_mgr      = ctx[_ESTIMATED_BY]
    user                = ctx[_RECORDED_BY]
    plan_type           = ctx[_PLAN_TYPE]
    journey             = ctx[_JOURNEY]
    
    BAD_SCHEMA_MSG      = "Bad estimation date provided in context"
    committing_date     = SchemaUtils.to_yaml_date(ctx[_ESTIMATED_ON], BAD_SCHEMA_MSG)
    
    # Load data and validate its geometric shape
    path, sheet         = _parse_url(url)
    #reader              = ExcelTableReader(url, excel_range)
    reader              = ExcelTableReader(path, sheet, excel_range)

    root_trace          = FunctionalTrace(None).doing("About to read Excel into a dataframe",
                                                                data = {'url': self.l0_url, 'excel_range': self.l0_excel_range})
    plan_df             = reader.read(root_trace)
    if len(plan_df.columns) != 2:
        raise ValueError ("Badly formatted Investment Plan: should have exactly two columns, "\
                          + "ideally called: 'Period' and Investment'. "\
                          + "Error when processing range= '" + excel_range + "' and url=\n\t" + url)
    plan_df.columns = ['Period', 'Investment']
    
    # Drop workstreams that were not defined
    plan_df             = SchemaUtils.drop_blanks(plan_df, 'Period')
    
    manifest_dict = {}
    investment_ts   = []
    BAD_SCHEMA_MSG      = "Incorrect schema for a Investment Plan in range '" + excel_range + "'."
    M                   = SchemaUtils.ValidationMonad(BAD_SCHEMA_MSG)
    
    for row in plan_df.iterrows():
        period          = row[1]['Period']
        investment      = row[1]['Investment']
        investment      = M.validate(investment).is_of_type([float, int])
        investment_ts.append({'period'      : period, 
                              'investment'  : investment,
                              'units'       : 'person-days'})

    # Namespace would typically be something like 'Development' or 'Production'
    metadata      = {'namespace': environment + '.' + scoring_cycle, 
                     'name'     : product + '.' + journey + '.' + planning_scenario,
                     'labels'   : {'product': product, 
                                   'scoringCycle': scoring_cycle, 
                                   'scenario': planning_scenario,
                                   'journey': journey}}

    manifest_dict['apiVersion']     = 'journeys.inbound.a6i.io/v1dev'
    manifest_dict['kind']           = 'JourneyInvestment'
    manifest_dict['metadata']       = metadata
    # Plan maturity can be one of: 'Not done', 'Drafted', 'Checked', 'Published'
    manifest_dict['planMaturity']   = plan_maturity
    manifest_dict['committment']           = {'committed_by': committing_mgr, 
                                              'committed_on': committing_date,
                                              'recorded_by': user,
                                              'investment': investment_ts}    
    
    _yaml.dump(manifest_dict, _sys.stdout)
    
    with open(repo_root_dir + '/' + product + '-investment-committment.yaml', 'w') as file:
        _yaml.dump(manifest_dict, file)

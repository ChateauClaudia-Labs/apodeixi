#import pandas      as _pd
import yaml        as _yaml
import re          as _re
import sys         as _sys
import os          as _os
import math        as _math
import datetime    as _datetime

from .xlimporter import ExcelTableReader

class UID_Store:
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
            '''
            link_dict                                = {}
            link_dict[l2_key]                        = l2_children
            streams_dict[link.L1_UID]  = link_dict
            '''
            l1_key                      = link.L1_UID + '-detail' # For example, 'W.03-detail'
            if l1_key not in streams_dict.keys():
                streams_dict[l1_key]    = {}
            streams_dict[l1_key][l2_key] = l2_children
            
        _yaml.dump(manifest_dict, _sys.stdout)

        with open(self.manifests_repo_dir + '/' + pursuit + '-breakdown.yaml', 'w') as file:
            _yaml.dump(manifest_dict, file)
    
    def _nice(txt):
        return txt.strip().lower().replace(' ', '-')
    
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
        
    def _strip(txt):
        '''
        Removes any whitespace or other "noise" from txt and return sit
        '''
        if type(txt)==float and _math.isnan(txt):
            return ''
        stripped_txt = str(txt).replace('\n', '').strip(' ')
        return stripped_txt
    
    def _cleanup_UID(txt):
        '''
        If the 'txt' finishes in a number but lacks a dot required for UIDs (e.g., txt="W4" or "W-4" instead of "W.04")
        it will return the correctly formatted txt ("W.04")
        '''
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
            l1_uid                       = BreakdownBuilder._cleanup_UID(l1_data[UID])
            l0_dict[l1_uid]              = l1_data[TITLE]
            l0_dict[l1_uid + '-detail']  = {}
            for idx in range(2, len(columns)):
                col                      = columns[idx]
                l1_details_dict          = l0_dict[l1_uid + '-detail']
                l1_details_dict[col]     = l1_data[col]

        return l0_dict
    
    def _buildLevel2Breakdown(self, link):
        '''
        Returns a pair of a key and a sub-dictionary for a portion of the YAML to be built by this class.
        
        Below is an example of the YAML fragment that callers can build from the sub-dictionary created in this function.
        The example correspond to an Excel spreadsheet block that has columns called: 
        'UID', 'Expectation', 'Description', 'Acceptance Criteria Artifact', 'Evidence of correctness'

        expectations:
          E.01.01: Segment market using "jobs-to-be-done"
          E.01.01-detail:
            description: Follow methodology from Clayton Christensen
            acceptance-criteria-artifacts:
            - AC.01.01.01: Analysis of verticals, tiers, and geos evidence-of-correctness: a written analysis
            - AC.01.01.02 Sizing per segment
              evidence-of-correctness: a chart with sizings
          E.01.02: Deliver on time
          E.01.02-detail:
            description: stick to agreed milestones
            acceptance-criteria-artifacts:
            - AC.01.02.01 Project plan showing dates and staffing levels
              evidence-of-correctness: a Gant chart
            - AC.01.02.02 Completion of GA version 
              evidence-of-correctness: a monitoring report proving delivery to production
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
        l3_UID_i            = None
        
        # Data that changes on the nth time a new Level 2 is entered
        l3_children_n       = {}
        l2_UID_n            = None

        # Data constructed in subsequent cycles of loop
        all_l2s_dict        = {}
        
        # YAML-friendly keys derived from the columns (e.g., "Acceptance Criteria" becomes "acceptance-criteria")
        Y_L2                = BreakdownBuilder._nice(L2) + "s" # Plural, as we have multiple level 2 things
        Y_L2_DESC           = BreakdownBuilder._nice(L2_DESC)
        Y_L3                = BreakdownBuilder._nice(L3) + "s" # Plural, as we have multiple level 3 things
        Y_L3_DESC           = BreakdownBuilder._nice(L3_DESC)

        for row in l2l3_df.iterrows(): # nth cycle of loop
            data_i                       = row[1]
            l2_i                         = data_i[L2]
            l2_desc_i                    = BreakdownBuilder._strip(data_i[L2_DESC])
            l3_i                         = data_i[L3]
            l3_desc_i                    = BreakdownBuilder._strip(data_i[L3_DESC])
            
            if BreakdownBuilder.      _is_blank(l2_i): # We are within the same Level 2 as in prior cycle of the loop
                l3_UID_i                 = self.uid_store.generateUID(acronym=L3[0], parent_UID=l2_UID_n)
                l3_children_n[l3_UID_i]  = l3_i

            elif (type(l2_i)==str and len(l2_i)>0): # We just entered a new Level 2
                l2_UID_n                 = self.uid_store.generateUID(acronym    = BreakdownBuilder._acronym(L2[0]), 
                                                             parent_UID = link.L1_UID)
                l3_UID_i                 = self.uid_store.generateUID(acronym    = BreakdownBuilder._acronym(L3[0]), 
                                                             parent_UID = l2_UID_n)
                
                l3_children_n           = {}
                l3_children_n[l3_UID_i] = l3_i
                
                l2_dict_i               = {}
                l2_dict_i[Y_L2_DESC]    = l2_desc_i
                l2_dict_i[Y_L3]         = l3_children_n
                
                all_l2s_dict[l2_UID_n]   = l2_i 
                
                all_l2s_dict[l2_UID_n + '-detail']    = l2_dict_i
            else:
                raise ValueError("Expected a string or a blank, not a '" + str(type(l2_i)) 
                                 + '(row=' + str(row[0]) + " and text is '" + str(l2_i) + "')")
            

        return Y_L2, all_l2s_dict
    
    def _acronym(txt):
        '''
        Returns a string of initials for 'txt', in uppercase
        '''
        stripped_txt = BreakdownBuilder._strip(txt)
        tokens       = stripped_txt.split(' ')
        acronym      = ''.join([token[0].upper() for token in tokens])
        return acronym
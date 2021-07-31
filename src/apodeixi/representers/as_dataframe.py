import yaml                             as _yaml
import pandas                           as _pd

from apodeixi.util.a6i_error            import ApodeixiError
from apodeixi.xli                       import BreakdownTree, Interval, UID_Store

class AsDataframe_Representer:
    '''
    Class that can represent an Apodeixi manifest as a Pandas DataFrame
    '''
    def __init__(self):
        return

    def yaml_2_df(self, parent_trace, manifests_folder, manifests_file, contents_path):
        '''
        Loads a YAML file for an Apodeixi manifest, and returns a Pandas Dataframe for the data contents
        and a dictionary for all other fields
        
        @param contents_path A string using 'dot notation' to convey a path in a dictionary. For example,
                             for a dictionary  like this:
        .. code::
            
            {a: 
                {b: 5, c: 6, streams: {W1: {UID: S1.W1, cost: 4, name: 'requirements gathering'}, 
                                       W2: {UID: S1.W2, cost: 5, name: 'design'}},
                 g: 23
                }
            }
            
        then if contents-path=`a.streams` that denotes the sub-tree 
        
        .. code::

            {W1: {UID: S1.W1, cost: 4, name: 'requirements gathering'}, 
                                       W2: {UID: S1.W2, cost: 5, name: 'design'}}
 
        which will be turned into DataFrame like

        .. code::

            df =    | UID   |     streams               | cost  |
                    ---------------------------------------------
                    | S1.W1 | requirements gathering    |   4    |
                    | S1.W2 | design                    |   5    |
        
        The function also computes the remaining subtree, which in this example is:

        .. code::
            
            {a: 
                {b: 5, c: 6, 
                 g: 23
                }
            }
        
        The return value is the tuple `(df, subtree)`
        '''
        manifest_path       = manifests_folder + '/' + manifests_file
        my_trace            = parent_trace.doing('Loading YAML Manifest', data = {'path': manifest_path})
        with open(manifest_path, 'r') as file:
            manifest_dict   = _yaml.load(file, Loader=_yaml.FullLoader)

        path_tokens         = contents_path.split('.')
        
        # Create the dictionary of everything except what is in the path  
        my_trace             = parent_trace.doing('Splitting manifest', data = {'path_tokens': path_tokens})
        content_dict, non_content_dict = self._split_out(my_trace, manifest_dict, path_tokens)

        df                  = self.dict_2_df(parent_trace, content_dict, contents_path)
        return df, non_content_dict


    def dict_2_df(self, parent_trace, content_dict, contents_path):

        my_trace            = parent_trace.doing('Converting content to DataFrame')
        intervals, rows     = self._build_df_rows(  parent_trace    = my_trace,
                                                    content_dict    = content_dict,
                                                    parent_path     = contents_path,
                                                    parent_uid      = None)
        
        all_columns         = []
        for interval in intervals:
            all_columns.extend(interval.columns)
            
        df                  =  _pd.DataFrame(columns=all_columns, data=rows)
        df                  = df.fillna('')

        return df
    
    def _split_out(self, parent_trace, manifest_dict, splitting_path):
        '''
        Spits the `manifest_dict` into two dictionaries, based on the `splitting_path`: 
        
        * the `off_path_dict`, which is a sub-dictionary of `manifest_dict` consisting of everything not
          under the `splitting path`
        * the `on_path_dict`, which is the sub-dictionary under that `splitting_path`.
        
        Returns the pair `(on_path_dict, off_path_dict)
        
        For example, if `manifest_dict` is given by
        
        .. code-block::
            
            {a: 
                {b: 5, c: 6, d: {e:4, f: 5},
                 g: 23
                }
            }
            
        then if splitting_path=`a.d` then the `on_path_dict` is 
        
        .. code-block::
            off_path_dict = {a: 
                                {b: 5, c: 6,
                                 g: 23
                                }
                            }        
        
        
            on_path_dict  = {e:4, f: 5}
                
        @param manifest_dict
        @param path_to_filter A list of strings, for a path to split the manifest_dict against
        '''
        off_path_dict                           = {}
        on_path_dict                            = {}
        
        if len(splitting_path) == 0: # This means we hit bottom, and everything is on path
            off_path_dict                       = {}
            on_path_dict                        = manifest_dict
        else:
            head                                = splitting_path[0]
            tail                                = splitting_path[1:]
            # First handle children other than the head
            for child in [key for key in manifest_dict.keys() if key != head]:
                off_path_dict[child]            = manifest_dict[child]
            # Now we use recursion:
            sub_dict                            = manifest_dict[head]
            my_trace                            = parent_trace.doing('Recursively splitting', data = {'tail': tail})
            on_path_dict, off_path_sub_dict     = self._split_out(my_trace, sub_dict, tail)
            if len(off_path_sub_dict.keys()) > 0:
                off_path_dict[head]             = off_path_sub_dict
                
        return on_path_dict, off_path_dict
    
    def _build_df_rows(self, parent_trace, content_dict, parent_path, parent_uid):
        '''
        Creates the data from which a Pandas DataFrame can be easily created by the caller,
        based on the dictionary `content_dict`: it returns:
        
        * The list of intervals whose concatenation would yield the columns for such a DataFrame-to-be
        * The list of rows (as dictionaries)
        
        The keys of `content_dict` are expected to be "incremental UID pairs" for the entity type given by the
        last token in `parent_path`. 
        
        For example, if `parent_path` is "S1.Workstream", then the entity type is "Workstream".
        
        As for the "incremental UID pairs" in `contect_dict`, that is best understood with an example:
        
        Consider again the entity called 'Workstream' with a parent path of "S1.Workstream". The UIDs
        of its children might be something like `S1.W0, S1.W1, S1.W2`.
        
        However, in `content_dict` only the incremental UIDs would appear as keys: `W0, W1, W2`, each as
        root to a dictionary.
        
        Because of the conventions in apodeixi.xli.breakdown_builder that were
        used to build such `content-dict`, there will also be keys in `content-dict` called
        `W0-name, W1-name, W2-name` for YAML readability reasons. Yet these are not UIDs, but we call
        the pair `(Wi, Wi-name)` a "(incremental) UID pair" in this context.
        
        For purposes of building the DataFrame, we are only interested in "real content", i.e., the
        sub-dictionaries under each (incremental) UID keys `W-, W1, W2` in `content-dict`, 
        not under the `UID-name` keys.
        
        @param parent_path A string using 'dot notation' for the path in the original YAML file that led
                          to the `content_dict`. For example, "W2.workstream"
        '''
        my_trace                = parent_trace.doing("Validating parent_path '" + parent_path + "''",
                                                        data = {'signaledFrom': __file__})
        if True:
            if parent_path == None or len(parent_path.strip()) == 0:
                raise ApodeixiError(my_trace, "Can't process a parent_path that is null or blank")
        
        path_tokens             = parent_path.split('.')
        entity_name             = path_tokens[-1]
        
        entity_uids             = [key for key in content_dict.keys() if not key.endswith('-name')]
        all_rows                = [] # Will be one per entity_value, a dictionary of level_1_columns -> scalar value
        
        # Some manifest field names that have fixed, hard-coded values in Apodeixi
        UID                     = Interval.UID
        NAME                    = 'name'
        SYNTHETIC_COLUMNS       = [UID, NAME] # These are added when parsing Excel, so not "real" content
        
        if parent_uid == None:
            UID_COL             = UID
        else:
            UID_COL             = UID + '-' + str(len(parent_uid.split('.')))
        
        my_trace                = parent_trace.doing("Processing interval for '" + entity_name + "'",
                                                        data = {'signaledFrom': __file__})
        all_intervals           = []
        my_interval             = Interval(parent_trace = my_trace, columns = [UID_COL, entity_name], entity_name = entity_name)
        
        all_intervals.append(my_interval)
        
        for e_uid in entity_uids:
            # Example: e_uid might be 'W2' and full_e_uid might be 'S1.W2'
            if parent_uid == None:
                full_e_uid      = e_uid
            else:
                full_e_uid      = parent_uid + '.' + e_uid
                
            e_path              = parent_path  + '.' + e_uid
            loop_trace          = parent_trace.doing("Looping on entity with path '" + e_path + "'",
                                                    data = {'signaledFrom': __file__})
            e_dict              = content_dict[e_uid]

            inner_trace         = loop_trace.doing("Checking tree under '" + e_path + "' is well formed",
                                            data = {'signaledFrom': __file__})
            if True:
                # Check e.g. parent.workstreams[W2] exists
                if e_dict == None:
                    raise ApodeixiError(inner_trace, "Badly formatted tree: found nothing under '" + e_path + "'")
                # Check e.g. parent.workstreams[W2] is a dictionary
                if type(e_dict) != dict:
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected dictionary at '" + e_path
                                                       + "' but instead found a " + str(type(e_dict)))
                # Check e.g. parent.workstreams[W2][UID] exists
                if not UID in e_dict.keys():
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected a child called '" + UID
                                                    + "' under '" + e_path + "'") 
                # Check e.g. parent.workstreams[W2][UID] == W2
                if e_dict[UID] != full_e_uid:
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected '" + e_path
                                                   + "[" + UID + "] = " + full_e_uid + "'", 
                                                   data = {"expected": full_e_uid, "actual": str(e_dict[UID])})
                # Check e.g. parent.workstreams[W2]['name'] exists
                if not NAME in e_dict.keys():
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected a child called '" + NAME
                                                    + "' under '" + e_path + "'") 
                    
            new_level_1_row                 = {}
            # Add the entity column to the level_1 row
            # But first replace by "friendly" UID like 1.2 instead of BR1.B2
            abbreviated_full_e_uid          = UID_Store(parent_trace).abbreviate_uid(parent_trace, uid=full_e_uid)
            new_level_1_row[UID_COL]        = abbreviated_full_e_uid #full_e_uid
            new_level_1_row[entity_name]    = e_dict[NAME]
            
            # While Apodeixi's data model allows more manifests where an entity can branch out in more than one way
            # for purposes of representing a manifest tree as a DataFrame we can only allow at most one branching out
            # below any one entity. So check that
            sub_entities                    = self._find_sub_entities(e_dict) # should find at most 1
            if len(sub_entities) > 1:
                raise ApodeixiError(loop_trace, "At most one sub entity is allowed, but found several: " 
                                    + sub_entities)
            for attrib in [a for a in e_dict.keys() if not a in sub_entities and a not in SYNTHETIC_COLUMNS]:
                if not attrib in my_interval.columns:
                    my_interval.columns.append(attrib)
                new_level_1_row[attrib]     = e_dict[attrib]
            sub_rows                        = []
            sub_intervals                   = []
            if len(sub_entities) > 0: # By now we know this is at most 1
                sub_entity                  = sub_entities[0]
                inner_trace                 = loop_trace.doing("Making a recursive call for '" + sub_entity + "'",
                                                                data = {'signaledFrom': __file__})
                
                sub_intervals, sub_rows     = self._build_df_rows(  parent_trace    = inner_trace, 
                                                                    content_dict    = e_dict[sub_entity], 
                                                                    parent_path     = e_path + '.' + sub_entity,
                                                                    parent_uid      = full_e_uid)

            self._merge_interval_lists(loop_trace, all_intervals, sub_intervals)
            
            # Change of algorithm made on July 29, 2021: 
            #
            # it used to be that we would display the
            # first sub-entity in the same row as its parent entity. That was modified to have it displayed
            # in the *next* row instead, to force that each UID is in a different row and make it easier
            # to make "joins". 
            # For example, UIDs "BR1" and "BR1.B1" used to be in the same row, with "BRI1.B2" in a row below.
            # So these 3 UIDs would appear in 2 rows in the DataFrame.
            # This caused ambiguity for joins: if the end-user expresses a join in Excel against the row that contains
            # both "BR1" and "BR1.B1", how can one tell which of these two UIDs is the join with?
            # To remedy this, after July 29, 2021 we changed that so that each UID would be in its own row.
            # In our example, that means 3 rows:  one for "BR1", follwed by one for "BR1.B1"
            # below it, and below that a 3rd row for "BR1.B2".
            # As a result, the code below was changed to input empty strings into anything that used to be
            # contributed to the "BR1" row by "BR1.B1" data.
            if len(sub_rows) > 0:
                # Merge 1st sub_row into the new_level_1_row
                first_sub_row               = sub_rows[0]
                for k in first_sub_row.keys():
                    new_level_1_row[k]      = '' # Changed to empty string on 7/29/21. Used to be: first_sub_row[k]
                     
            all_rows.append(new_level_1_row)
            # Now add the other sub_rows, the ones after the first one that go after new_level_1_row
            for idx in range(0, len(sub_rows)): # Changed to start from 0 on 7/29/21. Used to start at 1
                all_rows.append(sub_rows[idx])
        
        # Temporary return value, for testing
        return all_intervals, all_rows
        
    def _find_sub_entities(self, content_dict):
        '''
        Finds the sub-entities in `content_dict`, defined as any child that is a dictionary and not
        a scalar.
        
        Returns a list of strings for the keys of all such children
        '''
        sub_entities                    = []
        for k in content_dict.keys():
            child                       = content_dict[k]
            if type(child) == dict:
                sub_entities.append(k)
        return sub_entities
    
    def _merge_2_intervals(self, parent_trace, growing, contributing):
        '''
        Helper methods that merges intervals for the same entity. expand growingInterval if needed
        so that all the columns on contributing
        
        @param growing an Interval to expand by adding columns from `contributing`
        @param contributing an Interval whose columns should be added to growing, if they are not already present
        '''
        if growing.entity_name != contributing.entity_name:
            raise ApodeixiError(parent_trace, "Can't merge intervals for different entities: ''" 
                                + growing.entity_name + "' and '" + contributing.entity_name + "'")
        for c in contributing.columns:
            if not c in growing.columns:
                growing.columns.append(c)
    
    def _merge_interval(self, parent_trace, interval_list, contributing):
        '''
        Merges the Interval `contributing` into the list of intervals `interval_list`, following these
        procedures:
        
        * If none of the intervals in `interval_list` is for the same entity as `contributing`, then we
          add `contributing` as another member at the end of `interval_list`. 
        * If on the other hand there is an index idx such that interval_list[idx] is for the same entity
          as `contributing`, then we enlarge interval_list[idx] so that its columns include those of 
          `contributing`. 
          This can happen if there are some properties for an entity are "optional". 
          For example, perhaps we are processing a manifest dict arose from parsing a posting like this:

                UID         |   Big rock        |   Asset classes           | Intended user
                ===========================================================================
                BR1         | Lending UI        |  Mortgages, commercial    |
                BR2         | Treasury UI       |                           | FX traders

          Then the manifest will have a branch for the first row that will make us infer an
          interval like 
          
                [UID, Big rock, Asset classes]
                
          Later when we process the manifest's branch that arose from the second row we will instead get 
          an interval like 
          
                [UID, Big rock, Intended user]
           
          The correct "merge" behavior in such case is not to treat these as separate intervals, but to merge them 
          as 
                [UID, Big rock, Asset classes, Intended user]

          
        @param interval_list A list of Interval objects. It is modified by this method
        @param contributing An Interval object
        '''
        for interval in interval_list:
            if interval.entity_name == contributing.entity_name:
                self._merge_2_intervals(parent_trace, interval, contributing)
                return
        # If we get this far, then we have a brand new entity
        interval_list.append(contributing)
                  
    def _merge_interval_lists(self, parent_trace, growing_list, contributing_list):
        '''
        Helper method to merge intervals from `contributing_list` into the `growing_list`, ensuring
        that there is at most one interval per entity. So if two intervals from each list are
        from the same entity, their columns get merged into 1 interval, as opposed to ending up with 2
        intervals
        
        @param growing_list A list of Interval objects. It is modified by this method
        @param contributing_list A list of interval_objects
        '''
        for interval in contributing_list:
            self._merge_interval(parent_trace, growing_list, interval)
        
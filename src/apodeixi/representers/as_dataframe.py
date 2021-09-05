
import yaml                             as _yaml
import pandas                           as _pd

from apodeixi.util.a6i_error            import ApodeixiError
from apodeixi.xli                       import Interval
from apodeixi.xli.uid_store             import UID_Utils

class AsDataframe_Representer:
    '''
    Class that can represent an Apodeixi manifest as a Pandas DataFrame
    '''
    def __init__(self):
        return

    def yaml_2_df(self, parent_trace, manifests_folder, manifests_file, contents_path, sparse, abbreviate_uids):
        '''
        Loads a YAML file for an Apodeixi manifest, and returns a Pandas Dataframe for the data contents
        and a dictionary for all other fields
        
        @param sparse A boolean. If True, it returns a "sparse" representation suitable for Excel rendering,
                    with exactly 1 UID per row (helpful when making joins). 

                    If on the other hand sparse=False then a "full" representation is returned, more suitable
                    for data analysis in Pandas. 

                    For examples and details, refer to the documentation for`self.dict_2_df`

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

        @param abbreviate_uids A boolean. If True, UIDs will only keep the top acronym. For example, 
                    a UID like "BR2.MR2.SM4" in the manifest would be transformed to "BR2.2.4" in the
                    DataFrame returned by this method
        '''
        manifest_path       = manifests_folder + '/' + manifests_file
        my_trace            = parent_trace.doing('Loading YAML Manifest', data = {'path': manifest_path})
        with open(manifest_path, 'r') as file:
            manifest_dict   = _yaml.load(file, Loader=_yaml.FullLoader)

        path_tokens         = contents_path.split('.')
        
        # Create the dictionary of everything except what is in the path  
        my_trace             = parent_trace.doing('Splitting manifest', data = {'path_tokens': path_tokens})
        content_dict, non_content_dict = self._split_out(my_trace, manifest_dict, path_tokens)

        df                  = self.dict_2_df(parent_trace, content_dict, contents_path, sparse, abbreviate_uids)
        return df, non_content_dict

    def dict_2_df(self, parent_trace, content_dict, contents_path, sparse, abbreviate_uids):
        '''
        Used to represent the contents of a manifest as a Pandas DataFrame. There are two main
        use cases for what such DataFrame would be used for, and the needs of each of them
        are catered to depending on how the `sparse` parameter is set:

        * As input to subsequent processing to render an Excel visualization (using sparse=True)
        * As input to data analysis in Pandas (using sparse=False). 
        
        Refer to detailed documentation for method `self._build_df_rows`, that does the heavy lifting.

        @param contents_dict A dict object representing the contents of a manifest, as opposed to the
                            entire manifest. For example, if manifest_dict represents a full manifest in 
                            the Journeys domain, the content_df = manifest_dict['assertion']['journey']
        @param contents_path A string using 'dot notation' for the path in the original YAML file that led
                          to the `content_dict`. For example, "assertion.journey"
        @param sparse A boolean. If True, it returns a "sparse" representation suitable for Excel rendering,
                    with exactly 1 UID per row (helpful when making joins), such as this:

                UID |      Big Rock         | UID-1 |     Sub rock
            =============================================================
                BR1 |   New UX              |       |   
                    |                       | BR1.1 |   FX UI
                    |                       | BR1.2 |   Lending UI
                BR2 |   Containerization    |       |   
                    |                       | BR2.1 |   Pricing service
                    |                       | BR2.2 |   Market data svc

                If on the other hand sparse=False then a "full" representation is returned, more suitable
                for data analysis in Pandas:

                UID |      Big Rock         | UID-1 |     Sub rock
            ==============================================================
                BR1 |   New UX              | BR1.1 |   FX UI
                BR1 |   New UX              | BR1.2 |   Lending UI
                BR2 |   Containerization    | BR2.1 |   Pricing service
                BR2 |   Containerization    | BR2.2 |   Market data svc

        @param abbreviate_uids A boolean. If True, UIDs will only keep the top acronym. For example, 
                    a UID like "BR2.MR2.SM4" in the manifest would be transformed to "BR2.2.4" in the
                    DataFrame returned by this method
        '''
        my_trace            = parent_trace.doing('Converting content to DataFrame')

        # For reasons explained in the documentation of the method _find_acronyminfo_list, we need to do a first
        # pass to get the correct, holistic set of acronyms before we call the _build_df_rows method
        all_acronyminfos    = self._find_acronyminfo_list(  parent_trace        = my_trace, 
                                                            content_dict        = content_dict, 
                                                            parent_path         = contents_path, 
                                                            parent_uid          = None)

        intervals, rows     = self._build_df_rows(          parent_trace        = my_trace,
                                                            content_dict        = content_dict,
                                                            all_acronyminfos    = all_acronyminfos,
                                                            parent_path         = contents_path,
                                                            parent_uid          = None,
                                                            sparse              = sparse,
                                                            abbreviate_uids     = abbreviate_uids)
        
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
    
    def _build_df_rows(self, parent_trace, content_dict, all_acronyminfos, parent_path, parent_uid, sparse,
                                abbreviate_uids):
        '''
        Recursive method that creates the data from which a Pandas DataFrame can be easily created by the caller,
        based on the dictionary `content_dict`: it returns:
        
        * The list of intervals whose concatenation would yield the columns for such a DataFrame-to-be (see 
            example below for an explanation)
        * The list of rows (each row represented as a dict, whose keys are DataFrame columns, at least those
            columns for which the row has a non-NaN value)

        The rows might be populated to be "sparse" or not, depending on the `sparse` paremeter (a boolean).
        This is best explained in an example. The following is a non-sparse DataFrame:

                UID |      Big Rock         | UID-1 |     Sub rock
            ==============================================================
                BR1 |   New UX              | BR1.1 |   FX UI
                BR1 |   New UX              | BR1.2 |   Lending UI
                BR2 |   Containerization    | BR2.1 |   Pricing service
                BR2 |   Containerization    | BR2.2 |   Market data svc

        This "non sparse" representation is well suited for making data analysis.

        In contrast, the "sparse" representation is geared towards visualization in Excel, where usability
        calls for leaving out repetitive text, replacing it by blanks since humans can easily infer
        what the values should be by glancing at preceding rows:

                UID |      Big Rock         | UID-1 |     Sub rock
            =============================================================
                BR1 |   New UX              |       |   
                    |                       | BR1.1 |   FX UI
                    |                       | BR1.2 |   Lending UI
                BR2 |   Containerization    |       |   
                    |                       | BR2.1 |   Pricing service
                    |                       | BR2.2 |   Market data svc

        In particular, the sparse representation has exactly 1 UID per row, using more rows if needed
        (in the example, the non-sparse representation has 4 rows but the sparse representation has 6 rows)

        This example also helps us comment some other nuances of the algorithm:

        1. The first object returned by this method is a "list of intervals", which in the example would be

                [["UID", "Big Rock"], ["UID-1", "Sub rock"]]

        2. The second object returned by this method is "all the rows as dictionaries", which for a sparse
            situation would be:

                [{  "UID": "BR1",   "Big Rock": "New UX"                                                                },          
                                                                  { "UID-1", "BR1.1",   "Sub rock": "FX UI"             },
                                                                  { "UID-1", "BR1.2",   "Sub rock": "Lending UI"        },
                 {  "UID": "BR2",   "Big Rock": "Contanerization"                                                       },  
                                                                  { "UID-1", "BR2.1",   "Sub rock": "Pricing service"   },
                                                                  { "UID-1", "BR2.2",   "Sub rock": "Market data svc"   },
                ]

        3. The dictionaries representing rows don't need to have all columns present as keys. Pandas can still
            create a DataFrame from that, and will just put a null (nan or such) as the value of that column for
            the row in question. The algorithm makes use of this.
        
        4. The UIDs are "abbreviated". For example, UID-1 has a value like "BR1.1" instead of "BR1.SR1". So only
            the first acronym "BR" (for "Big Rock") is displayed, not the second acronym "SR" (for Sub rock).
            This is for usability. The `contenct_dict` parameter is expected to contain non-abbreviated UIDs.

        5. The `content_dict` representing the manifest's content uses "incremental" non-abbreviated UIDs
            for its recursive structure ("recursive" as in: a dict that contains some children that are sub
            dictionaries, not just scalars). By "incremental" we mean that content_dict["BR1"] would be
            a dict and the children are accessed by keys like "SR1" and "SR2", not "BR1.SR1" and "BR1.SR2".
            Thus, in our example content_dict["BR1"]["SR1"] and content_dict["BR1"]["SR2"] are the
            expected way to naviate the "recursive" nature of the contect_dict.

        6. Because of the conventions in apodeixi.xli.breakdown_builder that were used to build 
            such `content_dict`, there are columns like "BR1-name" and "SR1-name". These are ignored by this
            method.

        7. This algorithm operates recursively, one interval at a time. In the example, we first process
            interval ["UID", "Big Rock"], first identify this row fragment:

             {  "UID": "BR1",   "Big Rock": "New UX"}

            The algorithm then makes a recursive call on `content_df["BR1"], which returns two objects:

                * A list of intervals: [["UID-1", "Sub rock"]], which is then merged with the caller's interval
                    list to date and results in [["UID", "Big Rock"], ["UID-1", "Sub rock"]]

                * A list of rows:
                                                                [ { "UID-1", "BR1.1",   "Sub rock": "FX UI"             },
                                                                  { "UID-1", "BR1.2",   "Sub rock": "Lending UI"        }
                                                                ]
                    These then need to be "merged" with the caller, and the merging varies depending on whether
                    sparse=True or not. In the sparse case, the merging would look like 3 rows:

                [{  "UID": "BR1",   "Big Rock": "New UX"                                                                },          
                                                                  { "UID-1", "BR1.1",   "Sub rock": "FX UI"             },
                                                                  { "UID-1", "BR1.2",   "Sub rock": "Lending UI"        }
                ]

                    In the case sparse=False, the merging would look like 2 rows:

                [{  "UID": "BR1",   "Big Rock": "New UX",           "UID-1", "BR1.1",   "Sub rock": "FX UI"             },
                 {  "UID": "BR1",   "Big Rock": "New UX",           "UID-1", "BR1.2",   "Sub rock": "Lending UI"        }
                ]

        8. Apart from sub-dictionaries, `content_dict` usually has scalar attributes. These need to be included
            in the rows when they have a value. 

        9. Scalar attributes introduce a nuance with the merging of intervals: as subsequent rows of the result
            are gradually created, the algorithm only has a partial view of what the intervals are, since it infers
            intervals' columns based on what it has seen so far. It thus may happen that when dealing with 
            a later row it will encounter additional columns for an entity's interval that had been previously
            seen. This must be taken into consideration in the merging of intervals.

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


        @param contents_dict A dict object representing the contents of a manifest, as opposed to the
                            entire manifest. 
                            In the first example above, if manifest_dict represents a full manifest, 
                            then content_df = manifest_dict['assertion']['big-rock']
        @param all_acronyminfos A list of _AcronymInfo objects, containing all the acronyms for `content_dict`
                            as well as their corresponding entity names. This should be
                            "global", i.e., is not for a "sub tree" but for the full manifest.
                            Example: [("BR", "big-rock"), ("MR", "medium_rock"), ("SR", "small rock")] 
                            where for clearer notation we use notation like("BR", "big-rock") to denote
                            _AcronyInfo("BR", "big-rock")
        @param parent_path A string using 'dot notation' for the path in the original YAML file that led
                          to the `content_dict`. 
                          In the first example above, that would be "assertion.big-rock" when this method is
                          first called, and "assertion.big-rock.BR1.Sub rock" when it recursively
                          calls itself.
        @param parent_uid   A string used to assist in recursive calls.
                            In the first example above, that would be None when this method is first called,
                            and "BR1" on a 1st recursion, or "BR1.SR1" on a 2nd nested recursion.
        @param sparse A boolean. If True, it returns a "sparse" representation suitable for Excel rendering,
                    with exactly 1 UID per row (helpful when making joins)
        @param abbreviate_uids A boolean. If True, UIDs will only keep the top acronym. For example, 
                    a UID like "BR2.MR2.SM4" in the manifest would be transformed to "BR2.2.4" in the
                    DataFrame returned by this method
        '''
        my_trace                = parent_trace.doing("Validating parent_path '" + parent_path + "''",
                                                        data = {'signaledFrom': __file__})
        if True:
            if parent_path == None or len(parent_path.strip()) == 0:
                raise ApodeixiError(my_trace, "Can't process a parent_path that is null or blank")
        
        # parent_path is something like "assertion.big-rock" when this method is first called, and 
        # like  "assertion.big-rock.BR1.Sub rock" when this method is calls recursively on itself
        path_tokens             = parent_path.split('.') 

        #entity_name             = path_tokens[-1] # like "big-rock" on 1st call, and "Sub rock" on recursive call
        
        entity_uids             = [key for key in content_dict.keys() if not key.endswith('-name')]

        # Will be one per entity_value, a dictionary of level_1_columns -> scalar value. By "level 1 columns"
        # we mean columns for the interval being processed here (subsequent intervals would be processed
        # in recursive invocations of this method). See method documentation for explanation of algorithm.
        all_rows                = [] 
        
        # Some manifest field names that have fixed, hard-coded values in Apodeixi
        UID                     = Interval.UID
        NAME                    = 'name'
        SYNTHETIC_COLUMNS       = [UID, NAME] # These are added when parsing Excel, so not "real" content
        
        all_intervals           = []

        # On a first call we loop through something like e_uid = "BR1", "BR2", "BR3", .... For that call
        #       parent_uid = None and parent_path = "assertion.big-rock"
        # On a recursive call with parent_uid = "BR1" we loop through e_uid = "SR1", "SR2", "SR3", .... In this case
        #       parent_path = "assertion.big-rock.BR1.Sub rock"
        for e_uid in entity_uids:
            if parent_uid == None:
                full_e_uid      = e_uid
            else:
                full_e_uid      = parent_uid + '.' + e_uid
                
            e_path              = parent_path  + '.' + e_uid
            e_dict              = content_dict[e_uid]
            loop_trace          = parent_trace.doing("Looping on entity with path '" + e_path + "'",
                                                    data = {'signaledFrom': __file__})

            inner_trace         = loop_trace.doing("Determining name to give to UID column in DataFrame for a UID",
                                                    data = {"entity UID": str(full_e_uid)})            
                
            e_acronym           = UID_Utils().parseToken(my_trace, e_uid)[0]
            e_acronyminfo_guesses   = [info for info in all_acronyminfos if info.acronym == e_acronym]
            if len(e_acronyminfo_guesses) != 1:
                raise ApodeixiError(my_trace, "Algorithm to infer acronyms seems to be making incorrect inferences: "
                                            " it does not recognize a unique acronym for entity's UID",
                                                data = {"entity_UID": str(e_uid),
                                                        "inferred acronyms": str(all_acronyminfos)})
            e_acronyminfo       = e_acronyminfo_guesses[0]
            level               = all_acronyminfos.index(e_acronyminfo)
            if level==0:
                UID_COL         = UID
            else:
                UID_COL         = UID + '-' + str(level) # We start at "UID-1", "UID-2", etc. "UID" is on  

            # Check if we already have an interval for this acronym info, and if not, create one
            my_prior_interval   = [interval for interval in all_intervals if e_acronyminfo.entity_name in interval.columns]
            if len(my_prior_interval) == 0:          
                my_interval     = Interval( parent_trace    = my_trace, 
                                            columns         = [UID_COL, e_acronyminfo.entity_name],
                                            entity_name     = e_acronyminfo.entity_name)
                all_intervals.append(my_interval)


            inner_trace         = loop_trace.doing("Checking tree under '" + e_path + "' is well formed",
                                            data = {'signaledFrom': __file__})
            if True:
                # Check e.g. if content_dict = manifest_dict["assertion"]["big-rock"]["BR1"]["SubRock"]
                # that content_dict["SR2"] exists
                if e_dict == None:
                    raise ApodeixiError(inner_trace, "Badly formatted tree: found nothing under '" + e_path + "'")
                # Check e.g. content_dict["SR2"] is a dictionary
                if type(e_dict) != dict:
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected dictionary at '" + e_path
                                                       + "' but instead found a " + str(type(e_dict)))
                # Check e.g. content_dict["SR2"]["UID"] exists
                if not UID in e_dict.keys():
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected a child called '" + UID
                                                    + "' under '" + e_path + "'") 
                # Check e.g. content_dict["SR2"]["UID"] == "SR2"
                if e_dict[UID] != full_e_uid:
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected '" + e_path
                                                   + "[" + UID + "] = " + full_e_uid + "'", 
                                                   data = {"expected": full_e_uid, "actual": str(e_dict[UID])})
                # Check e.g. content_dict["SR2"]["UID"]['name'] exists
                if not NAME in e_dict.keys():
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected a child called '" + NAME
                                                    + "' under '" + e_path + "'") 
                    
            # We call it "level 1" because it is for my_interval. Recursive calls would be the subsequent
            # intervals, which are "level 2, 3, ..." in the content_df "tree"
            new_level_1_row                 = {} 
            # Add the entity column to the level_1 row
            # But first replace by "friendly" UID like 'BR1.2' instead of "BR1.SR2", if we are thus configured
            if abbreviate_uids == True:
                abbreviated_full_e_uid      = UID_Utils().abbreviate_uid(parent_trace, uid=full_e_uid)
                new_level_1_row[UID_COL]    = abbreviated_full_e_uid 
            else:
                new_level_1_row[UID_COL]    = full_e_uid 
            new_level_1_row[e_acronyminfo.entity_name]    = e_dict[NAME]
            
            # Apodeixi's data model allows "multiple dimensional" branching. An example of branching is having
            # a "big-rock" entity "BR1" branch into multiple "Sub rock" entities "BR1.SR1", "BR1.SR2", "BR1.SR3", ...
            # "Multi-dimensional" branching happens if the "big-rock" entity can also branch into another
            # entity like "Epic", leading to children like "BR1.E1", "BR1.E2", "BR1.E3", ...
            # While that is allowed in the data model, it is not possible to represent such multi-dimensional
            # branching neatly in a tabular representation like a DataFrame.
            # So since this method is about creating such tabular representation, we will error out if we find that
            # "multi-dimensional" branching occurs in the manifest.
            sub_entities                    = self._find_sub_entities(e_dict) # should find at most 1
            if len(sub_entities) > 1:
                raise ApodeixiError(loop_trace, "At most one sub entity is allowed when representing a manifest as as "
                                                + " DataFrame, but found several: " 
                                    + sub_entities)

            # Now add the "scalar" attributes to the row and if needed also to the interval. A reason they may
            # not be in the interval already arises if we are creating the "first row" (i.e., entity e_uid) 
            # or if that attribute was not present in "previous rows"
            for attrib in [a for a in e_dict.keys() if not a in sub_entities and a not in SYNTHETIC_COLUMNS]:
                if not attrib in my_interval.columns:
                    my_interval.columns.append(attrib)
                new_level_1_row[attrib]     = e_dict[attrib]

            # Now we gear up to make a recursive call. For example, if we have been processing the interval
            # ["UID", "big-rock"] and e_dict = content_df["BR1"], we are now going to take the plunge into
            # the unique sub-entity "Sub rock" and make a recursive call to process interval
            # ["UID-1", "Sub rock"] passing content_df["BR1"]["Sub rock"] as the content to process.
            #
            # For our e_path = "assertion"."big-rock"."BR1" we pass a path of "assertion"."big-rock"."BR1"."Sub rock"
            # we set "ourselves" ("BR1") as the parent_uid in the recursive call
            sub_rows                        = []
            sub_intervals                   = []
            if len(sub_entities) > 0: # By now we know this is at most 1
                sub_entity                  = sub_entities[0] # Something like "Sub rock"
                inner_trace                 = loop_trace.doing("Making a recursive call for '" + sub_entity + "'",
                                                                data = {'signaledFrom': __file__})
                
                sub_intervals, sub_rows     = self._build_df_rows(  parent_trace        = inner_trace, 
                                                                    content_dict        = e_dict[sub_entity], 
                                                                    all_acronyminfos    = all_acronyminfos,
                                                                    parent_path         = e_path + '.' + sub_entity,
                                                                    parent_uid          = full_e_uid,
                                                                    sparse              = sparse,
                                                                    abbreviate_uids     = abbreviate_uids)

            # Post-processing recursive call: handle the columns
            # 
            # The recursive call discovered what other columns pertain to the sub-entity. We need to merge this
            # from two perspectives:
            # -If this was the first time we created an interval for the sub-entity (e.g., for "Sub rock"),
            #  then add it to the list of intervals.
            # -However, if we already had an interval for "Sub rock" from having processed "previous rows",
            #  then it may be that the recursive call we just made uncovered additional columns to be added to
            #  that pre-existing row. See documentation for self._merge_interval
            self._merge_interval_lists(loop_trace, all_intervals, sub_intervals)

            # Post-processing recursive call: handle the rows
            #
            # This is where the logic of sparse or non-sparse applies. See documentation to this method to explain
            # that algorithm
            if sparse == True:                              # Add (1 + N) rows, here N = len(sub_rows)
                all_rows.append(new_level_1_row)
                for idx in range(len(sub_rows)):
                    all_rows.append(sub_rows[idx])

            else:                                           # Add N rows, where N = max(len(sub_rows), 1)
                if len(sub_rows) > 0:
                    for r in sub_rows: # Copy the "level 1" data to all sub-rows and add them
                        for k in new_level_1_row.keys():
                            r[k]                    = new_level_1_row[k]
                        all_rows.append(r)
                else:
                    all_rows.append(new_level_1_row)

        
        # Return value to caller (which for recursive call was this method itself, processing left interval to ours)
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

    def _find_acronyminfo_list(self, parent_trace, content_dict, parent_path, parent_uid):
        '''
        This method is used as a pre-amble to determine the ordered set of acronyms to be used by other methods
        of this class when attempting to build a Pandas DataFrame
        representing the information in `content_dict`.

        The reason for doing a first pass just to get the acronyms is it is not possible to correctly infer
        UIDs at different levels (i.e., UID-1, UID-2, UID-3, ...) just based on full UIDs because some acronyms
        might be missing in some of the tree paths of `content_dict`.

        NOTE: because of needs by the caller, this method does not return a simple list of acronyms. I.e., instead
        of returning a list of strings, it returns a list of _AcronymInfo objects, which is more informative (it includes
        the entity name)

        Example:
        
        Consider a path in `content_dict` involving these UIDs: A1, A1.I1, A1.II.AS1.

        If we inferred level-based UID column names from these, we might think that A1 corresponds to "UID", that
        A1.I1 corresponds to "UID-1", and that A1.I1.AS1 corresponds to "UID-2".

        However, such an algorithm was found to be buggy in real life, in an example like this, where
        this table represents the Excel posting where every column is an entity:


               Area |  Indicator        |  Sub Indicator    | Applicable Space
            ====================================================================
             Adopt  |  %containeraized  |                   | Components
                    |  %testing         | Functional Tests  | Scenarios.functional
                    |                   | Performance Tests | 
 

        In this example there are 4 acronyms: A (for Area), I (for Indicator), SI (for Sub Indicator), and
        AS (for Applicable Area)

        The first row has no SubIndicator, so the leaf entity would get a full UID of A1.I1.AS1, whereas the other
        two paths (i.e., rows) would get full UIDs of A1.I2.SI1.AS1 and A1.I2.SI2

        If we assigned level-based UID column names, we would incorrectly use UID-2 for the interval
        [Applicable Space] in row1, and use UID-2 for a different interval [Sub Indicator] for the other two rows.

        This would be a bug, that would corrupt the DataFrame constructed by this class. When this bug was found, the
        effect was that the DataFrame and "UID-2" appearing as two separate columns, causing errors downstream in code
        that assumed that each column name was unique.

        So to fix this problem, this method does a pass through the entire `content_dict` to get a list of acronyms, which
        in this example would be:

            ["A", "I", SI", "AS"]

        That way other methods of this class can use that list when finding out the leveled-UID column name to use 
        for an full UID. 

        For example, other methods in this class that encounter "A1.I1.AS1" would look up acronym "AS" and found it is 
        index 3 in the acronym list, and impute a UID column name of "UID-3", which would be correct.

        The implementation of this methods is in two passes (sort of a map-reduce)

        * First pass is recursive, going through the `content_dict` and getting a list of lists, one for each path.
          In our example that would produce (notice not all acronyms appear in all lists, and in some cases may
          not all appear in even 1 list)

            [ ["A", "I", "AS"], ["A", "I", SI", "AS"], ["A", "I", SI"]]

        * Second pass then reduces this to a single list that has the property that it includes all acronyms listed
          in any of the lists in the first pass, in the same order. In the example, that is ["A", "I", SI", "AS"]


        '''
        # all_acronyms_list is a list of lists of _AcronymInfo objects
        all_acronym_info_lists          = self._map_acronyminfo_lists(parent_trace, content_dict, parent_path, parent_uid)

        # Now the "reduce" phase
        result                          = []
        working_acronyminfo_lists       = all_acronym_info_lists.copy()
        MAX_LOOPS                       = 1000 # To avoid inadvertent infinite loops if there is a bug in the logic in the loop
        loop_nb                         = 0
        while loop_nb < MAX_LOOPS and len(working_acronyminfo_lists) > 0:
            loop_trace                  = parent_trace.doing("Determining next acronym to append to the acronyms list",
                                            data = {"result so far":        str(result), 
                                                    "pending to explore":   str(working_acronyminfo_lists)})
            first_acronyminfo           = self._find_first_acronyminfo(loop_trace, working_acronyminfo_lists)
            if not first_acronyminfo in result:
                result.append(first_acronyminfo)
            next_working_lists          = []
            for a_list in working_acronyminfo_lists:
                if first_acronyminfo in a_list:
                    modified_list       = a_list.copy()
                    modified_list.remove(first_acronyminfo)
                    if len(modified_list) > 0:
                        next_working_lists.append(modified_list)
                else:
                    next_working_lists.append(a_list)
            # Initialize state for next cycle in loop
            loop_nb                     += 1
            working_acronyminfo_lists   = next_working_lists

        return result

    def _find_first_acronyminfo(self, parent_trace, all_acronyminfo_lists):
        '''
        This is a helper method to the "reduce" phase of the algorithm used by method _find_acronym_list.
        Refer to the documenation of that method for an explanation of the context for the algorithm.

        The particular contribution of this method is to identify the first acronym that should be used.
        This algorithm requires that there one unique such, meeting these conditions:
        
        * It appears in at least on list
        * If it appears in a list at all, it appears first
        * It is the unique such

        It returns the result as an _AcronymInfo object

        @param all_acronyminfo_list A list of lists, where inner lists contains _AcronymInfo objects
        '''
        candidates              = [a_list[0] for a_list in all_acronyminfo_lists if len(a_list) > 0]
        # Remove duplicates, if any
        candidates              = list(set(candidates))

        # Disqualify any candidate if it is not first in at least one of the lists
        disqualified            = [acronyminfo for acronyminfo in candidates 
                                        if max([a_list.index(acronyminfo) for a_list 
                                                in all_acronyminfo_lists if acronyminfo in a_list]) > 0]
        qualified               = [acronyminfo for acronyminfo in candidates if acronyminfo not in disqualified]
        if len(qualified) == 0:
            raise ApodeixiError(parent_trace, "Badly formed acronyms list: there is no acronym that occurs only first in the "
                                                + "lists where it appears",        
                                    data = {"all_acronyms_list": str(all_acronyminfo_lists)})
        if len(qualified) > 1:
            raise ApodeixiError(parent_trace, "Badly formed acronyms list: there are multiple acronyms competing to be "
                                                + "the first acrony",        
                                    data = {"all_acronyms_list": str(all_acronyminfo_lists),
                                            "competing acronyms": str(qualified)})
        # If we get this far we are in good shape. There is a unique qualified candidate, so return it
        return qualified[0]

    def _map_acronyminfo_lists(self, parent_trace, content_dict, parent_path, parent_uid):
        '''
        This is a recursive helper method to the "map-reduce" algorithm used by method _find_acronym_list. 
        Refer to the documentation of that method for an explanation of the context for the algorithm.

        This method returns a list of lists, where the inner list consist of _AcronymInfo objects.
        '''
        my_trace                = parent_trace.doing("Mapping acronym lists for '" + parent_path + "''",
                                                        data = {'signaledFrom': __file__})
        if True:
            if parent_path == None or len(parent_path.strip()) == 0:
                raise ApodeixiError(my_trace, "Can't process a parent_path that is null or blank")

        # parent_path is something like "assertion.big-rock" when this method is first called, and 
        # like  "assertion.big-rock.BR1.Sub rock" when this method is calls recursively on itself
        path_tokens             = parent_path.split('.') 
        entity_name             = path_tokens[-1] # like "big-rock" on 1st call, and "Sub rock" on recursive call 

        entity_uids             = [key for key in content_dict.keys() if not key.endswith('-name')]

        # Will be one per "path" within the "tree" represented by `content_dict`, consisting of the acronyms
        # encountered along that path, in order.
        all_acronyms_result     = [] 
                    
        my_trace                = parent_trace.doing("Mapping acronyms under of '" + str(parent_uid) + "'",
                                                        data = {'signaledFrom': __file__})

        
        # On a first call we loop through something like e_uid = "BR1", "BR2", "BR3", .... For that call
        #       parent_uid = None and parent_path = "assertion.big-rock"
        # On a recursive call with parent_uid = "BR1" we loop through e_uid = "SR1", "SR2", "SR3", .... In this case
        #       parent_path = "assertion.big-rock.BR1.Sub rock"
        for e_uid in entity_uids:
            loop_trace          = parent_trace.doing("Looping on entity with UID '" + str(e_uid) + "'",
                                                    data = {'signaledFrom': __file__})
            if parent_uid == None:
                full_e_uid      = e_uid
            else:
                full_e_uid      = parent_uid + '.' + e_uid
                
            e_acronym           = UID_Utils().parseToken(loop_trace, e_uid)[0]

            e_path              = parent_path  + '.' + e_uid

            e_dict              = content_dict[e_uid]

            inner_trace         = loop_trace.doing("Checking tree under '" + e_path + "' is well formed",
                                            data = {'signaledFrom': __file__})
            if True:
                # Check e.g. if content_dict = manifest_dict["assertion"]["big-rock"]["BR1"]["SubRock"]
                # and e_uid = "SR2", that content_dict["SR2"] exists and is a dictionary
                if e_dict == None:
                    raise ApodeixiError(inner_trace, "Badly formatted tree: found nothing under '" + e_path + "'")
                if type(e_dict) != dict:
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected dictionary at '" + e_path
                                                       + "' but instead found a " + str(type(e_dict)))
                    
                # Apodeixi's data model allows "multiple dimensional" branching. An example of branching is having
                # a "big-rock" entity "BR1" branch into multiple "Sub rock" entities "BR1.SR1", "BR1.SR2", "BR1.SR3", ...
                # "Multi-dimensional" branching happens if the "big-rock" entity can also branch into another
                # entity like "Epic", leading to children like "BR1.E1", "BR1.E2", "BR1.E3", ...
                # While that is allowed in the data model, it is not possible to represent such multi-dimensional
                # branching neatly in a tabular representation like a DataFrame.
                # So since this method is about creating such tabular representation, we will error out if we find that
                # "multi-dimensional" branching occurs in the manifest.
                sub_entities                    = self._find_sub_entities(e_dict) # should find at most 1
                if len(sub_entities) > 1:
                    raise ApodeixiError(inner_trace, "At most one sub entity is allowed when representing a manifest as as "
                                                    + " DataFrame, but found several: " 
                                        + sub_entities)

            inner_trace         = loop_trace.doing("Getting acronym lists under '" + e_path + "'",
                                            data = {'signaledFrom': __file__})
            # Now we gear up to make a recursive call. For example, if we have been processing the interval
            # ["UID", "big-rock"] and e_dict = content_df["BR1"], we are now going to take the plunge into
            # the unique sub-entity "Sub rock" and make a recursive call to process interval
            # ["UID-1", "Sub rock"] passing content_df["BR1"]["Sub rock"] as the content to process.
            #
            # For our e_path = "assertion"."big-rock"."BR1" we pass a path of "assertion"."big-rock"."BR1"."Sub rock"
            # we set "ourselves" ("BR1") as the parent_uid in the recursive call
            ME                              = AsDataframe_Representer
            if len(sub_entities) == 0: # We hit bottom in the recursion
                acronyms_list               = [ME._AcronymInfo(e_acronym, entity_name)]
                all_acronyms_result.append(acronyms_list)
            elif len(sub_entities) > 0: # Here we use recursion. By now we know this is at most 1
                sub_entity                  = sub_entities[0] # Something like "Sub rock"
                inner_trace                 = loop_trace.doing("Making a recursive call for '" + sub_entity + "'",
                                                                data = {'signaledFrom': __file__})

                acronyms_subresult          = self._map_acronyminfo_lists   (parent_trace    = inner_trace, 
                                                                        content_dict    = e_dict[sub_entity], 
                                                                        parent_path     = e_path + '.' + sub_entity,
                                                                        parent_uid      = full_e_uid)
                for acronyms_sublist in acronyms_subresult:
                    # Check we are not about to put duplicate acronyms - if so, that is an error with the `content_df`
                    if e_acronym in acronyms_sublist:
                        raise ApodeixiError(inner_trace, "Looks like manifest is corrupted because the same acronym is "
                                                    + " used at different levels. An acronym should be used in only 1 level",
                                                    data = {"Problem at UID": str(full_e_uid),
                                                            "Acronyms below UID": str(acronyms_sublist)})
                    acronyms_list           = [ME._AcronymInfo(e_acronym, entity_name)]
                    acronyms_list.extend(acronyms_sublist)
                    all_acronyms_result.append(acronyms_list)

        return all_acronyms_result
                

    class _AcronymInfo():
        '''
        Helper data structure class. It packages information about an acronym that is needed by the algorithms
        of this module.
        '''
        def __init__(self, acronym, entity_name):
            self.acronym            = acronym
            self.entity_name        = entity_name

        def copy(self):
            ME              = AsDataframe_Representer
            new_info        = ME._AcronymInfo(  acronym         = self.acronym,
                                                entity_name     = self.entity_name)
            return new_info 

        def __key(self):
            return (self.acronym, self.entity_name)

        def __hash__(self):
            return hash(self.__key())

        def __eq__(self, other):
            ME              = AsDataframe_Representer
            if isinstance(other, ME._AcronymInfo):
                return self.__key() == other.__key()
            return NotImplemented

        def __str__(self):
            return "acronym=" + str(self.acronym) + "; entity_name=" + str(self.entity_name)
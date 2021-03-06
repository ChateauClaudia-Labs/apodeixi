
import pandas                           as _pd

from apodeixi.util.a6i_error            import ApodeixiError
from apodeixi.util.yaml_utils       import YAML_Utils
from apodeixi.xli.interval              import Interval
from apodeixi.xli.uid_store             import UID_Utils
from apodeixi.xli.uid_acronym_schema    import UID_Acronym_Schema

class UID_Info:
    '''
    Data structure class, used to contain some contextual information around a UID. It is a by-product of the
    AsDataframe_Representer, and callers may use it. One use case is to create a list of all entities across all levels: for
    example, to add to Excel a drop down of all rock (a list of big rocks, medium rocks, etc), where each rock 
    is identified by UID along with the human-understandable description of the rock (i.e., the entity value).
    Such a list is returned as a by-product of AsDataframe_Representer, each member of the list being an instance of
    UID_Info.
    '''
    def __init__(self, uid, entity_value):
        self.uid                = uid
        self.entity_value       = entity_value

    def display(self):
        '''
        Returns a human-friendly string for the UID info
        '''
        return str(self.uid) + ": " + str(self.entity_value)

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
        manifest_dict       = YAML_Utils().load(my_trace, path = manifest_path)
        path_tokens         = contents_path.split('.')
        
        # Create the dictionary of everything except what is in the path  
        my_trace             = parent_trace.doing('Splitting manifest', data = {'path_tokens': path_tokens})
        content_dict, non_content_dict = self._split_out(my_trace, manifest_dict, path_tokens)

        df, uid_info_list    = self.dict_2_df(parent_trace, content_dict, contents_path, sparse, abbreviate_uids)
        return df, non_content_dict

    def dict_2_df(self, parent_trace, content_dict, contents_path, sparse, abbreviate_uids):
        '''
        Used to represent the contents of a manifest as a Pandas DataFrame. There are two main
        use cases for what such DataFrame would be used for, and the needs of each of them
        are catered to depending on how the `sparse` parameter is set:

        * As input to subsequent processing to render an Excel visualization (using sparse=True)
        * As input to data analysis in Pandas (using sparse=False). 
        
        Refer to detailed documentation for method `self._build_df_rows`, that does the heavy lifting.

        It returns two objects:

        * A DataFrame, corresponding to the manifests' content.
        * A list of UID_Info objects, built as a by-product of this method's processing and which some callers
            may find useful. Refer to the documentation of UID_Info for explanation and example use cases.

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
        acronym_schema      = UID_Acronym_Schema()
        acronym_schema.build_schema_from_manifest_content(  parent_trace        = my_trace, 
                                                            content_dict        = content_dict, 
                                                            parent_path         = contents_path)

        intervals, rows, uid_info_list      = self._build_df_rows(          
                                                            parent_trace        = my_trace,
                                                            content_dict        = content_dict,
                                                            acronym_schema      = acronym_schema,
                                                            parent_path         = contents_path,
                                                            parent_uid          = None,
                                                            sparse              = sparse,
                                                            abbreviate_uids     = abbreviate_uids)
        
        all_columns         = []
        for interval in intervals:
            all_columns.extend(interval.columns)
            
        df                  =  _pd.DataFrame(columns=all_columns, data=rows)
        df                  = df.fillna('')

        return df, uid_info_list
    
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
    
    def _build_df_rows(self, parent_trace, content_dict, acronym_schema, parent_path, parent_uid, sparse,
                                abbreviate_uids):
        '''
        Recursive method that creates the data from which a Pandas DataFrame can be easily created by the caller,
        based on the dictionary `content_dict`. It returns:
        
        * The list of intervals whose concatenation would yield the columns for such a DataFrame-to-be (see 
            example below for an explanation)
        * The list of rows (each row represented as a dict, whose keys are DataFrame columns, at least those
            columns for which the row has a non-NaN value)
        * A list of UID_Info objects, built as a by-product of this method's processing and which some callers
            may find useful. Refer to the documentation of UID_Info for explanation and example use cases.

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
        @param acronym_schema An AcronymSchema object that captures all the acronyms for `content_dict`
                            as well as their corresponding entity names. This should be
                            "global", i.e., is not for a "sub tree" but for the full manifest. 
                            Logically speaking the schema contains information that specifice the order
                            of the acronyms and their entities. While an object and not a list, logically
                            it is as in this example:

                                [("BR", "big-rock"), ("MR", "medium_rock"), ("SR", "small rock")] 
                            
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
        my_trace                            = parent_trace.doing("Validating parent_path '" + parent_path + "''",
                                                        data = {'signaledFrom': __file__})
        if True:
            if parent_path == None or len(parent_path.strip()) == 0:
                raise ApodeixiError(my_trace, "Can't process a parent_path that is null or blank")
        
        # parent_path is something like "assertion.big-rock" when this method is first called, and 
        # like  "assertion.big-rock.BR1.Sub rock" when this method is calls recursively on itself
        
        entity_uids                         = [key for key in content_dict.keys() if not key.endswith('-name')]

        # Will be one per entity_value, a dictionary of level_1_columns -> scalar value. By "level 1 columns"
        # we mean columns for the interval being processed here (subsequent intervals would be processed
        # in recursive invocations of this method). See method documentation for explanation of algorithm.
        all_rows                            = [] 
        
        # Some manifest field names that have fixed, hard-coded values in Apodeixi
        UID                                 = Interval.UID
        NAME                                = 'name'
        SYNTHETIC_COLUMNS                   = [UID, NAME] # These are added when parsing Excel, so not "real" content
        
        all_intervals                       = []

        uid_info_list                       = [] # We'll build this as a by-product and return it

        # On a first call we loop through something like e_uid = "BR1", "BR2", "BR3", .... For that call
        #       parent_uid = None and parent_path = "assertion.big-rock"
        # On a recursive call with parent_uid = "BR1" we loop through e_uid = "SR1", "SR2", "SR3", .... In this case
        #       parent_path = "assertion.big-rock.BR1.Sub rock"
        for e_uid in entity_uids:
            if parent_uid == None:
                full_e_uid                  = e_uid
            else:
                full_e_uid                  = parent_uid + '.' + e_uid
                
            e_path                          = parent_path  + '.' + e_uid
            e_dict                          = content_dict[e_uid]
            loop_trace                      = parent_trace.doing("Looping on entity with path '" + e_path + "'",
                                                    data = {'signaledFrom': __file__})

            inner_trace                     = loop_trace.doing("Determining name to give to UID column in DataFrame for a UID",
                                                    data = {"entity UID": str(full_e_uid)})            

            e_acronyminfo, UID_COL          = acronym_schema.schema_info_for_UID(parent_trace, e_uid)

            # Check if we already have an interval for this acronym info, and if not, create one
            my_prior_interval               = [interval for interval in all_intervals 
                                                        if e_acronyminfo.entity_name in interval.columns]
            if len(my_prior_interval) == 0:          
                my_interval                 = Interval( parent_trace    = my_trace, 
                                                        columns         = [UID_COL, e_acronyminfo.entity_name],
                                                        entity_name     = e_acronyminfo.entity_name)
                all_intervals.append(my_interval)


            inner_trace                     = loop_trace.doing("Checking tree under '" + e_path + "' is well formed",
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
                # Check e.g. content_dict["SR2"]["UID"] == "SR2", except possibly for padding (this occurs
                # when the end user skips an entity). Thus, content_dict["SR2"]["UID"] = "MR0.SR2" would be OK
                if e_dict[UID] != acronym_schema.pad_uid(parent_trace, full_e_uid):
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected '" + e_path
                                                   + "[" + UID + "] = " + full_e_uid + "'", 
                                                   data = {"expected": full_e_uid, "actual": str(e_dict[UID])})
                # Check e.g. content_dict["SR2"]["UID"]['name'] exists
                if not NAME in e_dict.keys():
                    raise ApodeixiError(inner_trace, "Badly formatted tree: expected a child called '" + NAME
                                                    + "' under '" + e_path + "'") 
                    
            inner_trace                     = loop_trace.doing("Building DataFrame row",
                                                    data = {"entity path": str(e_path)})
            # We call it "level 1" because it is for my_interval. Recursive calls would be the subsequent
            # intervals, which are "level 2, 3, ..." in the content_df "tree"
            new_level_1_row                 = {} 
            # Add the entity column to the level_1 row
            # But first replace by "friendly" UID like 'BR1.2' instead of "BR1.SR2", if we are thus configured
            if abbreviate_uids == True:
                abbreviated_full_e_uid      = UID_Utils().abbreviate_uid(   parent_trace    = inner_trace, 
                                                                            uid             = full_e_uid,
                                                                            acronym_schema  = acronym_schema)
                new_level_1_row[UID_COL]    = abbreviated_full_e_uid 
            else:
                # Remember to pad if needed, i.e., maybe full_e_uid is BR1.TR1, but if the acronym schema 
                # is [BR, MR, TR], we should put a BR1.MR0.TR1 in the new_level_1_row, not a BR1.TR1
                new_level_1_row[UID_COL]    = acronym_schema.pad_uid(parent_trace, full_e_uid) 
            new_level_1_row[e_acronyminfo.entity_name]    = e_dict[NAME]

            uid_info_list.append(UID_Info(  uid             = new_level_1_row[UID_COL], 
                                            entity_value    = new_level_1_row[e_acronyminfo.entity_name]))
            
            sub_entities                      = acronym_schema.find_entities(inner_trace, e_dict) # Something like "Sub rock"
            # Now add the "scalar" attributes to the row and if needed also to the interval. A reason they may
            # not be in the interval already arises if we are creating the "first row" (i.e., entity e_uid) 
            # or if that attribute was not present in "previous rows"
            #for attrib in [a for a in e_dict.keys() if not a in sub_entities and a not in SYNTHETIC_COLUMNS]:
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
            sub_rows_across_subentities     = []
            for sub_entity in sub_entities:
                sub_rows                    = []
                sub_intervals               = []
                inner_trace                 = loop_trace.doing("Making a recursive call for '" + sub_entity + "'",
                                                                data = {'signaledFrom': __file__})
                
                sub_intervals, sub_rows, sub_uid_info_list  = self._build_df_rows(  
                                                                    parent_trace        = inner_trace, 
                                                                    content_dict        = e_dict[sub_entity], 
                                                                    acronym_schema      = acronym_schema,
                                                                    parent_path         = e_path + '.' + sub_entity,
                                                                    parent_uid          = full_e_uid,
                                                                    sparse              = sparse,
                                                                    abbreviate_uids     = abbreviate_uids)

                uid_info_list.extend(sub_uid_info_list)

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

                sub_rows_across_subentities.extend(sub_rows)

            # Post-processing recursive call: handle the rows
            #
            # This is where the logic of sparse or non-sparse applies. See documentation to this method to explain
            # that algorithm
            if sparse == True:                              # Add (1 + N) rows, here N = len(sub_rows)
                all_rows.append(new_level_1_row)
                for idx in range(len(sub_rows_across_subentities)):
                    all_rows.append(sub_rows_across_subentities[idx])

            else:                                           # Add N rows, where N = max(len(sub_rows), 1)
                if len(sub_rows_across_subentities) > 0:
                    for r in sub_rows_across_subentities: # Copy the "level 1" data to all sub-rows and add them
                        for k in new_level_1_row.keys():
                            r[k]                    = new_level_1_row[k]
                        all_rows.append(r)
                else:
                    all_rows.append(new_level_1_row)

        # Before returning, we need to sort the intervals to be order-consistent with the acronym_schema.
        # This is needed because due to the possibility of some rows having skipped an entity, it is possible
        # that in `all_intervals` we have the interval for UID-3 before the interval for UID-2.
        my_trace                            = parent_trace.doing("Sorting intervals as per Acronym Schema",
                                                            data = {"parent_uid":       str(parent_uid),
                                                                    "acronym schema":   str(acronym_schema)})
        sorted_intervals                    = []
        for acronyminfo in acronym_schema.acronym_infos():
            # Find the interval for this acronym, if there is one in our list so far
            entity_name                     = acronyminfo.entity_name
            matches                         = [interval for interval in all_intervals if entity_name in interval.columns]
            if len(matches) > 1:
                raise ApodeixiError(my_trace, "Found multiple intervals for the same entity, and there shoud be at most 1")
            elif len(matches) == 1:
                sorted_intervals.append(matches[0])

        # Check we sorted everything
        if len(sorted_intervals) != len(all_intervals):

            raise ApodeixiError(my_trace, "Was not able to sort all intervals based on the Acronym Schema. Some intervals "
                                            + " did not seem to correspond to anything recognized in the Acronym Schema, "
                                            + "The sorted intervals should have been equally long as all_intervals",
                                            data = {"len(all_intervals)":       str(len(all_intervals)),
                                                    "len(sorted_intervals)":    str(len(sorted_intervals))})
        
        # Return value to caller (which for recursive call was this method itself, processing left interval to ours)
        return sorted_intervals, all_rows, uid_info_list
        

    
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


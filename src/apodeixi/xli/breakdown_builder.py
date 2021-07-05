import re                                       as _re
import pandas

from apodeixi.util.a6i_error                    import ApodeixiError
from apodeixi.xli.interval                      import IntervalUtils, Interval
from apodeixi.xli.uid_store                     import UID_Store
from apodeixi.util.dataframe_utils              import DataFrameUtils

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
        result                                          = {}
        CLEANED                                         = DataFrameUtils().clean  # Abbreviation to express intent
        for k in self.children.keys():
            entity_instance                             = self.children[k]
            entity_instance_dict                        = {}
            entity_instance_dict[Interval.UID]    = entity_instance.UID
            entity_instance_dict['name']                = CLEANED(entity_instance.name)

            for prop_k in entity_instance.scalar_children.keys():
                entity_instance_dict[prop_k]            = CLEANED(entity_instance.scalar_children[prop_k])

            for tree_k in entity_instance.breakdown_children.keys():
                entity_instance_dict[tree_k]            = entity_instance.breakdown_children[tree_k].as_dicts()

            result[entity_instance.leaf_UID]            = entity_instance_dict
            # For YAML readibility purposes, we also make the names of the data be visible at the same level as the nodes,
            # side by side. This helps humans know which child is what, without having to repeatedly expand the UID-keyed
            # groupings. This done via the children, and as a convention it is keyed with lowercase
            # versions of otherwise capitalized-only UIDs. That is a trick so that they appear side by side with the
            # rich nodes in the YAML.
            result[entity_instance.leaf_UID + '-name']  = entity_instance_dict['name']

        return result
        
    def readDataframeFragment(self, interval, row, parent_trace, config, all_rows): 
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
        

        @param interval     An Interval object, corresponding to the columns in `row` that pertain to an entity being processed
        @param row          A tuple `(idx, series)` representing a row in a larger Pandas Dataframe as yielded by
                            the Dataframe `iterrows()` iterator.
        @param parent_trace A apodeixi.util.a6i_error.FunctionalTrace object. It contains human-friendly information 
                            for humans to troubleshoot problems when error are raised.
        @param config An PostingConfig object to help steer some of the stateful handling that sometimes is needed.
                            For example, how to handle the eventuality that the
                            user's postings includes UIDs already (e.g., as when the user updates instead of create). Or as
                            another example, how to handle a situation where there is a need to put a referential link
                            the UIDs in branches of another previously generated manifest.
        @returns The full UID of the new _EntityInstance node that was added as a child to this tree, or None if no node was added.
        '''
        update_policy                       = None
        if config != None:
            update_policy                   = config.update_policy
            
        encountered_new_entity              = False
        entity_column_idx                   = None
        known_entity_types                  = list(self.last_path.keys())
        my_trace                            = parent_trace.doing("Validating inputs are well-formed",
                                                    data = {    'known_entity_types': known_entity_types},
                                                    origination = {
                                                                'signaled_from': __file__})
        if True:
            # Check against nulls
            if interval         ==  None:
                raise ApodeixiError(my_trace, "Null interval of columns was given.")
            if type(interval)   !=  Interval:
                raise ApodeixiError(my_trace, "Wrong type of input. Expected an Interval and instead got a " + str(type(interval)))

            # Check we got a real Dataframe row
            if row==None or type(row)!=tuple or len(row)!=2 or type(row[1])!=pandas.core.series.Series:
                raise ApodeixiError(my_trace, "Didn't get a real Pandas row")   

            # Check interval and row are consistent
            columns                     = list(row[1].index)
            
            if len(interval.columns)==0:
                raise ApodeixiError(my_trace, "Empty interval of columns was given.")

            if not interval.is_subset(set(columns)):
                raise ApodeixiError(my_trace, "Interval's non-UID columns are not a subset of the row's columns.",
                                            data = {'interval': interval.columns, 'columns': columns})

            # Check entity appears in exactly one column. 
            
            def _matches_entity(idx):
                '''
                Returns a boolean if the column at index `idx` is the same as the interval's entity name

                If the user entered two columns with the same name, such as "Account", Pandas will re-name the second
                one to be "Account.1". But that is still a user error for an entity, so we will strip the ".1" suffix
                for purposes of validating that the user did not enter duplicate entity column names.
                Also, if the user put comments to itself in the form of parenthesis, we remove that
                '''
                GIST_OF                     = IntervalUtils().without_comments_in_parenthesis # Abbreviation for readability
                raw_col                     = columns[idx]
                no_parenthesis_col          = GIST_OF(my_trace, raw_col)
                REGEX                       = "(\.[0-9]+)$"
                suffix_search               =  _re.search(REGEX, no_parenthesis_col)
                if suffix_search == None:
                    cleaned_col             = no_parenthesis_col
                else:
                    suffix                  = suffix_search.group(0)
                    cleaned_len             = len(no_parenthesis_col) - len(suffix)
                    cleaned_col             = no_parenthesis_col[:cleaned_len]
                return cleaned_col == interval.entity_name


            #idxs                        = [idx for idx in range(len(columns)) if GIST_OF(my_trace, columns[idx])==interval.entity_name]
            idxs                        = [idx for idx in range(len(columns)) if _matches_entity(idx)]
            if len(idxs)>1:
                raise ApodeixiError(my_trace, "Entity '" + interval.entity_name + "' appears in multiple columns. Should appear only once.")
            elif len(idxs)==0:
                raise ApodeixiError(my_trace, "Entity '" + interval.entity_name + "' missing in given row. Should appear exactly once.")
            entity_column_idx           = idxs[0]

            # Check that if interval's entity is blank, all of interval is bank
            blank_cols                  = [col for col in interval.columns if IntervalUtils().is_blank(row[1][col])]
            encountered_new_entity      = not interval.entity_name in blank_cols
            uid_to_overwrite             = None # This will be used later when looking for a docking UID
            if not encountered_new_entity and len(blank_cols) < len(interval.columns):
                # Before raising an error, attempt to recover: perhaps user entered the entity_name in the previous
                # row, left the rest of that previous row blank, and then moved to this one. If so, pretend that
                # the user actually entered that entity_name in the current row
                # If inference falis, then raise the error
                
                if self._can_infer_entity_from_prior_row(my_trace, interval.entity_name, row, all_rows):
                    encountered_new_entity  = True # Reverse prior impression so we dock values onto the tree
                    #uid_to_overwrite = TODO
                    instance_to_overwrite   = self.last_path[interval.entity_name]
                    uid_to_overwrite        = instance_to_overwrite.UID

                else:
                    # Create a friendly error message 
                    excel_row_nb            = config.excel_row_nb(my_trace, row[0])
                    excel_sheet             = config.excel_sheet(my_trace)
                    non_black_cols          = [col for col in interval.columns if not col in blank_cols]
                    raise ApodeixiError(my_trace, "Did you forget to set '" + interval.entity_name 
                                                    + "' in excel row " + str(excel_row_nb) + " of worksheet '" + excel_sheet + "'?"
                                                    + "\nYou can't leave it blank unless you also clear data you wrote "
                                                    + " in row " + str(excel_row_nb) + " for these " 
                                                    + str(len(non_black_cols)) + " columns:\n['"
                                                    + "', '".join(non_black_cols) + "']"
                                                    + "\n\n=> Alternatively, consider changing the range in the Posting Label to "
                                                    + "exclude such rows.\n")

            # Check that interval itself has no subentities (as any subentity should be *after* the interval)
            # Remember to not count interval.entity_name as "illegal", since it is clearly an entity and not a sub-entity
            illegal_sub_entities        = set(known_entity_types).intersection(interval.non_entity_cols())    #set(interval[1:])) 
            if len(illegal_sub_entities) > 0:
                raise ApodeixiError(my_trace, "There shouldn't be subentities inside the interval, but found some: " 
                                                + str(illegal_sub_entities))

        columns                             = list(row[1].index)            
        
        my_trace                            = parent_trace.doing("Discovering parent entity",
                                                                    origination = {'signaled_from': __file__})
        if encountered_new_entity: 
            my_trace                        = parent_trace.doing("Figuring out docking coordinates for '" + interval.entity_name + "'.",
                                                                    origination = {'signaled_from': __file__})
            if True:
                docking_uid                 = self._discover_docking_uid(   parent_trace        = my_trace, 
                                                                            interval            = interval,
                                                                            entity_column_idx   = entity_column_idx,
                                                                            original_row_nb     = row[0], 
                                                                            current_row_nb      = row[0], 
                                                                            all_rows            = all_rows, 
                                                                            config              = config)

            my_trace                        = parent_trace.doing("Docking a new '" + interval.entity_name 
                                                                    + "' below docking_uid '" + str(docking_uid) + "'",
                                                                    origination = {'signaled_from': __file__})
            subtree_full_uid                = self.dockEntityData(  parent_trace        = my_trace,
                                                                    full_docking_uid    = docking_uid, 
                                                                    entity_type         = interval.entity_name, 
                                                                    data_to_attach      = row[1][interval.columns],
                                                                    uid_to_overwrite     = uid_to_overwrite,
                                                                    config              = config)
            return subtree_full_uid
            
        else: # Didn't encounter a new entity - so nothing to do for this interval
            return None

    def _can_infer_entity_from_prior_row(self, parent_trace, entity_column, row, all_rows):
        '''
        Helper method to try to "forgive" the user if the user fails to enter a value for an entity_column in a row
        but entered it in the previous row, leaving blank the rest of the previous row. If so, we pretend that the
        user intended for that entity_name to be entered in this row

        This methods returns a boolean: True if the entity_name can be defaulted (in which case input `row` is mutated),
        or False otherwise.
        '''
        current_row_nb              = row[0]
        if current_row_nb == 0:
            return False # There is no prior row

        prior_row                   = all_rows[current_row_nb -1]
        prior_entity                = prior_row[1][entity_column]
        if IntervalUtils().is_blank(prior_entity): # Can't infer it as prior row has no entity set
            return False

        columns                     = list(prior_row[1].index)
        entity_idx                  = columns.index(entity_column)
        non_blanks_to_the_right     = [col for col in columns[entity_idx+1:] if not IntervalUtils().is_blank(prior_row[1][col])]
        if len(non_blanks_to_the_right) > 0: # Not true user simply switched to current row after entering entity in prior row
            return False
        # We got this far implies we can safely infer the entity name
        row[1][entity_column]       = prior_entity
        return True


    def _discover_docking_uid(self, parent_trace, interval, entity_column_idx, original_row_nb, current_row_nb, all_rows, config):
        '''
        Helper method used when a new entity is encountered in dataframe cell, where the cell's coordinates
        are:
        * row is determined by int `original_row_nb`
        * column is determined by int `entity_column_idx`

        In these conditions, this method does a "lexicographic" search to find the "last branch in the tree seen so far"
        to which to get attached. This is done by searching like this:

        * Search in the current row for the last entity to the left of `entity_column_idx` for which we don't have a
          blank in this row. Initially the current row (defined by paramter `current_row_nb`) should be the same
          as `original_row_nb`.
        * If not found, recursively try the preceding row. That call keeps the same `original_row_nb` but decrements
          `current_row_nb`

        Once the search is done and a `parent entity` is found, then we use the UID of the last node for that entity
        (available from the memory captured in self.last path from prior pricessing). That is the UID to which we want
        to dock, and that is what this method returns.

        If in the process the search never finds a UID, then it raises an ApodeixiError unless the `entity_column_idx`
        corresponds to the first (highest level) entity, in which case self.parent_UID is returned
        '''
        known_entity_types              = list(self.last_path.keys())
        row_data                        = all_rows[current_row_nb][1]
        columns                         = list(row_data.index)
        ancestor_entities_idxs          = [idx for idx in range(len(columns)) if columns[idx] in known_entity_types 
                                                                                and idx < entity_column_idx]
        if len(ancestor_entities_idxs) == 0: # Only legal if we are the top-level entity, in which case return the parent_UID
            my_trace                    = parent_trace.doing("Validating we are the root entity", 
                                            data={'self.entity_type': self.entity_type,
                                                    'entity_column_idx': entity_column_idx})
            if interval.entity_name != self.entity_type:
                raise ApodeixiError(my_trace, "Could not find a parent entity for '" + interval.entity_name + "'."
                                    + "  You should have a column called '" + str(self.entity_type)
                                    + "' with a non-blank value") 
            else:
                return self.parent_UID

        # If we get this far, then we are not the top entity so we must find some UID to which to dock.
        # First search in the current row for the last entity that didn't have a non-blank value. If we find one,
        # we dock to its UID. If not, try again in the preceding row
        my_trace                        = parent_trace.doing("Searching for docking UID for an entity in row " + str(current_row_nb),
                                                        data = {    'entity':       str(columns[entity_column_idx]),
                                                                    'row_nb':       str(current_row_nb)})
        row_data                        = all_rows[current_row_nb][1]
        non_blank_ancestors_idx         = [idx for idx in ancestor_entities_idxs if not
                                            IntervalUtils().is_blank( row_data[columns[idx]]  )
                                        ]

        if len(non_blank_ancestors_idx) == 0: # No luck in this row. Try the preceding one, unless there isn't any, which means fail

            if current_row_nb == 0: # No preceding row, so search stops with failure
                # Search failed bacause we have only seen blanks in all rows, so fail with an error message explaining
                # to the user which part of the Excel spreadsheet is blank and needs fixing
                excel_original_row_nb   = config.excel_row_nb(my_trace, original_row_nb)
                excel_current_row_nb    = config.excel_row_nb(my_trace, current_row_nb)
                excel_sheet             = config.excel_sheet(my_trace)
                ancestor_entities       = [columns[idx] for idx in ancestor_entities_idxs]
                msg                     = "You left blank columns \n['" + "', '".join(ancestor_entities) + "']" \
                                            + "\nfor excel rows " + str(excel_current_row_nb) + "-" + str(excel_original_row_nb) + "." \
                                            + "\nThat is not allowed since you have non-blank data in column '" \
                                            + str(columns[entity_column_idx]) + "' at excel row " + str(excel_original_row_nb) + "'"
                raise ApodeixiError(my_trace, msg)
            else: # Try our lack in the preceding row
                return self._discover_docking_uid(  parent_trace            = my_trace,
                                                    interval                = interval,
                                                    entity_column_idx       = entity_column_idx, 
                                                    original_row_nb         = original_row_nb, 
                                                    current_row_nb          = current_row_nb -1, 
                                                    all_rows                = all_rows,
                                                    config                  = config)
        else: # We found it!
            parent_entity               = columns[max(non_blank_ancestors_idx)]
            parent_entity_instance      = self.last_path[parent_entity]
            docking_uid                 = parent_entity_instance.UID
            return docking_uid

    def dockEntityData(self, parent_trace, full_docking_uid, entity_type, data_to_attach, uid_to_overwrite, config):
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
        @param data_to_attach A Pandas Series   
        @uid_to_overwrite    A string. If set to None (normal when creating), a new UID will be generated
            for the data_to_attach. Otherwise whatever exists at `uic_to_overwrite` will be replaced by 
            `data_to_attach`
        @return the full UID of the _EntityInstance node that was created and attached to this BreakdownTree
        '''
        my_trace                = parent_trace.doing("Looking for an acronym for '" + entity_type + "'",
                                                        data = {'entity_type': entity_type},
                                                        origination = {
                                                                'signaled_from': __file__})
        acronym_for_attachment  = self.getAcronym(my_trace, entity_type)
        my_trace                = parent_trace.doing("Identifying sub tree to attach to",
                                                        origination = {'signaled_from': __file__})
        if full_docking_uid==self.parent_UID: # We are attaching at the root
            tree_to_attach_to   = self

        else:
            parent_entity_instance  = self.find(full_docking_uid, my_trace)
            if parent_entity_instance == None:
                raise ApodeixiError(my_trace, "No node exists for UID '" + full_docking_uid + "'",
                                                origination = {'signaled_from': __file__})

            tree_to_attach_to       = self._get_tree_to_attach_to(parent_entity_instance, entity_type, my_trace)

            sub_trace           = my_trace.doing("Validating acronym is not used by another entity",
                                                    origination = {'signaled_from': __file__})
            if tree_to_attach_to.entity_type != entity_type:
                raise ApodeixiError(sub_trace, "Can't add entity '" + entity_type 
                                    + "' because its acronym conflicts with acronym of previously used entity '"
                                    + tree_to_attach_to.entity_type + "'")

        my_trace                = parent_trace.doing("Generating UID for new node to attach ",
                                                        data = {    'acronym_for_attachment': acronym_for_attachment,
                                                                    'acronym is for'        : entity_type,
                                                                    'full_docking_uid'      : full_docking_uid},
                                                        origination = {
                                                                    'signaled_from'         : __file__})  

        if uid_to_overwrite == None:
            full_uid, leaf_uid      = self.uid_store.generateUID(   parent_trace    = my_trace,
                                                                    acronym         = acronym_for_attachment, 
                                                                    parent_UID      = full_docking_uid)
        else:
            full_uid                = uid_to_overwrite
            leaf_uid                = full_uid.split('.')[-1]

        new_node                = BreakdownTree._EntityInstance(    uid_store   = self.uid_store, 
                                                                    name        = data_to_attach[entity_type],
                                                                    uid         = full_uid,
                                                                    leaf_uid    = leaf_uid)

        for idx in data_to_attach.index:
            property_name       = idx
            if IntervalUtils().is_a_UID_column(my_trace, property_name):
                if config.update_policy.reuse_uids == False:
                    continue # Don't change the UID value we just generated - ignore whatever the user entered
                else:
                    # Keep the user UID values, but "correct" the property name in case the user got "creative"
                    # and named them things like "UID.1", "UID.2", etc., since in the YAML manifest only "UID"
                    # makes sense
                    property_name   = Interval.UID
            if property_name != entity_type: # Don't attach entity_type as a property, since we already put it in as 'name
                val             = data_to_attach[idx]
                cleaned_val     = DataFrameUtils().clean(val) # Get rid of nan, bad dates, NaT, etc
                new_node.setProperty(property_name, cleaned_val)

        tree_to_attach_to.children[leaf_uid]    = new_node

        self.last_path[entity_type]             = new_node

        return full_uid

    def _get_tree_to_attach_to(self, containing_entity_instance, entity_type_to_attach, parent_trace):

        my_trace                = parent_trace.doing("Looking for an acronym for '" + entity_type_to_attach + "'",
                                                        data = {'entity_type_to_attach': entity_type_to_attach},
                                                        origination = {
                                                                'signaled_from': __file__})
        acronym_for_attachment  = self.getAcronym(my_trace, entity_type_to_attach)

        my_trace                = parent_trace.doing("Finding subtree to attach to",
                                                        data = {'acronym_for_attachment': acronym_for_attachment},
                                                        origination = {
                                                                'signaled_from': __file__})
        tree_to_attach_to       = containing_entity_instance.find_subtree(acronym_for_attachment, self, my_trace)

        if tree_to_attach_to==None: # This is first time we attach for this acronym, so create tree
            tree_to_attach_to   = BreakdownTree(self.uid_store, entity_type_to_attach, containing_entity_instance.UID)
            containing_entity_instance.breakdown_children[entity_type_to_attach]      = tree_to_attach_to

        return tree_to_attach_to

    def dock_subtree(self, entity_type, subtree_to_attach, parent_trace):

        my_trace                        = parent_trace.doing("Finding where to dock in containing tree",
                                                                origination = {'signaled_from': __file__})
        containing_equity_instance      = self.find(subtree_to_attach.parent_UID, my_trace)

        containing_equity_instance.breakdown_children[entity_type]    = subtree_to_attach

    def find(self, descendent_uid, parent_trace):
        '''
        Returns an _EntityInstance that descends from the root of this tree, and identified by `descendent_uid`
        as the unique UID identifying this _EntityInstance in the global BreakdownTree we belong to.
        '''
        if descendent_uid == None:
                raise ApodeixiError(parent_trace, "Can't find with a null descendent_uid")  

        relative_uid                        = descendent_uid
        my_trace                            = parent_trace.doing('Computing relative uid', data = { 'parent_UID': self.parent_UID},
                                                                    origination = {
                                                                                                    'signaled_from': __file__})

        
        if self.parent_UID != None:
            prefix                          = self.parent_UID + '.'
            if not descendent_uid.startswith(prefix):
                raise ApodeixiError(my_trace, "Bad  uid '" + descendent_uid + "': it should have started with '" + prefix + "'")  
            relative_uid                    = descendent_uid.lstrip (prefix)   

        my_trace                            = parent_trace.doing('Traversing uid path', data = {'relative_uid': relative_uid},
                                                                    origination = {
                                                                                                'signaled_from': __file__})
        uid_path                            = relative_uid.split('.')

        #previous_entity_instance            = None
        entity_instance                     = None # At start of loop, the entity instance for parth of uid_path already processed
        for idx in range(len(uid_path)):
            leaf_uid                        = uid_path[idx]
            loop_trace                      = my_trace.doing("Doing loop cycle for leaf_uid '" + leaf_uid + "'",
                                                                origination = {'signaled_from': __file__})

            if entity_instance == None: # First cycle in loop, so search in root tree
                next_tree                   = self
            else:
                uid_acronym, uid_nb         = _parse_leaf_uid(leaf_uid, loop_trace)
                sub_trace                   = loop_trace.doing("Looking for a subtree for the '" + uid_acronym + "' acronym",
                                                                origination = {'signaled_from': __file__})
                next_tree                   = entity_instance.find_subtree(uid_acronym, self, sub_trace) 
                if next_tree == None:
                    raise ApodeixiError(sub_trace, "Can't a subtree for acronym '" + uid_acronym + "'")

            # Set for next cycle of loop, or final value if we are in the last cycle
            entity_instance                 = next_tree.children[leaf_uid]

        # Return the last entity instance we got into
        return entity_instance
        
    def getAcronym(self, parent_trace, entity_type):
        '''
        Returns the entity's acronym. If none exists, it will generate a new one to ensure it does not conflict with
        the previously used acronyms
        '''
        # By convention, we only use upper case for acronyms
        if entity_type not in self.acronyms.keys():
            already_used        = [self.acronyms[e] for e in self.acronyms.keys()]
            nb_letters          = 1
            candidate           = _acronym(parent_trace, entity_type, nb_letters=nb_letters)
            while candidate in already_used:
                loop_trace      = parent_trace.doing("Looping through already used acronyms, searching for a candidate to re-use",
                                                        data            = {'candidate':             candidate},
                                                        origination     = {'signaled_from':         __file__})
                nb_letters      += 1
                new_candidate   = _acronym(loop_trace, entity_type, nb_letters=nb_letters)

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
                                                            data = {'breakdown keys': all_subtree_roots},
                                                            origination = {
                                                                    'signaled_from': __file__}) 
            potential_subtree_roots         = [root for root in all_subtree_roots 
                                                if containing_tree.getAcronym(my_trace, root)== uid_acronym]
            if len(potential_subtree_roots) > 1:
                raise ApodeixiError(my_trace, "Ambiguous paths for '" + uid_acronym + "': could be any of " + potential_subtree_roots)

            elif len(potential_subtree_roots) == 0:
                result_tree                 = None
            else: 
                found_root                  = potential_subtree_roots[0]
                result_tree                 = all_subtrees[found_root]
            return result_tree

def _acronym(parent_trace, txt, nb_letters=1):
    '''
    Returns a string of initials for 'txt', in uppercase, where each 'initial' consists of 1 or
    more letters, depending on the `nb_letters` parameter.

    Also, it ignores any sub-text within `txt` that is in parenthesis. 
    
    For example, if txt is 'Effort (man days) to deliver', this is treated the same as 'Effort to deliver', which results
    in a returned value of 'ETD' if nb_letters=1
    '''
    parentheis_free_txt         = IntervalUtils().without_comments_in_parenthesis(parent_trace, txt)
    # Now we got parenthesized text removed. So now we can go for the initials that compose the acronym
    tokens                      = parentheis_free_txt.split(' ')
    acronym                     = ''.join([token[0:min(nb_letters, len(token))].upper() for token in tokens])
    return acronym
    '''
    tokens       = stripped_txt.split(' ')
    acronym      = ''.join([token[0:min(nb_letters, len(token))].upper() for token in tokens])
    return acronym
    '''

def _parse_leaf_uid(leaf_uid, parent_trace):
    '''
    Parses a string like 'AC43' and returns two things: the acronym string 'AC' and the int 43
    '''
    REGEX               = '([a-zA-Z]+)([0-9])+'
    m                   = _re.match(REGEX, leaf_uid)
    my_trace            = parent_trace.doing("Parsing leaf_uid into acronym and number",
                                                origination = {'signaled_from': __file__})
    if m == None or len(m.groups()) != 2:
        raise ApodeixiError(parent_trace, "Couldn't parse leaf_uid '" + leaf_uid + "'")
    acronym             = m.group(1)
    nb                  = int(m.group(2))
    return acronym, nb


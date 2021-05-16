import yaml                         as _yaml
import re                           as _re
import sys                          as _sys
import os                           as _os
import math                         as _math
import datetime                     as _datetime
import pandas
from nltk.tokenize                  import SExprTokenizer 

from apodeixi.xli.xlimporter        import ExcelTableReader
from apodeixi.util.a6i_error        import ApodeixiError

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
        
        def initialize(self, parent_trace, tokens):
            '''
            Used in cases where the top level is determined externally
            '''
            for t in tokens:
                acronym, val           = self.parseToken(parent_trace, t)
                if acronym not in self.vals.keys():
                    self.vals[acronym] = []
                self.vals[acronym].append(val)
                self.children[t]       = UID_Store._TokenTree(parent_trace, self.level + 1)             
        
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
    
    def initialize(self, parent_trace, tokens):
        self.tree.initialize(parent_trace, tokens)
    
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

class IntervalSpec():
    '''
    Abstract helper class used to construct Interval objects. This is needed because sometimes all columns in an Interval
    are not known at configuration time, and are only known at runtime.
    
    For example, perhaps at configuration time we know where an interval starts, but not where it ends, since the
    end user might add columns to an Excel spreadsheet that quality as part of the interval. Thus, only at runtime
    in the context of a particular set of Excel columns (a "linear space") can it be determined which are the columns
    that qualify as belonging to an interval.

    Example: Say an interval spec is: "All columns from A to F, not inclusive". Then if the linear space is
    [Q, R, A, T, Y, U, F, G, W], the application of the spec to the linear space yields the Interval [A, T, Y, U]

    Concrete classes implement different "spec" algorithms, so this particular class is just an abstract class.
    '''
    def _init__(self, entity_name = None):
        self.entity_name            = entity_name

    def buildInterval(self, parent_trace, linear_space):
        '''
        Implemented by concrete derived classes.
        Must return an Interval object, constructed by applying the concrete class's semantics
        to the specificity of the linear_space given.

        Example: Say an interval spec is: "All columns from A to F, not inclusive". Then if the linear space is
        [Q, R, A, T, Y, U, F, G, W], the application of the spec to the linear space yields the Interval [A, T, Y, U]
        '''
        raise NotImplementedError("Class " + str(self.__class__) + " forgot to implement method buildInterval") 


class ClosedOpenIntervalSpec(IntervalSpec):
    '''
    Concrete interval spec class which builds an interval from a pre-determined list of columns. I.e.,
    the interval is "fixed", not dependent on the linear space.

    Example: Say an interval spec is: "All columns from A to F, not inclusive". Then if the linear space is
    [Q, R, A, T, Y, U, F, G, W], the application of the spec to the linear space yields the Interval [A, T, Y, U]

    @param start_column The column of at which the to-be-built Interval starts
    @param following_column The first column in the (runtime-determined) linear space that lies after the to-be-build Interval
    '''
    def __init__(self, parent_trace, start_column, following_column, entity_name):
        self.entity_name            = entity_name
        if entity_name == None:
            raise ApodeixiError(parent_trace, "Unable to instantiate an FixedIntervalSpec from a null or empty list")
        self.start_column           = start_column
        self.following_column        = following_column


    def buildInterval(self, parent_trace, linear_space):
        '''
        '''
        if self.start_column not in linear_space:
            raise ApodeixiError(parent_trace, "Can't build interval starting at '" + self.start_column 
                                                + "' because it does not appear in the linear space",
                                                data = {    'linear space'      : str(linear_space),
                                                            'start_column'      : self.start_column,
                                                            'signaled_from'     : __file__})
        if self.following_column not in linear_space:
            raise ApodeixiError(parent_trace, "Can't build interval preceding '" + self.following_column 
                                                + "' because it does not appear in the linear space",
                                                data = {    'linear space'      : str(linear_space),
                                                            'following_column'  : self.following_column,
                                                            'signaled_from'     : __file__})
        start_idx               = linear_space.index(self.start_column) 
        following_idx           = linear_space.index(self.following_column)

        if start_idx >= following_idx:
            raise ApodeixiError(parent_trace, "Can't build interval because start_column is not before the following_column",
                                                data = {    'linear space'      : str(linear_space),
                                                            'start_column'      : self.start_column,
                                                            'following_column'  : self.following_column,
                                                            'signaled_from'     : __file__})   

        interval_columns = []
        for idx in range(start_idx, following_idx):
            interval_columns.append(linear_space[idx])     
        
        return Interval(parent_trace, interval_columns, self.entity_name)

class FixedIntervalSpec(IntervalSpec):
    '''
    Concrete interval spec class which builds an interval based on only knowing in advance two columns: the column
    where the interval starts, and the first column *after* the interval.
    '''
    def __init__(self, parent_trace, columns, entity_name = None):
        self.entity_name            = entity_name
        if type(columns) != list or len(columns) == 0:
            raise ApodeixiError(parent_trace, "Unable to instantiate an FixedIntervalSpec from a null or empty list")
        self.columns                = columns
        if entity_name == None:
            self.entity_name        = columns[0]
        else:
            self.entity_name        = entity_name

    def buildInterval(self, parent_trace, linear_space):
        '''
        '''
        return Interval(parent_trace, self.columns, self.entity_name)


class Interval():
    '''
    Helper class used as part of the configuration for parsing a table in an Excel spreadsheet. It represents
    a list of string-valued column names in Excel, ordered from left to right, all for a given entity.
    Additionally, it indicates which of those column names is the name of the entity (as opposed to a property of)
    the entity. 
    '''
    def __init__(self, parent_trace, columns, entity_name = None):
        if type(columns) != list or len(columns) == 0:
            raise ApodeixiError(parent_trace, "Unable to instantiate an Interval from a null or empty list")
        self.columns                = columns
        if entity_name == None:
            self.entity_name        = columns[0]
        else:
            self.entity_name        = entity_name

    def is_subset(self, columns):
        '''
        UID-aware method to test if this Interval is a subset of the given columns. By "UID-aware" we mean
        that the method ignores any UID column when determining subset condition.
        For example, ['UID', 'Car', 'Make'] would be considered a subset of ['Car', 'Make', 'Driver']
        '''
        me                          = set(self.columns).difference(set([BreakdownTree._UID]))
        them                        = set(columns)
        return me.issubset(them)

    def non_entity_cols(self):
        '''
        Returns a list of strings, corresponding to the Interval's columns that are not the entity type
        '''
        return list(set(self.columns).difference(set([self.entity_name])))

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

    _UID                    = 'UID'  # Field name for anything that is a UID

    def as_dicts(self):
        '''
        Returns a dictionary of dictionaries representing this BreakdownTree. The keys are the leaf UIDs for the
        _EntityInstance objects comprising this BreakdownTree
        '''
        result                                          = {}

        for k in self.children.keys():
            entity_instance                             = self.children[k]
            entity_instance_dict                        = {}
            entity_instance_dict[BreakdownTree._UID]    = entity_instance.UID
            entity_instance_dict['name']                = entity_instance.name

            for prop_k in entity_instance.scalar_children.keys():
                entity_instance_dict[prop_k]            = entity_instance.scalar_children[prop_k]

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
        
    def readDataframeFragment(self, interval, row, parent_trace, update_policy): 
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
        @param update_policy An UpdatePolicy configuration object to determine how to handle the eventuality that the
                            user's postings includes UIDs already (e.g., as when the user updates instead of create)
        '''
        encountered_new_entity              = False
        entity_column_idx                   = None
        known_entity_types                  = list(self.last_path.keys())
        my_trace                            = parent_trace.doing("Validating inputs are well-formed",
                                                    data = {    'known_entity_types': known_entity_types,
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
            idxs                        = [idx for idx in range(len(columns)) if columns[idx]==interval.entity_name]
            if len(idxs)>1:
                raise ApodeixiError(my_trace, "Entity '" + interval.entity_name + "' appears in multiple columns. Should appear only once.")
            elif len(idxs)==0:
                raise ApodeixiError(my_trace, "Entity '" + interval.entity_name + "' missing in given row. Should appear exactly once.")
            entity_column_idx           = idxs[0]

            # Check that if interval's entity is blank, all of interval is bank
            blank_cols                  = [col for col in interval.columns if _is_blank(row[1][col])]
            encountered_new_entity      = not interval.entity_name in blank_cols
            if not encountered_new_entity and len(blank_cols) < len(interval.columns):
                raise ApodeixiError(my_trace, "Row has a blank '" + interval.entity_name 
                                    + "' so rest of row's interval should be blank, but isn't")

            # Check that interval itself has no subentities (as any subentity should be *after* the interval)
            # Remember to not count interval.entity_name as "illegal", since it is clearly an entity and not a sub-entity/
            illegal_sub_entities        = set(known_entity_types).intersection(interval.non_entity_cols())    #set(interval[1:])) 
            if len(illegal_sub_entities) > 0:
                raise ApodeixiError(my_trace, "There shouldn't be subentities inside the interval, but found some: " 
                                                + str(illegal_sub_entities))

        columns                             = list(row[1].index)            
        parent_entity                       = None
        my_trace                            = parent_trace.doing("Discovering parent entity",
                                                                    data = {'signaled_from': __file__})
        if True:
            ancestor_entities_idxs      = [idx for idx in range(len(columns)) if columns[idx] in known_entity_types 
                                                                                    and idx < entity_column_idx]
            if len(ancestor_entities_idxs) == 0:
                my_trace                = my_trace.doing("Validating we are the root entity", 
                                                data={'self.entity_type': self.entity_type,
                                                        'entity_column_idx': entity_column_idx})
                if interval.entity_name != self.entity_type:
                    raise ApodeixiError(my_trace, "Could not find a parent entity for '" + interval.entity_name + "'") 
            else:
                parent_entity           = columns[max(ancestor_entities_idxs)]

        if encountered_new_entity: 
            my_trace                        = parent_trace.doing("Figuring out docking coordinates for '" + interval.entity_name + "'.",
                                                                    data = {'signaled_from': __file__})
            if True:
                if parent_entity == None: # Attach to the root
                    docking_uid             = self.parent_UID
                else:
                    my_trace                = my_trace.doing("Validating we previously created a node for '" 
                                                                    + parent_entity + "' to which to attach '" 
                                                                    + interval.entity_name + "'.",
                                                                    data = {'signaled_from': __file__})
                    if parent_entity not in self.last_path.keys():
                        raise ApodeixiError(my_trace, "No prior node found for  '" + parent_entity + "'") 
                    
                    parent_entity_instance  = self.last_path[parent_entity]
                    docking_uid             = parent_entity_instance.UID

            my_trace                        = parent_trace.doing("Docking a new '" + interval.entity_name 
                                                                    + "' below docking_uid '" + str(docking_uid) + "'",
                                                                    data = {'signaled_from': __file__})
            self.dockEntityData(    full_docking_uid    = docking_uid, 
                                    #tree_to_attach_to   = tree_to_attach_to, 
                                    entity_type         = interval.entity_name, 
                                    data_to_attach      = row[1][interval.columns], 
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
        my_trace                = parent_trace.doing("Looking for an acronym for '" + entity_type + "'",
                                                        data = {'entity_type': entity_type,
                                                                'signaled_from': __file__})
        acronym_for_attachment  = self.getAcronym(my_trace, entity_type)
        my_trace                = parent_trace.doing("Identifying sub tree to attach to",
                                                        data = {'signaled_from': __file__})
        if full_docking_uid==self.parent_UID: # We are attaching at the root
            tree_to_attach_to   = self

        else:
            parent_entity_instance  = self.find(full_docking_uid, my_trace)
            if parent_entity_instance == None:
                raise ApodeixiError(my_trace, "No node exists for UID '" + full_docking_uid + "'",
                                                data = {'signaled_from': __file__})

            tree_to_attach_to       = self._get_tree_to_attach_to(parent_entity_instance, entity_type, my_trace)

            sub_trace           = my_trace.doing("Validating acronym is not used by another entity",
                                                    data = {'signaled_from': __file__})
            if tree_to_attach_to.entity_type != entity_type:
                raise ApodeixiError(sub_trace, "Can't add entity '" + entity_type 
                                    + "' because its acronym conflicts with acronym of previously used entity '"
                                    + tree_to_attach_to.entity_type + "'")

        my_trace                = parent_trace.doing("Generating UID for new node to attach ",
                                                        data = {    'acronym_for_attachment': acronym_for_attachment,
                                                                    'acronym is for'        : entity_type,
                                                                    'full_docking_uid'      : full_docking_uid,
                                                                    'signaled_from'         : __file__})        
        full_uid, leaf_uid      = self.uid_store.generateUID(   parent_trace    = my_trace,
                                                                acronym         = acronym_for_attachment, 
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

        my_trace                = parent_trace.doing("Looking for an acronym for '" + entity_type_to_attach + "'",
                                                        data = {'entity_type_to_attach': entity_type_to_attach,
                                                                'signaled_from': __file__})
        acronym_for_attachment  = self.getAcronym(my_trace, entity_type_to_attach)

        my_trace                = parent_trace.doing("Finding subtree to attach to",
                                                        data = {'acronym_for_attachment': acronym_for_attachment,
                                                                'signaled_from': __file__})
        tree_to_attach_to       = containing_entity_instance.find_subtree(acronym_for_attachment, self, my_trace)

        if tree_to_attach_to==None: # This is first time we attach for this acronym, so create tree
            tree_to_attach_to   = BreakdownTree(self.uid_store, entity_type_to_attach, containing_entity_instance.UID)
            containing_entity_instance.breakdown_children[entity_type_to_attach]      = tree_to_attach_to

        return tree_to_attach_to

    def dock_subtree(self, entity_type, subtree_to_attach, parent_trace):

        my_trace                        = parent_trace.doing("Finding where to dock in containing tree",
                                                                data = {'signaled_from': __file__})
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
        my_trace                            = parent_trace.doing('Computing relative uid', data = { 'parent_UID': self.parent_UID,
                                                                                                    'signaled_from': __file__})

        
        if self.parent_UID != None:
            prefix                          = self.parent_UID + '.'
            if not descendent_uid.startswith(prefix):
                raise ApodeixiError(my_trace, "Bad  uid '" + descendent_uid + "': it should have started with '" + prefix + "'")  
            relative_uid                    = descendent_uid.lstrip (prefix)   

        my_trace                            = parent_trace.doing('Traversing uid path', data = {'relative_uid': relative_uid,
                                                                                                'signaled_from': __file__})
        uid_path                            = relative_uid.split('.')

        #previous_entity_instance            = None
        entity_instance                     = None # At start of loop, the entity instance for parth of uid_path already processed
        for idx in range(len(uid_path)):
            leaf_uid                        = uid_path[idx]
            loop_trace                      = my_trace.doing("Doing loop cycle for leaf_uid '" + leaf_uid + "'",
                                                                data = {'signaled_from': __file__})

            if entity_instance == None: # First cycle in loop, so search in root tree
                next_tree                   = self
            else:
                uid_acronym, uid_nb         = _parse_leaf_uid(leaf_uid, loop_trace)
                sub_trace                   = loop_trace.doing("Looking for a subtree for the '" + uid_acronym + "' acronym",
                                                                data = {'signaled_from': __file__})
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
                                                            data = {'breakdown keys': all_subtree_roots,
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

def _is_blank(txt):
    '''
    Returns True if 'txt' is NaN or just spaces
    '''
    if type(txt)==float and _math.isnan(txt):
        return True
    elif type(txt)==str:
        stripped_txt = _strip(txt)
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

def _acronym(txt, nb_letters=1):
    '''
    Returns a string of initials for 'txt', in uppercase, where each 'initial' consists of 1 or
    more letters, depending on the `nb_letters` parameter.

    Also, it ignores any sub-text within `txt` that is in parenthesis. 
    
    For example, if txt is 'Effort (man days) to deliver', this is treated the same as 'Effort to deliver', which results
    in a returned value of 'ETD' if nb_letters=1
    '''
    stripped_txt = _strip(txt)

    # Remove text within parenthesis, if any, using the natural language tool nltk.tokenize.SExprTokenizer
    sexpr                       =SExprTokenizer(strict=False)
    sexpr_tokens                = sexpr.tokenize(stripped_txt)
    parenthesis_free_tokens     = [t for t in sexpr_tokens if not ')' in t and not '(' in t]
    parentheis_free_txt         = ' '.join(parenthesis_free_tokens)

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
                                                data = {'signaled_from': __file__})
    if m == None or len(m.groups()) != 2:
        raise ApodeixiError(parent_trace, "Couldn't parse leaf_uid '" + leaf_uid + "'")
    acronym             = m.group(1)
    nb                  = int(m.group(2))
    return acronym, nb


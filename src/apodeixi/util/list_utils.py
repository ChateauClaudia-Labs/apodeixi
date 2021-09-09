from apodeixi.util.a6i_error                        import ApodeixiError

class ListUtils():
    '''

    '''
    def __init__(self):
        return
    
    def print(self, parent_trace, a_list):
        '''
        Utility to produce as string out of possibly nested set of lists, by calling str(x) for the atomic element x of
        the list (or the sub-lists of the list, etc)
        '''
        if a_list == None or type(a_list) != list:
            return str(a_list)
        
        return str([self.print(parent_trace, elt) for elt in a_list])
        

class ListMerger():
    '''
    Utility class to do an order-preserving merge two lists of indices, i.e., lists whose entries can be compared with '==' and 
    which can be queried for membership in a list using the 'in' operator (e.g., `x in my_list`)

    It requires the input lists to be order-consistent. That condition is defined as follows: 
    
    For a list L, and members x, y in L, say "x < y in L" iff L.index(x) < L.index(y).

    Then if L1 and L2 are lists, L1 and L2 are order-consistent iff for any x, y in both L1 and L2, x < y in L1 iff x < y in L2.

    Given order-consistent L1, L2, this method computes a new merged list L_merged such that:

    * L_merged is a list of triples.
    * For an entry E in L_merged:
      * E[0] belongs to either L1, L2, or both
      * For i=1,2, E[i] is a boolean that is True iff E[i] belongs to Li
    '''
    def __init__(self, parent_trace, list1, list1_name, list2, list2_name):
        ME                              = ListMerger
        if not ME._are_order_consistent(parent_trace, list1, list2):
            raise ApodeixiError("Can't use a ListMerger on lists that are not order-consistent",
                                    data = {"list1": str(list1), "list2": str(list2)})
        self.list1              = list1
        self.list1_name         = list1_name
        self.list2              = list2
        self.list2_name         = list2_name

        self.walk1              = ME._DoingAWalk(parent_trace, self.list1, merger=self)
        self.walk2              = ME._DoingAWalk(parent_trace, self.list2, merger=self)

        self.result             = []
        return

    def merge(self, parent_trace):
        ME                      = ListMerger
        while self._has_next(parent_trace):
            entry               = self._choose_next(parent_trace)
            self.result.append(entry)
        return self.result
        '''
        return [['foo', False, True],
                ['bar', True, True],
                    ['pura vida', True, False]]
        '''

    def format_results(self, parent_trace):
        '''
        Returns a string representation of the results (so far) for this ListMerger
        '''
        output_txt                      = '\n'.join(['\t\t'.join(["Element: " + str(e[0]), 
                                                                "LEFT" if e[1] else "    ", 
                                                                "RIGHT" if e[2] else "     "]) for e in self.result])
        return output_txt

    def _has_next(self, parent_trace):
        '''
        Returns True if there are elements in either self.list1 or self.list2 to still walk to
        '''
        if self.walk1._walk_is_over(parent_trace) and self.walk2._walk_is_over(parent_trace):
            return False
        return True

    def _choose_next(self, parent_trace):
        '''
        Returns the instance of _DoingAWalk that should be advanced, without advancing it just yet.
        I.e., which of the two lists to progress.

        Returns the entry to select next
        '''
        if self.walk1._walk_is_over(parent_trace):
            elt                     = self.walk2.peek(parent_trace)
            self.walk2.advance_if_safe(parent_trace)
            return [elt, False, True]
        elif self.walk2._walk_is_over(parent_trace):
            elt                     = self.walk1.peek(parent_trace)
            self.walk1.advance_if_safe(parent_trace)
            return [elt, True, False]
        else:
            elt1                    = self.walk1.peek(parent_trace)
            elt2                    = self.walk2.peek(parent_trace)

            if elt1 == elt2:
                elt                     = elt1
                self.walk1.advance_if_safe(parent_trace)
                self.walk2.advance_if_safe(parent_trace)
                return [elt, True, True]                
            elif self.walk2.lies_ahead(parent_trace, elt1): # We will run into elt1 later on, so choose to advance walk2
                elt                     = elt2
                self.walk2.advance_if_safe(parent_trace)
                return [elt, False, True]
            elif self.walk1.lies_ahead(parent_trace, elt2):
                elt                     = elt1
                self.walk1.advance_if_safe(parent_trace) # Advance walk1 since elt2 will re-appear later
                return [elt, True, False]
            else: # It doesn't matter what we pick
                elt                     = elt2
                self.walk2.advance_if_safe(parent_trace)
                return [elt, False, True]

    def _are_order_consistent(parent_trace, list1, list2):
        '''
        Return True if list1 and list2 are order consistent, and false otherwise.
        Raises an ApodeixiError if types are not as expected.
        '''
        ME                              = ListMerger
        # Check that list 1 is order consistent with list2
        for x in list1:
            for y in list1:
                if x in list2 and y in list2:
                    if ME._precedes(parent_trace, x, y, list1) and not ME._precedes(parent_trace, x, y, list2):
                        return False
        # So far so good. No inconsistencies found. Now check the other way around
        for x in list2:
            for y in list2:
                if x in list1 and y in list1:
                    if ME._precedes(parent_trace, x, y, list2) and not ME._precedes(parent_trace, x, y, list1):
                        return False
        # No problems found so far, so things are consistent
        return True

    def _precedes(parent_trace, x, y, a_list):
        '''
        Returns True if x appears before y in a_list. False if not.

        Raises exception if x, y are not in a_list of if the types are bad
        '''
        if x == None or y == None:
            raise ApodeixiError(parent_trace, "Can't compare elements that are null",
                                                data = {'x': str(x), 'y': str(y)})
        if type(a_list) != list:
            raise ApodeixiError(parent_trace, "Expected a list, and instead got a " + str(type(a_list)))

        if not x in a_list:
            raise ApodeixiError(parent_trace, "x is not in list",
                                                data = {'x': str(x), 'a_list': str(a_list)})
        if not y in a_list:
            raise ApodeixiError(parent_trace, "y is not in list",
                                                data = {'y': str(y), 'a_list': str(a_list)})

        if a_list.index(x) < a_list.index(y):
            return True
        return False

    class _DoingAWalk():
        '''
        Helper class to maintain state as we walk through a list

        @param merger   The ListMerger instance that is using this _DoingAWalk instance. Used to get state from the caller e.g., for error handling.
        '''
        def __init__(self, parent_trace, a_list, merger):
            if type(a_list) != list:
                raise ApodeixiError(parent_trace, "Can only walk a list, not a " + str(type(a_list)))
            if len(a_list) == 0:
                raise ApodeixiError(parent_trace, "Can only walk an empty list")
            self.a_list         = a_list
            self.merger         = merger
            self.current_idx    = 0 # Where in the list we are pointing to
            

        def _walk_is_over(self, parent_trace):
            '''
            Returns True if there is we have traversed through all the elements in self.a_list
            '''
            if self.current_idx >= len(self.a_list):
                return True
            return False

        def lies_ahead(self, parent_trace, elt):
            '''
            Returns True if 'elt' is a member of self.a_list and lies further ahead than the self.current_idx

            Raises an ApodeixeError if the walk is already over
            '''
            if self._walk_is_over(parent_trace):
                raise ApodeixiEror(parent_trace, "Walk is over, so can't inquire what lies ahead")
            if elt in self.a_list[self.current_idx:]:
                return True
            return False

        def peek(self, parent_trace):
            '''
            Returns the element in self.a_list where we are currently at

            Raises an ApodeixeError if the walk is already over
            '''
            if self._walk_is_over(parent_trace):
                raise ApodeixiError(parent_trace, "Walk is over, so peeking is not allowed",
                                        data = {'results (so far)': self.merger.format_results(parent_trace)})
            return self.a_list[self.current_idx]

        def advance_if_safe(self, parent_trace):
            '''
            Walks to the next element in the list, if there is one

            Raises an ApodeixeError if the walk is already over
            '''
            if not self._walk_is_over(parent_trace):
                self.current_idx = self.current_idx + 1
                #return self.peek(parent_trace)

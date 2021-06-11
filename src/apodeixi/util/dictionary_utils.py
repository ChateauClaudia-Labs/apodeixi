from apodeixi.util.a6i_error                    import ApodeixiError

class DictionaryUtils():
    '''
    Helper class to group a number of commonly used utilities around the manipulation and validation of dictionaries
    '''
    def __init__(self):
        return

    def validate_path(self, parent_trace, root_dict, root_dict_name, path_list, valid_types=None):
        '''
        Used to validate that dictionaries adhere to a certain "schema", in situations where the dictionary represents a "tree"
        where the leaves are any kind of object but the intermediate nodes are dictionaries.

        In such cases, it is often necessary to validate that a certain branch exists in the tree.
        For example, suppose we want to get the date of the 3rd milestone for workstream W2 in strategic initiative S1.
        This may be represented as this "branch" in the dictionary:

            root_dict['S1']['W2']['milestones'][3]['date']

        To avoid getting exceptions, this method can be called with path_list = ['S1', 'W2', 'milestones', 3, 'date'].
        Them method will return two things:

        * A boolean, stating whether the branch in question exists or not
        * A string explanation which explains which part of the branch does not exist, if the branch doesn't exist. Else the
          explanation None
        
        Optionally, the method can validate that the leaf root_dict['S1']['W2']['milestones'][3]['date'] belongs to a list of valid types.

        @param parent_trace An Apodeixi FunctionalTrace, used to send functionally friendlier errors in case of problems.
        @param root_dict A dictionary for which we want to validate if it is the root of a tree with a branch as given by path_list
        @param root_dict_name A string used as a friendly name when referring to this dictionary in error messages
        @param path_list A list such as ['S1', 'W2', 'milestones', 3, 'date'] for which we want to verify if 
                         root_dict['S1']['W2']['milestones'][3]['date'] is valid.
        @param valid_types A list of types constraining the allowed types for the leaf object. If set to None then no type validation is made.
        '''
        if type(root_dict) != dict:
            raise ApodeixiError(parent_trace, "validate_path expects to be given a dictionary, but instead it was given a " 
                                                    + str(type(root_dict)),
                                                data = {'path_list': path_list},
                                                origination = {'signaled_from': __file__})
        if type(path_list) != list:
            raise ApodeixiError(parent_trace, "validate_path expects to be given the path as a list, but instead it was given a " 
                                                    + str(type(path_list)),
                                                data = {'path_list': path_list},
                                                origination = {'signaled_from': __file__})
        if valid_types != None and type(valid_types) != list:
            raise ApodeixiError(parent_trace, "validate_path expects to be given the valid leaf types as a list, but instead it was given a " 
                                                    + str(type(valid_types)),
                                                data = {'valid_types': valid_types},
                                                origination = {'signaled_from': __file__})
        current_dict                = root_dict
        current_dict_description    = root_dict_name
        explanation                 = ''
        for idx in range(len(path_list)):
            link                    = path_list[idx]
            if not link in current_dict.keys():
                explanation         = "'" + link + "' is not a valid key of the dictionary '" + current_dict_description \
                                        + "'"
                return False, explanation

            child                   = current_dict[link]
            if idx < len(path_list) - 1: # We are not yet at a leaf - should have found a dictionary in that case
                if type(child) != dict:
                    # if path_list = ['S1', 'W2', 'milestones', 3, 'date'] and idx=2, the explanation below would read like
                    # 
                    #     'root_dict[S1][W2][milestones]' is not a dictionary, so can't continue navigating rest of path '[3][date]'
                    #
                    explanation         = "'" + current_dict_description + "[" + link + "]' is not a dictionary, so can't" \
                                            + " continue navigating rest of path '[" + "][".join([str(elt) for elt in path_list[idx+1:]]) + "]'"
                    return False, explanation
            elif valid_types != None: # We are at a leaf and caller gave us types to validate against. 
                if not type(child) in valid_types:
                    explanation         = "'" + current_dict_description + "[" + link + "]' is of type '" + str(type(child)) \
                                            + "' but it was supposed to be one of " + ",".join(valid_types)

            # We survived to live another cycle of the loop. Initialize state for that next cycle
            current_dict_description    = current_dict_description + "[" + link + "]"
            current_dict                = child
                    
        # If we get this far, we haven't found problems  
        return True, explanation
               

    def replace_path(self, parent_trace, root_dict, root_dict_name, path_list, replacement_lambda):
        '''
        Returns a new dictionary, equal to the `root_dict` except that the given `path_list` has been removed, if it exists at all.

        @param parent_trace An Apodeixi FunctionalTrace, used to send functionally friendlier errors in case of problems.
        @param root_dict A dictionary from which we want to create a "subtree" identical to it except for removal of the branch as given by path_list
        @param root_dict_name A string used as a friendly name when referring to this dictionary in error messages
        @param path_list A list such as ['S1', 'W2', 'milestones', 3, 'date'] corresponding to a "branch" in the "tree" represented by `root_dict` 
                            Accepts the wildcard "*", which is then taken to me: all the keys at that level (in effect, multiple branches)
        @param replacement_lambda A function that takes as input the value of the `root_dict` at the branch, and returns the value that should
                                replace it in the returned dictionary.
        '''
        new_dict                    = root_dict.copy()
        WILDCARD                    = '*'
        if len(path_list) == 0:
            return new_dict

        path_start                  = path_list[0]

        my_trace = parent_trace.doing("Traversing one step in path", data = {'step': str(path_start)}) 
        children_to_process         = []
        # Check for wildcards
        if path_start == WILDCARD:
            children_to_process     = list(new_dict.keys())
        else:
            children_to_process     = [path_start]

        # Filter out anything that is not really a key
        children_to_process         = [child for child in children_to_process if child in new_dict.keys()]
        if len(path_list) == 1: # we hit bottom
            for child in children_to_process:
                old_val             = new_dict[child]
                new_dict[child]     = replacement_lambda(old_val)
        else: # recursively go down
            for child in children_to_process:
                loop_trace = my_trace.doing("Recursively going down one tree level", data = {'child': str(child)})
                new_dict[child]     = self.replace_path(   parent_trace         = loop_trace, 
                                                            root_dict           = new_dict[child], 
                                                            root_dict_name      = root_dict_name + "." + str(child), 
                                                            path_list           = path_list[1:],
                                                            replacement_lambda  = replacement_lambda)  
        return new_dict

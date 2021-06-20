from apodeixi.util.a6i_error                    import ApodeixiError

class DictionaryUtils():
    '''
    Helper class to group a number of commonly used utilities around the manipulation and validation of dictionaries
    '''
    def __init__(self):
        return

    WILDCARD                    = '*'

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
                explanation         = "'" + str(link) + "' is not a valid key of the dictionary '" + current_dict_description \
                                        + "'"
                return False, explanation

            child                   = current_dict[link]
            if idx < len(path_list) - 1: # We are not yet at a leaf - should have found a dictionary in that case
                if type(child) != dict:
                    # if path_list = ['S1', 'W2', 'milestones', 3, 'date'] and idx=2, the explanation below would read like
                    # 
                    #     'root_dict[S1][W2][milestones]' is not a dictionary, so can't continue navigating rest of path '[3][date]'
                    #
                    explanation         = "'" + current_dict_description + "[" + str(link) + "]' is not a dictionary, so can't" \
                                            + " continue navigating rest of path '[" + "][".join([str(elt) for elt in path_list[idx+1:]]) + "]'"
                    return False, explanation
            elif valid_types != None: # We are at a leaf and caller gave us types to validate against. 
                if not type(child) in valid_types:
                    explanation         = "'" + current_dict_description + "[" + str(link) + "]' is of type '" + str(type(child)) \
                                            + "' but it was supposed to be one of " + ",".join(valid_types)

            # We survived to live another cycle of the loop. Initialize state for that next cycle
            current_dict_description    = current_dict_description + "[" + str(link) + "]"
            current_dict                = child
                    
        # If we get this far, we haven't found problems  
        return True, explanation
               
    def replace_path(self, parent_trace, root_dict, root_dict_name, path_list, replacement_lambda):
        '''
        Returns a new dictionary, equal to the `root_dict` except that the given `path_list` has been replaced, if it exists at all.

        @param parent_trace An Apodeixi FunctionalTrace, used to send functionally friendlier errors in case of problems.
        @param root_dict A dictionary from which we want to create an almost equal "cloned tree" identical to it except for 
                        replacement of the branch as given by path_list, with a leaf node chnaged as per the replacement lambda
        @param root_dict_name A string used as a friendly name when referring to this dictionary in error messages
        @param path_list A list such as ['S1', 'W2', 'milestones', 3, 'date'] corresponding to a "branch" in the "tree" 
                        represented by `root_dict` 
                        Accepts the wildcard "*", which is then taken to me: all the keys at that level (in effect, multiple branches)
        @param replacement_lambda A function that takes as input the value of the `root_dict` at the branch, and returns the value 
                        that should replace it in the returned dictionary.
        '''
        new_dict                    = root_dict.copy()
        if len(path_list) == 0:
            return new_dict

        path_start                  = path_list[0]

        my_trace = parent_trace.doing("Traversing one step in path", data = {'step': str(path_start)}) 
        children_to_process         = []
        # Check for wildcards
        if path_start == DictionaryUtils.WILDCARD:
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

    def filter(self, parent_trace, root_dict, root_dict_name, path_list, filter_lambda):
        '''
        Returns a dictionary which is a subset of the `root_dict`, using the given `path_list` as a filter.

        If one thinks of the root_dictionary as a tree, then the returned dictionary is a subtree where a branch in root_dict
        also appears in the returned dictionary if and only if that branch matches the path_list. Wildcards ("*") are allowed
        in the path_list

        @param parent_trace An Apodeixi FunctionalTrace, used to send functionally friendlier errors in case of problems.
        @param root_dict A dictionary from which we want to compute a "subtree" 

        @param root_dict_name A string used as a friendly name when referring to this dictionary in error messages
        @param path_list A list such as ['S1', 'W2', 'milestones', 3, 'date'] corresponding to a "branch filter to apply. 
                        Wildcard "*", which is then taken to me: all the keys at that level pass the filter (in effect, 
                        multiple branches)
        @param filter_lambda A function that takes as input the value of the `root_dict`'s leaf at the branch, and returns the value 
                that should replace it in the returned dictionary.
        '''
        new_dict                    = {}
        
        if len(path_list) == 0:
            return new_dict

        path_start                  = path_list[0]

        my_trace = parent_trace.doing("Traversing one step in path", data = {'step': str(path_start)}) 
        children_to_process         = []
        # Check for wildcards
        if path_start == DictionaryUtils.WILDCARD:
            children_to_process     = list(root_dict.keys())
        else:
            children_to_process     = [path_start]

        # Filter out anything that is not really a key
        children_to_process         = [child for child in children_to_process if child in root_dict.keys()]
        if len(path_list) == 1: # we hit bottom
            for child in children_to_process:
                val                 = root_dict[child]
                if filter_lambda(val):
                    new_dict[child]     = val
        else: # recursively go down
            for child in children_to_process:
                loop_trace = my_trace.doing("Recursively going down one tree level", data = {'child': str(child)})
            
                sub_result          = self.filter(  parent_trace        = loop_trace, 
                                                    root_dict           = root_dict[child], 
                                                    root_dict_name      = root_dict_name + "." + str(child), 
                                                    path_list           = path_list[1:],
                                                    filter_lambda       = filter_lambda)  
                if sub_result != {}: # Didn't filter out everything, so this child counts
                    new_dict[child] = sub_result

        return new_dict

    def get_val(self, parent_trace, root_dict, root_dict_name, path_list):
        '''
        Thinking of `root_dict` dictionary as a tree, and of `path_list` as a branch, this method returns the
        value of the leaf node of the branch.

        If the branch does not exist, it raises an ApodeixiError
        
        '''
        if path_list == None or type(path_list) != list or len(path_list) == 0:
            raise ApodeixiError(parent_trace, "Can't get a value at path that is not a non-empty list",
                                            data = {'root_dict_name': root_dict_name, 'path_list': str(path_list)})

        check, explanations     = DictionaryUtils().validate_path(  parent_trace        = parent_trace, 
                                                                    root_dict           = root_dict, 
                                                                    root_dict_name      = root_dict_name, 
                                                                    path_list           = path_list, 
                                                                    valid_types         = None)  
        if not check:
            raise ApodeixiError(parent_trace, "Can't get value for a path that does not exist",
                                                data = {'root_dict_name': root_dict_name, 'path_list': str(path_list),
                                                            'explanations': str(explanations)}) 

        sub_dict                = root_dict
        for step in path_list[:-1]:
            sub_dict = sub_dict[step]
        
        val                     = sub_dict[path_list[-1]]
        return val
             

    def set_val(self, parent_trace, root_dict, root_dict_name, path_list, val):
        '''
        Thinking of `root_dict` dictionary as a tree, and of `path_list` as a branch, this method adds the branch to the
        tree if it no longer exists, and then sets the value of the leaf node to be val.
        
        '''
        if path_list == None or type(path_list) != list or len(path_list) == 0:
            raise ApodeixiError(parent_trace, "Can't set a value at path that is not a non-empty list",
                                            data = {'root_dict_name': root_dict_name, 'path_list': str(path_list)})

        path_start                      = path_list[0]

        my_trace = parent_trace.doing("Traversing one step in path", data = {'step': str(path_start)}) 

        if len(path_list) == 1: # We hit bottom
            root_dict[path_start]       = val
        else: # Recurse down
            if not path_start in root_dict.keys(): # Add it if missing
                root_dict[path_start]   = {}
            
            sub_dict                    = root_dict[path_start]
            sub_path                    = path_list[1:]
            my_trace                    = parent_trace.doing("Recursively setting-value",
                                                            data = {'path_list': str(sub_path)})
            self.set_val(   parent_trace    = my_trace, 
                            root_dict       = sub_dict, 
                            root_dict_name  = root_dict_name + "." + str(path_start), 
                            path_list       = sub_path,
                            val             = val)  
        return

class ListUtils():

    def is_sublist(self, parent_trace, super_list, alleged_sub_list):
        '''
        Checks if `alleged_sub_list` is a sublist of `super_list`. Returns a boolean to state if it is a sublist, as well
        as two lists: pre_list and sub_list that are "split" by the `alleged_sub_list`. 
        If the boolean is True then the following will hold true:

            Isublist == pre_list + alleged_sub_list + post_list
        
        If on the other hand the boolean is False, then both `pre_list` and `post_list` are None.

        If either the super_list or the alleged_sub_list is empty then it return false.
        '''
        if type(super_list) != list or type(alleged_sub_list) != list:
            raise ApodeixiError(parent_trace, "Can't determine if we have a sub list because was given wrong types, not lists",
                                                data = {'type of super_list':       str(type(super_list)),
                                                        'type of alleged_sub_list': str(type(alleged_sub_list))})
        if len(super_list) == 0 or len(alleged_sub_list) == 0:
            return False, None, None
        
        # Get the indices in super_list for the first element of alleged_sub_list that leave enough room for the
        # alleged_sub_list to fit after that. These are candidate locations for a split
        sub_length              = len(alleged_sub_list)
        candidate_idxs          = [idx for idx, x in enumerate(super_list) 
                                        if x == alleged_sub_list[0] and len(super_list[idx:]) >= sub_length]

        # Now see if any of the candidate split locations work
        for idx in candidate_idxs:
            if alleged_sub_list == super_list[idx:idx + sub_length]: # Found a match!
                pre_list        = super_list[:idx]
                post_list       = super_list[idx + sub_length:]
                return True, pre_list, post_list

        # If we get this far, there is no match
        return False, None, None
            


class DictionaryFormatter():
    '''
    Utility class that represents a dictionary as as string, by flattening its hierarchical representation. Require that all
    entries are either dictionaries, strings, floats, or lists, recursively down.
    '''
    def __init__(self):
        return

    def dict_2_nice(self, a_dict, flatten=False, delimeter="."):
        '''
        Helper method to return a "nice" string where each entry in the dictionary is placed on a separate line.
        Useful when saving a dictionary as text output, to make it more readable

    '''
        # First flatten dictionary to a 1-level dictionary
        if flatten:
            working_dict    = {}
            self._flatten(  input_dict  = a_dict, 
                            result_dict = working_dict,    
                            delimeter   = delimeter)
        else:
            working_dict    = a_dict

        # Now convert to a nice string
        result_nice         = ''
        for k in working_dict.keys():
            result_nice     += str(k) + '\t\t' + str(working_dict[k]) + '\n'
        return result_nice

    def _flatten(self, input_dict, result_dict = {}, parent_key=None, delimeter="."):
            '''
            Reduces the levels of a given dictionary, by creating a new dictionary whose keys are computed as follows:
            - For each key K in the input whose value is a scalar: K is key in the output
            - For each key K in the input whose value is a sub-dictionary S: K.subKey is a key in the output, where each
            subKey is a key in S (this example assumes that the delimeter is "." - more generally, whatever string is
            passed in for delimeter is what will be used)
            - And so on recursively
            '''
            def _full_key(key):
                if parent_key == None:
                    return key
                else:
                    return str(parent_key) + delimeter + str(key)
                
            if type(input_dict) in [str, float, int, list, bool, type(None)]: # We hit bottom
                result_dict[parent_key] = input_dict
                return
            
            if type(input_dict) != dict: # Nothing to flatten, input is not really a dict
                raise ValueError("Unable to flatten a non-dict '" + str(type(input_dict)) + "'' under parent_key='"
                                + str(parent_key) + "': " + str(input_dict))

            for key in input_dict.keys():
                val = input_dict[key]
                if type(val) == dict:
                    self._flatten(val, result_dict, _full_key(key), delimeter=delimeter)
                elif type(val) == list and len(val) > 0:
                    for idx in range(len(val)):
                        self._flatten(val[idx], result_dict, _full_key(key + delimeter + str(idx)), delimeter=delimeter)
                else:
                    result_dict[_full_key(key)] = val

            return


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
                return input_dict
            
            if type(input_dict) != dict: # Nothing to flatten, input is not really a dict
                raise ValueError("Unable to flatten a non-dict '" + str(type(input_dict)) + "'' under parent_key='"
                                + str(parent_key) + "': " + str(input_dict))

            for key in input_dict.keys():
                val = input_dict[key]
                if type(val) == dict:
                    self._flatten(val, result_dict, _full_key(key), delimeter=delimeter)
                elif type(val) == list:
                    for idx in range(len(val)):
                        self._flatten(val[idx], result_dict, _full_key(key + delimeter + str(idx)), delimeter=delimeter)
                else:
                    result_dict[_full_key(key)] = val

            return

import inspect                                  as _inspect
import sys                                      as _sys

import nbformat                                 as _nbformat
from nbconvert.preprocessors                    import ExecutePreprocessor

from apodeixi.util.a6i_error                    import ApodeixiError

# As documented in https://www.gitmemory.com/issue/zeromq/pyzmq/1521/824694187, need to change the Windows default event loop
# policy for asyncio (used indirectly by nbconvert, in turn used by NotebookUtils) to work
import asyncio                              as _asyncio
if _sys.platform == 'win32':
    _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())


class StringUtils():

    def rreplace(self, input_txt, old, new, nb_replaments=1):
        '''
        Replaces the *last* `nb_replaments` occurrences of the `old` text by the `new` text in the given `input_txt`.
        By default `nb_replaments` is 1, in which case only the last occurrence is replaced.
        '''
        li = input_txt.rsplit(old, nb_replaments)
        return new.join(li)

class NotebookUtils():
    '''
    Utilities to process Jupyter notebooks
    '''
    def __init__(self, src_folder, src_filename, destination_folder, destination_filename):
        self.src_folder                 = src_folder
        self.src_filename               = src_filename
        self.destination_folder         = destination_folder
        self.destination_filename       = destination_filename
    
    def run(self, parent_trace):
        # As documented in https://nbconvert.readthedocs.io/en/latest/execute_api.html
        #
        # May get an error like this unless we explicity use UTF8 encoding:
        #
        #   File "C:\Alex\CodeImages\technos\anaconda3\envs\ea-journeys-env\lib\encodings\cp1252.py", line 19, in encode
        #   return codecs.charmap_encode(input,self.errors,encoding_table)[0]
        #   UnicodeEncodeError: 'charmap' codec can't encode character '\u2610' in position 61874: character maps to <undefined>
        #     
        my_trace                        = parent_trace.doing("Attempting to load notebook")
        try:
            with open(self.src_folder + '/' + self.src_filename, encoding="utf8") as f:
                nb = _nbformat.read(f, as_version=4)
        except Exception as ex:
            raise ApodeixiError("Encountered this error while loading notebook: " + str(ex),
                                data    = { 'src_folder':           self.src_folder,
                                            'src_filename':         self.src_filename})


        my_trace                        = parent_trace.doing("Attempting to execute notebook")
        try:
            #ep = ExecutePreprocessor(timeout=600, kernel_name='python3') 
            ep = ExecutePreprocessor(timeout=600) # Use virtual-env's kernel, so don't specify: kernel_name='python3'

            ep.preprocess(nb, {'metadata': {'path': self.destination_folder + '/'}}) # notebook executes in the directory specified by the 'path' metadata field
        except Exception as ex:
            raise ApodeixiError(my_trace, "Encountered this error while executing notebook: " + str(ex),
                                data    = { 'src_folder':           self.src_folder,
                                            'src_filename':         self.src_filename})


        my_trace                        = parent_trace.doing("Attempting to save notebook")
        try:
            if self.destination_folder != None and self.destination_filename != None:
                with open(self.destination_folder + '/' + self.destination_filename, 'w', encoding='utf-8') as f:
                    _nbformat.write(nb, f)
        except Exception as ex:
            raise ApodeixiError("Encountered this error while executing notebook: " + str(ex),
                                data    = { 'destination_folder':           self.destination_folder,
                                            'destination_filename':         self.destination_filename})

        my_trace                        = parent_trace.doing("Converting notebook to dictionary after executing it")
        return NotebookUtils._val_to_dict(my_trace, nb) 

    def _val_to_dict(parent_trace, val):
        try:
            result                  = {}
            if type(val) == _nbformat.notebooknode.NotebookNode:
                for key in val.keys():
                    loop_trace      = parent_trace.doing('Recursive for dictionary element', data = {'key': key})
                    result[key] = NotebookUtils._val_to_dict(loop_trace, val[key])
            elif type(val) == list:
                for idx in range(len(val)):
                    loop_trace      = parent_trace.doing('Recursive for list element', data = {'idx': str(idx)})
                    result[idx] = NotebookUtils._val_to_dict(loop_trace, val[idx])
            else:
                result              = val
            return result
        except Exception as ex:
            val_txt                 = str(val)
            if len(val_txt) > 100:
                val_txt             = val_txt[:100] + " .... .... ...." + str(len(val_txt)-100) + "  additional text characters ... ..."

            raise ApodeixiError(parent_trace, "Encountered error while converting notebook to dictionary: " + str(ex),
                                    data = {'val': val_txt})

class ListUtils():

    def is_sublist(self, parent_trace, super_list, alleged_sub_list):
        '''
        Checks if `alleged_sub_list` is a sublist of `super_list`. Returns a boolean to state if it is a sublist, as well
        as two lists: pre_list and sub_list that are "split" by the `alleged_sub_list`. 
        If the boolean is True then the following will hold true:

            super_list == pre_list + alleged_sub_list + post_list
        
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

    def dict_2_nice(self, parent_trace, a_dict, flatten=False, delimeter="."):
        '''
        Helper method to return a "nice" string where each entry in the dictionary is placed on a separate line.
        Useful when saving a dictionary as text output, to make it more readable
        '''
        # First flatten dictionary to a 1-level dictionary
        if flatten:
            working_dict    = {}
            self._flatten(  parent_trace    = parent_trace,
                            input_dict      = a_dict, 
                            result_dict     = working_dict,    
                            delimeter       = delimeter)
        else:
            working_dict    = a_dict

        # Now convert to a nice string
        result_nice         = ''
        for k in working_dict.keys():
            result_nice     += str(k) + '\t\t' + str(working_dict[k]) + '\n'
        return result_nice

    def _flatten(self, parent_trace, input_dict, result_dict = {}, parent_key=None, delimeter="."):
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
            
            if type(input_dict) != dict: # Looks bad... usually can't flatten objects that are not really a dict
                # Before giving up, see if object has a "to_dict" method to convert input_dict to a real _dict
                my_trace            = parent_trace.doing("Attempting to convert a '" + str(type(input_dict)) + "' to a dict in order to flatten it")
                to_dict_op          = None
                try: 
                    to_dict_op      = getattr(input_dict, 'to_dict')
                    if callable(to_dict_op):
                        args_list = _inspect.getfullargspec(to_dict_op).args # Should be something like ['self', 'parent_trace']
                        if len(args_list) == 2 and args_list[1] == 'parent_trace': # We are in luck: try again but converting to a dict
                            return self._flatten(   parent_trace        = my_trace, 
                                                    input_dict          = input_dict.to_dict(my_trace), 
                                                    result_dict         = result_dict, 
                                                    parent_key          = parent_key, 
                                                    delimeter           = delimeter)                            
                except Exception as ex:
                    raise ApodeixiError(my_trace, "Failed attempt to convert to  dict",
                                                    data = {    'exception_encountered':    str(ex),
                                                                'parent_key':               str(parent_key),
                                                                'type_to_convert_from':     str(type(input_dict)),
                                                                'object_being_converted':   str(input_dict)}) 
  

            # If we get this far and still don't have a dict after attempting to convert to a dict above, just fail                                                           
            if type(input_dict) != dict: 
                raise ApodeixiError(my_trace, "Can't flatten object of unsupported type",
                                                data = {    'parent_key':           str(parent_key),
                                                            'unsupported_type':     str(type(input_dict)),
                                                            'unsupported_object':   str(input_dict)}) 
            for key in input_dict.keys():
                loop_trace                                  = parent_trace.doing("Processing loop cycle", data = {'key': key})
                val                                         = input_dict[key]
                if type(val) == dict:
                    self._flatten(      parent_trace        = loop_trace, 
                                        input_dict          = val, 
                                        result_dict         = result_dict, 
                                        parent_key          = _full_key(key), 
                                        delimeter           = delimeter)
                        
                elif type(val) == list and len(val) > 0:
                    for idx in range(len(val)):
                        self._flatten(  parent_trace        = loop_trace, 
                                        input_dict          = val[idx], 
                                        result_dict         = result_dict, 
                                        parent_key          = _full_key(str(key) + delimeter + str(idx)), 
                                        delimeter           = delimeter)
                else:
                    result_dict[_full_key(key)] = val

            return

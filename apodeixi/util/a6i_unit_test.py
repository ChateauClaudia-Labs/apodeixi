import unittest
import sys                  as _sys
import os                   as _os
import yaml                 as _yaml
import pandas               as _pd
import inspect
from io                     import StringIO

class ApodeixiUnitTest(unittest.TestCase):
    '''
    Parent class for unit tests in Apodeixi
    '''

    def setUp(self):
        super().setUp()

        # We can't rely on Python's built-in '__file__' property to find the location of the concrete class
        # that is running, since we are in the parent class and we will get the parent class's filename, not the concrete class's.
        # So instead we rely on the inspect package
        me__file__                  = inspect.getfile(self.__class__)
        # self.input_data             = _os.path.join(_os.path.dirname(__file__), 'input_data') # Doesn't work - use inpectt instead
        self.input_data             = _os.path.join(_os.path.dirname(me__file__), 'input_data') # Works ! :-) Thanks inspect!
        # self.output_data            = _os.path.join(_os.path.dirname(__file__), 'output_data') # Doesn't work - use inpectt instead
        self.output_data            = _os.path.join(_os.path.dirname(me__file__), 'output_data') # Works ! :-) Thanks inspect!

    def load_csv(self, path):
        '''
        Helper method to load a "clean DataFrame" from a CSV file, correcting for spurious columns and NAs
        '''
        data_df             = _pd.read_csv(path)
        data_df             = data_df.fillna('')
        data_df             = data_df.drop(['Unnamed: 0'], axis=1)

        return data_df

    def dict_2_nice(self, a_dict, flatten=False):
        '''
        Helper method to return a "nice" string where each entry in the dictionary is placed on a separate line.
        Useful when saving a dictionary as text output, to make it more readable

    '''
        # First flatten dictionary to a 1-level dictionary
        if flatten:
            working_dict    = {}
            self._flatten(input_dict     = a_dict, result_dict   = working_dict)
        else:
            working_dict    = a_dict

        # Now convert to a nice string
        result_nice         = ''
        for k in working_dict.keys():
            result_nice     += str(k) + '\t\t' + str(working_dict[k]) + '\n'
        return result_nice

    def _flatten(self, input_dict, result_dict = {}, parent_key=None):
            '''
            Reduces the levels of a given dictionary, by creating a new dictionary whose keys are computed as follows:
            - For each key K in the input whose value is a scalar: K is key in the output
            - For each key K in the input whose value is a sub-dictionary S: K.subKey is a key in the output, where each
            subKey is a key in S
            - And so on recursively
            '''
            def _full_key(key):
                if parent_key == None:
                    return key
                else:
                    return str(parent_key) + '.' + str(key)
                
            if type(input_dict) in [str, float, int, list, bool, type(None)]: # We hit bottom
                return input_dict
            
            if type(input_dict) != dict: # Nothing to flatten, input is not really a dict
                raise ValueError("Unable to flatten a non-dict '" + str(type(input_dict)) + "'' under parent_key='"
                                + str(parent_key) + "': " + str(input_dict))

            for key in input_dict.keys():
                val = input_dict[key]
                if type(val) == dict:
                    self._flatten(val, result_dict, _full_key(key))
                elif type(val) == list:
                    for idx in range(len(val)):
                        self._flatten(val[idx], result_dict, _full_key(key + '.' + str(idx)))
                else:
                    result_dict[_full_key(key)] = val

            return


    def _save_output(self, output):
        '''
        Helper class used while developing test cases. Test cases will produce some output that needs to be compared
        to an expected output. When first written, one needs to capture the generated output somewhere in order to copy-and-paste
        it into the test case's code as the expected output. This method is used in such situations by temporarily calling
        it at the end of a test case in order to save the output to a text file. The text file's contents can then be pasted
        in the test case as the 'expected output'. Once that is done the test case should pass, and one can remove the line
        that called this method.
        '''
        with open(self.output_data + '/' + 'tmp.txt', 'w') as file:
            file.write(str(output))

    def _compare_to_expected_yaml(self, result_dict, test_case_name):
        '''
        Utility method for derived classes that create YAML files and need to check they match an expected output
        previously saves as a YAML file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        # Persist output and retrieve expected output
        with open(self.output_data + '/' + test_case_name + '_OUTPUT.yaml', 'w') as file:
            _yaml.dump(result_dict, file)
        with open(self.output_data + '/' + test_case_name + '_EXPECTED.yaml', 'r') as file:
            expected_dict           = _yaml.load(file, Loader=_yaml.FullLoader)

        output_stream               = StringIO()
        _yaml.dump(result_dict, output_stream)
        result_yaml                 = output_stream.getvalue()

        expected_stream             = StringIO()
        _yaml.dump(expected_dict, expected_stream)
        expected_yaml               = expected_stream.getvalue()

        self.assertEqual(result_yaml, expected_yaml)
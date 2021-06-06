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

        # We will have to clean data a bit, since some packaging procedures (for example,
        # creating a Conda package) introduces some carriage returns '\r\n' where the original expected output only
        # has a newline '\n', causing tests to fail when users install the Conda package. So simply remove the
        # '\r' from amu offending column, which typically are columns whose values are stringied arrays (i.e., strings with
        # newlines '\n' that confuse the Conda packaging). For packaging procedures that have no '\r', no harm is
        # done by this cleanup (i.e., expected_df is left "as is" if there are no '\r' in its 'Words per row')
        def _remove_carriage_returns(obj):
            if type(obj) == str:
                return obj.replace('\\r', '').replace('\r', '')
            elif type(obj) == list: # Remove carriages element by element
                return [_remove_carriage_returns(elt) for elt in obj]
            else:
                return obj

        # First clean the columns
        data_df.columns = [_remove_carriage_returns(col) for col in data_df.columns]

        # Now clear the cells
        for col in data_df.columns:
            data_df[col] = data_df.apply(lambda row: _remove_carriage_returns(row[col]), axis=1)

        return data_df

    def _compare_to_expected_yaml(self, output_dict, test_case_name, save_output_dict=False):
        '''
        Utility method for derived classes that create YAML files and need to check they match an expected output
        previously saves as a YAML file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        # Check not null, or else rest of actions will "gracefully do nothing" and give the false impression that test passes
        # (at least it would erroneously pass when the expected output is set to an empty file)
        self.assertIsNotNone(output_dict)

        # Persist output (based on save_output_dict flag)
        if save_output_dict:
            with open(self.output_data + '/' + test_case_name + '_OUTPUT.yaml', 'w') as file:
                _yaml.dump(output_dict, file)

        # Retrieve expected output
        with open(self.output_data + '/' + test_case_name + '_EXPECTED.yaml', 'r') as file:
            expected_dict           = _yaml.load(file, Loader=_yaml.FullLoader)

        output_stream               = StringIO()
        _yaml.dump(output_dict, output_stream)
        result_yaml                 = output_stream.getvalue()

        expected_stream             = StringIO()
        _yaml.dump(expected_dict, expected_stream)
        expected_yaml               = expected_stream.getvalue()

        self.assertEqual(result_yaml, expected_yaml)

    def _compare_to_expected_txt(self, output_txt, test_case_name, save_output_txt=False):
        '''
        Utility method for derived classes that create text files and need to check they match an expected output
        previously saves as a text file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        # Check not null, or else rest of actions will "gracefully do nothing" and give the false impression that test passes
        # (at least it would erroneously pass when the expected output is set to an empty file)
        self.assertIsNotNone(output_txt)

        # Persist output (based on save_output_dict flag)
        if save_output_txt:
            with open(self.output_data + '/' + test_case_name + '_OUTPUT.txt', 'w') as file:
                file.write(str(output_txt))

        # Retrieve expected output
        with open(self.output_data + '/' + test_case_name + '_EXPECTED.txt', 'r') as file:
            expected_txt            = str(file.read())

        self.assertEqual(str(output_txt), expected_txt)
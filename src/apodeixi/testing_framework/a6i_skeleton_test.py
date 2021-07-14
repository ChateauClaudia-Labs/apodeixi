import unittest
import sys                  as _sys
import os                   as _os
import yaml                 as _yaml
import pandas               as _pd
from io                     import StringIO


from apodeixi.util.formatting_utils                 import DictionaryFormatter
from apodeixi.util.path_utils                       import PathUtils
from apodeixi.util.dataframe_utils                  import DataFrameUtils, DataFrameComparator
from apodeixi.util.a6i_error                        import ApodeixiError

class ApodeixiSkeletonTest(unittest.TestCase):  
    '''
    Abstract parent class for all Apodeixi tests (both unit and integration tests)
    '''

    def setUp(self):
        super().setUp()

        # Remember it before we change it to use a test configuration, and then restore it in the tearDown method
        self.original_config_directory                      = _os.environ.get('APODEIXI_CONFIG_DIRECTORY')

        # Here we want the location of this class, not its concrete derived class,
        # since the location of the Apodexei config to be used for tests is globally unique
        # So we use __file__ 
        _os.environ['APODEIXI_CONFIG_DIRECTORY']            = _os.path.join(_os.path.dirname(__file__), 'config') 

        def _path_mask(path):
            tokens                                          = path.split('apodeixi')
            masked_path                                     = '<MASKED>/apodeixi' + "/".join(tokens[1:])
            return masked_path

        # Used by derived classes to mask some paths that are logged out so that regressino output is
        # deterministic
        self._path_mask                                     = _path_mask

    def tearDown(self):
        super().tearDown()

        # Restore the environment variable that we modeified in setUp
        old_dir                                             = self.original_config_directory
        # Dictionaries abhor null values, so default of empty string if null. 
        if old_dir == None:
            old_dir                                         = ''
        _os.environ['APODEIXI_CONFIG_DIRECTORY']            = old_dir

    def load_csv(self, parent_trace, path):
        '''
        Helper method to load a "clean DataFrame" from a CSV file, correcting for spurious columns and NAs
        '''
        try:
            data_df             = _pd.read_csv(path)
        except FileNotFoundError as ex:
            raise ApodeixiError(parent_trace, "Can't load CSV file because it doesn't exist",
                                    data = {'path':             path,
                                            'error':            str(ex)})

        data_df             = data_df.fillna('')
        SPURIOUS_COL        = 'Unnamed: 0'
        if SPURIOUS_COL in data_df.columns:
            data_df             = data_df.drop([SPURIOUS_COL], axis=1)

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

        # Clean up numbers and all else to a standard
        CLEANED                                         = DataFrameUtils().clean  # Abbreviation to express intent
        for col in data_df.columns:
            data_df[col] = data_df.apply(lambda row: CLEANED(row[col]), axis=1)
        return data_df

    
    def _compare_to_expected_yaml(self, parent_trace, output_dict, test_case_name, data_dir, save_output_dict=False):
        '''
        Utility method for derived classes that create YAML files and need to check they match an expected output
        previously saves as a YAML file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        # Check not null, or else rest of actions will "gracefully do nothing" and give the false impression that test passes
        # (at least it would erroneously pass when the expected output is set to an empty file)
        self.assertIsNotNone(output_dict)

        PathUtils().create_path_if_needed(parent_trace = parent_trace, path = data_dir)

        # Persist output (based on save_output_dict flag)
        if save_output_dict:
            # As documented in https://nbconvert.readthedocs.io/en/latest/execute_api.html
            #
            # May get an error like this unless we explicity use UTF8 encoding:
            #
            #   File "C:\Alex\CodeImages\technos\anaconda3\envs\ea-journeys-env\lib\encodings\cp1252.py", line 19, in encode
            #   return codecs.charmap_encode(input,self.errors,encoding_table)[0]
            #   UnicodeEncodeError: 'charmap' codec can't encode character '\u2610' in position 61874: character maps to <undefined>
            #
            # Happens in particular when trying to save a string representing a Jupyter notebook's execution, since for the same
            # reason above that string had to be written to a string using UTF8 encoding, so now if we save to a file we must use UTF8
            with open(data_dir + '/' + test_case_name + '_OUTPUT.yaml', 'w', encoding="utf8") as file:
                _yaml.dump(output_dict, file)

        # Retrieve expected output
        with open(data_dir + '/' + test_case_name + '_EXPECTED.yaml', 'r', encoding="utf8") as file:
            expected_dict           = _yaml.load(file, Loader=_yaml.FullLoader)

        output_stream               = StringIO()
        _yaml.dump(output_dict, output_stream)
        result_yaml                 = output_stream.getvalue()

        expected_stream             = StringIO()
        _yaml.dump(expected_dict, expected_stream)
        expected_yaml               = expected_stream.getvalue()

        self.assertEqual(result_yaml, expected_yaml)

    def _compare_to_expected_txt(self, parent_trace, output_txt, test_case_name, data_dir, save_output_txt=False):
        '''
        Utility method for derived classes that create text files and need to check they match an expected output
        previously saves as a text file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        # Check not null, or else rest of actions will "gracefully do nothing" and give the false impression that test passes
        # (at least it would erroneously pass when the expected output is set to an empty file)
        self.assertIsNotNone(output_txt)

        PathUtils().create_path_if_needed(parent_trace = parent_trace, path = data_dir)

        # Persist output (based on save_output_dict flag)
        if save_output_txt:
            # As documented in https://nbconvert.readthedocs.io/en/latest/execute_api.html
            #
            # May get an error like this unless we explicity use UTF8 encoding:
            #
            #   File "C:\Alex\CodeImages\technos\anaconda3\envs\ea-journeys-env\lib\encodings\cp1252.py", line 19, in encode
            #   return codecs.charmap_encode(input,self.errors,encoding_table)[0]
            #   UnicodeEncodeError: 'charmap' codec can't encode character '\u2610' in position 61874: character maps to <undefined>
            #
            # Happens in particular when trying to save a string representing a Jupyter notebook's execution, since for the same
            # reason above that string had to be written to a string using UTF8 encoding, so now if we save to a file we must use UTF8
            with open(data_dir + '/' + test_case_name + '_OUTPUT.txt', 'w', encoding="utf8") as file:
                file.write(str(output_txt))

        # Retrieve expected output
        with open(data_dir + '/' + test_case_name + '_EXPECTED.txt', 'r', encoding="utf8") as file:
            expected_txt            = str(file.read())

        self.assertEqual(str(output_txt), expected_txt)

    def _compare_to_expected_df(self, parent_trace, output_df, test_case_name, data_dir, columns_to_ignore=[], id_column=None):
        '''
        Utility method for derived classes that creates DataFrames (saved as CSV files) and checks they match an expected output
        previously saves as a CSV file as well. 

        It also saves the output as a CSV file, which can be copied to be the expected output when test case is created.

        @param data_dir Directory to which to save any output and from which to retrieve any previously saved expected output.
        @param columns_to_ignore List of column names (possibly empty), for columns that should be excluded from the comparison
        @param id_column A string representing the column that should be used to identify rows in comparison text produced. 
                         If set to None, then the row index is used.
        '''
        OUTPUT_FOLDER               = data_dir
        OUTPUT_FILE                 = test_case_name + '_OUTPUT.csv'
        EXPECTED_FILE               = test_case_name + '_EXPECTED.csv'
        OUTPUT_COMPARISON_FILE      = test_case_name + '_comparison_OUTPUT.txt'
        EXPECTED_COMPARISON_FILE    = test_case_name + '_comparison_EXPECTED.txt'

        # Check not null, or else rest of actions will "gracefully do nothing" and give the false impression that test passes
        # (at least it would erroneously pass when the expected output is set to an empty file)
        self.assertIsNotNone(output_df)

        PathUtils().create_path_if_needed(parent_trace = parent_trace, path = data_dir)

        OUTPUT_COLUMNS              = [col for col in output_df.columns if not col in columns_to_ignore] 
        output_df[OUTPUT_COLUMNS].to_csv(OUTPUT_FOLDER + '/' + OUTPUT_FILE)

        # Load the output we just saved, which we'll use for regression comparison since in Pandas the act of loading will
        # slightly change formats (e.g., strings for numbers become Numpy numbers) 
        # and we want to apply the same such changes as were applied to the expected output,
        # to avoid frivolous differences that don't deserve to cause this test to fail
        loaded_output_df            = self.load_csv(parent_trace, OUTPUT_FOLDER + '/' + OUTPUT_FILE)

        # Retrieve expected output
        expected_df                 = self.load_csv(parent_trace, OUTPUT_FOLDER + '/' + EXPECTED_FILE)

        EXPECTED_COLUMNS            = [col for col in expected_df.columns if not col in columns_to_ignore]  


        my_trace                    = parent_trace.doing("Invoking the DataFrameComparator")
        comparator                  = DataFrameComparator(  df1         = loaded_output_df[OUTPUT_COLUMNS], 
                                                            df1_name    = "output",
                                                            df2         = expected_df[EXPECTED_COLUMNS], 
                                                            df2_name    = "expected",
                                                            id_column   = id_column)

        check, comparison_dict      = comparator.compare(my_trace)

        df_comparison_nice          = DictionaryFormatter().dict_2_nice(    parent_trace    = parent_trace,
                                                                            a_dict          = comparison_dict, 
                                                                            flatten         = True)
        with open(OUTPUT_FOLDER + '/'  + OUTPUT_COMPARISON_FILE, 'w', encoding="utf8") as file:
            file            .write(df_comparison_nice)
        try:
            with open(OUTPUT_FOLDER + '/'  + EXPECTED_COMPARISON_FILE, 'r', encoding="utf8") as file:
                expected_df_comparison  = file.read()    
        except FileNotFoundError as ex:
            raise ApodeixiError(parent_trace, "Can't load comparison file because it doesn't exist",
                                    data = {'file':             EXPECTED_COMPARISON_FILE,
                                            'path':             OUTPUT_FOLDER + '/'  + EXPECTED_COMPARISON_FILE,
                                            'error':            str(ex)})
        self.assertEqual(df_comparison_nice,       expected_df_comparison)
        self.assertTrue(check)
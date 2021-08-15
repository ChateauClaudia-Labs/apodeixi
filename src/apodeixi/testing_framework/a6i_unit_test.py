import sys                  as _sys
import os                   as _os
import inspect

from apodeixi.testing_framework.a6i_skeleton_test   import ApodeixiSkeletonTest
from apodeixi.util.a6i_error                        import FunctionalTrace
from apodeixi.util.path_utils                       import PathUtils


class ApodeixiUnitTest(ApodeixiSkeletonTest):  
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

        # Output data is not in source control, so if we are in a clean repo the folder might not exist, so created it
        # if needed
        root_trace                  = FunctionalTrace(None, path_mask=self._path_mask)
        PathUtils().create_path_if_needed(root_trace, self.output_data)

        # For unit tests, don't enforce referential integrity since we will test data in mock stores that may
        # reference things that don't really exist
        self.a6i_config.enforce_referential_integrity = False

    def tearDown(self):
        super().tearDown()

    def _compare_to_expected_yaml(self, parent_trace, output_dict, test_output_name, save_output_dict=False):
        '''
        Utility method for derived classes that create YAML files and need to check they match an expected output
        previously saves as a YAML file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        super()._compare_to_expected_yaml(  parent_trace, 
                                            output_dict, 
                                            test_output_name    = test_output_name, 
                                            output_data_dir     = self.output_data, 
                                            expected_data_dir   = self.output_data, 
                                            save_output_dict    = save_output_dict)

    def _compare_to_expected_txt(self, parent_trace, output_txt, test_output_name, save_output_txt=False):
        '''
        Utility method for derived classes that create text files and need to check they match an expected output
        previously saves as a text file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        super()._compare_to_expected_txt(   parent_trace,
                                            output_txt, 
                                            test_output_name    = test_output_name, 
                                            output_data_dir     = self.output_data, 
                                            expected_data_dir   = self.output_data, 
                                            save_output_txt     = save_output_txt)

    def _compare_to_expected_df(self, parent_trace, output_df, test_output_name, columns_to_ignore=[], id_column=None):
        '''
        Utility method for derived classes that creates DataFrames (saved as CSV files) and checks they match an expected output
        previously saves as a CSV file as well. 

        It also saves the output as a CSV file, which can be copied to be the expected output when test case is created.

        @param columns_to_ignore List of column names (possibly empty), for columns that should be excluded from the comparison
        @param id_column A string representing the column that should be used to identify rows in comparison text produced. 
                         If set to None, then the row index is used.
        '''
        super()._compare_to_expected_df(    parent_trace, 
                                            output_df, 
                                            test_output_name    = test_output_name, 
                                            output_data_dir     = self.output_data, 
                                            expected_data_dir   = self.output_data, 
                                            columns_to_ignore   = columns_to_ignore, 
                                            id_column=id_column)

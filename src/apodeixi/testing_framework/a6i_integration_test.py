import sys                                              as _sys
import os                                               as _os
import inspect

from apodeixi.testing_framework.a6i_skeleton_test       import ApodeixiSkeletonTest

from apodeixi.util.a6i_error                            import FunctionalTrace , ApodeixiError

#from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase
from apodeixi.knowledge_base.file_kb_store              import File_KnowledgeBaseStore

from apodeixi.util.apodeixi_config                      import ApodeixiConfig

class ApodeixiIntegrationTest(ApodeixiSkeletonTest):  
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
        self.results_data           = _os.path.join(_os.path.dirname(me__file__), 'results_data') # Works ! :-) Thanks inspect!

        root_trace                  = FunctionalTrace(None).doing("Loading Apodeixi configuration",
                                                                        origination = {'signaled_from': __file__})
        self.config                 = ApodeixiConfig(root_trace)
        self.postings_folder        = self.config.get_KB_PostingsRootFolder(root_trace)
        self.manifests_folder       = self.config.get_KB_ManifestsRootFolder(root_trace)

        self.store                  = File_KnowledgeBaseStore(  postings_rootdir        = self.postings_folder,
                                                                derived_data_rootdir    = self.manifests_folder)


    def tearDown(self):
        super().tearDown()

    def _compare_to_expected_yaml(self, output_dict, test_case_name, save_output_dict=False):
        '''
        Utility method for derived classes that create YAML files and need to check they match an expected output
        previously saves as a YAML file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        super()._compare_to_expected_yaml(output_dict, test_case_name, data_dir = self.results_data, save_output_dict=False)

    def _compare_to_expected_txt(self, output_txt, test_case_name, save_output_txt=False):
        '''
        Utility method for derived classes that create text files and need to check they match an expected output
        previously saves as a text file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        super()._compare_to_expected_txt(output_txt, test_case_name, data_dir = self.results_data, save_output_txt=False)

    def _compare_to_expected_df(self, parent_trace, output_df, test_case_name, columns_to_ignore=[], id_column=None):
        '''
        Utility method for derived classes that creates DataFrames (saved as CSV files) and checks they match an expected output
        previously saves as a CSV file as well. 

        It also saves the output as a CSV file, which can be copied to be the expected output when test case is created.

        @param columns_to_ignore List of column names (possibly empty), for columns that should be excluded from the comparison
        @param id_column A string representing the column that should be used to identify rows in comparison text produced. 
                         If set to None, then the row index is used.
        '''
        super()._compare_to_expected_df(parent_trace, output_df, test_case_name, data_dir = self.results_data, 
                                            columns_to_ignore=[], id_column=None)

import sys                                              as _sys
import os                                               as _os
import shutil                                           as _shutil
import inspect
import re                                               as _re
import yaml                                             as _yaml

from apodeixi.testing_framework.a6i_skeleton_test       import ApodeixiSkeletonTest

from apodeixi.util.a6i_error                            import FunctionalTrace , ApodeixiError

from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase
from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore
from apodeixi.knowledge_base.shutil_kb_store            import Shutil_KBStore_Impl
from apodeixi.knowledge_base.git_kb_store               import GIT_KBStore_Impl
from apodeixi.knowledge_base.kb_environment             import KB_Environment_Config

from apodeixi.util.path_utils                           import PathUtils

class IntegrationTestStack():
    '''
    Abstract class

    Helper class to the ApodeixiIntegrationTest. It groups a choice for how to provision all
    externa dependencies needed by Apodeixi integration tests.
    '''
    def __init__(self, parent_trace):
        return

    def name(self, parent_trace):
        '''
        Abstract method. Returns a string used to identify this stack, used in the filing structure for
        the regression output of integration tests using this stack
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'name' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def store(self, parent_trace):
        '''
        Abstract method. Returns the KnowledgeBaseStore instance provisioned as part of this stack.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'store' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def kb(self, parent_trace):
        '''
        Abstract method. Returns the KnowledgeBase instance provisioned as part of this stack.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'kb' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def seedTestClientArea(self, parent_trace):
        '''
        Populates the client area that the integration test should use, determined based on the
        store's current environment as of the moment this method is called.
        '''
        # We are using an isolated collaboration folder specific to our environment, so need
        # to populate it with the data in the test_db/sharepoint area (the "immutable, deterministic seed")
        current_env             = self.store().current_environment(parent_trace)

        current_env.seedCollaborationArea(parent_trace, sourceURL = self._clientURL)

class ShutilStoreTestStack(IntegrationTestStack):
    '''
    Helper class to represent the stack used by an ApodeixiIntegrationTest, when the stack choice made is
    for a Shutil_KBStore_Impl
    '''
    def __init__(self, parent_trace, a6i_config):
        super().__init__(parent_trace)
        self.a6i_config                = a6i_config

        my_trace                        = parent_trace.doing("Initializing file-based stack",
                                                                        origination = {'signaled_from': __file__})
        self._kb_rootdir                = self.a6i_config.get_KB_RootFolder(my_trace)
        self._clientURL                 = self.a6i_config.get_ExternalCollaborationFolder(my_trace) 

        store_impl                      = Shutil_KBStore_Impl( parent_trace         = my_trace,
                                                                        kb_rootdir      = self._kb_rootdir, 
                                                                        clientURL       = self._clientURL)
        self._store                     = KnowledgeBaseStore(my_trace, store_impl)
        my_trace                        = parent_trace.doing("Starting KnowledgeBase")
        self._kb                        = KnowledgeBase(my_trace, self._store, a6i_config=self.a6i_config)

    MY_NAME                             = "shutil_store"
    def name(self, parent_trace):
        '''
        Returns a string used to identify this stack, used in the filing structure for
        the regression output of integration tests using this stack
        '''
        ME                  = ShutilStoreTestStack
        return ME.MY_NAME

    def store(self):
        '''
        Returns the KnowledgeBaseStore instance provisioned as part of this stack.
        '''
        return self._store

    def kb(self):
        '''
        Returns the KnowledgeBase instance provisioned as part of this stack.
        '''
        return self._kb

class GITStoreTestStack(IntegrationTestStack):
    '''
    Helper class to represent the stack used by an ApodeixiIntegrationTest, when the stack choice made is
    for a GIT_KBStore_Impl
    '''
    def __init__(self, parent_trace, a6i_config):
        super().__init__(parent_trace)
        self.a6i_config              = a6i_config

        my_trace                      = parent_trace.doing("Initializing GIT-based stack",
                                                            origination = {'signaled_from': __file__})
        self._kb_rootdir                = self.a6i_config.get_KB_RootFolder(my_trace)
        self._clientURL                 = self.a6i_config.get_ExternalCollaborationFolder(my_trace) 

        store_impl                      = GIT_KBStore_Impl(   parent_trace        = my_trace,
                                                                    kb_rootdir          = self._kb_rootdir,
                                                                    clientURL           = self._clientURL,
                                                                    remote              = None)

        self._store                     = KnowledgeBaseStore(my_trace, store_impl)
        my_trace                        = parent_trace.doing("Starting KnowledgeBase")
        self._kb                        = KnowledgeBase(my_trace, self._store, a6i_config=self.a6i_config)

    MY_NAME                             = "git_store"
    def name(self, parent_trace):
        '''
        Returns a string used to identify this stack, used in the filing structure for
        the regression output of integration tests using this stack
        '''
        ME                  = GITStoreTestStack
        return ME.MY_NAME

    def store(self):
        '''
        Returns the KnowledgeBaseStore instance provisioned as part of this stack.
        '''
        return self._store

    def kb(self):
        '''
        Returns the KnowledgeBase instance provisioned as part of this stack.
        '''
        return self._kb

class ApodeixiIntegrationTest(ApodeixiSkeletonTest):  
    '''
    Parent class for integration tests in Apodeixi. A test is considered an integration test (as opposed to a unit test)
    if it requires access to data or services through an external dependency, such as an independently deployable 
    KnowledgeBase store. In such cases, the test requires the provisioning of test-dedicated instances for such external 
    dependencies. This is in contrast to Apodeixi unit tests, which don't require any external dependency: any I/O done
    by unit tests is via folders pre-existing within the Apodeixi project itself.

    Integration tests have two key characteristics:

    * scenario: refers to the functional capability being tested by the integration test. For example, a scenario
            might test a user flow whereby a user requests a form, fills it out, submits it as a posting,
            and subsequently requests a form for updating the posting.
    * stack: refers to the choice of external dependencies that are provisioned for a test to run. For example,
            a KnowledgeBase store might be provisioned as a File_KnowledgeBasedStore or as a GIT_KnowledgeBasedStore.
            Another example is the provisioning of end-user collaboration areas such as SharePoint, from which
            postings would be submitted to the KnowledgeBase.

    Though an integration test uses external dependencies for all KnowledgeBase I/O, the integration test is also a
    regression test, so it outputs information about the processing of the scenario which is considered
    regression output. Test success is dependent on whether such output matches previously recorded correct output. 
    All this regression output is not considered a functional by-product of Apodeixi but of the test program itself,
    so it is not stored in the external dependencies. Instead, as for unit tests, it is stored in data folders within
    the Apodeixi project itself. In effect, the Apodeixi project defines its correct behavior through the expected
    regression output files within the Apodeixi project itself.

    Apodeixi external dependencies for integration tests are "seeded" from a GIT project containing a "test_db".
    This is a separate GIT project from the Apodeixi GIT project itself, and may contain test data provided
    by Apodeixi users, so it is not publicly made available. That said, the normal bootup sequence for an Apodeixi
    integration test is to take some of that "seed data" and create a test-case-specific environment in which to
    provision the necessary dependencies and populate them with copies of the appropriate "seed data". This 
    test-case level isolation ensures determinism of output for integration tests (i.e., no integration test will
    interfere with the data used by another, since no integration test modifies the "test_db" from where the "seed data"
    comes). This makes it possible for an integration test to delete or modify data at will, safely.

    Unlike unit tests (which typically output 1-2 regression test files), integration tests are expected to output many
    regression files since the scenarios are more complicated, involving multiple steps in a stateful flow, 
    snapshots and logs at different stages and from different API calls, etc.
    For a given integration test, its multiple regression test files (expected and actual) will be stored in a folder
    structure such as this (where the <scenario> and <stack> jointly identify the specific integration test done)

    <module folder>/tests_integration/results_data/<scenario>/<stack>/

    It is considered good practice to organize the test code so that the same scenario can be tested in multiple
    stacks.
    '''
    def setUp(self):
        super().setUp()

        # We can't rely on Python's built-in '__file__' property to find the location of the concrete class
        # that is running, since we are in the parent class and we will get the parent class's filename, not the concrete class's.
        # So instead we rely on the inspect package
        me__file__                  = inspect.getfile(self.__class__)
        # self.input_data             = _os.path.join(_os.path.dirname(__file__), 'input_data') # Doesn't work - use inpectt instead
        self.input_data             = _os.path.join(_os.path.dirname(me__file__), 'input_data') # Works ! :-) Thanks inspect!
        # self.input_data             = _os.path.join(_os.path.dirname(__file__), 'input_data') # Doesn't work - use inpectt instead
        self.results_data           = _os.path.join(_os.path.dirname(me__file__), 'results_data') # Works ! :-) Thanks inspect!

        # Test canses can choose to have self.results_data modified, if they configure themselves in test_config.yam.
        # This is recommended for tests
        # with very long folder structures, since Windows and GIT on Windows impose limits and may cause problems
        # saving files or doing GIT commits unless results are put in a "high up" folder
        #
        # So here we remember the test config as a dict attribute of self, so that it is available later for
        # integration tests that chose to take advantage of it to save results to a shorter folder structure.
        root_trace                  = FunctionalTrace(None).doing("Checking where results should be saved to",
                                                                    origination = {'signaled_from': __file__})
        self.test_db_dir            = _os.path.dirname(self.a6i_config.get_KB_RootFolder(root_trace))           
        with open(self.test_db_dir + '/test_config.yaml', 'r', encoding="utf8") as file:
            self.test_config_dict   = _yaml.load(file, Loader=_yaml.FullLoader)
    


        root_trace                  = FunctionalTrace(None).doing("Provisioning stack for integration test",
                                                                    origination = {'signaled_from': __file__})

        # These will be set by each individual test case (i.e., each method in a derived class with a name like "test_*")
        self._current_test_name     = None
        
        # For ease of maintenance of tests, each output for a test will be named using standard numbering 
        # enforced by the "next_*" functions
        self._output_nb             = 0

        # As a general pattern, we only enforce referential integrity tests in "flow" tests, which is the
        # more "realistic" flavor of integration tests
        self.a6i_config.enforce_referential_integrity = False

    def tearDown(self):
        super().tearDown()


    def stack(self):
        return self._stack

    def selectStack(self, parent_trace):
        '''
        Abstract method.

        Called as part of setting up each integration test case. It chooses and provisions the stack that should
        be used by this test case.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'selectStack' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def currentTestName(self):
        return self._current_test_name

    def setCurrentTestName(self, test_name):
        '''
        Must be called by all concrete integration tests at the start. It will impact the filename in which
        regression test is persisted.
        '''
        self._current_test_name = test_name

    def scenario(self):
        return self._scenario

    def setScenario(self, scenario):
        '''
        Must be called by all concrete integration tests at the start. It will impact the folder in which
        regression test is persisted.
        '''
        self._scenario          = scenario

    def config(self):
        return self.a6i_config

    def current_environment_name(self, parent_trace):
        '''
        Returns the name of the current environment in the stack's store.
        '''
        self.stack().store().current_environment(parent_trace).name(parent_trace)

    def changeResultDataLocation(self):
        '''
        Changes self.result_data and self.input_data if that was configured in self.test_config_dict.
        This should only be called after self.setScenario(-) has been set, since the look up in the configuration
        is based on scenario.
        '''
        result_directories          = self.test_config_dict['integration-tests-results']
        if self.scenario() in result_directories.keys():
            test_id                 = result_directories[self.scenario()]
            new_results_location    = self.test_db_dir + "/results_data/" + str(test_id)
            self.results_data       = new_results_location
            new_input_location    = self.test_db_dir + "/input_data/" + str(test_id)
            self.input_data       = new_input_location

    def provisionIsolatedEnvironment(self, parent_trace, environment_name = None, 
                                            read_misses_policy  = KB_Environment_Config.FAIL_ON_READ_MISSES,):
        '''
        Creates a new environment as a sub-environment of the current environment, and activates it.
        The new environment is configured to have a dedicated, isolated collaboration area which
        this method populates by downloading the content from the clientURL area configured in
        the Apodeixi configuration used by the testing framework.

        @param environment_name A string. This paramenter is used as the name of the newly created environment,
        unless it is set to None (the default), in which case a standard name is given using
        the structure

            <scenario>.<test name>_ENV

        @param read_misses_policy A string that is recognized by the KB_Environment_Config as a valid
                policy. The default is a high level of isolation, i.e., if data is missing
                in the isolated environment then the store will not attempt to retrieve the
                data from the parent environment.  

                GOTCHA: Normally this higher level of isolation is needed for tests that create
                manifests that exist in the base environment, since version consistency checks
                prevent creation of a manifest (i.e., with version=1) if it finds such a manifest
                existing. So if the base environment has such a manifest, then want to not
                failover the the parent environment during read misses.

                On the other hand, other tests make postings directly from the knowledge base
                (not from the collaboration area), using postings saved in the base environment.
                For them a different policy should be used (such as KB_Environment_Config.FAILOVER_ALL_READS_TO_PARENT).

        '''
        if environment_name == None:
            environment_name        = self.scenario() + "." + self.currentTestName() + "_ENV"

        my_trace                    = parent_trace.doing("Removing previously created environment, if any",
                                                    data = {'environment name': environment_name})
        store                       = self.stack().store()
        stat                        = store.removeEnvironment(parent_trace = my_trace, name = environment_name)
        
        my_trace                    = parent_trace.doing("Creating an isolated environment for integration test")
        env_config                  = KB_Environment_Config(
                                            parent_trace, 
                                            #read_misses_policy  = KB_Environment_Config.FAILOVER_ALL_READS_TO_PARENT,
                                            read_misses_policy  = read_misses_policy,
                                            use_timestamps      = False,
                                            path_mask           = self._path_mask)
        store.current_environment(my_trace).addSubEnvironment(my_trace, environment_name, env_config,
                                                                    isolate_collab_area = True)
        store.activate(parent_trace = my_trace, environment_name = environment_name)

        my_trace                    = parent_trace.doing("Seeding client area for integration test")
        self.stack().seedTestClientArea(parent_trace)

    def check_environment_contents(self, parent_trace, snapshot_name = None):     
        '''
        Helper method to validate current environment's folder hierarchy is as expected at this point in time
        in the execution of a test case.

        @param snapshot_name A string, corresponding to the output name under which the regression output should
                            be generated. If set to None, then it will be computed by calling self.next_snapshot()
        '''
        current_env         = self.stack().store().current_environment(parent_trace)

        if snapshot_name == None:
            snapshot_name   = self.next_snapshot()

        description_dict    = current_env.describe(parent_trace, include_timestamps = False)

        '''
        self._compare_to_expected_yaml( parent_trace        = parent_trace,
                                        output_dict         = description_dict,
                                        test_output_name    = snapshot_name, 
                                        save_output_dict    = True)
        '''
        def tolerance_lambda(key, output_val, expected_val):
            '''
            When an Excel filename is displayed as a key in a folder hierarchy, and it has a 
            description given by a string that includes things like "Size (in bytes):  7677",
            we want to tolerate a small deviation from the number of bytes in the size.
            For example, "Size (in bytes):  7678" would not be considered a test failure
            '''
            TOLERANCE               = 4 # We will tolerate up to these many bites of difference
            if type(key) == str and key.endswith(".xlsx"): # This is an Excel file, apply tolerance
                output_bytes        = _extract_bytes(output_val)
                expected_bytes      = _extract_bytes(expected_val)
                if output_bytes == None or expected_bytes == None: # Default to default comparison
                    return output_val == expected_val
                else:
                    return abs(output_bytes - expected_bytes) <= TOLERANCE

            # If we get this far we were unable to detect the conditions for which tolerance applies, so
            # do a straight compare
            return output_val == expected_val

        def _extract_bytes(file_info_message):
            '''
            @param file_info_message A string, expected to contain subtrings like "Size (in bytes):  7677"

            @returns The number of bytes in the message as an int (7677 in the example), or None if the
                    file_info_message does not contain a substring as indicated
            '''
            if type(file_info_message) != str:
                return None
            REGEX               = "Size \(in bytes\):  ([0-9]+)"
            m                   = _re.search(REGEX, file_info_message)
            if m == None or len(m.groups()) != 1:
                return None
            nb_bytes            = int(m.group(1))
            return nb_bytes

        self._compare_yaml_within_tolerance(    parent_trace        = parent_trace,
                                                output_dict         = description_dict,
                                                test_output_name    = snapshot_name, 
                                                save_output_dict    = True,
                                                tolerance_lambda    = tolerance_lambda)
                              

    def trace_environment(self, parent_trace, activity):
        '''
        Helper method to reduce clutter in derived classes. 
        
        It returns a FunctionalTrace for the `activity` that is a child of `parent_trace`.
        It appends some data elements, such as the KnowledgeBaseStore's current environment we are under,
        so having this done in a common function is how clutter is reduced and consistency maximized.

        @param parent_trace     A FunctionalTrace from which we seek a child trace
        @param activity  A string corresponding to the description of the functional behavior that the resulting
                        trace is about.
        '''
        current_env_name    = self.stack().store().current_environment(parent_trace).name(parent_trace)
        my_trace            = parent_trace.doing(activity,
                                data        = { "environment":     current_env_name },
                                origination = { 'concrete class':   str(self.__class__.__name__), 
                                                'signaled_from':    __file__})
        return my_trace

    def snapshot_generated_form(self, parent_trace, form_request_response):     
        '''
        Helper method to remember a generated form at a given point in time, in case it is subsequently
        modified and submitted as an update posting.

        Basically, this will copy the generated form to self._regression_output_dir(parent_trace)

        @param form_request_response A FormRequestResponse object with the information needed to locate
                        the generated form in question.
        '''
        form_path       = form_request_response.clientURL(parent_trace) + "/" \
                            + form_request_response.getRelativePath(parent_trace)
        filename        = _os.path.split(form_path)[1]
        snapshot_name   = self.next_form(filename)
        dst_dir         = self._regression_output_dir(parent_trace)
        _shutil.copy2(src = form_path, dst = dst_dir + "/" + snapshot_name)

    def modify_form(self, parent_trace, form_request_response):     
        '''
        Helper method to simulate an end-user's edits of a generated form, where the end-user's intention would
        typically be to submit an update posting using the form.

        This "simulation" is done by copying a manually created "edited form" from the self.inputs area

        remember a generated form at a given point in time, in case it is subsequently
        modified and submitted as an update posting.

        Basically, this will copy the generated form to self.results_data/self.scenario()

        @param form_request_response A FormRequestResponse object with the information needed to locate
                        the generated form in question.
        '''
        form_path   = form_request_response.clientURL(parent_trace) + "/" + form_request_response.getRelativePath(parent_trace)
        form_filename = _os.path.split(form_path)[1]

        simulation_filename = self.input_data + "/" + self.scenario() + "/" + self.currentTestName() + "." + form_filename
        _shutil.copy2(src = simulation_filename, dst = form_path)

    def next_form(self, description=None):
        '''
        Returns a string that can be used as the output name for test output that is a snapshot of
        a form, i,e,, an Excel spreadsheet generated by calling the generateForm API of the Knowledge
        Base. This is useful to remember the form before it is modified (as it might be if the 
        test case subsequently wants to do an update by modifying the form and submitting it as posting)
        '''
        return self.next_output_name(output_type="form", description=description)

    def next_snapshot(self, description=None):
        '''
        Returns a string that can be used as the output name for test output that is a snapshot of
        a KnowledgeBaseStore's environment
        '''
        return self.next_output_name(output_type="snapshot", description=description)

    def next_manifest(self, description=None):
        '''
        Returns a string that can be used as the output name for test output that is a manifest YAML file
        '''
        return self.next_output_name(output_type="manifest", description=description)

    def next_log(self, description=None):
        '''
        Returns a string that can be used as the output name for test output that is a log
        produced KnowledgeBase processing
        '''
        return self.next_output_name(output_type="log", description=description)

    def next_xl_layout(self, worksheet_name, description=None):
        '''
        Returns a string that can be used as the output name for test output describing an Excel layout
        for the worksheet called `worksheet_name`
        '''
        if description == None:
            new_description     = worksheet_name
        else:
            new_description     = description + "." + worksheet_name
        return self.next_output_name(output_type="xl_layout", description=new_description)

    def next_xl_format(self, worksheet_name, description=None):
        '''
        Returns a string that can be used as the output name for test output describing an Excel format
        for the worksheet called `worksheet_name`
        '''
        if description == None:
            new_description     = worksheet_name
        else:
            new_description     = description + "." + worksheet_name
        return self.next_output_name(output_type="xl_format", description=new_description)

    def next_output_name(self, output_type, description=None):
        '''
        Returns a string that can be used as the output name for test output of the given `output_type`.
        For readability of test output filenames, extra space padding is added in the returned filename

        @param output_type A string, to identify the kind of output  this is
        @paran description An optional string, which if given gets appended to the output name returned.
                            Ignored if set to None (the default)
        '''
        # Pad the output_type to at least 20 characters
        if len(output_type) < 20:
            padding                 = " " * (20 - len(output_type))
            output_type             += padding
        if description == None:
            description             = ""

        # Pad description to at least 30 characters
        if len(description) < 30:
            padding                 = " " * (30 - len(description))
            description             += padding  

        output_name             = self._current_test_name + ".T" \
                                    + str(self._output_nb) + "_" + output_type + description
        self._output_nb         += 1
        return output_name

        

    def _regression_output_dir(self, parent_trace):
        if self._scenario == None:
            raise ApodeixiError(None, "Test case not properly intialized - scenario is null. Must be set")
        dir         = self.results_data + "/" + self._scenario + "/" + self.stack().name(parent_trace)
        #dir         = self.results_data 
        return dir

    def _regression_expected_dir(self, parent_trace):
        if self._scenario == None:
            raise ApodeixiError(None, "Test case not properly intialized - scenario is null. Must be set")
        dir         = self.results_data + "/" + self._scenario
        #dir         = self.results_data 
        return dir

    def _compare_to_expected_yaml(self, parent_trace, output_dict, test_output_name, save_output_dict=False):
        '''
        Utility method for derived classes that create YAML files and need to check they match an expected output
        previously saves as a YAML file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        super()._compare_to_expected_yaml(  parent_trace,
                                            output_dict, 
                                            test_output_name    = test_output_name, 
                                            output_data_dir     = self._regression_output_dir(parent_trace), 
                                            expected_data_dir   = self._regression_expected_dir(parent_trace), 
                                            save_output_dict    = save_output_dict)

    def _compare_yaml_within_tolerance(self, parent_trace, output_dict, test_output_name, save_output_dict, tolerance_lambda):
        '''
        Utility method for derived classes that create YAML files and need to check they match an expected output
        previously saves as a YAML file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        super()._compare_yaml_within_tolerance(  parent_trace,
                                            output_dict, 
                                            test_output_name    = test_output_name, 
                                            output_data_dir     = self._regression_output_dir(parent_trace), 
                                            expected_data_dir   = self._regression_expected_dir(parent_trace), 
                                            save_output_dict    = save_output_dict,
                                            tolerance_lambda    = tolerance_lambda)


    def _compare_to_expected_txt(self, parent_trace, output_txt, test_output_name, save_output_txt=False):
        '''
        Utility method for derived classes that create text files and need to check they match an expected output
        previously saves as a text file as well. 

        It also saves the output as a yaml file, which can be copied to be the expected output when test case is created.
        '''
        super()._compare_to_expected_txt(   parent_trace,
                                            output_txt, 
                                            test_output_name    = test_output_name,
                                            output_data_dir     = self._regression_output_dir(parent_trace), 
                                            expected_data_dir   = self._regression_expected_dir(parent_trace), 
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
                                            output_data_dir     = self._regression_output_dir(parent_trace), 
                                            expected_data_dir   = self._regression_expected_dir(parent_trace), 
                                            columns_to_ignore   = columns_to_ignore, 
                                            id_column           = id_column)


import os                                               as _os
import shutil                                           as _shutil

import re                                               as _re
import yaml                                             as _yaml

from apodeixi.testing_framework.a6i_skeleton_test       import ApodeixiSkeletonTest

from apodeixi.util.a6i_error                            import FunctionalTrace , ApodeixiError
from apodeixi.util.dictionary_utils                     import DictionaryUtils
from apodeixi.util.path_utils                           import PathUtils

from apodeixi.knowledge_base.knowledge_base             import KnowledgeBase
from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore
from apodeixi.knowledge_base.shutil_kb_store            import Shutil_KBStore_Impl
from apodeixi.knowledge_base.git_kb_store               import GIT_KBStore_Impl
from apodeixi.knowledge_base.kb_environment             import KB_Environment_Config

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

        self.input_data             = None # Will be set later by method selectTestDataLocation        
        self.results_data           = None # Will be set later by method selectTestDataLocation

        # Integration test cases must call self.selectTestDataLocation(-) to set self.results_data
        # and self.input_data. 
        # This is required for 2 reasons:
        #   1. Ease of management - all integration tests are registered in test_config.yaml and
        #       their output is externalized from the Apodeixi code base
        #   2. Reduce the size of folder structure by placing output in a less nested directory structure
        #       (i.e., not under the code of the tests themselves). This is needed in Windows to avoid
        #       issues with long paths that impede file persistence and/or impede committing to GIT.
        #       As an added benefit, I noticed it improves test performance by 50% to use shorter paths.
        #
        # To support all this we have these two attributes that get used later in self.selectTestDataLocation(-):
        #   - self.test_db_dir
        #   - self.test_config_dict
        #.
        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Checking where results should be saved to",
                                                                    origination = {'signaled_from': __file__})
        self.test_db_dir            = _os.path.dirname(self.a6i_config.get_KB_RootFolder(root_trace))           
        with open(self.test_db_dir + '/test_config.yaml', 'r', encoding="utf8") as file:
            self.test_config_dict   = _yaml.load(file, Loader=_yaml.FullLoader)

        # Remember location of test_db in ApodeixiConfig.
        # This flag will be set by test cases to assist with masking non-deterministic information about the
        # location of the test database. It is used in the masking function that hides parts of paths from regression
        # output, to avoid non-deterministic test output. When not using the test regression suite, this flag plays no role
        # in Apodeixi.
        self.a6i_config.test_db_dir = self.test_db_dir

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Provisioning stack for integration test",
                                                                    origination = {'signaled_from': __file__})

        # These will be set by each individual test case (i.e., each method in a derived class with a name like "test_*")
        self._current_test_name     = None
        
        # For ease of maintenance of tests, each output for a test will be named using standard numbering 
        # enforced by the "next_*" functions
        self._output_nb             = 0

        # As a general pattern, we only enforce referential integrity tests in "flow" tests, which is the
        # more "realistic" flavor of integration tests
        self.a6i_config.enforce_referential_integrity   = False

        # Log output files like "POST_EVENT_LOG.txt" are normally masked in test output, so we want
        # them to match expected output to the byte when showing environment contents.
        # *HOWEVER*, in the case of CLI tests we don't mask their contents to make them "more realistic" and because 
        # CLI test output doesn't show the contents of such log files. 
        # So to ensure CLI tests don't frivolously fail when the test_db is relocated, this setting
        # (normally set to False) can be enabled by derived classes (such as CLI tests) can set to True
        # so the test case accepts accept whatever byte size is displayed for log files when displaying environment contents.
        self.ignore_log_files_byte_size                 = False

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

    def getResultsDataFolder(self, parent_trace):
        if self.results_data == None:
            raise ApodeixiError(parent_trace, "Test case not initialized properly - results data folder not set")
        else:
            return self.results_data

    def getInputDataFolder(self, parent_trace):
        if self.input_data == None:
            raise ApodeixiError(parent_trace, "Test case not initialized properly - input data folder not set")
        else:
            return self.input_data

    def selectTestDataLocation(self):
        '''
        Changes self.result_data and self.input_data if that was configured in self.test_config_dict.
        This should only be called after self.setScenario(-) has been set, since the look up in the configuration
        is based on scenario.
        '''
        result_directories          = self.test_config_dict['integration-tests-results']
        if result_directories != None and self.scenario() in result_directories.keys():
            test_id                 = result_directories[self.scenario()]
            new_results_location    = self.test_db_dir + "/results_data/" + str(test_id)
            self.results_data       = new_results_location
            new_input_location    = self.test_db_dir + "/input_data/" + str(test_id)
            self.input_data       = new_input_location

    def provisionIsolatedEnvironment(self, parent_trace, environment_name = None, 
                                            read_misses_policy  = KB_Environment_Config.FAIL_ON_READ_MISSES,
                                            seed_client_area    = False):
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

        @param seed_client_area A boolean. If True, this method will initialize the isolated environment's
                collaboration area by copying the contents of the base environment's collaboration area.

        '''
        if environment_name == None:
            result_directories          = self.test_config_dict['integration-tests-results']
            if self.scenario() in result_directories.keys():
                test_id                 = result_directories[self.scenario()]
                environment_name        = str(test_id) + "_ENV"
            else:
                environment_name        = self.scenario() + "_ENV"

        my_trace                    = parent_trace.doing("Removing previously created environment, if any",
                                                    data = {'environment name': environment_name})
        store                       = self.stack().store()
        stat                        = store.removeEnvironment(parent_trace = my_trace, name = environment_name)
        
        my_trace                    = parent_trace.doing("Creating an isolated environment for integration test")
        env_config                  = KB_Environment_Config(
                                            parent_trace        = my_trace, 
                                            read_misses_policy  = read_misses_policy,
                                            use_timestamps      = False,
                                            path_mask           = self._path_mask)
        store.current_environment(my_trace).addSubEnvironment(my_trace, environment_name, env_config,
                                                                    isolate_collab_area = True)
        store.activate(parent_trace = my_trace, environment_name = environment_name)

        if seed_client_area == True:
            my_trace                    = parent_trace.doing("Seeding client area for integration test")
            self.stack().seedTestClientArea(parent_trace)

    def seedCurrentEnvironment(self, parent_trace, manifest_relative_folder, postings_relative_folder):
        '''
        Populates the current environment's manifests or excel postings' area by copying the folder tree structures.

        @param manifest_relative_folder A string. Should be a relative path that adheres to a valid path structure in the 
            KnowledgeBase store under the manifests folder. 
            It must also be the case that the input folder for this test has a subfolder called "manifests" which
            contains the `manifest_relative_folder` as a sub-subfolder.
            Behavior is to copy everything under the latter to the KnowledgeBase store's manifests area.
            If set to None, nothing is copied.

            Example: "my-corp.production/modernization.dec-2020.fusionopus.default"

        @param postings_relative_folder A string. Should be a relative path that adheres to a valid path structure in the 
            KnowledgeBase store under the excel-postings folder. 
            It must also be the case that the input folder for this test has a subfolder called "excel-postings" which
            contains the `postings_relative_folder` as a sub-subfolder.
            Behavior is to copy everything under the latter to the KnowledgeBase store's manifests area.
            If set to None, nothing is copied.

            Example: "journeys/Dec 2020/FusionOpus/Default"
        '''
        INPUT_FOLDER                    = self.getInputDataFolder(parent_trace) + "/" + self.scenario()
        my_trace                        = self.trace_environment(parent_trace, "Seeding manifests under " 
                                                                                    + str(manifest_relative_folder))
        if manifest_relative_folder != None:
            src_folder                  = INPUT_FOLDER + "/manifests/" + manifest_relative_folder
            PathUtils().checkPathExists(my_trace, src_folder)
            manifestsURL                = self.stack().store().current_environment(my_trace).manifestsURL(my_trace)
            dst_folder                  = manifestsURL + "/" + manifest_relative_folder
            
            try:
                PathUtils().remove_folder_if_exists(my_trace, dst_folder)
                _shutil.copytree(   src                 = src_folder, 
                                    dst                 = dst_folder,
                                    ignore              = None)
            except Exception as ex:
                raise ApodeixiError(my_trace, "Found an error in seeding the manifests for test " + self.scenario(),
                                                data = {"URL to download from":     src_folder, 
                                                        "URL to copy to":           manifestsURL,
                                                        "error":                    str(ex)})

        my_trace                        = self.trace_environment(parent_trace, "Seeding Excel postings under " 
                                                                                    + str(postings_relative_folder))
        if postings_relative_folder != None:
            src_folder                  = INPUT_FOLDER + "/excel-postings/" + postings_relative_folder
            PathUtils().checkPathExists(my_trace, src_folder)
            postingsURL                 = self.stack().store().current_environment(my_trace).postingsURL(my_trace)
            dst_folder                  = postingsURL + "/" + postings_relative_folder
            
            try:
                PathUtils().remove_folder_if_exists(my_trace, dst_folder)
                _shutil.copytree(   src                 = src_folder, 
                                    dst                 = dst_folder,
                                    ignore              = None)
            except Exception as ex:
                raise ApodeixiError(my_trace, "Found an error in seeding the Excel postings for test " + self.scenario(),
                                                data = {"URL to download from":     src_folder, 
                                                        "URL to copy to":           postingsURL,
                                                        "error":                    str(ex)})


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

        raw_description_dict    = current_env.describe(parent_trace, include_timestamps = False)

        # Some keys are timestamped filenames or folders, like "210915 Some_report.xlsx" (for Sep 15, 2021)
        # or even "210917.072312 Some_report.xlsx" (if report was produced at 7:32:12 am). To mask such 
        # timestamps, we replace the occurrence of any 6 digits in a key by the string "<MASKED>"
        def mask_timestamps(a_dict):
            REGEX                   = "[0-9]{6}"
            new_dict                = {}
            for key in a_dict:
                raw_child           = a_dict[key]
                if type(raw_child) == dict:
                    new_child       = mask_timestamps(raw_child)
                else:
                    new_child       = raw_child
                new_key             = _re.sub(REGEX, "<MASKED>", key)
                new_dict[new_key]   = new_child
            return new_dict

        description_dict            = mask_timestamps(raw_description_dict)
        
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = parent_trace, 
                                                                root_dict       = self.test_config_dict, 
                                                                root_dict_name  = "test_config.yaml",
                                                                path_list       = ["regression-parameters", "xl-tolerance"],
                                                                valid_types     = [int])  
        if check == False:
            raise ApodeixiError(parent_trace, "test_config.yaml misses a correct configuration for 'xl-tolerance' "
                                                + " under the grouping 'regression-parameters'",
                                                data        = { "explanation":    explanation},
                                                origination = { 'concrete class':   str(self.__class__.__name__), 
                                                                'signaled_from':    __file__})      
        TOLERANCE               = self.test_config_dict["regression-parameters"]["xl-tolerance"]

        def tolerance_lambda(key, output_val, expected_val):
            '''
            We need to mask or tolerate differences in regression test output because of
            expected nondeterminism. Multiple cases:

            1. When an Excel filename is displayed as a key in a folder hierarchy, and it has a 
            description given by a string that includes things like "Size (in bytes):  7677",
            we want to tolerate a small deviation from the number of bytes in the size.
            For example, "Size (in bytes):  7678" would not be considered a test failure

            2. When an environment's "METADATA.yaml" file is displayed as a key in a folder hierarchy,
            its contents can't be masked because the test harness itself needs the full paths inside
            the "METADATA.yaml" when, for example, re-creating a pre-existing environment from disk
            (as it happens in CLI testing - each CLI command is a initializes a separate KnowledgeBaseStore object
            in memory, so to share environments across multiple CLI commands each successive command's
            KnowledgeBaseStore needs to load from disk the information about environments created from prior
            CLI commands, and that is what "METADATA.yaml" is for.
            Bottom line: no masking can go inside "METADATA.yaml", so its size in bytes will change if one
            reloates the test DB, since its location appears inside "METADATA.yaml". So we "accept" whatever
            byte size it has.

            3. Log output files like "POST_EVENT_LOG.txt" are normally masked in test output, so we want
            them to match expected output to the byte. *HOWEVER*, in the case of CLI tests we don't mask their
            contents to make them "more realistic" and because CLI test output doesn't show the contents of such
            log files. So to ensure CLI tests don't frivolously fail when the test_db is relocated, there is
            a setting (self.ignore_log_files_byte_size), normally set to False but which derived classes
            (such as CLI tests) can set to True. So if this flag is on, we also accept whatever byte size
            exists in log files.

            '''
            if type(key) == str and key.endswith(".xlsx"): # This is an Excel file, apply tolerance
                output_bytes        = _extract_bytes(output_val)
                expected_bytes      = _extract_bytes(expected_val)
                if output_bytes == None or expected_bytes == None: # Default to default comparison
                    return output_val == expected_val
                else:
                    return abs(output_bytes - expected_bytes) <= TOLERANCE
            elif key == "METADATA.yaml":
                return True # Just accept whatever number of bytes are shown, as per method documentation above
            elif self.ignore_log_files_byte_size == True and \
                        (key == "POST_EVENT_LOG.txt" or key == "FORM_REQUEST_EVENT_LOG.txt"):
                return True # Just accept whatever number of bytes are shown, as per method documentation above.



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
        PathUtils().copy_file(parent_trace, form_path, dst_dir + "/" + snapshot_name)
        

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

        simulation_filename = self.getInputDataFolder(parent_trace) + "/" + self.scenario() + "/" + self.currentTestName() + "." + form_filename
        PathUtils().copy_file(parent_trace, simulation_filename, form_path)

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

    def next_kb_introspection(self, description=None):
        '''
        Returns a string that can be used as the output name for test output that is a log
        produced KnowledgeBase processing
        '''
        return self.next_output_name(output_type="kb_introspection", description=description)
 
    def next_posting_label(self, description=None):
        '''
        Returns a string that can be used as the output name for test output that is a posting label's content
        produced KnowledgeBase processing
        '''
        return self.next_output_name(output_type="posting_label", description=description)

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
        dir         = self.getResultsDataFolder(parent_trace) + "/" + self._scenario + "/" + self.stack().name(parent_trace)
        return dir

    def _regression_expected_dir(self, parent_trace):
        if self._scenario == None:
            raise ApodeixiError(None, "Test case not properly intialized - scenario is null. Must be set")
        dir         = self.getResultsDataFolder(parent_trace) + "/" + self._scenario
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


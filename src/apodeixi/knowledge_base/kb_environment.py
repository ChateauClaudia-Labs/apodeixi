import os                                               as _os
import shutil                                           as _shutil
import yaml                                             as _yaml

from apodeixi.util.a6i_error                            import ApodeixiError
from apodeixi.util.path_utils                           import PathUtils, FolderHierarchy

class KB_Environment_Config():
    '''
    Configuration class used by the KB_Environment to hold some settings affecting environment
    functionality

    @param read_misses_policy A string determining how to handle I/O situations when a piece of data
            does not exist in the current environment. Possibilities are:
            * 'FAILOVER_ALL_READS_TO_PARENT': Causes the store to search for the missing information in the parent
                environment, and if found, it will be copied to the current environment
            * 'FAIL_ON_READ_MISSES': Causes the store to fail when the datum is not found. Exact failure 
                semantics depends on each I/O service. For example, some may raise an ApodeixiError while
                others might return  None. Refer to the documentation of each I/O read method.
    @param use_timestamps A boolean. If True (the default), then all "observability" records, such as
                logs and archival folder names, will include a timestamp. If False, such timestamp
                information is omitted. A typical use case for setting this to False is regression testing,
                to ensure that the output data is always the same.\
    @param path_mask A function that takes a string argument and returns a string. Normally it is None, but
                it is used in situations (such as in regression testing) when observability should not
                report the paths "as is", but with a mask. For example, this can be used in regression
                tests to hide the user-dependent portion of paths, so that logs would otherwise display a path
                like:

                'C:/Users/aleja/Documents/Code/chateauclaudia-labs/apodeixi/test-knowledge-base/envs/big_rocks_posting_ENV/excel-postings'

                instead display a "masked" path where the user-specific prefix is masked, so that only the
                logical portion of the path (logical as in: it is the structure mandated by the KnowledgeStore)
                is displayed. In the above example, that might become:

                '<KNOWLEDGE_BASE>/envs/big_rocks_posting_ENV/excel-postings'

    '''
    def __init__(self, parent_trace, read_misses_policy, use_timestamps=True, path_mask=None):
        ME                                  = KB_Environment_Config
        if not read_misses_policy in ME.READ_MISSES_POLICIES:
            raise ApodeixiError(parent_trace, "The read misses policy that was provided is not supported",
                                data = {"read_misses_policy": str(read_misses_policy),
                                        "supported policies": str(ME.READ_MISSES_POLICIES)})

        self.read_misses_policy             = read_misses_policy
        self.use_timestamps                 = use_timestamps
        self.path_mask                      = path_mask

    FAILOVER_ALL_READS_TO_PARENT            = 'FAILOVER_ALL_READS_TO_PARENT'
    FAILOVER_MANIFEST_READS_TO_PARENT       = 'FAILOVER_MANIFEST_READS_TO_PARENT'
    FAILOVER_POSTING_READS_TO_PARENT        = 'FAILOVER_POSTING_READS_TO_PARENT'
    FAIL_ON_READ_MISSES                     = 'FAIL_ON_READ_MISSES'
    READ_MISSES_POLICIES = [FAILOVER_ALL_READS_TO_PARENT, 
                            FAILOVER_MANIFEST_READS_TO_PARENT,
                            FAILOVER_POSTING_READS_TO_PARENT,
                            FAIL_ON_READ_MISSES]

class KB_Environment():
    '''
    Represents a logical "environment", which can be thought of as a slice of a KnowledgeBaseStore that has 
    the following isolation functionality:

    * At any point in time, the store's state points to a particular instance of a KB_Environment,
      referred to as the "current environment"
    * A store can have multiple environments, which are organized in a tree structure in that each environment has 
      a unique parent environment. 
    * An environment is the root of the tree if its parent environment is set to None
    * Each environment instance is configured with policies for handling I/O for data not in an environment
    * A typical policy is: when reading an object, if it is not in the current environment then attempt to load
      it from the environment's parent, before failing. 
    * An alternative policy is: fail on reads if the object in question is not in the current environment.
    * All writes are done only in the current environment.
    * All deletes are done only in the current environment.
    * Among the use cases for which environments can be used, one is to support transactions, whereby an
      environment serves as a transaction cache for its parent environment. For that reason environments
      support "commit" functionality, in which an environment's data is copied into its parent and overwrites
      it. It is up to concrete environment classes to determine if that is an atomic operation or not. The "commit"
      applies also to deletes - an object that a child environment marked as "deleted" will be deleted in the
      parent environment upon commit.
    * Another illustrative use case of environments is to support testing, whereby a sequence of steps involving
      modifying postings or manifests is done in successive child environments. The linked list of such environments
      can be thought of as snapshots in time of the whole processing, providing enough "white box" observability to
      a testing program that aims to verify if each the correct behaviour happened at each step.

    Environments naturally are organized in a tree structure. Each node is an instance of the KB_Environment,
    and are part of "doubly linked list": each node points to its parent, and also each node has a dictionary
    of its children, whose keys are the names (of type str) of the child environments.

    There can be multiple implementation of environment services. This class supports swapping different
    implementations by delegating all services to an implementation class

    @param impl An object implementing the services of a KB_Environment, to which this KB_Environment
                class can delegate to.
    '''
    def __init__(self, parent_trace, impl):
        self._impl                           = impl
        return

    def postingsURL(self, parent_trace):
        '''
        Returns a string that can be used to locate the postings area in the Knowledge Base store's current environment
        '''
        return self._impl.postingsURL(parent_trace)

    def manifestsURL(self, parent_trace):
        '''
        Returns a string that can be used to locate the manifests area in the Knowledge Base store's current environment
        '''
        return self._impl.manifestsURL(parent_trace)

    def clientURL(self, parent_trace):
        '''
        Returns a string that can be used to locate external collaboration area (such as SharePoint) that
        this environment is associated with
        '''
        return self._impl.clientURL(parent_trace)

    def name(self, parent_trace):
        '''
        Returns a string corresponding to the unique name that identifes this environment object among all
        environments known to the KnowledgeBaseStore.
        '''
        return self._impl.name(parent_trace)

    def config(self, parent_trace):
        '''
        Return a KB_Environment_Config object for this environment
        '''
        return self._impl.config(parent_trace)

    def parent(self, parent_trace):
        '''
        Returns a KB environment object, corresponding to this environment's parent, if one exists, or None otherwise.
        '''
        return self._impl.parent(parent_trace)

    def children_names(self, parent_trace):
        '''
        Returns a list of strings, corresponding to the names that uniquely identify environments that are
        direct children of this environment in the KnowledgeBaseStore.
        '''
        return self._impl.children_names(parent_trace)

    def child(self, parent_trace, child_name):
        '''
        Returns a KB_Environment object, corresponding to the child of this environment identified by the
        string `child_name`. Returns None if no such child exists.
        '''
        return self._impl.child(parent_trace, child_name)

    def removeChild(self, parent_trace, child_name):
        '''
        Disconnects an environment called `child_name` as a direct child of this environment, if is indeed a child.

        @param child_name A string, uniquely identifying the environment to disconnect among all environments in
                the KnowledgeBaseStore.
        '''
        return self._impl.removeChild(parent_trace, child_name)

    def findSubEnvironment(self, parent_trace, name):
        '''
        Searches for a descendent environment with the given name (so a child environment or a 
        child of a child, etc. If none exists, returns None
        '''
        return self._impl.findSubEnvironment(parent_trace, name)

    def addSubEnvironment(self, parent_trace, name, env_config, isolate_collab_area = False):
        '''
        Creates and returns a new File_KBEnv_Impl with name `name` and using self as the parent environment.

        @param name A string, used as the unique name of this environment among all environments in the store
        @param env_config A KB_Environment_Config object that will be set as the configuration of the newly
                    created sub-environment
        @param isolate_collab_area A boolean to determine the relationship that the sub-environment being
                    created should have with the external collaboration area (such as SharePoint) from where users 
                    of the KnowledgeBase post spreadsheets and into which users request generated forms and reports 
                    to be written to.

                    By default, the boolean is False, in which case the sub-environment shares the same
                    external collaboration folder as the parent.

                    If the caller sets it to True, then the sub-environment will create an internal area
                    that will be treated as the "external collaboration area" for all KnowledgeBaseStore
                    processing when this sub-environment is set as the current environment.
                    
                    This setting should be set to False in normal production usage. It is mainly used in test situations 
                    where the parent environment is associated to a collaboration is a deterministic set of files 
                    that should not be mutated by test cases, since it is used to "seed" multiple test_cases.
                    In such cases, test cases will need to create an environment to serve as
                    the test case's "root", and which will have to be associated to a dedicated notion of 
                    "external collaboration area" specific to that test case.
                    In those cases this flag should be set to True to ensure the creation of such an
                    environment-specific "external collaboration area" with the required isolation.
        '''
        return self._impl.addSubEnvironment(    parent_trace, 
                                                parent_env          = self,
                                                name                = name, 
                                                env_config          = env_config, 
                                                isolate_collab_area = isolate_collab_area)

    def seedCollaborationArea(self, parent_trace, sourceURL):
        '''
        Populates the "external collaboration area" associated to this environment by copying information
        from the sourceURL

        @param sourceURL A string identifying an area with content that should be downloaded to populate
                        the "external collaboration area" associated to this environment.
        '''
        return self._impl.seedCollaborationArea(parent_trace, sourceURL)

    def describe(self, parent_trace, include_timestamps = True):
        '''
        Returns a dictionary object that describes the contents of the environment

        @param include_timestamps A boolean, which defaults to True. If False, it will mask 
                all timestamps from the description (for example, in logs). In production this flag should normally
                 be set to True.
                The main use case for setting it to false is regression testing, where the desire for
                deterministic output motivates the need for masking timestamps.
        '''
        return self._impl.describe(parent_trace, include_timestamps)

class File_KBEnv_Impl():
    '''
    Implementation of KB_Environment services when KnowledgeBase is configured to use a file-system based stack.
    '''
    def __init__(self, parent_trace, name, store, parent_environment, config, 
                    postings_rootdir, manifests_roodir, clientURL):
        '''
        super().__init__(   parent_trace            = parent_trace, 
                            name                    = name, 
                            store                   = store, 
                            parent_environment      = parent_environment,
                            config                  = config)
        '''
        if not type(config)==KB_Environment_Config:
            raise ApodeixiError(parent_trace, "Unsupported config provided when creating environment",
                                                data = {"config type expected":         str(KB_Environment_Config.__name__),
                                                        "config type provided":         str(type(config)),
                                                        "environment name":             str(name)})

        # The check below was added to fix bugs whereby the programmer of Apodeixi could get easily confused and
        # corrupt the dependency tree among environments, by confusing environment vs environment implementation classes,
        # and not keeping child-parent relationships consistent (e.g., an environment implementation whose
        # parent is not an environment (as it should be) but instead another environment implementation)
        if parent_environment != None and not type(parent_environment) == KB_Environment: 
            raise ApodeixiError(parent_trace, "Invalid parent environment class provided when creating File_KBEnv_Impl",
                                                data = {"type expected":         str(KB_Environment.__name__),
                                                        "type provided":         str(type(parent_environment)),
                                                        "environment name":             str(name)})
            
        self._parent_environment             = parent_environment
        self._config                         = config
        self._store                          = store
        self._name                           = name
        self._children                       = {}

        self._postings_rootdir                      = postings_rootdir
        self._manifests_roodir                      = manifests_roodir 
        self._clientURL                             = clientURL

    ENVS_FOLDER                                     = "envs"
    LOGS_FOLDER                                     = "logs"
    REPORTS_FOLDER                                  = "reports"
    POSTINGS_ENV_DIR                                = "kb/excel-postings"
    MANIFESTS_ENV_DIR                               = "kb/manifests"
    COLLABORATION_DIR                               = "external-collaboration"

    def postingsURL(self, parent_trace):
        '''
        Returns a string that can be used to locate the postings area in the Knowledge Base store's current environment
        '''
        return self._postings_rootdir

    def manifestsURL(self, parent_trace):
        '''
        Returns a string that can be used to locate the manifests area in the Knowledge Base store's current environment
        '''
        return self._manifests_rootdir

    def clientURL(self, parent_trace):
        '''
        Returns a string that can be used to locate external collaboration area (such as SharePoint) that
        this environment is associated with
        '''
        return self._clientURL

    def name(self, parent_trace):
        '''
        Returns a string corresponding to the unique name that identifes this environment object among all
        environments known to the KnowledgeBaseStore.
        '''
        return self._name

    def config(self, parent_trace):
        return self._config

    def parent(self, parent_trace):
        return self._parent_environment

    def children_names(self, parent_trace):
        return self._children.keys()

    def child(self, parent_trace, child_name):
        if child_name in self._children.keys():
            return self._children[child_name]

    def removeChild(self, parent_trace, child_name):
        if child_name in self._children.keys():
            self._children.pop(child_name)

    def postingsURL(self, parent_trace):
        return self._postings_rootdir

    def manifestsURL(self, parent_trace):
        return self._manifests_roodir

    def clientURL(self, parent_trace):
        return self._clientURL

    def findSubEnvironment(self, parent_trace, name):
        '''
        Searches for a descendent environment with the given name (so a child environment or a 
        child of a child, etc. 

        If it is not found, this method will attempt to load it from disk if metadata for such
        an environment exists, but only if the environment sought is either a child of self
        or a child of the base environment.
        
        If none exists, returns None
        '''
        # First search in memory

        descendent_env          = self.findSubEnvironmentInMemory(parent_trace, name)

        if descendent_env == None:
            # If we get here it means the sub-environment does not exist or it is not in memory, as when
            # it was created by another Python process. If so, we can load it from metadata as long as it is
            # an immediate child of self or of the base environment
            descendent_env      = self.find_child_environment_from_metadata(parent_trace, name)

        return descendent_env

    def findSubEnvironmentInMemory(self, parent_trace, name):
        '''
        Searches for a descendent environment with the given name (so a child environment or a 
        child of a child, etc. If none exists, returns None
        '''
        # Do a depth-first search
        for child_name in self._children.keys():
            child_env           = self._children[child_name]
            if name == child_name:
                return child_env
            descendent_env = child_env.findSubEnvironment(parent_trace, name)
            if descendent_env != None:
                return descendent_env
        # If we get this far it means we never found it
        return None

    def addSubEnvironment(self, parent_trace, parent_env, name, env_config, isolate_collab_area = False):
        '''
        Creates and returns a new File_KBEnv_Impl with name `name` and using self as the parent environment.

        @param parent_env A KB_Environment object, that contains this File_KBEnv_Impl as its implementation
                    (i.e., parent_env._impl == self)
        @param name A string, used as the unique name of this environment among all environments in the store
        @param env_config A KB_Environment_Config object that will be set as the configuration of the newly
                    created sub-environment
        @param isolate_collab_area A boolean to determine how the `_clientURL`
                    attribute should be set for the sub-environment being created. This is an attribute that
                    points to folders external to the KnowledgeBase (such as SharePoint) from where users post 
                    spreadsheets and into which users request generated forms and reports to be written to.
                    By default, the boolean is False, in which case the sub-environment shares the same
                    external collaboration folder as the parent.
                    If the caller sets it to True, then the sub-environment will have its own dedicated
                    local folder for the `_clientURL`.
                    This setting should be set to False in normal production usage. It is mainly in test situations 
                    where the parent environment is a deterministic set of files that should not be mutated by
                    test cases. In such cases, test cases will need to create an environment to serve as
                    the test case's "root", and will need to have a notion of `_clientURL`
                    in that root. In those cases this flag should be set to True to ensure the required isolation.
        '''
        ME                          = File_KBEnv_Impl

        root_dir                    = _os.path.dirname(self._store.base_environment(parent_trace).manifestsURL(parent_trace))
        envs_dir                    = root_dir + "/" + ME.ENVS_FOLDER
        PathUtils().create_path_if_needed(parent_trace, envs_dir)

        self._store._validate_environment_name(parent_trace    = parent_trace, name = name)

        sub_env_name                = name.strip()
        my_trace                    = parent_trace.doing("Checking sub environment's name is available")
        if sub_env_name in list(_os.listdir(envs_dir)):
            raise ApodeixiError(my_trace, "Can't create a environment with a name that is already used for another environment",
                                        data = {'sub_env_name': str(sub_env_name)})
        if sub_env_name in self._children.keys():
            raise ApodeixiError(my_trace, "Can't create a sub environment with a name that is already used for another environment",
                                        data = {'sub_env_name': str(sub_env_name)})

        my_trace                    = parent_trace.doing("Creating sub environment's folders",
                                                            data = {'sub_env_name': sub_env_name})

        subenv_postings_rootdir     = envs_dir + "/" + sub_env_name + "/" + ME.POSTINGS_ENV_DIR
        subenv_manifests_rootdir    = envs_dir + "/" + sub_env_name + "/" + ME.MANIFESTS_ENV_DIR

        if isolate_collab_area:
            subenv_collab_folder = envs_dir + "/" + sub_env_name + "/" + ME.COLLABORATION_DIR
        else:
            subenv_collab_folder = self._clientURL

        PathUtils().create_path_if_needed(my_trace, subenv_postings_rootdir)
        PathUtils().create_path_if_needed(my_trace, subenv_manifests_rootdir)
        PathUtils().create_path_if_needed(my_trace, subenv_collab_folder)

        my_trace                    = parent_trace.doing("Creating sub environment", data = {'sub_env_name': sub_env_name})
        sub_env_impl                = File_KBEnv_Impl(  parent_trace                    = my_trace, 
                                                        name                            = sub_env_name, 
                                                        store                           = self._store, 
                                                        parent_environment              = parent_env,
                                                        config                          = env_config,
                                                        postings_rootdir                = subenv_postings_rootdir,
                                                        manifests_roodir                = subenv_manifests_rootdir,
                                                        clientURL   = subenv_collab_folder)

        sub_env                     = KB_Environment(   parent_trace                        = my_trace,
                                                        impl                                = sub_env_impl)

        self._children[sub_env_name] = sub_env
        sub_env_impl.save_environment_metadata(my_trace)
        return sub_env

    def save_environment_metadata(self, parent_trace):
        '''
        Creates and saves a YAML file called "METATATA.yaml" in the root folder for self.
        It is sufficient information from which to re-create the environment (for example, if it was
        created in a different Python process, so this Python process wouldn't have an in-memory object
        for it unless it loads it, leveraing the "METADATA.yaml" file).

        This can happen when the CLI creates a sandbox that will later be used by subsequent commands.
        Since each CLI invocation is its own Python process, different invocations can only share the
        same sandbox environment if there is a way to persist and then load the state of an environment.
        '''
        ME                                  = File_KBEnv_Impl
        METADATA_FILENAME                   = "METADATA.yaml"
        metadata_dict                       = {}
        metadata_dict['name']               = self.name(parent_trace)
        metadata_dict['parent']             = self.parent(parent_trace).name(parent_trace)
        metadata_dict['postingsURL']        = self.postingsURL(parent_trace)
        metadata_dict['manifestsURL']       = self.manifestsURL(parent_trace)
        metadata_dict['clientURL']          = self.clientURL(parent_trace)

        config                              = self.config(parent_trace)

        config_dict                         = {}
        config_dict['read_misses_policy']   = config.read_misses_policy
        config_dict['use_timestamps']       = config.use_timestamps

        metadata_dict['config']             = config_dict

        if self == self._store.base_environment(parent_trace):
            environment_dir                 = _os.path.dirname(self._store.base_environment(parent_trace). \
                                                    manifestsURL(parent_trace))
        else:
            root_dir                        = _os.path.dirname(self._store.base_environment(parent_trace). \
                                                    manifestsURL(parent_trace))
            envs_dir                        = root_dir + "/" + ME.ENVS_FOLDER
            environment_dir                 = envs_dir + "/" + self.name(parent_trace)
        
        PathUtils().create_path_if_needed(parent_trace, environment_dir)

        with open(environment_dir + "/" + METADATA_FILENAME, 'w') as file:
            _yaml.dump(metadata_dict, file)

    def find_child_environment_from_metadata(self, parent_trace, child_env_name):
        '''
        Attempts to instantiate an immediate child environment based on its metadata.
        It must be an immediate child of self.

        This method deliberately only looks for an immediate child.
        
        However, before attempting to instantiate such an environment it checks if an environment
        with that name already exists in memory. If so, it defers to the in-memory object and does
        not load the metadata, returning the in-memory object instead.

        If no metadata for such an environment exists, or if it does but is not for an immediate
        child of self, then this method will return None.

        NOTE: It is important to return None (as opposed to raising an ApodeixiError) because this
        method will likely be called in a recursive search by self.findSubEnvironment, and it is
        "normal" in such a recursion to attempt calling this method from different "self" in the
        environment hierarcy. So for most but one of them, the child_env_name is not for a real
        child, so it is OK to return None. It would be erroneous to raise an ApodeixiError since that
        would cause the recursion of self.findSubEnvironment to abort before it has a chance to get
        to the real parent of `child-env_name`

        '''
        # First, determine if the environment exists in memory
        child_env                   = self.findSubEnvironmentInMemory(parent_trace, child_env_name)
        if child_env != None:
            return child_env

        ME                          = File_KBEnv_Impl

        my_trace                    = parent_trace.doing("Retrieving metadata for child environment", 
                                                            data = {'child_env_name': child_env_name,})
        METADATA_FILENAME           = "METADATA.yaml"
        root_dir                    = _os.path.dirname(self._store.base_environment(parent_trace).manifestsURL(parent_trace))
        envs_dir                    = root_dir + "/" + ME.ENVS_FOLDER
        environment_dir             = envs_dir + "/" + child_env_name

        metadata_path               = environment_dir + "/" + METADATA_FILENAME

        if not _os.path.exists(metadata_path):
            return None

        with open(metadata_path, 'r', encoding="utf8") as file:
            metadata_dict                = _yaml.load(file, Loader=_yaml.FullLoader)

        if self.name(my_trace) != metadata_dict['parent']:
            return None 

        my_trace                    = parent_trace.doing("Instantiating child environment from metadata", 
                                                            data = {'child_env_name': child_env_name,
                                                                    'metadata':     metadata_dict})

        config_dict                 = metadata_dict["config"]
        child_env_config            = KB_Environment_Config(    parent_trace            = my_trace,
                                                                read_misses_policy      = config_dict["read_misses_policy"],
                                                                use_timestamps          = config_dict["use_timestamps"],
                                                                path_mask               = None, # This was not persisted
                                                            )

        # GOTCHA: When constructing the child_env_impl, we must give a parent_environment that is
        # of type KB_Environment.
        #
        # However, here we are an implementation class, so not derived from KB_Environment, so will need
        # first to find our wrapping KB_Environment object for which self is the impl
        base_environment            = self._store.base_environment(my_trace)
        our_name                    = self.name(my_trace)
        if our_name == base_environment.name(my_trace):
            our_env                 = base_environment
        else:
            our_env                 = base_environment.findSubEnvironment(  parent_trace    = my_trace, 
                                                                            name            = our_name)

        child_env_impl              = File_KBEnv_Impl(  parent_trace                    = my_trace, 
                                                        name                            = child_env_name, 
                                                        store                           = self._store, 
                                                        parent_environment              = our_env,
                                                        config                          = child_env_config,
                                                        postings_rootdir                = metadata_dict["postingsURL"],
                                                        manifests_roodir                = metadata_dict["manifestsURL"],
                                                        clientURL                       = metadata_dict["clientURL"])

        child_env                     = KB_Environment(   parent_trace                        = my_trace,
                                                        impl                                = child_env_impl)
        self._children[child_env_name] = child_env
        return child_env

    def seedCollaborationArea(self, parent_trace, sourceURL):
        '''
        Populates the "external collaboration area" associated to this environment by copying information
        from the sourceURL

        @param sourceURL A string identifying an area with content that should be downloaded to populate
                        the "external collaboration area" associated to this environment.
        '''
        # We are using an isolated collaboration folder specific to our environment, so need
        # to populate it with the data in the test_db/sharepoint area (the "immutable, deterministic seed")
        area_to_seed     = self.clientURL(parent_trace)

        def _ignore(subdir, file_list):
            IGNORE_LIST         = ["Thumbs.db"]
            dont_copy_list      = [f for f in file_list if f in IGNORE_LIST]
            return dont_copy_list
        try:
            _shutil.copytree(   src                 = sourceURL, 
                                dst                 = area_to_seed,
                                ignore              = _ignore)
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Found an error in downloading the content for an environment's collaboration area",
                                            data = {"URL to download from":            self._clientURL, 
                                                    "environment collaobration area":     area_to_seed,
                                                    "error":                str(ex)})

    def describe(self, parent_trace, include_timestamps):
        '''
        Returns a dictionary object that describes the contents of the environment

        @param include_timestamps A boolean. If False, it will mask 
                all timestamps from the description (for example, in logs). In production this flag should normally
                 be set to True.
                The main use case for setting it to false is regression testing, where the desire for
                deterministic output motivates the need for masking timestamps.
        '''
        env_hierarchy       = self._folder_hierarchy(   parent_trace        = parent_trace,
                                                        include_timestamps  = include_timestamps)
        return env_hierarchy.to_dict()

    def _folder_hierarchy(self, parent_trace, include_timestamps):
        '''
        Returns a FolderHierarchy object that describes the current contents of this environment
        '''
        ME                      = File_KBEnv_Impl

        root_dir                = _os.path.dirname(self._store.base_environment(parent_trace).manifestsURL(parent_trace))
        if self.name(parent_trace) == self._store.base_environment(parent_trace).name(parent_trace):
            my_dir              = root_dir
            # If we are showing the base environment, exclude the transient envs subfolder that is not part
            # of the "official data" of the base environment. Ditto for the logs folder
            def avoid_envs_and_logs_folders(subdir):
                avoid1          = _os.path.normpath(root_dir + "/" + ME.ENVS_FOLDER)
                avoid2          = _os.path.normpath(root_dir + "/" + ME.LOGS_FOLDER) 
                path            = _os.path.normpath(subdir)
                return (not path.startswith(avoid1)) and (not path.startswith(avoid2))
            filter              = avoid_envs_and_logs_folders
        else:        
            my_dir              = root_dir + "/" + ME.ENVS_FOLDER + "/" + self._name
            # In this case, include everything under my_dir
            filter              = None


        hierarchy                   = FolderHierarchy.build(    parent_trace        = parent_trace, 
                                                                rootdir             = my_dir, 
                                                                filter              = filter,
                                                                include_timestamps  = include_timestamps)
        return hierarchy

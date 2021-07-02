import os                                               as _os


from apodeixi.util.a6i_error                            import ApodeixiError
from apodeixi.util.path_utils                           import PathUtils, FolderHierarchy

class KB_Environment():
    '''
    Abstract class.

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
    '''
    def __init__(self, parent_trace, name, store, parent_environment):
        self._parent_environment             = parent_environment
        self._store                          = store
        self._name                           = name
        self._children                       = {}
        return

    def postingsURL(self, parent_trace):
        '''
        Abstract method.

        Returns a string that can be used to locate the postings area in the Knowledge Base store's current environment
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'postings_rootdir' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def manifestsURL(self, parent_trace):
        '''
        Abstract method.

        Returns a string that can be used to locate the manifests area in the Knowledge Base store's current environment
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'manifests_roodir' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

class File_KB_Environment(KB_Environment):
    '''
    '''
    def __init__(self, parent_trace, name, store, parent_environment, postings_rootdir, manifests_roodir):
        super().__init__(   parent_trace            = parent_trace, 
                            name                    = name, 
                            store                   = store, 
                            parent_environment      = parent_environment)

        self._postings_rootdir                      = postings_rootdir
        self._manifests_roodir                      = manifests_roodir

    ENVS_FOLDER                                     = "envs"
    POSTINGS_ENV_DIR                                = "excel-postings"
    MANIFESTS_ENV_DIR                               = "manifests"

    def postingsURL(self, parent_trace):
        return self._postings_rootdir

    def manifestsURL(self, parent_trace):
        return self._manifests_roodir

    def name(self, parent_trace):
        return self._name

    def findSubEnvironment(self, parent_trace, name):
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
                return True
        # If we get this far it means we never found it
        return False

    def addSubEnvironment(self, parent_trace, name):
        ME                          = File_KB_Environment

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
        PathUtils().create_path_if_needed(my_trace, subenv_postings_rootdir)
        PathUtils().create_path_if_needed(my_trace, subenv_manifests_rootdir)

        my_trace                    = parent_trace.doing("Creating sub environment", data = {'sub_env_name': sub_env_name})
        sub_env                     = File_KB_Environment(  parent_trace            = my_trace, 
                                                            name                    = sub_env_name, 
                                                            store                   = self._store, 
                                                            parent_environment      = self,
                                                            postings_rootdir        = subenv_postings_rootdir,
                                                            manifests_roodir        = subenv_manifests_rootdir)

        self._children[sub_env_name] = sub_env

    def folder_hierarchy(self, parent_trace, include_timestamps = True):
        '''
        Returns a FolderHierarchy object that describes the current contents of this environment
        '''
        ME                          = File_KB_Environment

        if self == self._store.base_environment(parent_trace):
            my_dir                      = self._store.base_environment(parent_trace).manifestsURL(parent_trace)
        else:        
            root_dir                    = _os.path.dirname(self._store.base_environment(parent_trace).manifestsURL(parent_trace))
            my_dir                      = root_dir + "/" + ME.ENVS_FOLDER + "/" + self._name


        hierarchy                   = FolderHierarchy.build(    parent_trace        = parent_trace, 
                                                                rootdir             = my_dir, 
                                                                filter              = None,
                                                                include_timestamps  = include_timestamps)
        return hierarchy

import os                                               as _os
import shutil                                           as _shutil
import yaml                                             as _yaml

from apodeixi.knowledge_base.knowledge_base_store       import KnowledgeBaseStore
from apodeixi.knowledge_base.kb_environment             import File_KB_Environment, KB_Environment_Config
from apodeixi.knowledge_base.filing_coordinates         import JourneysFilingCoordinates, \
                                                                InitiativesFilingCoordinates, \
                                                                ArchiveFilingCoordinates, LogFilingCoordinates
from apodeixi.knowledge_base.knowledge_base_util        import ManifestHandle, ManifestUtils, PostingLabelHandle
from apodeixi.util.path_utils                           import PathUtils
from apodeixi.util.a6i_error                            import ApodeixiError, FunctionalTrace

class TransactionEvents():
    '''
    Helper class to keep track of all the writes and deletes that happen in a transaction's environment
    '''
    def __init__(self, transaction_name):
        self._transaction_name      = transaction_name

        # These are lists of of relative paths from root of transactional environment
        self._posting_writes        = [] 
        self._posting_deletes       = []
        self._manifest_writes       = [] 
        self._manifest_deletes      = []
        self._clientURL_writes      = []
        self._clientURL_deletes     = []

    def remember_posting_write(self, relative_path):
        self._posting_writes.append(relative_path)

    def remember_posting_delete(self, relative_path):
        self._posting_deletes.append(relative_path)

    def remember_manifest_write(self, relative_path):
        self._manifest_writes.append(relative_path)

    def remember_manifest_delete(self, relative_path):
        self._manifest_deletes.append(relative_path)

    def remember_clientURL_write(self, relative_path):
        self._clientURL_writes.append(relative_path)

    def remember_clientURL_delete(self, relative_path):
        self._clientURL_deletes.append(relative_path)

    def posting_writes(self):
        return self._posting_writes

    def manifest_writes(self):
        return self._manifest_writes

    def clientURL_writes(self):
        return self._clientURL_writes

    def posting_deletes(self):
        return self._posting_deletes

    def manifest_deletes(self):
        return self._manifest_deletes

    def clientURL_deletes(self):
        return self._clientURL_deletes

class Isolation_KnowledgeBaseStore(KnowledgeBaseStore):
    '''
    Abstract class.

    Defines a file-system-based implementation of the KnowledgeBaseStore with isolation capabilities.

    The file-system nature of this KnowledgeBaseStore class is expressed in the fact that the entire knowledge base 
    is held under a two root folders (one for postings and one for all derived data, including manifests)
    and follows a structure based on filing schemes of the KB_ProcessingRules.

    The isolation capabilities are handled via KB_Environment objects.
    KB_Environment objects are lower-level isolation levels, which can be used for very different use cases,
    including:
    * Transactionality, as to support atomic Knowledge Base operations (i.e., all I/O either works or none is committed)
    * Intermediate snapshots of the store, as to support regression testing.

    Normally, clients of a KnowledgeBaseStore are not expected to directly access KB_Environments or the
    KB_Environment-related services in this class. Instead, they should access higher level 
    KnowledgeBaseStore isolation APIs (such as beginTransaction(-) and commitTransaction(-)), which derived concrete
    classes are expected to possibly re-implement by leveraging the KB_Environment-related services in this class.
    
    *** NOTE ON FAILOVER ***
    Notably, derived classes are supposed to handle any read fail-overs. I.e., this abstract class will only
    search for data in the current environment, and not default to the parent environment even if that is how
    the current environment is configured. Derived concrete classes define how failover is handled, and typically
    re-implement read I/O methods by writing failover code around calls to super()'s (i.e., to this class's)
    read I/O methods.

    @param kb_rootdir A string, corresponding to the absolute path in the local machine
                            corresponding to the KnowledgeBase.
    @param clientURL A string, corresponding to the absolute path to a root folder in a collaboration
                            drive system (such as SharePoint) in which end-users will collaborate to create
                            the Excel spreadsheets that will be eventually posted to the KnowledgeBase. This
                            shared drive is also the location to which the KnowledgeBase will save
                            generated forms or reports requested by end-users. This is a "root folder" in that
                            the structure below will be assumed to follow the filing structure of the
                            KnowledgeBase for postings.
    '''
    def __init__(self, parent_trace, kb_rootdir, clientURL):

        my_trace                        = parent_trace.doing("Validating root folders are valid")
        if True:
            # Check parameters are indeed directories
            if not _os.path.isdir(kb_rootdir):
                raise ApodeixiError(parent_trace, "Unable to initialize KnowledgeBaseStore because an invalid directory was given "
                                                    + " for the root of the KnoweldgeBaseStore",
                                                    data = {"kb_rootdir": kb_rootdir})
            if not _os.path.isdir(clientURL):
                raise ApodeixiError(parent_trace, "Unable to initialize KnowledgeBaseStore because an invalid directory was given "
                                                    + " for the root of the collaboration area",
                                                    data = {"collaboration_rootdir": clientURL})

            self._kb_rootdir                       = kb_rootdir
            self._clientURL     = clientURL

            postings_rootdir                        =  kb_rootdir + "/excel-postings" 
            manifests_roodir                        =  kb_rootdir + "/manifests"      

            # If missing, create the postings and manifest folders 
            if not _os.path.exists(postings_rootdir):                                                                                               
                _os.mkdir(postings_rootdir)
            if not _os.path.exists(manifests_roodir):
                _os.mkdir(manifests_roodir)

            # Check nobody previously created these things as files instead of folders by mistake
            if  _os.path.isfile(postings_rootdir):
                raise ApodeixiError(parent_trace, "Unable to initialize KnowledgeBaseStore postings root is a file, "
                                                    + " and should instead have been a directory",
                                                    data = {"postings root": postings_rootdir})
            if  _os.path.isfile(manifests_roodir):
                raise ApodeixiError(parent_trace, "Unable to initialize KnowledgeBaseStore manifests root is a file, "
                                                    + " and should instead have been a directory",
                                                    data = {"manifests root": manifests_roodir}) 
        super().__init__()

        _BASE_ENVIRONMENT           = '_BASE_ENVIRONMENT'
        root_trace                  = FunctionalTrace(None).doing("Creating KB's store's base environment")
        env_config                  = KB_Environment_Config(
                                            root_trace, 
                                            read_misses_policy  = KB_Environment_Config.FAILOVER_READS_TO_PARENT,
                                            use_timestamps      = True,
                                            path_mask           = None)
        self._base_env              = File_KB_Environment(  parent_trace            = root_trace, 
                                                            name                    = _BASE_ENVIRONMENT, 
                                                            store                   = self, 
                                                            parent_environment      = None,
                                                            config                  = env_config,
                                                            postings_rootdir        = postings_rootdir,
                                                            manifests_roodir        = manifests_roodir,
                                                            clientURL               = self._clientURL)  
          
        self._current_env           = self._base_env

        self.filing_rules           = { #List of associations of posting API => FilingCoordinate class to use for such posting API
            'big-rocks.journeys.a6i':                               JourneysFilingCoordinates,
            'milestone.journeys.a6i':                               JourneysFilingCoordinates,
            'capability-hierarchy.bdd.kernel.a6i':                  None, # TODO
            'workstream.initiatives.a6i':                           InitiativesFilingCoordinates,
            'charter.initiatives.a6i':                              InitiativesFilingCoordinates, 
        }

        # Stack of nested environments used during transactions
        self._transactions_stack    = []
        self._transaction_nb        = 1 # Used for the number of the "next" transaction

        # Per transactional environment, it tracks all writes and deletes, in case they need to be applied
        # to a parent environment
        self._transaction_events_dict   = {} 

    _TRANSACTION                    = "store-transaction"

    def transaction_env(self, parent_trace):
        '''
        Helper method to return the environment of the transaction we are in the midst of, if any.
        Otherwise returns None
        '''
        if len(self._transactions_stack) == 0:
            return None
        else:
            env                     = self._transactions_stack[-1]
            return env

    def parent_transaction_env(self, parent_trace):
        '''
        Helper method to return the environment of the transaction that is parent to the transaction
        we are in the midst of, if any.
        Otherwise returns None
        '''
        if len(self._transactions_stack) < 2:
            return None
        else:
            env                     = self._transactions_stack[-2]
            return env

    def _gen_transaction_name(self, parent_trace):
        '''
        Helper method to generate and return a unique string that can be used to identify the next
        transaction for this store
        '''
        ME                          = Isolation_KnowledgeBaseStore
        name                        = ME._TRANSACTION + "." + str(self._transaction_nb)
        self._transaction_nb        += 1
        return name

    def beginTransaction(self, parent_trace):
        '''       
        Starts an isolation state in which all subsequent I/O is done in an isolation area
        dedicated to this transaction, and not applied back to the store's persistent area until the
        transaction is committed.

        If an error is raised in this method, then the transaction is not begun (hence an
        abortTransaction should not be attempted if this method raises an error)
        '''
        env                         = self.transaction_env(parent_trace) 
        if env == None:
            env                     = self.current_environment(parent_trace)
        else:
            current                 = self.current_environment(parent_trace)
            if env != current:
                raise ApodeixiError(parent_trace, "Store is an inconstent state: the current environment "
                                                    + " and the transactional environment are different",
                                                    data = {"current environment":          current.name(parent_trace),
                                                            "transactional environment":    env.name(parent_trace)})
            
        
        name                        = self._gen_transaction_name(parent_trace)
        isolation_env               = env.addSubEnvironment(parent_trace, name, env.config(parent_trace))

        self.activate(parent_trace, name)

        # **GOTCHA** 
        #
        # Mutate the transactions tack state, but do so at the very end of the method, before returning.
        # This will make it official that we are in a new transaction. 
        # This is not done earlier because the spec of this method is to guarantee
        # that a transaction has not begun unless this method is successful. Thus, if the code above raised
        # an error, we don't want to have appended a new entry in the transaction stack. 
        # This ensures adherence to the semantics there is no need (and it would be buggy) for the caller
        # to call abortTransaction in response to an error arising in beginTransaction, since beginTransaction
        # is not supposed to start any transaction at all unless it succeeds.
        self._transactions_stack.append(isolation_env)
        self._transaction_events_dict[name]  = TransactionEvents(name)

    def _validate_transaction_end_of_life(self, parent_trace):
        '''
        Helper method to validate some internal consistency relationships that must hold true within
        the Knowledge Store, whenver a transaction is behing ended (via abort or commit)

        If successful, returns a pair of environments: the environment corresponding for the transaction
        being ended, and its parent environment.

        If validation fails then this method raises an ApodeixiError
        '''
        env                         = self.transaction_env(parent_trace) 
        if env == None:
            raise ApodeixiError(parent_trace, "Can't end transaction because we are not in the middle of a transaction")
        parent_env                  = env.parent(parent_trace)   
        if parent_env == None:
            raise ApodeixiError(parent_trace, "Can't end transaction because store is an inconsistent state: "
                                                " the transaction being aborted has no parent environment",
                                                data = {"transaction being ended":    env.name(parent_trace)}) 
        
        
        parent_transaction_env      = self.parent_transaction_env(parent_trace)
        if parent_transaction_env != None and parent_env != parent_transaction_env:
            raise ApodeixiError(parent_trace, "Can't e d transaction because store is an inconsistent state: "
                                            + " the transaction being aborted was a child transaction of "
                                            + "an environment that is not its parent",
                                            data = {"transaction being ended":    env.name(parent_trace),
                                                    "parent transaction":           parent_transaction_env.name(parent_trace),
                                                    "parent environment":           parent_env.name(parent_trace)})

        return env, parent_env

    def abortTransaction(self, parent_trace):
        '''
        Aborts a transaction previously started by beginTransaction, by deleting transaction's isolation area,
        effectively ignoring any I/O previously done during the transaction's lifetime, and leaving the
        KnowledgeBaseStore in a state such that any immediately following I/O operation would be done 
        directly to the store's persistent area.
        '''  
        env, parent_env             = self._validate_transaction_end_of_life(parent_trace)

        # Remove state that makes us track the transaction being aborted
        aborted_env                 = self._transactions_stack.pop()
        self._transaction_events_dict.pop(aborted_env.name(parent_trace))
        
        # Now remove the environment of the transaction we just aborted
        self.removeEnvironment(parent_trace, env.name(parent_trace)) 
        self.activate(parent_trace, parent_env.name(parent_trace))

    def _failover_reads_to_parent(self, parent_trace):
        '''
        Returns a boolean to determine if parent environment should be used to retrieve data that is not
        present in the current environment.

        It is used by the I/O read services of the store whenever a read operation results in a "miss": if the
        current environment lacks the data in question, the I/O read service will search in the parent 
        environment and, if it finds it, will copy it to the current environment. 
        '''
        if self._current_env._parent_environment == None: # Can't failover to a non-existent parent
            return False
        if self._current_env._config.read_misses_policy == KB_Environment_Config.FAILOVER_READS_TO_PARENT:
            return True
        else:
            return False

    def supported_apis(self, parent_trace):
        '''
        Returns a list of the posting APIs that this KnowledgeStore knows about.
        '''
        return list(self.filing_rules.keys())

    def getFilingClass(self, parent_trace, posting_api):
        '''
        Returns a class object, derived from FilingCoordinates, that this store uses to structure postings for 
        the giving posting api
        '''
        if not posting_api in self.supported_apis(parent_trace):
            raise ApodeixiError(parent_trace, "Posting API '" + str(posting_api) + "' is not supported.")
        klass                           = self.filing_rules[posting_api]
        return klass

    def getPostingsURL(self, parent_trace):
        '''
        Returns a string that can be used to locate the postings area in the Knowledge Base store's current environment
        '''   
        current_env_postings_url              = self._current_env.postingsURL(parent_trace)
        return current_env_postings_url


    def getClientURL(self, parent_trace):
        '''
        Returns a string that can be used to locate the user-specific area (such as a SharePoint folder)
        into which generated forms and reports should be store.
        '''   
        current_env_client_url              = self._current_env.clientURL(parent_trace)
        return current_env_client_url
        
    def resetClientArea(self, parent_trace, coords):
        '''
        This method "refreshes" the area under the clientURL identified by the given coordinates, so that it is
        identical the the area under the store's postingsURL corresponding to those coordinates (as per
        the store's current environment)
        '''
        current_env         = self.current_environment(parent_trace)
        path_tokens         = coords.path_tokens(parent_trace)

        src_root            = current_env.postingsURL(parent_trace)
        src_area            = src_root              + "/" + "/".join(path_tokens)

        dst_root            = current_env.clientURL(parent_trace)
        dst_area            = dst_root              + "/" + "/".join(path_tokens)

        PathUtils().create_path_if_needed(parent_trace, dst_area)

        area_to_refresh     = self.current_environment(parent_trace).clientURL(parent_trace)

        def _ignore(subdir, file_list):
            IGNORE_LIST         = ["Thumbs.db"]
            dont_copy_list      = [f for f in file_list if f in IGNORE_LIST]
            return dont_copy_list
        try:
            _shutil.copytree(   src                 = src_area, 
                                dst                 = dst_area,
                                ignore              = _ignore,
                                dirs_exist_ok       = True)
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Found an error in copying refreshing clientURL area",
                                            data = {"area to refresh":      dst_area, 
                                                    "area used as source":  src_area,
                                                    "error":                str(ex)})       

    def current_environment(self, parent_trace):
        return self._current_env

    def parent_environment(self, parent_trace):
        return self._current_env._parent_environment

    def base_environment(self, parent_trace):
        return self._base_env

    def removeEnvironment(self, parent_trace, name):
        '''
        Removes the environment with the given name, if one exists, in which case returns 0.
        If no such environment exists then it returns -1.

        In the process it also removes any child environment, recursively down.
        '''
        ME                          = File_KB_Environment

        env_to_remove               = self.base_environment(parent_trace).findSubEnvironment(parent_trace, name)

        # Don't error out if env_to_remove is None, as it might have been created by an earlier Python process, 
        # so in memory we lost track of who are the children, since that information is not persisted to disk
        if env_to_remove != None: 
            for child_name in env_to_remove.children_names(parent_trace):
                loop_trace              = parent_trace.doing("Removing chid environment before removing parent",
                                                            data = {"child being removed":  str(child_name),
                                                                    "parent to remove later":   str(name)})
                self.removeEnvironment(loop_trace, child_name)

        root_dir                    = _os.path.dirname(self.base_environment(parent_trace).manifestsURL(parent_trace))
        envs_dir                    = root_dir + "/" + ME.ENVS_FOLDER
        PathUtils().create_path_if_needed(parent_trace, envs_dir)

        self._validate_environment_name(parent_trace    = parent_trace, name = name)

        sub_env_name                = name.strip()
        dir_to_remove               = envs_dir + "/" + sub_env_name
        try:
            if _os.path.isdir(dir_to_remove):
                _shutil.rmtree(dir_to_remove)
                # Also remove it as a child in the parent, lest later on when the parent is removed
                # it will think this child is still around and will try to remove a non-existent environment, and error out
                # As per earlier comment, we also don't error out if env_to_remove is None, since it might have been
                # created by an earlier process, so it is None since it isn't in memory in this process
                if env_to_remove != None:
                    parent_env          = env_to_remove.parent(parent_trace)
                    if parent_env != None:
                        parent_env.removeChild(parent_trace = parent_trace, child_name = name)
                else:
                    x=1 # DUMMY statement, just to stop debugger here
            else:
                return -1
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Encountered a problem deleting environment",
                                data = {"environment name": name, "exception": ex})
        
    def _validate_environment_name(self, parent_trace, name):
        my_trace                    = parent_trace.doing("Checking environment's name is a str")
        if not type(name) == str:
            raise ApodeixiError(my_trace, "Can't create an environment with a name that is not a string",
                                        data = {'name': str(name), 'type(name)': str(type(name))})

        my_trace                    = parent_trace.doing("Checking environment's name not blank")
        env_name                = name.strip()
        if len(env_name) == 0:
            raise ApodeixiError(my_trace, "Can't create a sub environment with a name that is blank",
                                        data = {'sub_env_name': str(env_name)})

    def activate(self, parent_trace, environment_name):
        '''
        Switches the store's current environment to be the one identified by the `environment_name`, unless
        no such environment exists in which case it raises an ApodeixiError
        '''
        base_environment                = self.base_environment(parent_trace)
        if environment_name == base_environment.name(parent_trace):
            next_env                    = base_environment
        else:
            next_env                    = base_environment.findSubEnvironment(parent_trace, environment_name)
        
        if next_env != None:
            self._current_env           = next_env
        else:
            raise ApodeixiError(parent_trace, "Can't activate an environment that does not exist",
                                                    data = {"environment_name": str(environment_name)})

    def deactivate(self, parent_trace):
        '''
        Switches the store's current environment to be the base environment.
        '''
        self._current_env               = self._base_env

    def searchPostings(self, parent_trace, posting_api, filing_coordinates_filter=None, posting_version_filter=None):
        '''
        Returns a list of PostingLabelHandle objects, one for each posting in the Knowledge Base that matches
        the given criteria:

        * They are all postings for the `posting_api`
        * They pass the given filters

        @param posting_api A string that identifies the type of posting represented by an Excel file. For example,
                            'milestone.modernization.a6i' is a recognized posting API and files that end with that suffix,
                            such as 'opus_milestone.modernization.a6i.xlsx' will be located by this method.
        @param filing_coordinates_filter A function that takes a FilingCoordinates instance as a parameter and returns a boolean. 
                            Any FilingCoordinates instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        @param posting_version_filter A function that takes a PostingVersion instance as a parameter and returns a boolean. 
                            Any PostingVersion instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.n.
        '''
        # TODO - Implement logic to filter by posting version. Until such time, abort if user needs such filtering
        if posting_version_filter != None:
            raise ApodeixiError(parent_trace, "Apologies, but filtering postings by version is not yet implemented in "
                                                + "File_KnowledgeBaseStore. Aborting the effort to searchPostings.")


        my_trace                    = parent_trace.doing("Scanning existing filing coordinates",
                                                data = {"environment":  
                                                        self.current_environment(parent_trace).name(parent_trace)})
        if True:
            scanned_handles         = []
            for currentdir, dirs, files in _os.walk(self.current_environment(my_trace).postingsURL(my_trace)):
                #for subdir in dirs:
                for a_file in files:
                    if a_file.startswith("~"):
                        continue # Skip such files, they are temporary Excel locks
                    loop_trace          = my_trace.doing("Scanning directory", data = {'currentdir': currentdir, 'file': a_file})
                    try:
                        handle      = self.buildPostingHandle(  parent_trace        = loop_trace,
                                                                excel_posting_path  = _os.path.join(currentdir, a_file))
                    except ApodeixiError as ex:
                        continue # This just means that this directory had nothing matching the posting API
                    if handle.posting_api != posting_api:
                        continue # Don't count this handle, since it for the wrong posting_api
                    if filing_coordinates_filter == None or filing_coordinates_filter(handle.filing_coords): # Passed the filter, if any
                        scanned_handles.append(handle)

        return scanned_handles

    def persistManifest(self, parent_trace, manifest_dict):
        '''
        Persists manifest_dict as a yaml object and returns a ManifestHandle that uniquely identifies it.
        '''
        kind                = manifest_dict['kind']
        name                = manifest_dict['metadata']['name']
        namespace           = manifest_dict['metadata']['namespace']
        suffix              = ''

        version             = ManifestUtils().get_manifest_version(parent_trace, manifest_dict)
        if version != None and len(str(version).strip()) > 0:
            suffix = '.' + str(version)
        manifest_dir        = self._current_env.manifestsURL(parent_trace) + "/" + namespace  + "/" + name
        PathUtils().create_path_if_needed(parent_trace=parent_trace, path=manifest_dir)
        manifest_file       = kind + suffix + ".yaml"
        relative_path       = namespace  + "/" + name + "/" + manifest_file
        my_trace            = parent_trace.doing("Persisting manifest", 
                                                    data = {    'manifests_dir': manifest_dir, 
                                                                'manifest_file': manifest_file},
                                                    origination = {
                                                                'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})
        if True:
            with open(manifest_dir + "/" + manifest_file, 'w') as file:
                _yaml.dump(manifest_dict, file)
            self._remember_manifest_write(my_trace, relative_path)
            
            handle          = ManifestUtils().inferHandle(my_trace, manifest_dict)
            return handle

    def _remember_posting_write(self, parent_trace, relative_path):
        '''
        Helper method. If we are in a transaction, it will remember the relative path of a write
        for a posting
        '''
        current_env             = self.current_environment(parent_trace)
        env_name                = current_env.name(parent_trace)
        if env_name in self._transaction_events_dict.keys():
            transaction_events = self._transaction_events_dict[env_name]
            transaction_events.remember_posting_write(relative_path)

    def _remember_posting_delete(self, parent_trace, relative_path):
        '''
        Helper method. If we are in a transaction, it will remember the relative path of a delete
        for a posting
        '''
        current_env             = self.current_environment(parent_trace)
        env_name                = current_env.name(parent_trace)
        if env_name in self._transaction_events_dict.keys():
            transaction_events = self._transaction_events_dict[env_name]
            transaction_events.remember_posting_delete(relative_path)
              

    def _remember_manifest_write(self, parent_trace, relative_path):
        '''
        Helper method. If we are in a transaction, it will remember the relative path of a write
        for a manifest
        '''
        current_env             = self.current_environment(parent_trace)
        env_name                = current_env.name(parent_trace)
        if env_name in self._transaction_events_dict.keys():
            transaction_events = self._transaction_events_dict[env_name]
            transaction_events.remember_manifest_write(relative_path)

    def _remember_clientURL_write(self, parent_trace, relative_path):
        '''
        Helper method. If we are in a transaction, it will remember the relative path of a write
        for a clientURL file
        '''
        current_env             = self.current_environment(parent_trace)
        env_name                = current_env.name(parent_trace)
        if env_name in self._transaction_events_dict.keys():
            transaction_events = self._transaction_events_dict[env_name]
            transaction_events.remember_clientURL_write(relative_path)

    def _remember_clientURL_delete(self, parent_trace, relative_path):
        '''
        Helper method. If we are in a transaction, it will remember the relative path of a delete
        for a posting
        '''
        current_env             = self.current_environment(parent_trace)
        env_name                = current_env.name(parent_trace)
        if env_name in self._transaction_events_dict.keys():
            transaction_events = self._transaction_events_dict[env_name]
            transaction_events.remember_clientURL_delete(relative_path)

    def retrieveManifest(self, parent_trace, manifest_handle):
        '''
        Returns a dict and a string.
        
        The dict represents the unique manifest in the store that is identified by the `manifest handle`.
        
        The string represents the full pathname for the manifest.

        If none exists, it returns None, None. 

        @param manifest_handle A ManifestHandle instance that uniquely identifies the manifest we seek to retrieve.
        '''
        matching_manifests      = [] # List of dictionaries, one per manifest
        matching_filenames      = [] # List of filename strings. Will be 1-1 lined up with matching_manifests

        folder                  = self._current_env.manifestsURL(parent_trace) + '/' \
                                        + manifest_handle.namespace + '/' + manifest_handle.name

        manifests, filenames    = self._getMatchingManifests(   parent_trace    = parent_trace, 
                                                                folder          = folder, 
                                                                manifest_handle = manifest_handle)
        matching_manifests.extend(manifests)
        matching_filenames.extend(filenames)
        
        if len(matching_filenames) > 1:
            raise ApodeixiError(parent_trace, "Found multiple manifests for given handle",
                                                data = {'manifest_handle': str(manifest_handle),
                                                        'matching files':   str(matching_filenames)},
                                                origination = {
                                                        'concrete class': str(self.__class__.__name__), 
                                                        'signaled_from': __file__})
        if len(matching_filenames) == 0:
            return None, None

        # By now we know there is exactly one match - that must be the manifest we are after
        manifest_path                   = folder + "/" + matching_filenames[0]
        return matching_manifests[0], manifest_path

    def _getMatchingManifests(self, parent_trace, folder, manifest_handle):
        '''
        Returns two lists of the same length:

        * A list of dictionaries, one per manifest that matches the given manifest handle
        * A list of filenames, which is where each of those manifests was retrieved from

        The search is done over the space of objects in the store that lie "at or below the folder", where
        the notion of "folder" depends on the concrete store class. For filesystem-based stores, "folder" would
        literally be a directory of some filesystem mount.

        @param folder A string scoping a subset of the store
        @param manifest_handle A ManifestHandle instance that (should) uniquely identify a single manifest in the store
        '''
        matching_manifests = [] # List of dictionaries, one per manifest
        matching_filenames = [] # List of filename strings. Will be 1-1 lined up with matching_manifests

        # Two areas where to search for manifests: input area, and output area. First the input area
        for filename in self._getFilenames(parent_trace, folder):
            my_trace            = parent_trace.doing("Loading manifest from file",
                                                        data = {'filename':         filename,
                                                                'folder':           folder},
                                                        origination = {
                                                                'concrete class':   str(self.__class__.__name__), 
                                                                'signaled_from':    __file__})
            with open(folder + '/' + filename, 'r') as file:
                manifest_dict   = _yaml.load(file, Loader=_yaml.FullLoader)
            
            inferred_handle     = ManifestUtils().inferHandle(my_trace, manifest_dict)
            if inferred_handle == manifest_handle:
                matching_filenames.append(filename)
                matching_manifests.append(manifest_dict)

        return matching_manifests, matching_filenames

    def _getFilenames(self, parent_trace, folder):
        '''
        Helper method that looks at all files in the given folder that end in the given suffix and returns their filenames

        The suffix might be ".yaml" to retrieve manifests, or even "_<version>.yaml" for versioned manifests
        '''
        matches                         = []
        if  _os.path.isdir(folder):
            matches                     = [filename for filename in _os.listdir(folder) if filename.endswith(".yaml")]

        return matches

    def archivePosting(self, parent_trace, posting_label_handle):
        '''
        Used after a posting Excel file has been processed. It moves the Excel file to a newly created folder dedicated 
        to this posting event and returns a PostingLabelHandle to identify the Excel file in this newly
        created archival folder.       
        '''
        submitted_posting_path              = self._getPostingFullPath(parent_trace, posting_label_handle)
        submitted_posting_coords            = posting_label_handle.filing_coords
        filename                            = posting_label_handle.excel_filename

        env_config                          = self.current_environment(parent_trace).config(parent_trace)
        archival_folder_coords              = ArchiveFilingCoordinates(
                                                            parent_trace            = parent_trace, 
                                                            posting_label_handle    = posting_label_handle,
                                                            use_timestamps          = env_config.use_timestamps)

        def _relativize_if_possible(parent_trace, parent_dir, path):
            '''
            Returns a boolean status and if boolean is true, a decomposition of the submitted path into root
            and relative path
            '''
            check   =   PathUtils().is_parent(  parent_trace            = parent_trace,
                                                parent_dir              = parent_dir, 
                                                path                    = path)
            if not check:
                return False, None, None
            relative_path, filename     = PathUtils().relativize(   parent_trace    = parent_trace, 
                                                                    root_dir        = parent_dir, 
                                                                    full_path       = path)
            root_path         = parent_dir
            relative_path     = relative_path + "/" + filename
            return True, root_path, relative_path

        def _copy(src, dst_root, dst_coords, dst_filename):
            path_tokens                     = dst_coords.path_tokens(parent_trace)
            folder                          = dst_root              + "/" + "/".join(path_tokens)
            relative_path                   = '/'.join(path_tokens) + "/" + dst_filename
            dst                             = folder                + "/" + dst_filename
            PathUtils().create_path_if_needed(parent_trace, folder)
            _shutil.copy2(  src     = src,
                            dst     = dst)
            self._remember_posting_write(parent_trace, relative_path)            

        def _conditional_move(src_root, src_relative_path, remove_src, dst_root, dst_coords, dst_filename):
            path_tokens                     = dst_coords.path_tokens(parent_trace)
            folder                          = dst_root              + "/" + "/".join(path_tokens)
            relative_path                   = '/'.join(path_tokens) + "/" + dst_filename
            dst                             = folder                + "/" + dst_filename
            src                             = src_root              + "/" + src_relative_path
            PathUtils().create_path_if_needed(parent_trace, folder)
            if _os.path.exists(src) and _os.path.exists(dst) and _os.path.samefile(src, dst):
                # Do nothing - just return
                return
            elif remove_src:
                _os.rename( src         = src, 
                            dst         = dst)
                self._remember_posting_write(parent_trace, relative_path)  
                if self.getPostingsURL(parent_trace) == src_root:
                    self._remember_posting_delete(parent_trace, src_relative_path)
                elif self.getClientURL(parent_trace) == src_root:
                    self._remember_clientURL_delete(parent_trace, src_relative_path)
            else:
                _shutil.copy2(  src     = src,
                                dst     = dst)
                self._remember_posting_write(parent_trace, relative_path)

        check, submitted_root_path, submitted_relative_path         = _relativize_if_possible(
                                                                        parent_trace    = parent_trace,
                                                                        parent_dir      = self.getPostingsURL(parent_trace),
                                                                        path            = submitted_posting_path)
        if not check:
            check, submitted_root_path, submitted_relative_path     = _relativize_if_possible(
                                                                        parent_trace    = parent_trace,
                                                                        parent_dir      = self.getClientURL(parent_trace),
                                                                        path            = submitted_posting_path)
        if not check:
            submitted_root_path, submitted_relative_path            = _os.path.split(submitted_posting_path
            )
            
        # Archive
        _copy(  src                         = submitted_posting_path,
                dst_root                    = self.getPostingsURL(parent_trace), 
                dst_coords                  = archival_folder_coords, 
                dst_filename                = filename)

        # Save posting in official area with official name, possibly removing it from the source
        _conditional_move(  src_root                    = submitted_root_path,
                            src_relative_path           = submitted_relative_path,
                            remove_src                  = check,
                            dst_root                    = self.getPostingsURL(parent_trace), 
                            dst_coords                  = submitted_posting_coords, 
                            dst_filename                = posting_label_handle.getPostingAPI(parent_trace) + ".xlsx")        

        archival_handle     = PostingLabelHandle(       parent_trace        = parent_trace,
                                                        posting_api         = posting_label_handle.posting_api,
                                                        filing_coords       = archival_folder_coords,
                                                        excel_filename      = filename, 
                                                        excel_sheet         = posting_label_handle.excel_sheet, 
                                                        excel_range         = posting_label_handle.excel_range)  

        # Copy archival logs to the clientURL area
        self.resetClientArea(parent_trace = parent_trace, coords = archival_folder_coords)      
        
        return archival_handle

    def logPostEvent(self, parent_trace, controller_response):
        '''
        Used to record in the store information about a posting event that has been completed.
        '''
        archival_list                       = controller_response.archivedPostings()
        if len(archival_list) != 1:
            raise ApodeixiError(parent_trace, "Can't log post event because it lacks a unique archival record",
                                                    data = {"Nb of archivals for this posting": str(len(archival_list))})
        original_handle, archival_handle    = archival_list[0]

        archival_path                       = self._getPostingFullPath(parent_trace, archival_handle)
        log_folder                          = _os.path.dirname(archival_path)

        #env_config                          = self.current_environment(parent_trace).config(parent_trace)

        log_txt                             = ""
        for handle in controller_response.createdManifests():
            log_txt                         += "\nCREATED MANIFEST:        " + handle.display(parent_trace) + "\n"

        for handle in controller_response.updatedManifests():
            log_txt                         += "\nUPDATED MANIFEST:        " + handle.display(parent_trace) + "\n"

        for handle in controller_response.deletedManifests():
            log_txt                         += "\nDELETED MANIFEST:        " + handle.display(parent_trace) + "\n"

        for handle1, handle2 in controller_response.archivedPostings():
            log_txt                         += "\nARCHIVED POSTING FROM:   " + handle1.display(parent_trace)
            log_txt                         += "\n             TO:         " + handle2.display(parent_trace) + "\n"

        for form_request in controller_response.optionalForms():
            log_txt                         += "\nPUBLISHED OPTIONAL FORM: " + form_request.display(parent_trace) + "\n"

        for form_request in controller_response.mandatoryForms():
            log_txt                         += "\nPUBLISHED MANDATORY FORM: " + form_request.display(parent_trace) + "\n"


        LOG_FILENAME                        = "POST_EVENT_LOG.txt"
        try:
            with open(log_folder + "/" + LOG_FILENAME, 'w') as file:
                file.write(str(log_txt))
                relative_path               = _os.path.dirname(archival_handle.getRelativePath(parent_trace)) \
                                                                    + "/" + LOG_FILENAME
                self._remember_posting_write(parent_trace, relative_path)

        except Exception as ex:
            raise ApodeixiError(parent_trace, "Encountered problem saving log for post event",
                                    data = {"Exception found": str(ex)})

        # Copy archival logs to the clientURL area
        self.resetClientArea(parent_trace = parent_trace, coords = archival_handle.filing_coords) 

        return log_txt

    def _get_log_folder(self, parent_trace, form_request):
        '''
        Helper method to get the log folder corresponding to a FormRequest
        '''
        env_config                          = self.current_environment(parent_trace).config(parent_trace)
        log_coords                          = LogFilingCoordinates(
                                                            parent_trace            = parent_trace, 
                                                            form_request            = form_request, 
                                                            use_timestamps          = env_config.use_timestamps)

        log_folder                          = self.getPostingsURL(parent_trace) \
                                                +  '/' + '/'.join(log_coords.path_tokens(parent_trace))

        PathUtils().create_path_if_needed(parent_trace, log_folder)
        return log_folder, log_coords

    def logFormRequestEvent(self, parent_trace, form_request, controller_response):
        '''
        Used to record in the store information about a request form event that has been completed.
        '''
        log_folder, log_coords              = self._get_log_folder(parent_trace, form_request)

        env_config                          = self.current_environment(parent_trace).config(parent_trace)

        log_txt                             = ""
        for handle in controller_response.createdForms():
            log_txt                         += "\nCREATED FORM:        " + handle.display(parent_trace) + "\n"
            unmasked_client_URL             = str(controller_response.clientURL(parent_trace))
            masked_client_URL               = controller_response.applyMask(parent_trace, unmasked_client_URL)
            log_txt                         += "clientURL =          " + masked_client_URL + "\n"

        LOG_FILENAME                        = "FORM_REQUEST_EVENT_LOG.txt"
        try:
            with open(log_folder + "/" + LOG_FILENAME, 'a') as file:
                file.write(str(log_txt))
                relative_path               = '/'.join(log_coords.path_tokens(parent_trace)) + "/" + LOG_FILENAME
                self._remember_posting_write(parent_trace, relative_path)
                

        except Exception as ex:
            raise ApodeixiError(parent_trace, "Encountered problem saving log for form request event",
                                    data = {"Exception found": str(ex)})

        # Copy archival logs to the clientURL area
        self.resetClientArea(parent_trace = parent_trace, coords = log_coords) 

        return log_txt

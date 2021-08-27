import sys                                          as _sys
import datetime                                     as _datetime
from importlib                                      import import_module

from apodeixi.knowledge_base.knowledge_base         import KnowledgeBase
from apodeixi.knowledge_base.knowledge_base_store   import KnowledgeBaseStore
from apodeixi.knowledge_base.kb_environment         import KB_Environment_Config
from apodeixi.knowledge_base.shutil_kb_store        import Shutil_KBStore_Impl

from apodeixi.util.apodeixi_config                  import ApodeixiConfig
from apodeixi.util.a6i_error                        import FunctionalTrace, ApodeixiError

from apodeixi.cli.error_reporting                   import CLI_ErrorReporting

class KB_Session_Initializer():
    '''
    Helper class to suport extensibility.

    Purpose:
    Apodeixi extensions may want to customize their own classes for the KnowledgeBase, KnowledgeBaseStore, etc.,
    by deriving the Apodeixi classes and have the CLI make use of them instead of the Apodexi default classes.

    Since the CLI accesses such objects through the KB_Session class, which the CLI has hard-coded knowledge about,
    the pattern for replacing the type of KnowledgeBase* classes used by the CLI is:

    * These classes are initialized outside the KB_Session, by an initializer class that chooses which concrete
      classes to use for KnowledgeBase* objects and sets them inside a KB_Session instance
    * The initializer class is looked up in the ApodeixiConfig object, which each Apodeixi implementation can
      set at will. For example, Apodeixi extensions could be configured to use a custom initializer class that chooses
      extension-specific KnowledgeBase* classes
    '''
    def __init__(self):
        return
    
    def initialize(self, parent_trace, kb_session):
        '''
        Sets these attributes of kb_session:
        * kb_session.a6i_config
        * kb_session.kb_rootdir
        * kb_session.clientURL
        * kb_session.store
        * kb_session.kb

        This method is intended to be called from within the KB_Session constructor.

        @param kb_session A KB_Session instance that needs to be initialized
        '''
        my_trace                            = parent_trace.doing("Loading Apodeixi configuration",
                                                                    origination     = {'signaled_from': __file__})
        kb_session.a6i_config               = ApodeixiConfig(my_trace)

        my_trace                            = parent_trace.doing("Initializing file-based stack",
                                                                    origination     = {'signaled_from': __file__})
        kb_session.kb_rootdir               = kb_session.a6i_config.get_KB_RootFolder(my_trace)
        kb_session.clientURL                = kb_session.a6i_config.get_ExternalCollaborationFolder(my_trace) 

        store_impl                          = Shutil_KBStore_Impl(  parent_trace    = my_trace,
                                                                    kb_rootdir      = kb_session.kb_rootdir, 
                                                                    clientURL       = kb_session.clientURL)
        kb_session.store                    = KnowledgeBaseStore(my_trace, store_impl)
        my_trace                            = parent_trace.doing("Starting KnowledgeBase")
        kb_session.kb                       = KnowledgeBase(my_trace, kb_session.store, a6i_config=kb_session.a6i_config)

class KB_Session():
    '''
    Represents runtime state and configuration pertaining to the running of the KnowledgeBase during a
    CLI "session". The time boundary of such a "session" is typically all the CLI commands that are performed
    within a single Python process.

    In practice that means a single CLI command, since each CLI command typically leads to the spawning of a
    dedicated Python process to handle such command.

    In future versions, that behavior might change if an "Apodeixi daemon" is introduced, to which a CLI command
    might latch if a daemon is running, or create the daemon if it is not running. In such a future state then
    the duration of a KB_Session would be the lifetime of such daemon.
    '''
    def __init__(self):
        try:
            func_trace                          = FunctionalTrace(      parent_trace    = None, 
                                                                        path_mask       = None) 
            root_trace                          = func_trace.doing("Initializing KB_Session for Apodeixi CLI",
                                                                        origination     = {'signaled_from': __file__})

            # The initializer will set self.a6i_config. But in a sort of chicken-and egg situation, we find
            # ourselves forced to load a "temporary" config object to figure out the class name of the initializer ot use.
            # This "temporary" config might not be the "right class" if the initializer
            # is not the default Apodeixi class (for example, if an Apodeixi extension is using a derived initializer
            # class), but at least the "temporary" config will let us get the initializer class.
            #
            temporary_config                    = ApodeixiConfig(root_trace)

            initializer_class_name              = temporary_config.get_CLI_InitializerClassname(root_trace)

            try:
                module_path, class_name         = initializer_class_name.rsplit('.', 1)
                module                          = import_module(module_path)
                initializer_class               = getattr(module, class_name)
                initializer                     = initializer_class()
            except (ImportError, AttributeError) as ex:
                raise ApodeixiError(root_trace, "Unable to construct class '" + str(initializer_class_name) + "'",
                                            data = {"error": ex.msg})

            initializer.initialize(root_trace, self)
            
            # This will look like '210703.102746', meaning the 3rd of July of 2021 at 10:27 am (and 46 sec).
            # Intention is this timestamp as an "identifier" of this KnowledgeBase session, by using as prefix
            # to folders or files (e.g., sandboxes, logs) created during the existence of this KnowledgeBase session
            dt                                  = _datetime.datetime.today()
            self.timestamp                      = dt.strftime("%y%m%d.%H%M%S")

            self.error_count                    = 1 # Increments each time we log an error

        except ApodeixiError as ex:
            error_msg                           = CLI_ErrorReporting(None).report_a6i_error( 
                                                                            parent_trace                = root_trace, 
                                                                            a6i_error                   = ex)
            # GOTCHA
            #       Use print, not click.echo or click exception because they don't correctly display styling
            #       (colors, underlines, etc.). So use vanilla Python print and then exit
            print(error_msg)
            _sys.exit()
        except Exception as ex:
            print("Unrecoverable error: " + str(ex))
            _sys.exit()


    def provisionSandbox(self, parent_trace):
        '''
        Provisions a sandbox for running KnowledgeBase requests. Typical use case is for dry-runs, where the user
        wants to see what a request would trigger, without actually changing the official KnowledgeBaseStore.
        In that case, calling this method in advance would create all writes to be only in a sandbox, so
        a full processing is done but has the feel of a "dry run" since no writes happen to the official
        KnowledgeBase store.

        Sandboxes are materialized as a KnowledgbeBaseStores environment. In terms of environments, this method
        creates a new environment as a sub-environment of the KnowledgeBaseStore's current environment, and activates it.
        The new environment is configured to have a dedicated, isolated collaboration area that is initially
        empty.

        This method returns the name of the sandbox being created (i.e., a string corresponding to the
        folder under the KnowledgeBaseStore's environments area)

        The new environment is named with a timestamp prefix that is hopefully unique. 
        For example,"210703.102746_sandbox" for a sandbox requested on the 3rd of July of 2021 at 10:27 am (and 46 sec). 
        The timestamp is as of the moment this method is invoked. Should it happen that two clients attempt to
        create a sandbox at exactly the same time, then at most one of them will succeed, and the other will have
        to re-try (which will change the timestamp, since the retry is at a later time).

        The new environment as a "read_misses_policy" equal to KB_Environment_Config.FAILOVER_ALL_READS_TO_PARENT,
        which means that any attempts to load manifests or postings will failover to the parent environment (i.e.,
        outside the sandbox) if the data is not already in the sandbox. 
        This turns the sandbox into a "virtual copy" of the parent environment: it feels like it has all the
        same data as the parent, but any writes are not made to the parent.
        '''
        # This will look like '210703.102746_sandbox' for a sandbox requested on the 3rd of July of 2021 at 10:27 am 
        # (and 46 sec). 
        # Intention is for this folder name to be unique across all sandboxes
        sandbox_name                = self.timestamp + "_sandbox"
        
        my_trace                    = parent_trace.doing("Creating an isolated environment for integration test")
        env_config                  = KB_Environment_Config(
                                            parent_trace        = my_trace, 
                                            read_misses_policy  = KB_Environment_Config.FAILOVER_ALL_READS_TO_PARENT,
                                            use_timestamps      = True,
                                            path_mask           = None)

        self.store.current_environment(my_trace).addSubEnvironment( parent_trace        = my_trace, 
                                                                    name                = sandbox_name, 
                                                                    env_config          = env_config,
                                                                    isolate_collab_area = True)
        self.store.activate(parent_trace = my_trace, environment_name = sandbox_name)

        return sandbox_name


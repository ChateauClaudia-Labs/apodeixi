import os                                               as _os
#import shutil                                           as _shutil
#import yaml                                             as _yaml

from apodeixi.knowledge_base.isolation_kb_store         import Isolation_KBStore_Impl
from apodeixi.util.a6i_error                            import ApodeixiError
#from apodeixi.util.path_utils                           import PathUtils

class GIT_KBStore_Impl(Isolation_KBStore_Impl):
    '''
    GIT-based implementation of the KnowledgeBaseStore. The entire knowledge base is held in a GIT project
    under a root folder with separate subfolders for postings, manifests, and possibly other derived data.

    Multi-User Configurations and SharePoint Interaction
    ====================================================

    In a multi-user configuration, it is expected that each GIT_KBStore_Impl "instance" corresponds
    to just one user, is local, and that each user has a different machine, so access is always single-threaded.
    These GIT_KBStore_Impl "instances" synchronize through standard GIT mechanisms (such as git pull
    and git push) that happen behind the scenes, not visible to the user.

    End users are not expected, or encouraged, to use GIT commands to interact with a GIT_KBStore_Impl.
    Instead they should use the KnowledgeBase's API, which will will lead to GIT commands being invoked behind the
    scenes.

    Specifically, end users are expected to invoke APIs such as post, generateForm, etc. which transmit
    Excel files to/from the KnowledgeBase's store and the user's chosen working area. The user's "working area"
    is a folder structure that mirrors a portion of the GIT_KBStore_Impl's folder structure, but is
    external to it (i.e., it is not in the GIT working tree). This prevent conflicts in situations where
    users collaborate with shared drive technologies such as SharePoint. In this scenario, there are two
    distributed file synchronization technologies simultaneously in play (GIT and SharePoint), so this is what is
    expected to avoid conflicts between them:

    1.  Each end-user with access to the KnowledgeBase API will have a local install of GIT with a GIT project
        dedicated to an instance of the GIT_KBStore_Impl.
    2.  Typically, end-users GIT_KBStore_Impl repos would have a common remote (such as in GitHub),
        and end-users' repos stay in sync as follows:
        a.  Each end user is allocated a user-specific branch in the common remote
        b.  The local install of the GIT_KBStore_Impl uses that user-specific branch for all pull/push
            communication with the remote, which is done behind the scenes by the KnowledgeBase API. So normally
            end users don't need to push/pull to the remote, or be aware on a daily basis that GIT is running locally.
        c.  The only GIT-awareness for users is that from time to time, they need to go to the remote (e.g., GitHub)
            and submit a pull request to integrate their local branch's data with the remote's official branch.
            The remote's "official branch" is the branch from which "official reports" are produced from the 
            KnowledgeBase (both periodic reports such as end-of-month or end-of-quarter, or ad-hoc queries from
            other users who don't contribute data but consume insights from the KnowledgeBase).
        d.  The "pull review" is expected to be a gate where technical authorities ensure that the user requesting
            a pull request has satisfactorily ensured correctness of the content being submitted for integration
            into the "official" branch.

    In contrast to the folders synchronized by GIT, this what happens in SharePoint:

    3.  Users who collaborate on the construction of data may share a common SharePoint area. This area is 
        external to the GIT project underying the GIT_KBStore_Impl.
    4.  Not all SharePoint users are necessarily users of the KnowledgeBase API. For example, often multiple
        heads of development, product managers and architect collaborate on the content of an Excel spreadsheet
        that will eventually be posted to the KnowledgeBase, but maybe only one of them (e.g., the chief
        architect) might have access ot the KnowledgeBase API.
    5.  When an end user *such as the Chief Archited) is ready, the end user can use the KnowledgeBase API 
        to post a Sharepoint-residing excel spreadsheet into the KnowledgeBase.
        a.  For convenience, this can be done using a CLI command where the working folder is the relevant SharePoint 
            folder, so the end-user retains the illustion of only working in SharePoint, unaware that there is
            also a GIT repo in his/her machine.
        b.  The API will cause the excel spreadsheet to be added to the GIT project in a secure, transactional
            way, and if the post is successful it will propagate the change to the remote.
        c.  To give visibility to the user, posting APIs might move the prior posting to an archive folder in
            GIT, and mirror that in SharePoint. Therefore, the user might see the Excel file in SharePoint
            "disappear" and move to an archive folder. This gives clarity to the user that it no longer is a
            spreadsheet "waiting to be posted".
    6.  Similar semantics apply to other KnowledgeBase APIs where the user needs to get data from the KnowledgeBase,
        such as the requestForm API. The KnowledgeBase API will generate the Excel spreadsheet and place it into
        a folder configured by the KnowledgeBase's configuration, typically a folder in the user's working area
        (in SharePoint). In that example, the user can then collaborate with others to complete the form, and
        when ready can submit it to the KnoweledgeBase via the post API, as above.
    7.  Thus, the SharePoint folder structure would generally be a "soft (next version) mirror" of the part of the
        GIT_KBStore_Impl that contains Excel spreadsheets. SharePoint is where users "are working on 
        future updates to the content", and the KnowledgeBase has the previously posted content.

    Apodeixi vs GIT domain models: environments vs branches and clones
    ==================================================================

    The interplay between GIT semantics and the KnowledgeBase semantics are as follows:

    1.  The GIT_KBStore_Impl has a notion of "environments", organized in a tree structure (every environment
        has a parent environment, except the base "root" environment)
    2.  Each "environment" is a folder with a structure, and can be thought of as a "partial mirror" of the logical
        KnowledgeBase.
    3.  These "environments" are used in multiple use cases, such as to ensure atomicity (e.g., an environment
        is used as a transactional cache), regression testing (e.g., an environment isolates a "copy" of a
        test knowledge base specific to a test case), or reporting (e.g., two environments are snapshots at different
        points in time).
    4.  In the case of the GIT_KBStore_Impl, GIT semantics interplay with the notion of "environment" as follows:
        a.  Each environment is a clone of its parent environment's GIT project, with the parent as the GIT "remote"
        b.  The base environment is a clone of the remote GIT project used to synchronize all users (e.g., in GitHub), 
            in multi-user situations.
        c.  The GIT_KBStore_Impl knows only about two types of GIT branches:
            i.  The user-specific branch used to integrate with the remote (in multi-user situations)
            ii. Branches used for baselining, which typically are also in the remote.
        d.  Each "writable environment" is a GIT working tree and at all times must be set to the user-specific branch.
        e.  The KnowledgeBase API will transparently synchronize each "writable environment" with its "parent" in response
            to API writes, via GIT push/pull mechanisms.
        f.  For API methods involving the generation of reports from baselines, the code will retrieve data
            from the baseline branches of the GIT project. For this, transient "read environments" may be used by the API
            (the API would create and delete them when no longer needed).
    5.  Normally, each KnowledgeBase API call is "atomic" - it may cause multiple environments to be created throughout
        the call, but at the end of the call they would be deleted. Only exceptins are:
        a.  When the API is invoked with certain settings, asking for the intermediate environments to remain (as for
            debugging, verbose dry-runs, or regression testing, for example) 
        b.  When the KnowledgeBase has a bug and didn't clean up after itself as it should.

    @param kb_rootdir A string, corresponding to the absolute path to a GIT project in the local machine
                            corresponding to the KnowledgeBase.
    @param clientURL A string, corresponding to the absolute path to a root folder in a collaboration
                            drive system (such as SharePoint) in which end-users will collaborate to create
                            the Excel spreadsheets that will be eventually posted to the KnowledgeBase. This
                            shared drive is also the location to which the KnowledgeBase will save
                            generated forms or reports requested by end-users. This is a "root folder" in that
                            the structure below will be assumed to follow the filing structure of the
                            KnowledgeBase for postings.
    '''
    def __init__(self, parent_trace, kb_rootdir, clientURL, remote):

        super().__init__(parent_trace, kb_rootdir, clientURL)

        # TODO - Initialize a git project, possibly making it point to a remote. Tricky thing is what to do
        #       about the separate folders for postings and manifests - need a higher level folder for the
        #       git repo, or 2 git repos, or find out how to do a git repo with a section of its
        #       working tree on a separate area (dynamic link??)
        #       
        raise ApodeixiError(parent_trace, "__init__ - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def beginTransaction(self, parent_trace):
        '''
        Starts an isolation state in which all subsequent I/O is done in an isolation area
        dedicated to this transaction, and not applied back to the store's persistent area until the
        transaction is committed..
        '''
        # TODO - in new environment set up a git project with remote origin being the 
        #       parent environment's git project. And do a git pull for good measure
        #
        # NOTE: the super().beginTransaction will call current_env.addSubEnvironment, and that should
        #       probably the the only way to add sub environments in the GIT KB store - i.e., only
        # as a result of a beginTransaction. Emphasis is here not to encourage client code to casually
        # create sub-environments by bypassing the KB's APIs and calling an_env.addSubEnvironment directly,
        # since the resulting sub_env would not have GIT awareness. 
        
        raise ApodeixiError(parent_trace, "beginTransaction - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})
        return super().beginTransaction(parent_trace)

    def commitTransaction(self, parent_trace):
        '''
        Finalizes a transaction previously started by beginTransaction, by cascading any I/O previously done in
        the transaction's isolation area to the store's persistent area.
        '''
        env, parent_env             = self._validate_transaction_end_of_life(parent_trace)

        src_postings_root           = env.postingsURL(parent_trace)
        dst_postings_root           = parent_env.postingsURL(parent_trace)

        src_manifests_root          = env.manifestsURL(parent_trace)
        dst_manifests_root           = parent_env.manifestsURL(parent_trace)

        ending_env                  = self._transactions_stack.pop()
        events                      = self._transaction_events_dict.pop(ending_env.name(parent_trace))

        # TODO - a git push from env to parent_env.
        #               
        raise ApodeixiError(parent_trace, "commitTransaction - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

        # Now remove the environment of the transaction we just committed
        self.removeEnvironment(parent_trace, env.name(parent_trace)) 
        self.activate(parent_trace, parent_env.name(parent_trace))    

    def commitTransaction(self, parent_trace):
        '''
        Finalizes a transaction previously started by beginTransaction, by cascading any I/O previously done in
        the transaction's isolation area to the store's persistent area.
        '''
        env, parent_env             = self._validate_transaction_end_of_life(parent_trace)

        src_postings_root           = env.postingsURL(parent_trace)
        dst_postings_root           = parent_env.postingsURL(parent_trace)

        src_manifests_root          = env.manifestsURL(parent_trace)
        dst_manifests_root           = parent_env.manifestsURL(parent_trace)

        ending_env                  = self._transactions_stack.pop()
        events                      = self._transaction_events_dict.pop(ending_env.name(parent_trace))

        # TODO - a git push from env to parent_env.
        # TODO - GOTCHA!!!! When going up the parent chain, and get to commit to the parent who originated
        #           the first commit, we may need to do an additional push to the remote at that point
        #               
        raise ApodeixiError(parent_trace, "commitTransaction - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

        # Now remove the environment of the transaction we just committed
        self.removeEnvironment(parent_trace, env.name(parent_trace)) 
        self.activate(parent_trace, parent_env.name(parent_trace))

    def baseline(self, parent_trace):
        '''
        Creates a baseline of the Knowledge Store. For example, and end-of-month tag to drive consistent
        computation of data based on a consistent snapshot of data in the store (i.e., data as of the end of the month)
        '''

        # TODO - Work in GIT to create a tag. Tricky things are:
        #           1) May need to do this across all environments, so in multiple GIT project
        #           2) 
        raise ApodeixiError(parent_trace, "baseline - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})
    def activateBaseline(self, parent_trace, baseline_name):
        '''
        Activates a "branch" as of the given baseline name
        '''
        # TODO - Work in GIT to do this. Tricky things are:
        #           1) Is this modeled as a GIT branch? If so, does the GIT store require some generalized notion of
        #               "environment" (that would still be a separate folder structure but it can either be
        #               just a branch of the parent or might sometimes be a clone of the parent pointing to the
        #               parent as a remote? If so we need a "GIT_KB_Environment.py" class
        #           2) May need to do this across all environments, so in multiple GIT project?
        #           3) What are implications for the parent class's methods to activate/de-activate environments?
        #               Are they "moot" if the GIT KB only things in terms of "baselines (GIT branch)" or 
        #               "transactional caches (GIT clone)",
        #               and every environment is one or the other?
        raise ApodeixiError(parent_trace, "activateBaseline - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__}) 

    def diff(self, parent_trace, handle, baseline1_name, baseline2_name):
        '''
        Produces and returns the difference in the KnowledgeBase's datum identified by "handle"
        across the two given baselines
        '''
        # TODO - Work in GIT to do this. Tricky things are:
        #           1) What is the data structure in which to express the diff? Want it easy to visualize
        #               in reports and in regression test output
        #           2) Ensure that there is no ambiguity in the interplay between the baseline and
        #               environment concepts: i.e., a baseline must determine a unique environment, so that
        #               a for a given baseline the datum does not look different if this method is
        #               called twice, where the caller is in a different "current environment" as of the moment
        #               the call is made.
        raise ApodeixiError(parent_trace, "diff - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__}) 

    def activate(self, parent_trace, environment_name):
        '''
        Switches the store's current environment to be the one identified by the `environment_name`, unless
        no such environment exists in which case it raises an ApodeixiError
        '''
        super().activate(parent_trace, environment_name)

        # TODO - Confirm there is nothing to do besides call to super(), given that activated
        #           environment's GIT project is modeled as a separate (downstream) GIT project
        #           from parent's (as opposed to a branch, which would require a git checkout to activate)
        raise ApodeixiError(parent_trace, "activate - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def deactivate(self, parent_trace):
        '''
        Switches the store's current environment to be the base environment.
        '''
        super().deactivate(parent_trace)


        # TODO - Confirm there is nothing to do besides call to super(), given that activated
        #           environment's GIT project is modeled as a separate (downstream) GIT project
        #           from parent's (as opposed to a branch, which would require a git checkout master to deactivate)
        raise ApodeixiError(parent_trace, "deactivate - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

    def removeEnvironment(self, parent_trace, name):
        '''
        Removes the environment with the given name, if one exists, in which case returns 0.
        If no such environment exists then it returns -1.

        In the process it also removes any child environment, recursively down.
        '''

        
        # TODO - Confirm there is nothing to do besides call to super(), given that 
        #           environment's GIT project is modeled as a separate (downstream) GIT project
        #           from parent's (as opposed to a branch, which would require a git checkout master to deactivate)
        raise ApodeixiError(parent_trace, "removeEnvironment - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

        return super().removeEnvironment(parent_trace, name)

    def loadPostingLabel(self, parent_trace, posting_label_handle):
        '''
        Loads and returns a DataFrame based on the `posting_label_handle` provided
        '''
        # TODO - Do a git pull before loading, to get parent environment's data.
        #           Tricky thing is that this may be needed recursively up the parent's chain...
        raise ApodeixiError(parent_trace, "loadPostingLabel - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

        label_df                    = super().loadPostingLabel(parent_trace, posting_label_handle)          

        return label_df

    def loadPostingData(self, parent_trace, data_handle, config):
        '''
        Loads and returns a DataFrame based on the `posting_data_handle` provided

        @param config PostingConfig
        '''

        # TODO - Do a git pull before loading, to get parent environment's data.
        #           Tricky thing is that this may be needed recursively up the parent's chain...
        raise ApodeixiError(parent_trace, "loadPostingData - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})
        df                      = super().loadPostingData(parent_trace, data_handle, config)

        return df

    def searchPostings(self, parent_trace, posting_api, filing_coordinates_filter=None):
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
        '''

        
        # TODO - Do a git pull before loading, to get parent environment's data.
        #           Tricky thing is that this may be needed recursively up the parent's chain...
        # if self._failover_reads_to_parent(parent_trace):
        raise ApodeixiError(parent_trace, "searchPostings - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})
        scanned_handles             = super().searchPostings(
                                                parent_trace                = parent_trace, 
                                                posting_api                 = posting_api, 
                                                filing_coordinates_filter   = filing_coordinates_filter)
        return scanned_handles

    def persistManifest(self, parent_trace, manifest_dict):
        '''
        Persists manifest_dict as a yaml object and returns a ManifestHandle that uniquely identifies it.
        '''
        # TODO - Do NOT do pull/push, just save and commit, so changes are only local
        #           Later when commit happens we worry about merge to parent environment...
        raise ApodeixiError(parent_trace, "persistManifest - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})
        handle              = super().persistManifest(parent_trace, manifest_dict)
        return handle

    def retrieveManifest(self, parent_trace, manifest_handle):
        '''
        Returns a dict and a string.
        
        The dict represents the unique manifest in the store that is identified by the `manifest handle`.
        
        The string represents the full pathname for the manifest.

        If none exists, it returns (None, None). That said, before giving up and returning (None, None), 
        this method will attempt to find the manifest in the parent environment if that is what is stipulated
        in the current environment's configuration

        @param manifest_handle A ManifestHandle instance that uniquely identifies the manifest we seek to retrieve.
        '''
        # TODO - Do a git pull before loading, to get parent environment's data.
        #           Tricky thing is that this may be needed recursively up the parent's chain...
        # if self._failover_reads_to_parent(parent_trace):
        raise ApodeixiError(parent_trace, "retrieveManifest - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

        manifest, manifest_path         = super().retrieveManifest(parent_trace, manifest_handle)


        return manifest, manifest_path

    def archivePosting(self, parent_trace, posting_label_handle):
        '''
        Used after a posting Excel file has been processed. It moves the Excel file to a newly created folder dedicated 
        to this posting event and returns a PostingLabelHandle to identify the Excel file in this newly
        created archival folder.       
        '''
        # TODO - Do NOT do pull/push, just save and commit, so changes are only local
        #           Later when commit happens we worry about merge to parent environment...
        raise ApodeixiError(parent_trace, "persistManifest - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

        archival_handle                     = super().archivePosting(parent_trace, posting_label_handle)
        
        return archival_handle

    def logPostEvent(self, parent_trace, controller_response):
        '''
        Used to record in the store information about a posting event that has been completed.
        '''
        # TODO - Do NOT do pull/push, just save and commit, so changes are only local
        #           Later when commit happens we worry about merge to parent environment...
        raise ApodeixiError(parent_trace, "logPostEvent - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})

        log_txt                             = super().logPostEvent(parent_trace, controller_response)

        return log_txt

    def logFormRequestEvent(self, parent_trace, form_request, controller_response):
        '''
        Used to record in the store information about a request form event that has been completed.
        '''
        # TODO - Do NOT do pull/push, just save and commit, so changes are only local
        #           Later when commit happens we worry about merge to parent environment...
        raise ApodeixiError(parent_trace, "logPostEvent - IMPLEMENTATION IS STILL TODO",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                                'signaled_from': __file__})


        log_txt                             = super().logFormRequestEvent(parent_trace, form_request, controller_response)
        return log_txt

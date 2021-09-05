#import os                                           as _os
#import yaml                                         as _yaml

#from apodeixi.knowledge_base.knowledge_base_util    import ManifestHandle, PostingLabelHandle
#from apodeixi.util.path_utils                       import PathUtils
#from apodeixi.util.a6i_error                        import ApodeixiError


class KnowledgeBaseStore():
    '''
    Class used to codify an API of the dependencies that theKnowledgeBase depends on from a "store" in which the
    KnowledgeBase can persist and retrieve manifests, postings, and any other persistent Apodeixi domain object.

    The physical mechanisms are delegated to an implementation object, and different implementation can be
    transparently swapped.

    Thus, the methods in this class are really an abstracted API for the services needed.
    These services include:

    * Persistence of postings, manifests
    * Support to archive logs and payloads involved in KnowledgeBase API operations, such as a posting
    * Transactional support
    * Sandbox support via the notion of "environment". These can be hierarchical, as the collection of all
      environments are a logical tree, with the root being the "base" environment that always exists, and the
      rest are added or removed by the caller via APIs. KnowledgeBase operations are applied only to the
      environment that is "active", with exactly 1 environment being active at all times.

    @impl A class that implements the methods of the KnowledgeBaseStore. This delegation is used as a means to
            be able to swap different implementations of the store's functionality, without changing the
            code that calls the store.
    '''
    def __init__(self, parent_trace, impl):
        self._impl          = impl
        return

    def beginTransaction(self, parent_trace):
        '''
        Starts an isolation state in which all subsequent I/O is done in an isolation area
        dedicated to this transaction, and not applied back to the store's persistent area until the
        transaction is committed..
        '''
        return self._impl.beginTransaction(parent_trace)

    def commitTransaction(self, parent_trace):
        '''
        Finalizes a transaction previously started by beginTransaction, by cascading any I/O previously done in
        the transaction's isolation area to the store's persistent area.
        '''
        return self._impl.commitTransaction(parent_trace)
        
    def abortTransaction(self, parent_trace):
        '''
        Aborts a transaction previously started by beginTransaction, by deleting transaction's isolation area,
        effectively ignoring any I/O previously done during the transaction's lifetime, and leaving the
        KnowledgeBaseStore in a state such that any immediately following I/O operation would be done 
        directly to the store's persistent area.
        '''
        return self._impl.abortTransaction(parent_trace)

    def supported_apis(self, parent_trace):
        '''
        Returns a list of the posting APIs that this KnowledgeStore knows about.
        '''
        return self._impl.supported_apis(parent_trace)

    def getFilingClass(self, parent_trace, posting_api):
        '''
        Returns a class object, derived from FilingCoordinates, that this store uses to structure postings for 
        the giving posting api. Used to build the posting handle.
        '''
        return self._impl.getFilingClass(parent_trace, posting_api)

    def getPostingsURL(self, parent_trace):
        '''
        Returns a string that can be used to locate the postings area in the Knowledge Base store's current environment
        '''
        return self._impl.getPostingsURL(parent_trace)

    def getClientURL(self, parent_trace):
        '''
        Returns a string that can be used to locate the area (quite possibly external to the KnowledgeBase store)
        where end users preare manifests they later post, and into which users expecte generated forms and reports
        to go
        '''
        return self._impl.getClientURL(parent_trace)

    def resetClientArea(self, parent_trace, coords):
        '''
        This method "refreshes" the area under the clientURL identified by the given coordinates, so that it is
        identical the the area under the store's postingsURL corresponding to those coordinates.
        '''
        return self._impl.resetClientArea(parent_trace, coords)

    def current_environment(self, parent_trace):
        '''
        Returns the current environment that is active in the KnowledgeBaseStore
        '''
        return self._impl.current_environment(parent_trace)

    def parent_environment(self, parent_trace):
        '''
        In the logical tree of environments, returns the parent to the currently active environment.
        If the current environment is the root of the logical tree then it returns None.
        '''
        return self._impl.parent_environment(parent_trace)

    def base_environment(self, parent_trace):
        '''
        Returns the root of the logical tree of environments for the KnoledgeBase
        '''
        return self._impl.base_environment(parent_trace)

    def activate(self, parent_trace, environment_name):
        '''
        Switches the store's current environment to be the one identified by the `environment_name`, unless
        no such environment exists in which case it raises an ApodeixiError
        '''
        return self._impl.activate(parent_trace, environment_name)

    def deactivate(self, parent_trace):
        '''
        Switches the store's current environment to be the base environment.
        '''
        return self._impl.deactivate(parent_trace)
 
    def removeEnvironment(self, parent_trace, name):
        '''
        Removes the environment with the given name, if one exists, in which case returns 0.
        If no such environment exists then it returns -1.

        In the process it also removes any child environment, recursively down.
        ''' 
        return self._impl.removeEnvironment(parent_trace, name)

    def buildPostingHandle(self, parent_trace, excel_posting_path, sheet, excel_range):
        '''
        Returns an PostingLabelHandle for the posting label embedded within the Excel spreadsheet that resides in 
        the path provided.
        '''
        return self._impl.buildPostingHandle(parent_trace, excel_posting_path, sheet, excel_range)

    def getBlindFormRequest(self, parent_trace, relative_path, posting_api, namespace, subnamespace):
        '''
        Returns an FormRequest that can in turn be used to request a form (an Excel spreadsheet)
        that the end-user can use to make a posting for the create or update the manifests 
        in for the posting label embedded within the Excel spreadsheet that resides in 
        the path provided.

        The FormRequest returned is a "blind" form, in the sense that it does not specify the specific
        ManifestHandle objects that will populate the Excel template obtainable by submitting the FormRequest.
        The system will have to do a search within the KnowledgeBase store to find out which manifests, if any,
        already exist for the filing structure and posting API provided.
        If not exist the form will be creating them.
        If on the other hand such manifests already exist, then the Excel template will be generated as an
        update form that is pre-populated with those manifests' contents.

        @param relative_path: A string, representing the path below the end-user's collaboration area root 
                                (the store's clientURL) for which the form is requested. This determines the 
                                filing coordinates for the requested form.
                                Example: "journeys/Dec 2020/FusionOpus/Default"
        @param posting_api: A string, representing a posting API supported by the knowledge base.
                                Example: 'big-rocks.journeys.a6i'
        @param namespace A string, representing a namespace in the KnowledgeBase store's manifests are that
                        delimits the scope for searching for manfiests in scope of this FormRequest.
                        Example: "my-corp.production"
        @param subnamespace An optional string representing a slice of the namespace that further restricts
                        the manifest names to search. If set to None, not subspace is assumed.
                        Example: in the manifest name "modernization.default.dec-2020.fusionopus", the
                                token "modernization" is the subnamespace. The other tokens come from filing coordinates
                                for the posting from whence the manifest arose.
        '''
        return self._impl.getBlindFormRequest(parent_trace, relative_path, posting_api, namespace, subnamespace)

    def loadPostingLabel(self, parent_trace, posting_label_handle):
        '''
        Loads and returns a DataFrame based on the `posting_label_handle` provided
        '''
        return self._impl.loadPostingLabel(parent_trace, posting_label_handle)

    def loadPostingData(self, parent_trace, data_handle, config):
        '''
        Loads and returns a DataFrame based on the `posting_data_handle` provided

        @param config PostingConfig
        '''
        return self._impl.loadPostingData(parent_trace, data_handle, config)      
        
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
        return self._impl.searchPostings(parent_trace, posting_api, filing_coordinates_filter)

    def persistManifest(self, parent_trace, manifest_dict):
        '''
        It persists a manifest object whose content is given by `manifest_dict`, and returns a 
        ManifestHandle that uniquely identifies it.
        '''
        return self._impl.persistManifest(parent_trace, manifest_dict)

    def retrievePreviousManifest(self, parent_trace, manifest_dict):
        '''
        Given a manifest expressed as a dict with a certain version N, will retrieve the same manifest
        but with version N-1, and return is a dict.

        If no prior version exists, it returns None
        '''
        return self._impl.retrievePreviousManifest(parent_trace, manifest_dict)

    def retrieveManifest(self, parent_trace, manifest_handle):
        '''
        Returns a dict and a string.
        
        The dict represents the unique manifest in the store that is identified by the `manifest handle`.

        The string represents the full path for the manifest.

        If none exists, it returns None.

        @param manifest_handle A ManifestHandle instance that uniquely identifies the manifest we seek to retrieve.
        '''
        return self._impl.retrieveManifest(parent_trace, manifest_handle)

    def findLatestVersionManifest(self, parent_trace, manifest_api_name, namespace, name, kind):
        '''
        For a given manifest API, a manifest is logically identified by its name and kind properties within 
        a given namespace.
        However, there might be multiple versions of a logical manifest (versions are integers starting
        at 1, 2, 3, ..., with version increasing each time the manifest gets updated).

        This method returns a manifest and a string.
        
        The manifest is the most recent version of the manifest that is logically identified
        by the parameters.
        The 2nd returned value is the path to that manifest.

        If no such manifest exists in the KnowledgeBase store then the first returned object is None

        Example: for file-based stores, a manifest may be stored in a filename like:

            $KB_STORE/manifests/my-corp.production/modernization.default.dec-2020.fusionopus/big-rock.2.yaml

            In this example, 
                * the namespace is "my-corp.production"
                * the name is "modernization.default.dec-2020.fusionopus"
                * the kind is "big-rock"
                * the version is 2 (an int)
                * the manifest api is embedded within the YAML file, and is something like 
                  "delivery-planning.journeys.a6i.io/v1a"

        @param manifest_api_name A string representing the Apodeixi API defining the YAML schemas for the
                    manifest kinds subsumed under such API. The search for manifests is filtered to those
                    whose YAML representation declares itself as falling under this API.
                    Example: 'delivery-planning.journeys.a6i.io'
        @param namespace A string. Represents the namespace in the KnowledgeBase store's manifests area 
                        where to look for the manifest.
        @param name A string representing the name of the manifest. Along with kind, this identifies a 
                    unique logical manifest (other than version number)
        @param kind A string representing the kind of the manifest. Along with kind, this identifies a unique 
                    logical manifest (other than version number)
        '''
        return self._impl.findLatestVersionManifest(parent_trace, manifest_api_name, namespace, name, kind)

    def searchManifests(self, parent_trace, kinds_of_interest, manifest_filter):
        '''
        Returns a list of dict objects, each representing the content of a manifest in the store for
        one of the kinds in the `kinds_of_interest` list.

        The returned list comprises all such manifests known to the KnowledgeBaseStore that pass the `manifest_filter`.

        I.e., it rturns a list of objects `manifest_dict` such that 
        
            `manifest_filter(parent_trace, manifest_dict) == True` and `manifest_dict["kind"]` is in `kinds_of_interest`

        If `manifest_filter` is None, then no filter is applied and all manifests in the store are returned.
        
        @param manifest_filter A function that takes two parameters: a FunctionalTrace and a dict object, and returns
                a boolean. 
        '''
        return self._impl.searchManifests(parent_trace, kinds_of_interest, manifest_filter)

    def archivePosting(self, parent_trace, posting_label_handle):
        '''
        Used after a posting Excel file has been processed. It moves the Excel file to a newly created folder dedicated 
        to this posting event and returns a FilingCoordinates object to identify that folder.       
        '''
        return self._impl.archivePosting(parent_trace, posting_label_handle)
        
    def logPostEvent(self, parent_trace, controller_response):
        '''
        Used to record in the store information about a posting event that has been completed.
        '''
        return self._impl.logPostEvent(parent_trace, controller_response)

    def logFormRequestEvent(self, parent_trace, form_request, controller_response):
        '''
        Used to record information about a request form event that has been handled by a controller, based on
        data in the `controller_response`.
        '''
        return self._impl.logFormRequestEvent(parent_trace, form_request, controller_response)

    def uploadForm(self, parent_trace, form_request, representer):
        '''
        Generates the requested form and uploads it to the ClientURL area, based on coordinates
        under the ClientURL determined by the form_request

        @param form_request A FormRequest object that specifies what form should be uploaded and to which
                            coordinates within the ClientURL area.
        @param representer A ManifestRepresenter object that can be used to generate the form to be uploaded.

        @return The filename (a string) under which the form was uploaded
        '''
        return self._impl.uploadForm(parent_trace, form_request, representer)
 
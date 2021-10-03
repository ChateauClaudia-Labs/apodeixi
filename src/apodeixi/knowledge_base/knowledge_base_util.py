import yaml                                                     as _yaml

from apodeixi.knowledge_base.filing_coordinates                 import TBD_FilingCoordinates

# To avoid circular dependencies, we had to move this import to the very few functions in this module that need
# ManifestUtils
#from apodeixi.knowledge_base.manifest_utils                     import ManifestUtils

from apodeixi.util.a6i_error                                    import ApodeixiError

class PostingLabelHandle():
    '''
    Object with all the information needed to identify and retrieve the Posting Label information in a posting.

    It is not meant to be created directly - it should be created only by the KnowledgeBase store, and then passed around as needed.
    '''
    def __init__(self, parent_trace, posting_api, filing_coords, excel_filename, excel_sheet, excel_range):
        self.excel_filename         = excel_filename
        self.excel_sheet            = excel_sheet
        self.excel_range            = excel_range

        self.posting_api            = posting_api 
        self.filing_coords          = filing_coords 

    def copy(self, parent_trace):
        new_handle      = PostingLabelHandle(   parent_trace        = parent_trace, 
                                                posting_api         = self.posting_api, 
                                                filing_coords       = self.filing_coords, 
                                                excel_filename      = self.excel_filename, 
                                                excel_sheet         = self.excel_sheet, 
                                                excel_range         = self.excel_range)
        return new_handle                                              
        
    def display(self, parent_trace):
        '''
        Returns a string friendly representation of this PostingLabelHandle
        '''
        msg = "" \
            + "\n\t\t posting_api     = '" + self.posting_api + "'" \
            + "\n\t\t filing_coords   = '" + str(self.filing_coords) + "'" \
            + "\n\t\t excel_filename  = '" + self.excel_filename + "'" \
            + "\n\t\t excel_sheet     = '" + self.excel_sheet + "'" \
            + "\n\t\t excel_range     = '" + str(self.excel_range) + "'" 
        return msg

    def getPostingAPI(self, parent_trace):
        return self.posting_api

    def getRelativePath(self, parent_trace):

        if type(self.filing_coords) == TBD_FilingCoordinates: # Filing Coords haven't been set yet, so use place holder
            return self.filing_coords.getFullPath()
        else:
            parsed_tokens               = self.filing_coords.path_tokens(parent_trace)
            excel_path                  = '/'.join(parsed_tokens)
            return excel_path + "/" + self.excel_filename

    def createTaggedFilename(self, parent_trace):
        '''
        Returns a filename that should be used when creating "copies" of a posting Excel file as a result
        of processing it with this PostingLabelHandle.
        
        Regardless of what the original filename was for the Excel posting, this returns a string
        consiting of a "tag" prefix followed by the posting API.

        The "tag" depends on the self.filing_coords, and is used to distinguish multiple Excel files
        that would otherwise have the same name.
        
        Example: when JourneyFilingCoords are used, the tag is the product, creating filenames like

                    LedgerPro.big-rocks.journeys.a6i

        '''
        tag                         = self.filing_coords.getTag(parent_trace)
        if type(tag) == str and len(tag) > 0:
            filename                = tag + "." + self.posting_api + ".xlsx"
        else:
            filename                = self.posting_api + ".xlsx"

        return filename

    def buildDataHandle(self, parent_trace, manifest_nb, kind, excel_sheet, excel_range):
        '''
        Constructs a new PostingDataHandle and returns it. It shares with this PostingLabelHandle the information to
        locate the Excel spreadsheet, but (may) differ with the information internal to the Excel spreadsheet, such as
        worksheet and range. It also will populate data specific to the manifest associated to the PostingDataHandle being built
        '''
        data_handle             = PostingDataHandle(    parent_trace        = parent_trace,
                                                        manifest_nb         = manifest_nb,
                                                        kind                = kind,
                                                        filing_coords       = self.filing_coords,
                                                        excel_filename      = self.excel_filename,
                                                        excel_sheet         = excel_sheet,
                                                        excel_range         = excel_range)
        return data_handle

    def createUpdateForm(self, parent_trace, manifest_handles):
        '''
        Creates and returns a FormRequest that can be used by the user to request an Excel spreadsheet with 
        which to later update the data that is being submitted in this posting. The intention is that as this
        posting is processed, after processing the user will have the opportunity (possibly days or weeks later)
        to ammend it by submitting an "update" posting. For that the user will need an Excel spreadsheet
        that the KnowledgeBase understands is an update to a prior posting, so to obtain such a spreadsheet
        the user can give the KnowledgeBase the FormRequest object returned by this function.

        @param manifest_handles A list of ManifestHandle objects
        '''
        coords                  = self.filing_coords
        if type(coords) == TBD_FilingCoordinates:
            my_trace            = parent_trace.doing("Replacing TBD coordinates by the inferred ones")
            coords              = coords.inferred_coords(my_trace)

        form_request            = FormRequest(  parent_trace            = parent_trace, 
                                                posting_api             = self.posting_api, 
                                                filing_coords           = coords,
                                                scope                   = FormRequest.ExplicitScope(manifest_handles))
        return form_request

class PostingDataHandle():
    '''
    Object with all the information needed to identify and retrieve the content for a particulra manifest in a posting.

    It is not meant to be created directly - it should be created only by the PostingLabelHandle, and then passed around as needed.
    '''
    def __init__(self, parent_trace, manifest_nb, kind, filing_coords, excel_filename, excel_sheet, excel_range):
        self.excel_filename         = excel_filename

        self.filing_coords          = filing_coords
        self.excel_sheet            = excel_sheet
        self.excel_range            = excel_range
        self.manifest_nb            = manifest_nb
        self.kind                   = kind

    def getRelativePath(self, parent_trace):
        if type(self.filing_coords) == TBD_FilingCoordinates: # Filing Coords' tokens don't correspond to the path
            return self.filing_coords.getFullPath()
        else:
            parsed_tokens               = self.filing_coords.path_tokens(parent_trace)
            excel_path                  = '/'.join(parsed_tokens)
            return excel_path + "/" + self.excel_filename


class ManifestHandle():
    '''
    Object that uniquely identifies a manifest in an Apodeixi knowledge base

    @param manifest_api_name    A string. Example: "delivery-planning.journeys.a6i.io"
    @param namespace            A string. Example: "my-corp.production"
    @param name                 A string. Example: "modernization.default.dec-2020.opus"
    @param kind                 A string. Example: "big-rock"
    '''
    def __init__(self, manifest_api, kind, namespace, name, version):
        self.manifest_api   = manifest_api
        self.kind           = kind
        self.namespace      = namespace
        self.name           = name
        self.version        = version
        
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    #def __copy__(self):
    def copy(self):
            return ManifestHandle(manifest_api = self.manifest_api, kind = self.kind, namespace = self.namespace, 
                                    name = self.name, version = self.version)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self.manifest_api)) + hash(str(self.kind)) + hash(str(self.namespace)) \
                        + hash(str(self.name)) + hash(str(self.version))

    def display(self, parent_trace, indentation=""):
        msg = "" \
            + "\n\t\t" + indentation + " manifest_api   = '" + str(self.manifest_api) + "'" \
            + "\n\t\t" + indentation + " namespace      = '" + str(self.namespace) + "'" \
            + "\n\t\t" + indentation + " kind           = '" + str(self.kind) + "'" \
            + "\n\t\t" + indentation + " name           = '" + str(self.name) + "'" \
            + "\n\t\t" + indentation + " version        = '" + str(self.version) + "'" \

        return msg

YAML_LOADER                     = _yaml.FullLoader
def manifest_handle_constructor(loader: YAML_LOADER, node: _yaml.nodes.MappingNode) -> ManifestHandle:
    '''
    Constructor of a ManifestHandler for the YAML loader
    '''
    return ManifestHandle(**loader.construct_mapping(node))

# "could not determine a constructor for the tag 
# 'tag:yaml.org,2002:python/object:apodeixi.knowledge_base.knowledge_base_util.ManifestHandle'"
# OR
# ? !!python/object:apodeixi.knowledge_base.knowledge_base_util.ManifestHandle

#TAG                             = "? !!python/object:apodeixi.knowledge_base.knowledge_base_util.ManifestHandle"
TAG                             = 'tag:yaml.org,2002:python/object:apodeixi.knowledge_base.knowledge_base_util.ManifestHandle'
YAML_LOADER.add_constructor(TAG, manifest_handle_constructor)

class Response():
    '''
    Abstract class used to represent the schema response from the KnowledgeBase to a request.

    @internal manifest_handles_dict A dictionary explaining what changed as a consequence of processing this request
                                    in the manifests section of the store.
                                    Keys are Response.CREATED, Response.UPDATED, and Response.DELETED. 
                                    Also supports key Response.UNCHANGED, for manifests (such as reference manifests
                                    used in joins by other manifests being created or updated within a single posting)
                                    that were involved in the processing by the controller, but were not saved.
                                    Values are (possibly empty) dictionaries where keys are integers that uniquely
                                    identify a manifest for the controller that generated the response, and the values
                                    are ManifestHandle objects for such manifest.
                                    There is one such entry in for each manifest that was processed by the controller and
                                    either created, updated, deleted or unchanged by the request in quesion.
    @internal posting_handles_dict A dictionary explaining what changed as a consequence of processing this request
                                    in the postings section of the store. 
                                    Keys are: Response.ARCHIVED. 
                                    Values are lists (possibly empty) of a 2-sized list of
                                    PostingLabelHandle objects, such as [handle_1, handle_2] where handle_1 was the
                                    handle for the posting submitted and has now been removed, and handle_2 for the 
                                    archived copy of the posting that has been created. In cases where the posting
                                    was submitted from outside the store (e.g., as from some random location in
                                    the file system external to the store), then handle1 is set to None.
    @internal form_requests_dict A dictionary explaining the next steps that a user might need to take as a consequence
                                    of having just finished processing this request.
                                    Keys are: Response.OPTIONAL_FORMS, Response.MANDATORY_FORMS.
                                    Values are lists (possibly empty) with FormRequest objects, one for each
                                    (future) posting that the user may want to do as follow-up to this request. For example,
                                    typically the FormRequests under Response.OPTIONAL_FORMS are for making updates
                                    to the same posting just submitted in this request (i.e., same posting APIs). By contrast, the FormRequests
                                    under Response.MANDATORY_FORMS typically are for other posting APIs where the 
                                    KnowledgeBase has detected that previously provided information (if any) is now
                                    inconsistent or incomplete as a result of having processed this request. For example,
                                    if the user just updated a posting for a Big Rocks plan by adding another rock,
                                    it may be that the user is asked in Response.MANDATORY_FORMS to update the
                                    Milestones manifests to indicate the milestone containing that new rock.
    '''
    def __init__(self):
        self.manifest_handles_dict          = { Response.CREATED: {},   Response.UPDATED: {}, 
                                                Response.DELETED: {},   Response.UNCHANGED: {}}
        self.posting_handles_dict           = {Response.ARCHIVED: []}
        self.clientURL_handles_dict         = {Response.CREATED: []}
        self.form_requests_dict             = {Response.OPTIONAL_FORMS: [], Response.MANDATORY_FORMS: []}

    CREATED                                 = 'CREATED' 
    UPDATED                                 = 'UPDATED' 
    DELETED                                 = 'DELETED'  
    UNCHANGED                               = 'UNCHANGED'

    ARCHIVED                                = 'ARCHIVED'   

    OPTIONAL_FORMS                          = 'OPTIONAL_FORMS'  
    MANDATORY_FORMS                         = 'MANDATORY_FORMS'  

    def createdManifests(self):
        return list(self.manifest_handles_dict[Response.CREATED].values())

    def updatedManifests(self):
        return list(self.manifest_handles_dict[Response.UPDATED].values())

    def deletedManifests(self):
        return list(self.manifest_handles_dict[Response.DELETED].values())

    def unchangedManifests(self):
        return list(self.manifest_handles_dict[Response.UNCHANGED].values())

    def allActiveManifests(self, parent_trace):
        '''
        Returns a list of ManifestHandles in this response corresponding to create, update, or unchanged
        events (so it does not include deletes, since those are not "active").

        Typical use case is for the caller to want such list in order to assemble a list of forms that
        are needed if in the future the user wants to update the manifests manipulated by the controller
        that produced this response.

        For deterministic reasons (so that caller can process them in the right sequence of dependencies),
        the list of ManifestHandles is *sorted* based on the manifest_nb that was passed to this Response
        object when the manifest was recorded into the response.
        '''
        all_handles_dict    = self.manifest_handles_dict[Response.CREATED] | self.manifest_handles_dict[Response.UPDATED] \
                                | self.manifest_handles_dict[Response.UNCHANGED]
        all_manifest_nbs    = list(all_handles_dict.keys())
        all_manifest_nbs.sort()
        result              = []
        for nb in all_manifest_nbs:
            result.append(all_handles_dict[nb])
        return result

    def allManifests(self, parent_trace):
        '''
        Returns a list of ManifestHandles in this response corresponding to create, delete, update, or unchanged
        events (so unlike the allActiveManifests method, this method includes deletes).
        
        One use case where this is used is in the Apodeixi CLI, to provide input to user's on the outcome of
        a user-initiated posting.
        '''
        all_handles_dict    = self.manifest_handles_dict[Response.CREATED] \
                                | self.manifest_handles_dict[Response.UPDATED] \
                                | self.manifest_handles_dict[Response.DELETED] \
                                | self.manifest_handles_dict[Response.UNCHANGED]
        all_manifest_nbs    = list(all_handles_dict.keys())
        all_manifest_nbs.sort()
        result              = []
        for nb in all_manifest_nbs:
            result.append(all_handles_dict[nb])
        return result

    def archivedPostings(self):
        return self.posting_handles_dict[Response.ARCHIVED]   
        
    def createdForms(self):
        return self.clientURL_handles_dict[Response.CREATED]

    def optionalForms(self):
        return self.form_requests_dict[Response.OPTIONAL_FORMS]

    def mandatoryForms(self):
        return self.form_requests_dict[Response.MANDATORY_FORMS]

class PostResponse(Response):
    '''
    Data structure used as a response to a post request on the knowledge base
    '''
    def __init__(self):
        super().__init__()
        # To avoid circular dependencies, we had to move this import to the very few functions in this module that need
        # ManifestUtils
        from apodeixi.knowledge_base.manifest_utils  import ManifestUtils
        self.MU                 = ManifestUtils()
    def recordCreation(self, parent_trace, manifest_dict, manifest_nb):
        '''
        Used to enrich the content of this PostResponse by recording that a manifest was created

        @param manifest_dict A dictionary representation of a manifest. It must have 'metadata.name', 'metadata.namespace' and 'kind'
                                since those are mandatory fields for all manifests.
        '''

        handle                  = self.MU.inferHandle(parent_trace, manifest_dict)
        self.manifest_handles_dict[Response.CREATED][manifest_nb] = handle

    def recordUpdate(self, parent_trace, manifest_dict, manifest_nb):
        '''
        Used to enrich the content of this PostResponse by recording that a manifest was updated

        @param manifest_dict A dictionary representation of a manifest. It must have 'metadata.name', 
                                'metadata.namespace' and 'kind'
                                since those are mandatory fields for all manifests.
        '''
        handle                  = self.MU.inferHandle(parent_trace, manifest_dict)
        self.manifest_handles_dict[Response.UPDATED][manifest_nb] = handle

    def recordUnchanged(self, parent_trace, manifest_dict, manifest_nb):
        '''
        Used to enrich the content of this PostResponse by recording that a manifest was not changed

        @param manifest_dict A dictionary representation of a manifest. It must have 'metadata.name', 
                                'metadata.namespace' and 'kind'
                                since those are mandatory fields for all manifests.
        '''
        handle                  = self.MU.inferHandle(parent_trace, manifest_dict)
        self.manifest_handles_dict[Response.UNCHANGED][manifest_nb] = handle

    def recordArchival(self, parent_trace, original_handle, archival_handle):
        self.posting_handles_dict[Response.ARCHIVED].append([original_handle, archival_handle])

    def recordOptionalForm(self, parent_trace, form_request):
        self.form_requests_dict[Response.OPTIONAL_FORMS].append(form_request)

class FormRequestResponse(Response):
    '''
    Data structure used as a response to a FormRequest request on the knowledge base

    @param clientURL A string corresponding to the root path of the client area (such as a SharePoint folder)
                        under which the form was saved in response to the FormRequest.
    @param posting_api A string, corresponding to the posting API for which this form was requested.
    @param filing_coords A FilingCoords object indicating where the form was persisted below the client URL directory.
    @param filename A string corresponding to the name of the file used to save the Excel form.
    @param path_mask A function that takes as tring argument and returns a string. Normally it is None, but
                it is used in situations (such as in regression testing) when observability should not
                report the paths "as is", but with a mask. For example, this can be used in regression
                tests to hide the user-dependent portion of paths, so that logs would otherwise display a path
                like:

                'C:/Users/aleja/Documents/Code/chateauclaudia-labs/apodeixi/test-knowledge-base/envs/big_rocks_posting_ENV/excel-postings'

                instead display a "masked" path where the user-specific prefix is masked, so that only the
                logical portion of the path (logical as in: it is the structure mandated by the KnowledgeStore)
                is displayed. In the above example, that might become:

                '<KNOWLEDGE_BASE>/envs/big_rocks_posting_ENV/excel-postings    
    @param manifest_identifiers A list of strings, corresponding to the identifiers or all manifest data sets
                in the form. 
                Example: 
                            ['big-rock.0', 'big-rock-estimates.1', 'investment.3']
    '''
    def __init__(self, clientURL, posting_api, filing_coords, filename, path_mask, manifest_identifiers):
        super().__init__()
        self._clientURL             = clientURL
        self._posting_api           = posting_api 
        self._filing_coords         = filing_coords 
        self._filename              = filename
        self._path_mask             = path_mask
        self._manifest_identifiers  = manifest_identifiers

    def clientURL(self, parent_trace):
        return self._clientURL

    def posting_api(self, parent_trace):
        return self._posting_api

    def filing_coords(self, parent_trace):
        return self._filing_coords

    def filename(self, parent_trace):
        return self._filename

    def manifest_identifiers(self, parent_trace):
        return self._manifest_identifiers

    def applyMask(self, parent_trace, original_txt):
        if self._path_mask != None:
            return self._path_mask(original_txt)
        else:
            return original_txt


    def recordClientURLCreation(self, parent_trace, response_handle):
        '''
        Used to enrich the content of this FormRequestResponse by recording that a form was created

        @param response_handle A PostingLabelHandle for the form that was created'
        '''
        self.clientURL_handles_dict[Response.CREATED].append(response_handle)

    def getRelativePath(self, parent_trace):
        '''
        Returns the relative path within the Knowledge Store's external collaboration area where the 
        form (an Excel spreadsheet) can be found. This is the form generated in the processing for
        which this class is the response.
        '''
        parsed_tokens               = self._filing_coords.path_tokens(parent_trace)
        tag                         = self._filing_coords.getTag(parent_trace)
        if type(tag) == str and len(tag) > 0:
            filename                = tag + "." + self._posting_api + ".xlsx"
        else:
            filename                = self._posting_api + ".xlsx"
        excel_path                  = '/'.join(parsed_tokens)
        return excel_path + "/" + filename

    def getManifestIdentifiers(self, parent_trace):
        return self._manifest_identifiers

class FormRequest():
    '''
    Object that allows the user to request a form (i.e., an Excel spreadsheet template) to the Knowledge Base.
    This form is intended to allow the user to make a posting.

    Upon receiving such a request, the Knowledge Base would:

    * Create an Excel spreadsheet in an area of the Knowledge Base's store determined by this FormRequest
    * The spreadsheet would have a pre-populated Posting Label area as determined by this FormRequest
    * The spreadsheet would be for a posting API determined by this FormRequest
    * The form would be pre-populated with content from "manifests in scope", i.e., the manifest instances
      whose updates are supposed to included in the posting.

    The user can subsequently make use of the generated form to enter any missing data (or update existing data)
    in the spreadsheet and submit it to the Knowledge Base as a posting. 
    
    Such submission would entail the creation of a PostingLabelHandle for the posting, resulting in the creation 
    or update of the manifests in scope for the form.
    
    A FormRequest may be "blind". This refers to the situation where the FormRequest does not explicity
    state which manifests are in scope. This can happen in two situations:

    * The user is requesting a form for creating manifests for the first time. So there are no "manifests
      in scope"
    * The user is requesting a form to update "whatever manifests are associated to a posting" without having
      or knowing ManifestHandles for them. In that case the processing controller will have to search
      in the KnowledgeBase store for the manifests that are in scope given the other parameters of the form
      request and what the concrete controller knows about the kind of manifests it deals with. 

    @param scope Object that specifies how to determine the manifests in scope. It must be of one of two types:
            1) An instance of FormRequest.ExplicitScope, for the case where the request is not blind.
                In this case, the scope contains a list of manifest handles.
            2) An instance of FormRequest.SearchScope, for the case where the request is blind.
                In this case, the scope contains a namespace to which to delimit the search

    '''
    def __init__(self, parent_trace, posting_api, filing_coords, scope):

        self._posting_api           = posting_api 
        self._filing_coords         = filing_coords 

        if type(scope) == FormRequest.ExplicitScope or type(scope) == FormRequest.SearchScope:
            self._scope                 = scope
        else:
            raise ApodeixiError("Invalid type of scope in FormRequest",
                                data = {"type(scope)": str(type(scope)),
                                        "valid types": str["FormRequest.ExplicitScope", "FormRequest.SearchScope"]})
       
    def display(self, parent_trace):
        '''
        Returns a string friendly representation of this FormRequest
        '''
        msg = "" \
            + "\n\t\t posting_api     = '" + self._posting_api + "'" \
            + "\n\t\t filing_coords   = '" + str(self._filing_coords) + "'" 

        msg += self._scope.display(parent_trace)

        return msg

    def getPostingAPI(self, parent_trace):
        return self._posting_api

    def getFilingCoords(self, parent_trace):
        return self._filing_coords

    def getScope(self, parent_trace):
        return self._scope


    def getRelativePath(self, parent_trace):
        '''
        Returns the relative path within the Knowledge Store's postings area where the form (an Excel spreadsheet)
        should reside
        '''
        parsed_tokens               = self._filing_coords.path_tokens(parent_trace)
        tag                         = self._filing_coords.getTag(parent_trace)
        if type(tag) == str and len(tag) > 0:
            filename                = tag + "." + self._posting_api + ".xlsx"
        else:
            filename                = self._posting_api + ".xlsx"

        excel_path                  = '/'.join(parsed_tokens)
        return excel_path + "/" + filename

    class ExplicitScope():
        '''
        Helper class for a FormRequest. It codifies the fact that the manifest scope is explicitly known 
        as a list of manifest handles

        @param manifest_handle_list: a list of ManifestHandle objects, for the manifests in scope for the request. If it 
                        is an empty list or None then this is interpreted a blind request. 
        '''
        def __init__(self, manifest_handle_list):
            self._manifest_handle_list  = manifest_handle_list

        def manifestHandles(self, parent_trace, controller):
            '''
            Used to obtain the ManifestHandles for the manifests in the scope of this FormRequest, assuming it is not
            a blind request.

            Specifically, it returns a dictionary whose keys are strings that uniquely identify each ManifestHandle in 
            this FormRequest, and the values are the corresponding ManifestHandle

            If ManifestHandles have not been configured in this FormRequest, returns None as this FormRequest is
            then interpreted to be a blind request.

            @param controller An instance of PostingController
            '''
            if self._manifest_handle_list != None and len(self._manifest_handle_list) > 0:
                result_dict                         = {}
                supported_kinds                     = controller.getSupportedKinds()
                for idx in range(len(self._manifest_handle_list)):
                    manifest_handle                 = self._manifest_handle_list[idx]
                    kind                            = manifest_handle.kind
                    if not kind in supported_kinds:
                        raise ApodeixiError(parent_trace, "Can't create a manifest handle for kind '" + str(kind)
                                                    + "' because it is not supported by controller '" + str(type(controller)) + "'")
                    manifest_nb                     = supported_kinds.index(kind)
                    manifest_key                    = str(kind) + "." + str(manifest_nb)
                    result_dict[manifest_key]       = manifest_handle

                return result_dict
            else:
                return None

        def display(self, parent_trace):
            '''
            Returns a string friendly representation of this FormRequest scope
            '''
            msg = ""
            
            for handle in self._manifest_handle_list:
                msg += "\n\t\t *** A ManifestHandle ***"
                msg += handle.display(parent_trace, indentation="\t")

            return msg

    class SearchScope():
        '''
        Helper class to a FormRequest. It codifies the fact that the manifest scope is not explicity known
        so the controller will have to determine it by searching the store.
        To assist in that search, this class delimits the search to a particular namespace. That gives the
        controller the "missing hint" for the search, as the controller can determine other search parameters
        from other information in the FormRequest (such as the filing coordinates) or information known
        to the controller (such as what kinds it supports).

        @param namespace A string, representing a namespace in the KnowledgeBase store's manifests are that
                        delimits the scope for searching for manfiests in scope of this FormRequest.
                        Example: "my-corp.production"

        @param subnamespace An optional string representing a slice of the namespace that further restricts
                        the manifest names to search. If set to None, not subspace is assumed.
                        Example: in the manifest name "modernization.default.dec-2020.fusionopus", the
                                token "modernization" is the subnamespace. The other tokens come from filing coordinates
                                for the posting from whence the manifest arose.
        '''
        def __init__(self, namespace, subnamespace):
            self.namespace      = namespace
            self.subnamespace   = subnamespace
        
        def display(self, parent_trace):
            '''
            Returns a string friendly representation of this FormRequest scope
            '''
            msg = "\n\t\t scope namespace = '" + str(self.namespace) + "'" \
                   + "\n\t\t scope subnamespace = '" + str(self.subnamespace) + "'"

            return msg
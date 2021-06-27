from apodeixi.util.dictionary_utils                             import DictionaryUtils
from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace

class PostingLabelHandle():
    '''
    Object with all the information needed to identify and retrieve the Posting Label information in a posting.

    It is not meant to be created directly - it should be created only by the KnowledgeBase store, and then passed around as needed.
    '''
    def __init__(self, parent_trace, posting_api, kb_postings_url, filing_coords, excel_filename, excel_sheet, excel_range):
        self.excel_filename         = excel_filename
        self.excel_sheet            = excel_sheet
        self.excel_range            = excel_range

        self.posting_api            = posting_api 
        self.filing_coords          = filing_coords 
        self.kb_postings_url        = kb_postings_url 

    def getPostingAPI(self, parent_trace):
        return self.posting_api

    def getFullPath(self, parent_trace):

        parsed_tokens               = self.filing_coords.path_tokens(parent_trace)
        excel_path                  = self.kb_postings_url  +  '/' + '/'.join(parsed_tokens)
        return excel_path + "/" + self.excel_filename

    def buildDataHandle(self, parent_trace, manifest_nb, kind, excel_sheet, excel_range):
        '''
        Constructs a new PostingDataHandle and returns it. It shares with this PostingLabelHandle the information to
        locate the Excel spreadsheet, but (may) differ with the information internal to the Excel spreadsheet, such as
        worksheet and range. It also will populate data specific to the manifest associated to the PostingDataHandle being built
        '''
        data_handle             = PostingDataHandle(    parent_trace        = parent_trace,
                                                        manifest_nb         = manifest_nb,
                                                        kind                = kind,
                                                        kb_postings_url     = self.kb_postings_url,
                                                        filing_coords       = self.filing_coords,
                                                        excel_filename      = self.excel_filename,
                                                        excel_sheet         = excel_sheet,
                                                        excel_range         = excel_range)
        return data_handle

class PostingDataHandle():
    '''
    Object with all the information needed to identify and retrieve the content for a particulra manifest in a posting.

    It is not meant to be created directly - it should be created only by the PostingLabelHandle, and then passed around as needed.
    '''
    def __init__(self, parent_trace, manifest_nb, kind, kb_postings_url, filing_coords, excel_filename, excel_sheet, excel_range):
        self.excel_filename         = excel_filename

        self.kb_postings_url        = kb_postings_url
        self.filing_coords          = filing_coords
        self.excel_sheet            = excel_sheet
        self.excel_range            = excel_range
        self.manifest_nb            = manifest_nb
        self.kind                   = kind

    def getFullPath(self, parent_trace):
        parsed_tokens               = self.filing_coords.path_tokens(parent_trace)
        excel_path                  = self.kb_postings_url  +  '/' + '/'.join(parsed_tokens)
        return excel_path + "/" + self.excel_filename

class ManifestUtils():
    def __init__(self):
        return

    def set_manifest_version(self, parent_trace, manifest_dict, manifest_version):
        _VERSION                            = "version" # Refers to the version of the manifest, not of the posting
        _METADATA                           = "metadata"
        _LABELS                             = "labels"

        my_trace                            = parent_trace.doing("Validating manifest dictionary structure before setting version")
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = manifest_dict, 
                                                                root_dict_name  = 'manifest_dict',
                                                                path_list       = [_METADATA, _LABELS],
                                                                valid_types     = None)
        if not check:
            raise ApodeixiError(my_trace, "Can't set manifest version because it is not structured correctly",
                                        data = {'explanation': explanation})

        metadata_dict                       = manifest_dict[_METADATA]
        metadata_dict[_VERSION]             = manifest_version
        metadata_dict[_LABELS][_VERSION]    = manifest_version

    def get_manifest_version(self, parent_trace, manifest_dict):
        _VERSION                            = "version" # Refers to the version of the manifest, not of the posting
        _METADATA                           = "metadata"
        _LABELS                             = "labels"

        my_trace                            = parent_trace.doing("Validating manifest dictionary structure before getting version")
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = manifest_dict, 
                                                                root_dict_name  = 'manifest_dict',
                                                                path_list       = [_METADATA, _VERSION],
                                                                valid_types     = None)
        if not check:
            raise ApodeixiError(my_trace, "Can't get manifest version because it is not structured correctly",
                                        data = {'explanation': explanation})

        metadata_dict                       = manifest_dict[_METADATA]
        manifest_version                    = metadata_dict[_VERSION] 
        return manifest_version
    
class ManifestHandle():
    '''
    Object that uniquely identifies a manifest in an Apodeixi knowledge base
    '''
    def __init__(self, apiVersion, kind, namespace, name, version):
        self.apiVersion     = apiVersion
        self.kind           = kind
        self.namespace      = namespace
        self.name           = name
        self.version        = version
        

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        msg = "<apiVersion = '" + self.apiVersion + "'" \
                + "'; namespace = '" + self.namespace \
                + "'; kind = '" + self.kind \
                + "'; name = '" + self.name \
                + "'; version = '" + str(self.version) + "'>"
        return msg

    def inferHandle(parent_trace, manifest_dict):
        '''
        Figures out and returns the ManifestHandle implied by the given manifest_dict. If the manifest_dict is not well
        formed it raises an error.
        '''
        if not type(manifest_dict) == dict:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because manifest was not passed as a dictionary. "
                                                "Instead was given a " + str(type(manifest_dict)),
                                                origination = {'signaled_from': __file__})
        API_VERSION                 = 'apiVersion'
        VERSION                     = 'version'
        NAME                        = 'name'
        NAMESPACE                   = 'namespace'
        KIND                        = 'kind'
        METADATA                    = 'metadata'

        REQUIRED_KEYS               = [API_VERSION, METADATA, KIND]

        REQUIRED_METADATA_SUBKEYS   = [NAME, NAMESPACE, VERSION]

        missed_keys                 = [key for key in REQUIRED_KEYS if not key in manifest_dict.keys()]
        if len(missed_keys) > 0:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because these mandatory fields were absent in the "
                                                "manifest: " + str(missed_keys),
                                                origination = {'signaled_from': __file__})

        metadata_dict               = manifest_dict[METADATA]
        missed_metadata_subkeys     = [key for key in REQUIRED_METADATA_SUBKEYS if not key in metadata_dict.keys()]
        if len(missed_metadata_subkeys) > 0:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because these mandatory fields were absent in the "
                                                "manifest's metadata: " + str(missed_metadata_subkeys),
                                                origination = {'signaled_from': __file__})

        handle                  = ManifestHandle(   apiVersion  = manifest_dict[API_VERSION],
                                                    namespace   = metadata_dict[NAMESPACE], 
                                                    name        = metadata_dict[NAME], 
                                                    kind        = manifest_dict[KIND],
                                                    version     = metadata_dict[VERSION])
        return handle

class Response():
    '''
    Abstract class used to represent the schema response from the KnowledgeBase to a request.

    @param manifest_handles_dict A dictionary explaining what changed as a consequence of processing this request.
                                    Keys are Response.CREATE, Response.UPDATE, and Response.DELETE. Values are lists
                                    (possibly empty) with ManifestHandle objects, one for each manifest that was either
                                    created, updated or deleted by the request in quesion.
    '''
    def __init__(self):
        self.manifest_handles_dict          = {Response.CREATE: [], Response.UPDATE: [], Response.DELETE: []}

    CREATE                      = 'CREATE' 
    UPDATE                      = 'UPDATE' 
    DELETE                      = 'DELETE'         

    def createdHandles(self):
        return self.manifest_handles_dict[Response.CREATE]

    def updatedHandles(self):
        return self.manifest_handles_dict[Response.UPDATE]

    def deletedHandles(self):
        return self.manifest_handles_dict[Response.DELETE]

class PostResponse(Response):
    '''
    Data structure used as a response to a post request on the knowledge base
    '''
    def __init__(self):
        super().__init__()

    def recordCreation(self, parent_trace, manifest_dict):
        '''
        Used to enrich the content of this PostResponse by recording that a manifest was created

        @param manifest_dict A dictionary representation of a manifest. It must have 'metadata.name', 'metadata.namespace' and 'kind'
                                since those are mandatory fields for all manifests.
        '''
        '''
        if not type(manifest_dict) == dict:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because manifest was not passed as a dictionary. "
                                                "Instead was given a " + str(type(manifest_dict)))
        NAME                        = 'name'
        NAMESPACE                   = 'namespace'
        KIND                        = 'kind'
        METADATA                    = 'metadata'
        REQUIRED_KEYS               = [METADATA, KIND]

        REQUIRED_METADATA_SUBKEYS   = [NAME, NAMESPACE]

        missed_keys                 = [key for key in REQUIRED_KEYS if not key in manifest_dict.keys()]
        if len(missed_keys) > 0:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because these mandatory fields were absent in the "
                                                "manifest: " + str(missed_keys))

        metadata_dict               = manifest_dict[METADATA]
        missed_metadata_subkeys     = [key for key in REQUIRED_METADATA_SUBKEYS if not key in metadata_dict.keys()]
        if len(missed_metadata_subkeys) > 0:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because these mandatory fields were absent in the "
                                                "manifest's metadata: " + str(missed_metadata_subkeys))

        handle                  = ManifestHandle(   namespace   = metadata_dict[NAMESPACE], 
                                                    name        = metadata_dict[NAME], 
                                                    kind        = manifest_dict[KIND])
        '''
        handle                  = ManifestHandle.inferHandle(parent_trace, manifest_dict)
        self.manifest_handles_dict[Response.CREATE].append(handle)

class PostingVersion():
    '''
    Helper class to represent different versions of the same posting
    '''
    def __init__(self, version_nb = 0):
        self.version_nb         = version_nb
        return
    
    def nextVersion(self, posting_version):
        return PostingVersion(posting_version.version_nb + 1)


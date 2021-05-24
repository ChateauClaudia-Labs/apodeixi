from apodeixi.util.a6i_error                                    import ApodeixiError, FunctionalTrace

class ManifestHandle():
    '''
    Object that uniquely identifies a manifest in an Apodeixi knowledge base
    '''
    def __init__(self, namespace, name, kind):
        self.namespace      = namespace
        self.name           = name
        self.kind           = kind

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        msg = "<namespace = '" + self.namespace + "'; name = '" + self.name + "'; kind = '" + self.kind + "'>"
        return msg

    def inferHandle(parent_trace, manifest_dict):
        '''
        Figures out and returns the ManifestHandle implied by the given manifest_dict. If the manifest_dict is not well
        formed it raises an error.
        '''
        if not type(manifest_dict) == dict:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because manifest was not passed as a dictionary. "
                                                "Instead was given a " + str(type(manifest_dict)),
                                                data = {'signaled_from': __file__})
        NAME                        = 'name'
        NAMESPACE                   = 'namespace'
        KIND                        = 'kind'
        METADATA                    = 'metadata'
        REQUIRED_KEYS               = [METADATA, KIND]

        REQUIRED_METADATA_SUBKEYS   = [NAME, NAMESPACE]

        missed_keys                 = [key for key in REQUIRED_KEYS if not key in manifest_dict.keys()]
        if len(missed_keys) > 0:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because these mandatory fields were absent in the "
                                                "manifest: " + str(missed_keys),
                                                data = {'signaled_from': __file__})

        metadata_dict               = manifest_dict[METADATA]
        missed_metadata_subkeys     = [key for key in REQUIRED_METADATA_SUBKEYS if not key in metadata_dict.keys()]
        if len(missed_metadata_subkeys) > 0:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because these mandatory fields were absent in the "
                                                "manifest's metadata: " + str(missed_metadata_subkeys),
                                                data = {'signaled_from': __file__})

        handle                  = ManifestHandle(   namespace   = metadata_dict[NAMESPACE], 
                                                    name        = metadata_dict[NAME], 
                                                    kind        = manifest_dict[KIND])
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



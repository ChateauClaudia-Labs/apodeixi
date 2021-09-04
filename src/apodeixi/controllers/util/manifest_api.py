from apodeixi.util.a6i_error        import ApodeixiError

class ManifestAPIVersion():
    '''
    Utility class to consistently parse and create the "apiVersion" strings that appear in manifests.

    By an "apiVersion" we mean a string such as 'capability-hierarchy.kernel.a6i.xlsx/v1a'.

    @param parent_trace     A FunctionalTrace object to support Apodeixi's error messages. Recommended usage is for it
                            to express the caller's functional moment.
    @param api:             A ManifestAPI object, encapsulating something like 'capability-hierarchy.kernel.a6i.xlsx'. 
    @param version:         'v1a'                   in the example 'capability-hierarchy.kernel.a6i.xlsx/v1a'
    '''
    def __init__(self, parent_trace, api, version):

        if type(api) == None:
            raise ApodeixiError(parent_trace, "Passed a null api. Pass a valid ManifestAPI object instead")
        if type(api) != ManifestAPI:
            raise ApodeixiError(parent_trace, "Invalid api: should be a ManifestAPI, but instead received a '"
                                                + str(type(api)) + "'")

        self.api            = api
        self.version        = ManifestAPI._trimmed(parent_trace,  "version", version)

    API_VERSION                 = 'apiVersion' # Used by other classes as a static string key
    
    def apiVersion(self):
        '''
        Returns a string such as 'capability-hierarchy.kernel.a6i.io/v1', assembled from the attributes of this class.
        '''
        return self.api.apiName() + '/' + self.version

    def parse(parent_trace, apiVersion):
        '''
        Parses an apiVersion string like 'capability-hierarchy.kernel.a6i.io/v1' and strips off the version,
        returning a ManifestAPIVersion object
        '''
        if type(apiVersion) != str:
            raise ApodeixiError(parent_trace, "Can't build a ManifestAPIVersion object through parsing because `apiVersion` "
                                                + " was not provided as a string",
                                                data = {"type(apiVersion":  str(type(apiVersion)),
                                                        "apiVersion":       str(apiVersion)})

        tokens              = apiVersion.split("/")
        if len(tokens) != 2:
            raise ApodeixiError(parent_trace, "Can't build a ManifestAPIVersion object through parsing because `apiVersion` "
                                                + " is not in the expected format '<api name>/<version>",
                                                data = {"apiVersion":       str(apiVersion)})
        apitokens           = tokens[0].split(".")
        if len(apitokens) != 4:
            raise ApodeixiError(parent_trace, "Can't build a ManifestAPIVersion object through parsing because `apiVersion` "
                                                + " is not in the expected format '"
                                                + "<subdomain>.<domain>.<api_publisher>.<extension>/<version>\n"
                                                + "For example, something like 'delivery-planning.journeys.a6i.io/v1",
                                                data = {"apiVersion":       str(apiVersion)})

        api                 = ManifestAPI(  parent_trace    = parent_trace, 
                                            subdomain       = apitokens[0], 
                                            domain          = apitokens[1], 
                                            api_publisher   = apitokens[2],
                                            extension       = apitokens[3])

        api_version         = ManifestAPIVersion(parent_trace=parent_trace, api=api, version=tokens[1])
        return api_version

class ManifestAPI():
    '''
    Utility class encapsulating the unique strings name that identify a manifest API. It does not include versioning,
    which is handled by the class `ManifestAPIVersion`

    By an "api name" we mean a string such as 'capability-hierarchy.kernel.a6i.io'.

    @param parent_trace     A FunctionalTrace object to support Apodeixi's error messages. Recommended usage is for it
                            to express the caller's functional moment.
    @param domain:          'kernel'                in the example 'capability-hierarchy.kernel.a6i.io/v1a'. 
    @param subdomain:       'capability-hierarchy'  in the example 'capability-hierarchy.kernel.a6i.io/v1a'
    @param api_publisher:   'a6i'                   in the example 'capability-hierarchy.kernel.a6i.io/v1a'. 
    @param extension:       'xlsx'                  in the example 'capability-hierarchy.kernel.a6i.io/v1a'.  
                                    Only 'xlsx' and 'io' are supported.
    
    All objects in Apodeixi's core domain model use 'a6i' as the API publisher, but extensions of Apodeixi should use
    a different value to correctly identify the organization that extended the domain model.
    '''
    def __init__(self, parent_trace, domain, subdomain, api_publisher, extension):

        self.domain         = ManifestAPI._trimmed(parent_trace, "domain",            domain)
        self.subdomain      = ManifestAPI._trimmed(parent_trace, "subdomain",         subdomain)
        self.api_publisher  = ManifestAPI._trimmed(parent_trace, "api_publisher",     api_publisher)
        self.extension      = ManifestAPI._trimmed(parent_trace, "extension",         extension)

        VALID_EXTENSIONS = ['xlsx', 'io']
        if extension not in VALID_EXTENSIONS:
            raise ApodeixiError(parent_trace, "Invalid extension '" + extension + "' - should be one of " + ", ".join(VALID_EXTENSIONS))

    def apiName(self):
        '''
        Returns a string such as 'capability-hierarchy.kernel.a6i.xlsx', assembled from the attributes of this class.
        '''
        return self.subdomain + '.' + self.domain + '.' + self.api_publisher + '.' + self.extension

    def _trimmed(parent_trace, obj_name, obj):
        '''
        Helper method that checks that `obj` is a non-blank string. If so, it trims it and retruns it. Otherwise, throws an error
        '''
        if type(obj) == None:
            raise ApodeixiError(parent_trace, "Invalid null value provided for " + obj_name)
        if type(obj) != str:
            raise ApodeixiError(parent_trace, "Invalid type for " + obj_name + " : should be a string, but instead was given a '"
                                                + str(type(obj)) + "'")
        
        trimmed = obj.strip()
        if len(trimmed) == None:
            raise ApodeixiError(parent_trace, "Invalid blank value provided for " + obj_name)
        return trimmed
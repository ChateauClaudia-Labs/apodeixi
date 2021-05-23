from apodeixi.util.a6i_error                        import ApodeixiError

class KnowledgeBaseStore():
    '''
    Abstract class used to encapsulate the common services that a KnowledgeBase depends on from a "store" in which the
    KnowledgeBase can persist and retrieve manifests, postings, and any other persistent Apodeixi domain object.
    '''
    def __init__(self):
        return

    def discoverPostingURL(self, parent_trace, excel_posting_path, sheet="Sheet1"):
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'discoverPostingURL' in concrete class",
                                                data = {'signaled_from': __file__})


    def persistManifest(self, parent_trace, manifest_dict, version = None):
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'persistManifest' in concrete class",
                                                data = {'signaled_from': __file__})
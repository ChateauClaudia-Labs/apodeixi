from apodeixi.util.a6i_error                    import ApodeixiError

class InitiativeMilestonesAggregator():
    '''
    Class to aggregate milestones across multiple workstreams for a particular strategic initiative
    '''
    def __init__(self, parent_trace, initative_UID, knowledge_base_store):
        self.initiative_UID         = initiative_UID
        self.kb_store               = knowledge_base_store


    def aggregateMetrics(self, parent_trace, filing_coordinates_filter=None, posting_version_filter=None):
        '''
        Returns a DataFrame that aggregates all metrics across all workstreams for self.initiative that exist in self.kb_store

        @param filing_coordinates_filter A function that takes a FilingCoordinates instance as a parameter and returns a boolean. 
                            Any FilingCoordinates instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        @param posting_version An instance of a posting version.
        
        '''
        POSTING_API                 = 'milestones.initiative.a6i'

        locations_dict              = self.kb_store.locatePostings( parent_trace                    = parent_trace, 
                                                                    posting_api                     = POSTING_API,
                                                                    filing_coordinates_filter       = None, 
                                                                    posting_version_filter          = None)
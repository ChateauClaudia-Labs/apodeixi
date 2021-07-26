import pandas                                   as _pd

from apodeixi.util.a6i_error                    import ApodeixiError

from apodeixi.representers                      import AsDataframe_Representer

class WorkstreamAggregator():
    '''
    Class to aggregate milestones across multiple workstreams for a particular strategic initiative
    '''
    def __init__(self, parent_trace, initiative_UID, knowledge_base):
        self.initiative_UID         = initiative_UID
        self.kb                     = knowledge_base


    def aggregateMetrics(self, parent_trace, filing_coordinates_filter=None):
        '''
        Returns a DataFrame that aggregates all metrics across all workstreams for self.initiative that exist in self.kb_store.
        If no such metrics exist, it returns None.

        @param filing_coordinates_filter A function that takes a FilingCoordinates instance as a parameter and returns a boolean. 
                            Any FilingCoordinates instance for which this filter returns False will be excluded from the output.
                            If set to None then no filtering is done.
        
        '''
        POSTING_API                             = 'workstream.initiatives.a6i'

        result_df                               = None

        my_trace                                = parent_trace.doing("Searching postings for given API",
                                                                    data = {'posting_api':      POSTING_API})
        handle_list                             = self.kb.store.searchPostings( 
                                                                    parent_trace                    = my_trace, 
                                                                    posting_api                     = POSTING_API,
                                                                    filing_coordinates_filter       = None)

        my_trace                                = parent_trace.doing("Posting " + str(len(handle_list)) + " handles in batch")
        successes, errors                       = self.kb.postInBatch(my_trace, handle_list)

        my_trace                                = parent_trace.doing("Loading manifests")
        df_list                                 = []
        for idx in successes.keys():
            loop_trace                          = my_trace.doing("Processing response to posting handle #" + str(idx))
            response                            = successes[idx]
            for handle              in response.createdManifests():
                if handle.kind != 'workstream-metric':
                    continue # We are only aggregating metrics here
                inner_loop_trace                = loop_trace.doing("Retrieving manifest for manifest handle " + str(handle),
                                                        origination = {    
                                                                    'concrete class': str(self.__class__.__name__), 
                                                                    'signaled_from': __file__})
                manifest_dict, manifest_path    = self.kb.store.retrieveManifest(inner_loop_trace, handle)

                content_dict                    = manifest_dict['assertion']['metric']

                rep                             = AsDataframe_Representer()
                contents_path                   = 'assertion.metric'
                df                              = rep.dict_2_df(parent_trace, content_dict, contents_path)
                df['WUID']                      = manifest_dict['metadata']['labels']['workstreamUID']
                df_list.append(df)
        
        if len(df_list) == 0:
            return None, errors
        else:
            result_df                   = _pd.concat(df_list)
            return result_df, errors
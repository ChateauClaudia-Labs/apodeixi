
class FunctionalTrace():
    '''
    Data structure used to record useful information about errors. This can be thought as the functional analogue of
    a "stack trace". A stack trace shows the technical sequence of calls that leads to an error. This is not always useful
    to functionally identify what went wrong because it misses the functional context of what the code was supposed to
    be doing when the error was raised.

    To remedy this, the pattern used in Apodeixi is to use the `FunctionalTrace` object to record that functional context.
    In functional terms, the system is treated as if it was some sort of BPMN flow, with various functionally meaningful
    activities that connect sequentially, happen in parallel, fork into loops of lower-level activities, or join up.

    The `FunctionalTrace` data structure identifies the fragment of such BPMN logical flow that leads to the error.
    The BPNM could be thought as some kind of sorted tree. For a given node, its immediate children can be any of:
    
    * sub-activities ordered in the sequence in which they should happen.
    * a sub-activity that is looped over multiple times

    The `FunctionalTrace` records the branch of such conceptual BPNM tree, thus identifying top-down the functional
    intention that lead to wanting to execute the code for the leaf of such branch.
    '''
    def __init__(self, parent_trace):
        self.functional_purpose     = None
        self.parent_trace           = parent_trace # Caller's FunctionalTrace

    def doing(self, activity, flow_stage=None, data=None):
        '''
        Meant for a caller to create a new FunctionalTrace object that it can pass to a subroutine it is calling, 
        recording the step (`activity`) the caller is in the midst of processing as it invokes the subroutine.
        .
        The caller can optionally indicate some information about its flow to situate such activity. For example, it
        may set `flow_stage` to a message like "After validations of order A-123 are complete".

        Anything else worth recording can be put in the dictionary `data`

        @param activity         A string that identifies the activity the caller is in the midst of processing
        @param flow_stage       An optional string for caller to say where in its flow this activity sits (e.g., "after such and such" or
                                "before such and such")
        @param data             A dictionary or useful information about how the activity is being run (e.g., "4th cycle of loop" or
                                "in cycle of loop processing item ABC")
        '''
        if activity==None:
            raise ApodeixiError(self.parent_trace, "Can't create a FunctionalTrace with a null activity")
        if type(activity) != str:
            raise ApodeixiError(self.parent_trace, "Can't create a FunctionalTrace with a non-string activity of type " + str.type(activity))
        if len(activity.strip('\n '))==0:
            raise ApodeixiError(self.parent_trace, "Can't create a FunctionalTrace with a blank activity '" + activity + "'")        

        # Ensure context is non-null
        if data == None:
            data = {}
        if flow_stage == None:
            flow_stage = ''

        subroutine_ctx                      = FunctionalTrace(parent_trace=self)
        subroutine_ctx.functional_purpose   = { 'activity'  : activity, 
                                                'flow_stage': flow_stage,
                                                'data'      : data}
        return subroutine_ctx

    def examine(self):
        '''
        Can be thought of as analogous to a (technical) stack trace, but expressed in functional terms.

        Specifically, this method returns a top-down list of runtime "functional intentions and context" that lead to the point in the
        code when this is invoked. The index nth of the list can be considered "Level n" for nexted functional contexts, where
        "Level 0" is the most general, root level.

        The "functional intentions and context" (i.e., the members of the list returned) are dictionaries with three keys:
        * 'activity':   a string describing the functional intention at the current level
        * 'flow_stage': a string describing where in the current level's functional flow we are
        * 'data':       a dictionary of potentially other useful information.
        '''
        trace                   = []
        trace.append(self.functional_purpose)

        if self.parent_trace != None and self.parent_trace.functional_purpose != None:
            trace               = self.parent_trace.examine() + trace
        
        return trace


class ApodeixiError (Exception):
    '''
    Error class recommended in Apodeixi. It extends ValueError with a FunctionalTrace object to make troubleshooting
    easier.
    '''
    def __init__(self, functional_trace, msg):
        super().__init__(self, msg)
        self.functional_trace           = functional_trace
        self.msg                        = msg

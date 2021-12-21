import sys                                              as _sys
import traceback                                        as _traceback
from io                                                 import StringIO

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

    @param path_mask A function that takes a string argument and returns a string. Normally it is None, but
                it is used in situations (such as in regression testing) when observability should not
                report the paths "as is", but with a mask. For example, this can be used in regression
                tests to hide the user-dependent portion of paths, so that logs would otherwise display a path
                like:

                'C:/Users/aleja/Documents/Code/chateauclaudia-labs/apodeixi/test-knowledge-base/envs/big_rocks_posting_ENV/excel-postings'

                instead display a "masked" path where the user-specific prefix is masked, so that only the
                logical portion of the path (logical as in: it is the structure mandated by the KnowledgeStore)
                is displayed. In the above example, that might become:

                '<MASKED>/envs/big_rocks_posting_ENV/excel-postings'
    '''
    def __init__(self, parent_trace, path_mask):
        self.functional_purpose     = None
        self.parent_trace           = parent_trace # Caller's FunctionalTrace

        self.path_mask              = path_mask

    ACTIVITY                        = 'activity'
    DATA                            = 'data'
    FLOW_STAGE                      = 'flow_stage'
    ORIGINATION                     = 'origination'

    def doing(self, activity, flow_stage=None, data=None, origination=None):
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
        @param 'origination': a dictionary of stack-related information (may include folder information that varies per installation)
        '''
        if activity==None:
            raise ApodeixiError(self.parent_trace, "Can't create a FunctionalTrace with a null activity")
        if type(activity) != str:
            raise ApodeixiError(self.parent_trace, "Can't create a FunctionalTrace with a non-string activity of type " + str.type(activity))
        if len(activity.strip('\n '))==0:
            raise ApodeixiError(self.parent_trace, "Can't create a FunctionalTrace with a blank activity '" + activity + "'")        

        # Ensure context is non-null
        if data == None:
            data                            = {}
        if flow_stage == None:
            flow_stage                      = ''
        if origination == None:
            origination                     = {}

        subroutine_ctx                      = FunctionalTrace(parent_trace=self, path_mask=self.path_mask)
        subroutine_ctx.functional_purpose   = { FunctionalTrace.ACTIVITY        : activity, 
                                                FunctionalTrace.FLOW_STAGE      : flow_stage,
                                                FunctionalTrace.DATA            : data,
                                                FunctionalTrace.ORIGINATION     : origination}

        return subroutine_ctx

    def examine(self, as_string=False, exclude_origination=False):
        '''
        Can be thought of as analogous to a (technical) stack trace, but expressed in functional terms.

        Specifically, this method produces a top-down list of runtime "functional intentions and context" that lead to the point in the
        code when this is invoked. The index nth of the list can be considered "Level n" for nexted functional contexts, where
        "Level 0" is the most general, root level.

        The "functional intentions and context" (i.e., the members of the list returned) are dictionaries with three keys:
        * 'activity:   a string describing the functional intention at the current level
        * 'flow_stage': a string describing where in the current level's functional flow we are
        * 'data':       a dictionary of potentially other useful information.
        * 'origination': a dictionary of stack-related information (may include folder information that varies per installation)

        Dependingon the `as_string` flag, this method either returns such list of dictionaries or a string that formats
        them nicely for display on a termina.
        '''
        trace                   = []
        if as_string:
            trace.append(self._format_functional_trace(exclude_origination))
        else:
            trace.append(self.functional_purpose)

        if self.parent_trace != None and self.parent_trace.functional_purpose != None:
            trace               = self.parent_trace.examine(as_string=as_string, exclude_origination=exclude_origination) + trace
        
        return trace

    def _format_functional_trace(self, exclude_origination):
        '''
        Returns a human-readable string with the content of the functional trace
        '''
        def MSK(txt): # Abbreviaation for the masking logic
            if self.path_mask != None:
                return self.path_mask(txt)
            else:
                return txt

        if self.functional_purpose == None:
            return ''
        result                  = ''
        result                  += '---->\tactivity\t'  + MSK(self.functional_purpose[FunctionalTrace.ACTIVITY]) + '\n'
        
        flow_stage              = self.functional_purpose[FunctionalTrace.FLOW_STAGE]
        if flow_stage != None and len(flow_stage.strip()) > 0:
            result              += '\n' + MSK(FunctionalTrace._ins(FunctionalTrace.FLOW_STAGE)) + ': ' \
                                    + MSK(self.functional_purpose[FunctionalTrace.FLOW_STAGE])
        data                    = self.functional_purpose[FunctionalTrace.DATA]
        for k in data.keys():
            result              += '\n' + MSK(FunctionalTrace._ins(k)) + ': ' + MSK(str(data[k]))

        origination             = self.functional_purpose[FunctionalTrace.ORIGINATION]
        if not exclude_origination:
            for k in origination.keys():
                result      += '\n' + MSK(FunctionalTrace._ins(k)) + ': ' + MSK(str(origination[k]))
        return result

    def _ins(txt):
        '''
        Helper method that returns a string of 32 characters, starting with 12 spaces and then txt followed by padding
        '''
        allowed_txt_length  = min (20, len(txt))
        allowed_txt         = txt[0:allowed_txt_length]
        padding_length      = 20 - allowed_txt_length
        padding             = ' ' * padding_length
        indentation         = ' ' * 12

        return indentation + allowed_txt + padding

class ApodeixiError (Exception):
    '''
    Error class recommended in Apodeixi. It extends ValueError with a FunctionalTrace object to make troubleshooting
    easier.

    @param external_stacktrace A string, containing the stacktrace for a component external to Apodeixi which
        resulted in failure. The component is "external" in the logical sense - it may well be in-process with
        Apodeixi. What makes it "external" is that it is code to which Apodeixi cedes control as a "black box",
        and if the "black box" fails Apodeixi raises a new ApodeixiError from the point at which the "black box"
        was invoked by Apodeixi.
        Thus, the ApodeixiError's stack trace only can tell us when Apodeixi knew something went wrong, but not
        the root cause of the problem within the external code. To assist debugging such problems, the construction
        of an ApodeixiError allows for attaching the external code's stack trace as an optional string. 
    '''
    def __init__(self, functional_trace, msg, data={}, origination={}, external_stacktrace=None):
        super().__init__(self, msg)
        self.functional_trace           = functional_trace
        self.msg                        = msg
        self.data                       = data
        self.origination                = origination
        self.external_stacktrace        = external_stacktrace

    def trace_message(self, exclude_stack_trace=False):

        def MSK(txt): # Abbreviation for the masking logic
            if self.functional_trace.path_mask != None:
                return self.functional_trace.path_mask(txt)
            else:
                return txt

        data_msg                    = ''
        for k in self.data.keys():
            data_msg                += '\n' + MSK(FunctionalTrace._ins(k)) + ': ' + MSK(str(self.data[k]))
        if not exclude_stack_trace:
            for k in self.origination.keys():
                data_msg            += '\n' + MSK(FunctionalTrace._ins(k)) + ': ' + MSK(str(self.origination[k]))
        if len(data_msg) > 0:
            data_msg                = '\n' + data_msg + '\n'

        advertisement_for_stack_trace = ''
        if not exclude_stack_trace:
            if self.external_stacktrace == None:
                advertisement_for_stack_trace = ' (stack trace at the bottom)'
            else:
                advertisement_for_stack_trace = '\n(failure occurred in an external component. So 2 strack traces are '\
                                    + 'provided at the bottom: '\
                                    + '\n\t-one originating from Apodeixi\'s invocation of the external component, '\
                                    + '\n\t-and one for the external component itself)'
        trace_msg               = '\n\n******** Functional Trace ********\n\n' + 'Problem:\t' + self.msg + data_msg \
                                    + '\nHere are the functional activities that led to the problem' \
                                    +  advertisement_for_stack_trace + ':' \
                                    + '\n\n' \
                                    + '\n\n'.join([str(trace_level) for trace_level in self.functional_trace.examine(as_string=True,
                                                                                        exclude_origination=exclude_stack_trace)]) \
                                    + '\n'   
        if not exclude_stack_trace:
            traceback_stream        = StringIO()
            _traceback.print_exc(file = traceback_stream)
            if self.external_stacktrace == None:
                trace_msg           += "\n" + "-"*60 + '\tTechnical Stack Trace\n\n'            
                trace_msg           += traceback_stream.getvalue()
                trace_msg           += "\n" + "-"*60  
            else:
                trace_msg           += "\n" + "-"*60 + '\tTechnical Stack Trace 1 of 2 (in external component)\n\n' 
                trace_msg           += self.external_stacktrace
                trace_msg           += "\n" + "-"*60 + '\tTechnical Stack Trace 2 of 2 (within Apodeixi)\n\n' 
                trace_msg           += traceback_stream.getvalue()
                trace_msg           += "\n" + "-"*60  
            
        return trace_msg

    
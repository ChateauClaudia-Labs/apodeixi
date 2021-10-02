import sys                                              as _sys
import warnings
import traceback
from io                                                 import StringIO

from apodeixi.util.a6i_error                            import ApodeixiError

class WarningUtils():

    def __init__(self):
        pass

    def turn_traceback_on(self, parent_trace):
        '''
        This method ensures that warnings print stack traces.

        Returns a StringIO object, to which stack traces are printed, that the caller can then examine, print, or dispose
        of as appropriate.

        The intention is to pin down the origin of warnings, in the case of warnings that should be caught in Apodeixi.
        For example, noisy warning that must be ignored, or serious warnings that should become errors.

        One of the motivations is to prevent warnings from creeping into test regression output, particularly in the CLI, 
        where that noise may be non-deterministic and cause spurious test failures.

        Implementation is as suggested in https://stackoverflow.com/questions/22373927/get-traceback-of-warnings 
        '''
        traceback_stream        = StringIO()
        def _warn_with_traceback(message, category, filename, lineno, file=None, line=None):

            #log = file if hasattr(file,'write') else _sys.stderr
            log = traceback_stream
            traceback.print_stack(file=log)
            log.write(warnings.formatwarning(message, category, filename, lineno, line))

        warnings.showwarning        = _warn_with_traceback 

        return traceback_stream

    def handle_yaml_warnings(self, parent_trace, warning_list, path, traceback_stream):
        '''
        Helper method for this class when invoking persistent methods of the yaml Python module.
        That module invokes asyncio.base_events.py, which as of this writing (September 2021) is noisy and
        prints out spurious ResourceWarnings about "unclosede event loop...". This method catches
        and ignores such warnings.

        For any other warnings, this method catches them and turns them into ApodeixiErrors.
        '''   
        if len(warning_list) == 1 and warning_list[0].category == ResourceWarning \
                                and str(warning_list[0].message).startswith("unclosed event loop"):
            #Ignore such warnings - they are noise
            pass
        else:
            self.handle_warnings(parent_trace, warning_list, traceback_stream)

    def handle_warnings(self, parent_trace, warning_list, traceback_stream):
        '''
        Helper method to catch warnings and turns them into ApodeixiErrors.
        '''   
        if len(warning_list) > 0:
            warning_dict                                = {}
            for idx in range(len(warning_list)):
                a_warning                               = warning_list[idx]
                warning_dict['Warning ' + str(idx)]     = str(a_warning.message)
                warning_dict['... from']                = str(a_warning.filename)
                warning_dict['... at line']             = str(a_warning.lineno)

            trace_msg                                   = "\n" + "-"*60 + "\tWarnings Stack Trace\n\n"
            trace_msg                                   += traceback_stream.getvalue()
            trace_msg                                   += "\n" + "-"*60
            warning_dict['Stack Trace']                 = trace_msg

            raise ApodeixiError(parent_trace, "A dependency issued at least one warning",
                                    data = {} | warning_dict)  

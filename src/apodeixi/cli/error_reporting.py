import datetime                                     as _datetime
import sys                                          as _sys
import os                                           as _os
import traceback                                    as _traceback
from io                                             import StringIO

from apodeixi.knowledge_base.kb_environment         import File_KBEnv_Impl
from apodeixi.util.a6i_error                        import FunctionalTrace, ApodeixiError
from apodeixi.util.path_utils                       import PathUtils

class bcolors:
    '''
    Color formatting in bash based on:
                   https://stackoverflow.com/questions/287871/how-to-print-colored-text-to-the-terminal
     
    See lso https://misc.flogisoft.com/bash/tip_colors_and_formatting for more codes, but beware
    that their "\e[" should be "\33e[" for it to work in my platform
    '''
    HEADER          = '\033[95m'        # Light magenta
    OKBLUE          = '\033[94m'        # Light blue
    OKCYAN          = '\033[96m'        # Light cyan
    OKGREEN         = '\033[92m'        # light green
    WARNING         = '\033[93m'        # Light yellow
    POINTERS        = '\033[38;5;110m'  # Light purple-like color
    FAIL            = '\033[91m'        # Light red
    ENDC            = '\033[0m'         # Resets everything
    BOLD            = '\033[1m'
    DIM             = '\033[2m'
    UNDERLINE       = '\033[4m'
    BLINK           = '\033[5m'
    INVERTED        = '\033[7m'
    HIDDEN          = '\033[8m'         # Useful for passwords
    
    

class CLI_ErrorReporting():
    '''
    Class to format and stream error information for the Apodeixi CLI. High level information will be displayed to
    end-users in standard output, and more detailed information will be persisted in logs.

    @param kb_session A KB_Session object with the KnowledegeBase-related state and configuration for the 
            CLI session during which the error arose.
    '''
    def __init__(self, kb_session):
        self.kb_session                 = kb_session
        return

    def _report_error(self, parent_trace, error, report_header):
        '''
        Helper method to enrich the `report_header` that describes an error with tracing information
        and links for the error

        @param error An instance of ApodeixiError or Exception. The kind of tracing information differs based on the class.

        @param report_header A string, with a high level description of the error.

        @returns A string that extends `report_header` with additional tracing information
        '''
        high_level_msg                  = report_header
        if self.kb_session != None:
            log_folder                  = self.kb_session.kb_rootdir + "/" + File_KBEnv_Impl.LOGS_FOLDER
            PathUtils().create_path_if_needed(parent_trace = parent_trace, path = log_folder)

            log_filename                = self.kb_session.timestamp + "_errors.txt"

            dt                          = _datetime.datetime.today()

            tokens                      = _sys.argv
            executable_path             = tokens[0]
            executable_name             = _os.path.split(executable_path)[1]
            command_typed_by_user       = executable_name + " " + " ".join(tokens[1:])

            detailed_msg                = dt.strftime("[%H:%M:%S %a %d %b %Y] => ") + command_typed_by_user

            if issubclass(type(error), ApodeixiError):
                trace_msg               = self._a6i_error_trace(error)
            elif issubclass(type(error), Exception):
                trace_msg               = self._generic_error_trace(error)
            else:
                raise ApodeixiError(parent_trace, "Can't report error because it is not an Exception",
                                        data = {"type(error)": str(type(error)), "error": str(error)})

            detailed_msg                += trace_msg

            with open(log_folder + "/" + log_filename, "a") as f:
                f.write(detailed_msg)

            high_level_msg              += self.POINTERS("\n\nCheck error log at ")
            high_level_msg              += self.POINTERS(self.UNDERLINE("file:///" + log_folder + "/" + log_filename))

        return high_level_msg

    def report_a6i_error(self, parent_trace, a6i_error):
        '''
        Displays a high-level summary of the `a6i_error`, with detailed information saved to a log file.

        The log file will be in the folder called 

        @param a6i_error An ApodeixiError object whose content must be reported to the user.
        '''
        def MSK(txt): # Abbreviation for the masking logic
            if a6i_error.functional_trace.path_mask != None:
                return a6i_error.functional_trace.path_mask(txt)
            else:
                return txt
        data_msg                    = ''
        for k in a6i_error.data.keys():
            data_msg                += '\n' + MSK(FunctionalTrace._ins(k)) + ': ' + MSK(str(a6i_error.data[k]))
        if len(data_msg) > 0:
            data_msg                = '\n' + data_msg + '\n'

        report_header               = self.FAIL("\n" + a6i_error.msg + data_msg)

        high_level_msg              = self._report_error(parent_trace, a6i_error, report_header)

        return high_level_msg

    def report_generic_error(self, parent_trace, generic_error):
        '''
        Displays a high-level summary of the `generic_error`, with detailed information saved to a log file.

        The log file will be in the folder called 

        @param generic_error An Exception object whose content must be reported to the user.
        '''
        report_header               = "Encountered an unexpected error\n\n"
        report_header               += "\tException type: " + str(type(generic_error)) + "\n"
        report_header               += "\tError message:" + str(generic_error) + "\n\n"

        high_level_msg              = self._report_error(parent_trace, generic_error, report_header)

        return high_level_msg

    def _a6i_error_trace(self, a6i_error):
        '''
        Returns a string, corresponding a formatted (i.e., with headers, footers) stack trace for the
        `a6i_error`

        @param a6i_error An instance of the ApodeixiError class
        '''   
        return a6i_error.trace_message(exclude_stack_trace=False)

    def _generic_error_trace(self, generic_error):
        '''
        Returns a string, corresponding a formatted (i.e., with headers, footers) stack trace for the
        `generic_error`

        @param generic_error An instance of the Exception class
        '''
        traceback_stream        = StringIO()
        trace_msg               = "\n" + "-"*60 + '\tTechnical Stack Trace\n\n'
        _traceback.print_exc(file = traceback_stream)
        trace_msg               += traceback_stream.getvalue()
        trace_msg               += "\n" + "-"*60  
        return trace_msg

    def FAIL(self, txt):
        return bcolors.FAIL + txt + bcolors.ENDC

    def UNDERLINE(self, txt):
        return bcolors.UNDERLINE + txt + bcolors.ENDC

    def POINTERS(self, txt):
        return bcolors.POINTERS + txt + bcolors.ENDC
 
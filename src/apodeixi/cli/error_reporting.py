import datetime                                     as _datetime
import sys                                          as _sys
import os                                           as _os

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

        high_level_msg              = self.FAIL("\n" + a6i_error.msg + data_msg)

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
            detailed_msg                = detailed_msg + a6i_error.trace_message(exclude_stack_trace=False)

            with open(log_folder + "/" + log_filename, "a") as f:
                f.write(detailed_msg)

            high_level_msg              += self.POINTERS("\n\nCheck error log at ")
            high_level_msg              += self.POINTERS(self.UNDERLINE("file:///" + log_folder + "/" + log_filename))

        return high_level_msg

    def FAIL(self, txt):
        return bcolors.FAIL + txt + bcolors.ENDC

    def UNDERLINE(self, txt):
        return bcolors.UNDERLINE + txt + bcolors.ENDC

    def POINTERS(self, txt):
        return bcolors.POINTERS + txt + bcolors.ENDC
 
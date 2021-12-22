import sys                                              as _sys
import pandas                                           as _pd
import warnings
import traceback
from io                                                 import StringIO

from apodeixi.util.a6i_error                            import ApodeixiError

class ApodeixiWarningMessage(warnings.WarningMessage):
    '''
    Helper data structure used by WarningUtils. It extends the parent class with additional stack trace
    information that Apodeixi is interested in getting for warnings that get raised by dependencies used by
    Apodeixi, to assist the developer in understanding where the warnings are being raised from

    @param stacktrace: A string, representing the stack trace from which a warning was raised
    '''
    def __init__(self, message, stacktrace, category, filename, lineno, file=None, line=None, source=None):
        super().__init__(message, category, filename, lineno, file, line, source)

        self.stacktrace             = stacktrace

class WarningUtils():

    def __init__(self):
        pass

    def turn_traceback_on(self, parent_trace, warnings_list):
        '''
        This method ensures that warnings print stack traces.

        Returns a StringIO object, to which stack traces are printed, that the caller can then examine, print, or dispose
        of as appropriate.

        The intention is to pin down the origin of warnings, in the case of warnings that should be caught in Apodeixi.
        For example, noisy warning that must be ignored, or serious warnings that should become errors.

        One of the motivations is to prevent warnings from creeping into test regression output, particularly in the CLI, 
        where that noise may be non-deterministic and cause spurious test failures.

        Implementation is as suggested in https://stackoverflow.com/questions/22373927/get-traceback-of-warnings 

        @param warnings_list A list, as created by the warnings.catch_warnings context manager, to which we will be
            appending each warning's message as an element to that list.
        '''
        def _warn_with_traceback(message, category, filename, lineno, file=None, line=None):

            log                     = StringIO()
            traceback.print_stack(file=log)
            log.write(warnings.formatwarning(message, category, filename, lineno, line))
            stacktrace              = log.getvalue()
            warn_msg                = ApodeixiWarningMessage(message, stacktrace, category, filename, lineno, file, line)
            warnings_list.append(warn_msg)

        warnings.showwarning        = _warn_with_traceback 

    def check_if_user_error(self, parent_trace, a_warning):
        '''
        Helper method for this class to handle certain warnings that Apodeixi considers user errors, as
        opposed to development-type errors.

        Normally 3rd-party warnings should be pre-empted at development time by the Apodeixi developers
        using those 3rd party dependencies correctly, avoiding code constructs that the 3rd party flags as
        risky or deprecated.

        However, in some cases the warning is really a user error, so the remedy lies with the user. However,
        the warning is probably very unfriendly to the user, so it should be converted to something more
        Apodeixi-like and less about the 3rd party dependency.

        That is the purpose of this method: if a warning is user error, it will raise an ApodeixiError with
        as friendly a message as possible. Otherwise, it does nothing.
        '''
        if str(a_warning.message).startswith("Defining usecols with out of bounds indices is deprecated"):
            # This is Pandas warning that happens when the user submits an Excel posting with a range of
            # columns that includes blank columns. For example, the user might submit H2:L30 as a range,
            # but if column L is blank, then the user should instead have submitted H2:K30
            #
            warning_dict        = {"Problem encountered": a_warning.message}
            raise ApodeixiError(parent_trace, "Something went wrong, most probably because you might be attempting "
                                            + "to post an Excel file and one of the PostingLabel's ranges includes empty "
                                            + "Excel columns. If so, please correct your PostingLabel and try again.",
                                data = warning_dict,
                                external_stacktrace     = a_warning.stacktrace)

        else:
            pass

    def check_if_should_ignore(self, parent_trace, a_warning):
        '''
        Helper method for this class to handle certain warnings from 3rd party libraries that Apodeixi should ignore.
        
        This method returns True if the warning should be ignored, and False otherwise
        '''
        if a_warning.category == ResourceWarning and str(a_warning.message).startswith("unclosed event loop"):
            #Ignore such warnings - they are noise generated by YAML
            return True

        elif a_warning.category == UserWarning and str(a_warning.message).startswith("Data Validation extension is not supported and will be removed"):
            # Ignore such warnings - they are noise generated by openpyxl that Pandas just transmits up to
            # Apodeixi. So it is "Pandas noise", i.e., Pandas is using openpyxl in a way that triggers warnings,
            # deep down and hidden from the Pandas API that Apodeixi gets to see. So not much Apodeixi can do other
            # than ignore it.
            return True
        elif a_warning.category == _pd.errors.PerformanceWarning and str(a_warning.message).startswith("dropping on a non-lexsorted multi-index without a level parameter may impact performance"):
            # Pandas generates this when we group by a column that is not a tuple when other columns are tuples
            # So ignore it - our reporting routinely does such group-by operations
            return True
        else:
            return False

    def handle_warnings(self, parent_trace, warning_list):
        '''
        Helper method to catch warnings and turns them into ApodeixiErrors.
        '''   
        if len(warning_list) > 0:
            warning_dict                                = {}
            for idx in range(len(warning_list)):
                a_warning                               = warning_list[idx]
                self.check_if_user_error(parent_trace, a_warning)
                if self.check_if_should_ignore(parent_trace, a_warning):
                    # In this case, this particular warning should not trigger an ApodeixiError.
                    # So ignore it and move on to examining the next warning
                    continue

                warning_dict['Warning ' + str(idx)]     = str(a_warning.message)
                warning_dict['... from']                = str(a_warning.filename)
                warning_dict['... at line']             = str(a_warning.lineno)

                trace_msg                               = "\n" + "-"*60 + "\tWarnings Stack Trace\n\n"
                trace_msg                               += str(a_warning.stacktrace)
                trace_msg                               += "\n" + "-"*60
                warning_dict['Stack Trace']             = trace_msg

            if len(warning_dict.keys()) > 0:
                raise ApodeixiError(parent_trace, "A dependency issued " + str(len(warning_list)) + " warning(s)",
                                    data = {} | warning_dict)  

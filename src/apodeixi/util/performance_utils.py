import datetime                         as _datetime
import re                               as _re


class ApodeixiTimer():
    '''
    Used to measure elapsed time from the time this object was constructed to the time its methods get invoked
    '''
    def __init__(self):

        self.T0                         = _datetime.datetime.now()

    def elapsed_time(self):
        '''
        Returns a datetime.timedelta object, corresponding to the amount of time elapsed since the construction of
        this object to the time this method is called
        '''
        T1                              = _datetime.datetime.now()
        delta                           = T1 - self.T0
        return delta
    
    def elapsed_time_message(self):
        '''
        Returns a string, expressing the amount of time elapsed since the construction of
        this object to the time this method is called        
        '''
        delta                           = self.elapsed_time()
        delta_msg                       = str(delta.seconds) + "." + str(delta.microseconds) + " sec"
        return delta_msg

    def get_mask_lambda(self, parent_trace):
        '''
        Returns a mask function to hide any line that displays an ApodeixiTimer's elapsed time message.

        A mask function takes a string argument and returns a string. 
        It is used in situations (such as in regression testing) when observability should not
        include non-deterministic information such as performance data.
        
        For example, without a mask function regression tests might output text that displays lines like:
    

                0.280188 sec

        By contrast, if the regression tests feeds that path to the "mask lambda" returned by this method, the
        modified regression output would not contain such a line

        The mask is separately applied "line-by-line".
        '''
        def _elapsed_time_mask(raw_txt):
            '''
            '''
            if type(raw_txt) != str:
                return raw_txt
            lines                                                   = raw_txt.split("\n")
            cleaned_lines                                           = []
            REGEX = "^[0-9]+.[0-9]+ sec$" # Something like '0.280188 sec'
            pattern = _re.compile(REGEX)
            for line in lines:
                if pattern.match(line) != None:
                    # This line's content is a displayed time message, so don't include this line in the output.
                    # So just move to the next line
                    continue
                else:
                    cleaned_lines.append(line)

            cleaned_txt                     = "\n".join(cleaned_lines)
            return cleaned_txt

        return _elapsed_time_mask
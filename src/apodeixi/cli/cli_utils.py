from posixpath import expanduser
from apodeixi.util.a6i_error                        import ApodeixiError

class CLI_Utils():
    '''
    Utility methods to help with CLI functionality
    '''
    def __init__(self):
        return

    # Static portions of sandbox announcements that should be structured like 
    # 
    #               "Using sandbox '210821.142725_sandbox'...\n"
    #
    PREFIX_EXPECTED             = "Using sandbox '"
    SANDBOX_NAME_LENGTH         = len("210821.142725_sandbox")    
    SUFFIX_EXPECTED             = "'..."

    def sandox_announcement(self, sandbox_name):
        '''
        Returns a string, which the standard message used when notifying the user that we are running in a sandbox
        '''
        ME                      = CLI_Utils
        return ME.PREFIX_EXPECTED + str(sandbox_name) + ME.SUFFIX_EXPECTED

    def parse_sandbox_announcement(self, parent_trace, announcement):
        '''
        Validates that the `announcement` is of the form "Using sandbox '210821.142725_sandbox'",
        and if so it returns the name of the sandbox, which in the example is '210821.142725_sandbox'

        If `announcement` does not conform with the expected form, this method raises an ApodeixiError
        '''
        ME                      = CLI_Utils
        if len(announcement) != (len(ME.PREFIX_EXPECTED) + ME.SANDBOX_NAME_LENGTH + len(ME.SUFFIX_EXPECTED)) \
            or not announcement.startswith(ME.PREFIX_EXPECTED) \
            or not announcement.endswith(ME.SUFFIX_EXPECTED):
            raise ApodeixiError(parent_trace, "Announcement is not in the expected form",
                                    data = {"announcement":     announcement,
                                            "expected":  self.sandox_announcement("<sandbox name>")})

        sandbox_name_start_idx  = len(ME.PREFIX_EXPECTED)
        sandbox_name_end_idx    = sandbox_name_start_idx + ME.SANDBOX_NAME_LENGTH
        sandbox_name            = announcement[sandbox_name_start_idx:sandbox_name_end_idx]

        return sandbox_name 

    def mask_sandbox_lambda(self, parent_trace):
        '''
        Returns a lambda that masks the sandbox name in a sandbox announcement.
        The sandbox announcement is required to be the first output that the CLI streamed to standard output
        in response to a user-entered command.
        '''
        def _mask_lambda(output_txt):
            '''
            Assumes output_txt starts with something like "Using sandbox '210821.142725_sandbox'\n..."
            and returns a modified string where the sandbox name "210821.142725_sandbox" is masked but
            all other content is left the same
            '''
            # output_lines should be something like 
            # 
            #       ["Using sandbox '210821.142725_sandbox'", ...] 
            #
            output_lines                            = output_txt.split('\n')
            ANNOUNCEMENT_IDX                        = 0
            # Remove the timestamp before checking that the output lines match our expectations
            assert len(output_lines) >= ANNOUNCEMENT_IDX+1
            dry_run_msg                             = output_lines[ANNOUNCEMENT_IDX]

            sandbox_name = CLI_Utils().parse_sandbox_announcement(  parent_trace    = parent_trace, 
                                                                    announcement    = dry_run_msg)
            cleaned_output_lines                    = output_lines.copy()
            cleaned_output_lines[ANNOUNCEMENT_IDX]  = CLI_Utils().sandox_announcement("<MASKED>") 

            cleaned_txt                             = '\n'.join(cleaned_output_lines)
            return cleaned_txt

        return _mask_lambda

    def infer_sandbox_name(self, parent_trace, output_txt):
        '''
        Assumes output_txt starts with something like "Using sandbox '210821.142725_sandbox'\n..."
        and returns the substring corresponding to the sandbox name, which in the example would be
        a"210821.142725_sandbox" 

        If the output_txt does not conform with the expected format, it returns None
        '''
        # output_lines should be something like 
        # 
        #       ["Using sandbox '210821.142725_sandbox'", ...] 
        #
        output_lines                            = output_txt.split('\n')
        ANNOUNCEMENT_IDX                        = 0
        # Remove the timestamp before checking that the output lines match our expectations
        if len(output_lines) < ANNOUNCEMENT_IDX+1:
            return None

        dry_run_msg                             = output_lines[ANNOUNCEMENT_IDX]
        try:
            sandbox_name = CLI_Utils().parse_sandbox_announcement(  parent_trace    = parent_trace, 
                                                                    announcement    = dry_run_msg)
        except ApodeixiError as ex:
            return None

        return sandbox_name
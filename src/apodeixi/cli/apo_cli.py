import sys                                  as _sys
import os                                   as _os
from apodeixi.cli.cli_utils import CLI_Utils
import click

import apodeixi
from apodeixi.cli.kb_session                import KB_Session
from apodeixi.cli.error_reporting           import CLI_ErrorReporting
from apodeixi.util.a6i_error                import FunctionalTrace, ApodeixiError

pass_kb_session                             = click.make_pass_decorator(KB_Session, ensure=True)

@click.group() 
@click.version_option(message="Apodeixi v" + apodeixi.__version__)
def apo_cli():
    '''
    Apodeixi KnowledgeBase command tool
    '''

@apo_cli.command()
@click.argument("file", type=click.STRING, required=True)
@click.option('--dry-run/--no-dry-run', default=False)
@click.option('--sandbox', type=click.STRING,help="Name of pre-existing sandbox within which to isolate processing")
@click.option('--timestamp', type=click.STRING,help="String used to tag KnowledgeBase posting logs, instead of the actual time")
@pass_kb_session
def post(kb_session, file, dry_run, sandbox, timestamp):
    '''
    Posts contents of an Excel file to the a6d KnowledgeBase. 
    The file must be named with a name consistent with supported a6i posting APIs.
    '''
    try:
        func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                                path_mask       = None) 
        root_trace                          = func_trace.doing("CLI call to post",
                                                                origination     = {'signaled_from': __file__})



        if sandbox:
            kb_session.store.activate(parent_trace = root_trace, environment_name = sandbox)
            click.echo(CLI_Utils().sandox_announcement(sandbox))
        elif dry_run:
            sandbox_name                    = kb_session.provisionSandbox(root_trace)
            click.echo(CLI_Utils().sandox_announcement(sandbox_name))
        else:
            raise ApodeixiError(root_trace, "Sorry, only dry runs are supported at this time. Aborting.")

        # Now that we have pinned down the environment (sandbox) in which to call the KnowledgeBase's services,
        # set that environment's tag to use for KnoweldgeBase's posting logs, if the user set it.
        if timestamp:
            kb_session.store.current_environment(root_trace).config(root_trace).use_timestamps = timestamp

        if len(_os.path.split(file)[0]) == 0: # This must be a local file in our working directory, no folder was given
            file                            = _os.getcwd() + "/" + file
        my_trace                            = root_trace.doing("Invoking KnowledgeBase's postByFile service")
        response, log_txt                   = kb_session.kb.postByFile( parent_trace                = my_trace, 
                                                                        path_of_file_being_posted   = file, 
                                                                        excel_sheet                 = "Posting Label")

        output                              = "Success"
        click.echo(output)
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()




import sys                                  as _sys
import os                                   as _os
from apodeixi.cli.cli_utils import CLI_Utils
from apodeixi.util.path_utils import PathUtils
import click
from tabulate                               import tabulate

import apodeixi
from apodeixi.cli.kb_session                import KB_Session
from apodeixi.cli.error_reporting           import CLI_ErrorReporting
from apodeixi.representers.as_dataframe     import AsDataframe_Representer
from apodeixi.util.a6i_error                import FunctionalTrace, ApodeixiError
from apodeixi.util.dictionary_utils         import DictionaryUtils
from apodeixi.xli.interval                  import Interval

pass_kb_session                             = click.make_pass_decorator(KB_Session, ensure=True)

@click.group() 
@click.version_option(message="Apodeixi v" + apodeixi.__version__)
def apo_cli():
    '''
    Apodeixi KnowledgeBase command tool
    '''

@apo_cli.group()
@pass_kb_session
def get(kb_session):
    '''
    Retrieves the specified data type from the KnowledgeBase store
    '''

@get.command()
@pass_kb_session
def namespaces(kb_session):
    '''
    Gets the list of valid namespaces for the system
    '''
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get namespace",
                                                            origination     = {'signaled_from': __file__})
    try:
        namespaces_description          = CLI_Utils().get_namespaces(root_trace, kb_session)
        click.echo(namespaces_description)
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()

@get.command()
@click.option('--all/--no-all', default=False, help="If set, products across both the base environment and all sandboxes will be returned")
@click.option('--sandbox', type=click.STRING,help="If provided, then only products in the given sandbox will be returned")
@pass_kb_session
def products(kb_session, all, sandbox):
    '''
    Gets the list of valid products for the system.
    '''
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get products",
                                                            origination     = {'signaled_from': __file__})
    try:
        environment_filter              = _get_environment_filter(root_trace, kb_session, all, sandbox)
        products_description            = CLI_Utils().get_products(root_trace, kb_session, environment_filter)
        click.echo(products_description)
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()

def _get_environment_filter(parent_trace, kb_session, all, sandbox):
    '''
    Helper method to get filter for which environment to look into when searching in the KnowledgeBase
    store.
    '''
    if all==True:
        environment_filter              = CLI_Utils().get_environment_filter(parent_trace, kb_session, 
                                                        filter_type = CLI_Utils.ANY_ENV_FILTER, sandbox=None)
    elif sandbox != None:
        click.echo(CLI_Utils().sandox_announcement(sandbox))
        environment_filter              = CLI_Utils().get_environment_filter(parent_trace, kb_session, 
                                                        filter_type = CLI_Utils.SPECIFIC_SANDBOX_ENV_FILTER, sandbox=sandbox)
    else:
        environment_filter              = CLI_Utils().get_environment_filter(parent_trace, kb_session, 
                                                        filter_type = CLI_Utils.ONLY_BASE_ENV_FILTER, sandbox=sandbox)
    return environment_filter

@get.command()
@click.option('--all/--no-all', default=False, help="If set, scoring cycles across both the base environment and all sandboxes will be returned")
@click.option('--sandbox', type=click.STRING,help="If provided, then only scoring cycles in the given sandbox will be returned")
@pass_kb_session
def scoring_cycles(kb_session, all, sandbox):
    '''
    Gets the list of valid scoring cycles for the system.
    '''
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get scoring cycles",
                                                            origination     = {'signaled_from': __file__})
    try:
        environment_filter              = _get_environment_filter(root_trace, kb_session, all, sandbox)
        sc_description                  = CLI_Utils().get_scoring_cycles(root_trace, kb_session, environment_filter)
        click.echo(sc_description)
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()

@get.command()
@pass_kb_session
def sandboxes(kb_session):
    '''
    Gets the list of existing sandboxes for the system.
    '''
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get sandboxes",
                                                            origination     = {'signaled_from': __file__})
    try:
        sandboxes_description           = CLI_Utils().get_sandboxes(root_trace, kb_session)
        click.echo(sandboxes_description)
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()

@get.command()
@pass_kb_session
def posting_apis(kb_session):
    '''
    Gets the list of posting APIs supported by the KnowledgeBase
    '''
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get posting APIs",
                                                            origination     = {'signaled_from': __file__})
    try:
        posting_apis_description        = CLI_Utils().get_posting_apis(root_trace, kb_session)
        click.echo(posting_apis_description)
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()

@apo_cli.command()
@click.argument("file", type=click.STRING, required=True)
@click.option('--dry-run/--no-dry-run', default=False)
@click.option('--sandbox', type=click.STRING,help="Name of pre-existing sandbox within which to isolate processing")
@click.option('--timestamp', type=click.STRING,help="String used to tag KnowledgeBase posting logs, instead of the actual time")
@pass_kb_session
def post(kb_session, file, dry_run, sandbox, timestamp):
    '''
    Posts contents of an Excel file to the KnowledgeBase.
    The filename must be of the form '<some string><posting API>.xlsx' for some supported a6i posting API.
    '''
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to post",
                                                            origination     = {'signaled_from': __file__})
    try:
        if sandbox != None:
            kb_session.store.activate(parent_trace = root_trace, environment_name = sandbox)
            click.echo(CLI_Utils().sandox_announcement(sandbox))
        elif dry_run == True:
            sandbox_name                    = kb_session.provisionSandbox(root_trace)
            click.echo(CLI_Utils().sandox_announcement(sandbox_name))
        else:
            raise ApodeixiError(root_trace, "Sorry, only sandbox-isolated runs are supported at this time. Aborting.")

        # Now that we have pinned down the environment (sandbox or not) in which to call the KnowledgeBase's services,
        # set that environment's tag to use for KnoweldgeBase's posting logs, if the user set it.
        if timestamp:
            kb_session.store.current_environment(root_trace).config(root_trace).use_timestamps = timestamp

        if len(_os.path.split(file)[0]) == 0: # This must be a local file in our working directory, no folder was given
            file                            = _os.getcwd() + "/" + file
        my_trace                            = root_trace.doing("Invoking KnowledgeBase's postByFile service")
        response, log_txt                   = kb_session.kb.postByFile( parent_trace                = my_trace, 
                                                                        path_of_file_being_posted   = file, 
                                                                        excel_sheet                 = "Posting Label")
        manifests_description               = CLI_Utils().describe_response(my_trace, response, kb_session.store)

        click.echo(manifests_description)
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


@get.command()
@click.argument("posting-api", type=click.STRING, required=True)
@click.argument("namespace", type=click.STRING, required=True)
@click.argument("subnamespace", type=click.STRING, required=False)
@click.option('--dry-run/--no-dry-run', default=False)
@click.option('--sandbox', type=click.STRING,help="Name of pre-existing sandbox within which to isolate processing")
@click.option('--timestamp', type=click.STRING,help="String used to tag KnowledgeBase posting logs, instead of the actual time")
@pass_kb_session
def form(kb_session, posting_api, namespace, subnamespace, dry_run, sandbox, timestamp):
    '''
    Requests a form (an Excel spreadsheet) which (after some edits, as appropriate) can be used as the
    input to the post command.
    '''
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to post",
                                                            origination     = {'signaled_from': __file__})
    try:
        if sandbox != None:
            kb_session.store.activate(parent_trace = root_trace, environment_name = sandbox)
            click.echo(CLI_Utils().sandox_announcement(sandbox))
        elif dry_run == True:
            sandbox_name                    = kb_session.provisionSandbox(root_trace)
            click.echo(CLI_Utils().sandox_announcement(sandbox_name))
        else:
            raise ApodeixiError(root_trace, "Sorry, only sandbox-isolated runs are supported at this time. Aborting.")

        # Now that we have pinned down the environment (sandbox or not) in which to call the KnowledgeBase's services,
        # set that environment's tag to use for KnoweldgeBase's posting logs, if the user set it.
        if timestamp:
            kb_session.store.current_environment(root_trace).config(root_trace).use_timestamps = timestamp

  
        my_trace                            = root_trace.doing("Invoking KnowledgeBase's requestForm service")

        click.echo("cwd = " + _os.getcwd())
        clientURL                           = kb_session.store.getClientURL(my_trace)
        relative_path, void                 = PathUtils().relativize(   parent_trace    = my_trace, 
                                                                        root_dir        = clientURL, 
                                                                        full_path       = _os.getcwd())
        form_request                        = kb_session.store.getBlindFormRequest( parent_trace    = my_trace, 
                                                                                    relative_path   = relative_path, 
                                                                                    posting_api     = posting_api, 
                                                                                    namespace       = namespace, 
                                                                                    subnamespace    = subnamespace)
        
        response, log_txt, rep              = kb_session.kb.requestForm(parent_trace        = my_trace, 
                                                                        form_request        = form_request)
        manifests_description               = CLI_Utils().describe_response(my_trace, response, kb_session.store)

        click.echo(manifests_description)
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

import sys                                          as _sys
import os                                           as _os

import click
import warnings

import apodeixi
from apodeixi.cli.kb_session                        import KB_Session
from apodeixi.cli.error_reporting                   import CLI_ErrorReporting
from apodeixi.cli.cli_utils                         import CLI_Utils
from apodeixi.util.a6i_error                        import FunctionalTrace, ApodeixiError
from apodeixi.util.path_utils                       import PathUtils
from apodeixi.util.performance_utils                import ApodeixiTimer
from apodeixi.util.warning_utils                    import WarningUtils
from apodeixi.util.formatting_utils                 import StringUtils
from apodeixi.knowledge_base.manifest_utils         import ManifestUtils


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
    timer                               = ApodeixiTimer()
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get namespace",
                                                            origination     = {'signaled_from': __file__})
    try:
        namespaces_description          = CLI_Utils().get_namespaces(root_trace, kb_session)
        click.echo(namespaces_description)
        output                              = "Success"
        click.echo(output)
        click.echo(timer.elapsed_time_message())
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
    except Exception as ex:
        click.echo("Unrecoverable error: " + str(ex))
        _sys.exit()

@get.command()
@click.option('--all/--no-all', default=False, help="If set, products across both the base environment and all sandboxes will be returned")
@click.option('--environment', type=click.STRING,help="If provided, then only products in the given environment will be returned")
@pass_kb_session
def products(kb_session, all, environment):
    '''
    Gets the list of valid products for the system.
    '''
    timer                               = ApodeixiTimer()
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get products",
                                                            origination     = {'signaled_from': __file__})
    try:
        environment_filter              = _get_environment_filter(root_trace, kb_session, all, environment)
        products_description            = CLI_Utils().get_products(root_trace, kb_session, environment_filter)
        click.echo(products_description)
        output                              = "Success"
        click.echo(output)
        click.echo(timer.elapsed_time_message())
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
    except Exception as ex:
        click.echo("Unrecoverable error: " + str(ex))
        _sys.exit()

@get.command()
@click.option('--all/--no-all', default=False, help="If set, products across both the base environment and all sandboxes will be returned")
@click.option('--environment', type=click.STRING,help="If provided, then only products in the given environment will be returned")
@pass_kb_session
def assertions(kb_session, all, environment):
    '''
    Gets the list of assertions (manifests) for the system.
    '''
    timer                               = ApodeixiTimer()
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get products",
                                                            origination     = {'signaled_from': __file__})
    try:
        environment_filter              = _get_environment_filter(root_trace, kb_session, all, environment)
        assertions_description          = CLI_Utils().manifests_description(root_trace, kb_session, 
                                                                            kinds_of_interest       = None, 
                                                                            labels_of_interest      = None, 
                                                                            environment_filter      = environment_filter)
        click.echo(assertions_description)
        output                              = "Success"
        click.echo(output)
        click.echo(timer.elapsed_time_message())
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
    except Exception as ex:
        click.echo("Unrecoverable error: " + str(ex))
        _sys.exit()

def _get_environment_filter(parent_trace, kb_session, all, environment):
    '''
    Helper method to get filter for which environment to look into when searching in the KnowledgeBase
    store.
    '''
    if all==True:
        environment_filter              = CLI_Utils().get_environment_filter(parent_trace, kb_session, 
                                                        filter_type = CLI_Utils.ANY_ENV_FILTER, sandbox=None)
    elif environment != None:
        click.echo(CLI_Utils().sandox_announcement(environment))
        environment_filter              = CLI_Utils().get_environment_filter(parent_trace, kb_session, 
                                                        filter_type = CLI_Utils.SPECIFIC_SANDBOX_ENV_FILTER, sandbox=environment)
    else:
        environment_filter              = CLI_Utils().get_environment_filter(parent_trace, kb_session, 
                                                        filter_type = CLI_Utils.ONLY_BASE_ENV_FILTER, sandbox=environment)
    return environment_filter


@get.command()
@click.option('--all/--no-all', default=False, help="If set, scoring cycles across both the base environment and all sandboxes will be returned")
@click.option('--environment', type=click.STRING,help="If provided, then only scoring cycles in the given environment will be returned")
@pass_kb_session
def scoring_cycles(kb_session, all, environment):
    '''
    Gets the list of valid scoring cycles for the system.
    '''
    timer                               = ApodeixiTimer()
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get scoring cycles",
                                                            origination     = {'signaled_from': __file__})
    try:
        environment_filter              = _get_environment_filter(root_trace, kb_session, all, environment)
        sc_description                  = CLI_Utils().get_scoring_cycles(root_trace, kb_session, environment_filter)
        click.echo(sc_description)
        output                              = "Success"
        click.echo(output)
        click.echo(timer.elapsed_time_message())
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
    except Exception as ex:
        click.echo("Unrecoverable error: " + str(ex))
        _sys.exit()

@get.command()
@pass_kb_session
def environments(kb_session):
    '''
    Gets the list of existing environments (e.g., sandboxes) for the system.
    '''
    timer                               = ApodeixiTimer()
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get sandboxes",
                                                            origination     = {'signaled_from': __file__})
    try:
        environments_description           = CLI_Utils().get_environments(root_trace, kb_session)
        click.echo(environments_description)
        output                              = "Success"
        click.echo(output)
        click.echo(timer.elapsed_time_message())
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
    except Exception as ex:
        click.echo("Unrecoverable error: " + str(ex))
        _sys.exit()

@get.command()
@pass_kb_session
def apis(kb_session):
    '''
    Gets the list of posting and manifest APIs supported by the KnowledgeBase
    '''
    timer                               = ApodeixiTimer()
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to get posting APIs",
                                                            origination     = {'signaled_from': __file__})
    try:
        posting_apis_description        = CLI_Utils().get_apodeixi_apis(root_trace, kb_session)
        click.echo(posting_apis_description)
        output                              = "Success"
        click.echo(output)
        click.echo(timer.elapsed_time_message())
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
    except Exception as ex:
        click.echo("Unrecoverable error: " + str(ex))
        _sys.exit()



@apo_cli.command()
@click.argument("file", type=click.STRING, required=True)
@click.option('--dry-run/--no-dry-run', default=False)
@click.option('--environment', type=click.STRING,help="Name of optional pre-existing environment within which to isolate processing.")
@click.option('--timestamp', type=click.STRING,help="Optional string used to tag KnowledgeBase posting logs. "\
                                                        "If not set then the current time will be used.")
@pass_kb_session
def post(kb_session, file, dry_run, environment, timestamp):
    '''
    Posts contents of an Excel file to the KnowledgeBase.
    The filename must be of the form '<some string><posting API>.xlsx' for some supported KnowledgeBase posting API.
    '''
    timer                               = ApodeixiTimer()
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to post",
                                                            origination     = {'signaled_from': __file__})

    kb_operation_succeeded              = False
    try:
        if environment != None:
            kb_session.store.activate(parent_trace = root_trace, environment_name = environment)
            click.echo(CLI_Utils().sandox_announcement(environment))
        elif dry_run == True:
            sandbox_name                    = kb_session.provisionSandbox(root_trace)
            click.echo(CLI_Utils().sandox_announcement(sandbox_name))
        '''
        else:
            raise ApodeixiError(root_trace, "Sorry, only sandbox-isolated runs are supported at this time. Aborting.")
        '''
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
        kb_operation_succeeded              = True
        manifests_description               = CLI_Utils().describe_post_response(my_trace, response, kb_session.store)

        click.echo(manifests_description)
        output                              = "Success"
        click.echo(output)
        click.echo(timer.elapsed_time_message())
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        if kb_operation_succeeded:
            error_msg                       = "KnowledgeBase operation completed, but run into a problem when preparing "\
                                                + "a description of the response:\n"\
                                                + error_msg
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
    except Exception as ex:
        try:
            error_msg                       = CLI_ErrorReporting(kb_session).report_generic_error( 
                                                                        parent_trace                = root_trace, 
                                                                        generic_error               = ex)
            if kb_operation_succeeded:
                error_msg                   = "KnowledgeBase operation completed, but run into a problem when preparing "\
                                                + "a description of the response:\n"\
                                                + error_msg
        except Exception as ex2:
            error_msg                       = "CLI run into trouble: found error:\n\n\t" + str(ex) + "\n\n" \
                                                + "To make things worse, when trying to produce an error log file with a "\
                                                + "stack trace, run into an additional error:\n\n\t" + str(ex2)
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
@click.option('--environment', type=click.STRING,help="Name of pre-existing environment within which to isolate processing")
@click.option('--timestamp', type=click.STRING,help="String used to tag KnowledgeBase posting logs, instead of the actual time")
@pass_kb_session
def form(kb_session, posting_api, namespace, subnamespace, dry_run, environment, timestamp):
    '''
    Requests a form (an Excel spreadsheet) which (after some edits, as appropriate) can be used as the
    input to the post command.
    '''
    timer                               = ApodeixiTimer()
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to post",
                                                            origination     = {'signaled_from': __file__})
    kb_operation_succeeded              = False
    try:
        # Catch warnings and handle them so that we avoid spurious noise in the CLI due to noisy 3rd party libraries
        with warnings.catch_warnings(record=True) as w:
            traceback_stream            = WarningUtils().turn_traceback_on(root_trace)        
            if environment != None:
                kb_session.store.activate(parent_trace = root_trace, environment_name = environment)
                click.echo(CLI_Utils().sandox_announcement(environment))
            elif dry_run == True:
                sandbox_name                    = kb_session.provisionSandbox(root_trace)
                click.echo(CLI_Utils().sandox_announcement(sandbox_name))
            '''
            else:
                raise ApodeixiError(root_trace, "Sorry, only sandbox-isolated runs are supported at this time. Aborting.")
            '''
            # Now that we have pinned down the environment (sandbox or not) in which to call the KnowledgeBase's services,
            # set that environment's tag to use for KnoweldgeBase's posting logs, if the user set it.
            if timestamp:
                kb_session.store.current_environment(root_trace).config(root_trace).use_timestamps = timestamp

    
            my_trace                            = root_trace.doing("Invoking KnowledgeBase's requestForm service")

            output_dir                          = _os.getcwd()
            clientURL                           = kb_session.store.getClientURL(my_trace)
            relative_path, void                 = PathUtils().relativize(   parent_trace    = my_trace, 
                                                                            root_dir        = clientURL, 
                                                                            full_path       = output_dir)

            form_request                        = kb_session.store.getBlindFormRequest( parent_trace    = my_trace, 
                                                                                        relative_path   = relative_path, 
                                                                                        posting_api     = posting_api, 
                                                                                        namespace       = namespace, 
                                                                                        subnamespace    = subnamespace)
            
            response, log_txt, rep              = kb_session.kb.requestForm(parent_trace        = my_trace, 
                                                                            form_request        = form_request)
            kb_operation_succeeded              = True
            manifests_description               = CLI_Utils().describe_req_form_response(my_trace, 
                                                                                    form_request_response   = response, 
                                                                                    store                   = kb_session.store,
                                                                                    representer             = rep)

            click.echo(manifests_description)
            output                              = "Success"
            click.echo(output)
            click.echo(timer.elapsed_time_message())

            WarningUtils().handle_warnings(root_trace, warning_list=w, traceback_stream=traceback_stream)

    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        if kb_operation_succeeded:
            error_msg                       = "KnowledgeBase operation completed, but run into a problem when preparing "\
                                                + "a description of the response:\n"\
                                                + error_msg
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
    except Exception as ex:
        try:
            error_msg                       = CLI_ErrorReporting(kb_session).report_generic_error( 
                                                                        parent_trace                = root_trace, 
                                                                        generic_error               = ex)
            if kb_operation_succeeded:
                error_msg                   = "KnowledgeBase operation completed, but run into a problem when preparing "\
                                                + "a description of the response:\n"\
                                                + error_msg
        except Exception as ex2:
            error_msg                       = "CLI run into trouble: found error:\n\n\t" + str(ex) + "\n\n" \
                                                + "To make things worse, when trying to produce an error log file with a "\
                                                + "stack trace, run into an additional error:\n\n\t" + str(ex2)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()

@apo_cli.command()
@click.argument("manifest_api", type=click.STRING, required=True)
@click.argument("kind", type=click.STRING, required=True)
@click.argument("namespace", type=click.STRING, required=True)
@click.argument("name", type=click.STRING, required=True)
@pass_kb_session
def diff(kb_session, manifest_api, kind, namespace, name):
    '''
    Makes a diff between two versions of a manifest.
    
    For a list of valid MANIFEST_APIs and KINDs, try 'get apis'
    
    For a list of valid NAMESPACEs and NAMEs, try 'get assertions'

    MANIFEST_API must be a versionless manifest API. 
    
    Example: 'delivery-planning.journeys.a6i.io', (as opposed to 'delivery-planning.journeys.a6i.io/v1a'). 
    '''
    timer                               = ApodeixiTimer()
    func_trace                          = FunctionalTrace(  parent_trace    = None, 
                                                            path_mask       = None) 
    root_trace                          = func_trace.doing("CLI call to post",
                                                            origination     = {'signaled_from': __file__})

    kb_operation_succeeded              = False
    try:

        my_trace                        = root_trace.doing("Invoking ManifestUtils's postByFile service")

        diff_result                     = ManifestUtils().diff_manifest(
                                                            parent_trace        = my_trace, 
                                                            store               = kb_session.store, 
                                                            manifest_api_name   = manifest_api, 
                                                            namespace           = namespace, 
                                                            name                = name, 
                                                            kind                = kind, 
                                                            version1            = None, 
                                                            version2            = None)
        kb_operation_succeeded              = True

        diff_description                    = CLI_Utils().describe_diff_response(my_trace, kb_session, diff_result)

        # GOTCHA:
        # Make sure to remove non-ascii characters before passing the description to click.echo, since it
        # will raise errors if there are characters like \uFFFFD in the description
        #
        diff_description                    = StringUtils().to_ascii(diff_description)

        click.echo(diff_description)
        output                              = "Success"
        click.echo(output)
        click.echo(timer.elapsed_time_message())
    except ApodeixiError as ex:
        error_msg                           = CLI_ErrorReporting(kb_session).report_a6i_error( 
                                                                        parent_trace                = root_trace, 
                                                                        a6i_error                   = ex)
        if kb_operation_succeeded:
            error_msg                       = "KnowledgeBase operation completed, but run into a problem when preparing "\
                                                + "a description of the response:\n"\
                                                + error_msg
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
    except Exception as ex:
        try:
            error_msg                       = CLI_ErrorReporting(kb_session).report_generic_error( 
                                                                        parent_trace                = root_trace, 
                                                                        generic_error               = ex)
            if kb_operation_succeeded:
                error_msg                   = "KnowledgeBase operation completed, but run into a problem when preparing "\
                                                + "a description of the response:\n"\
                                                + error_msg
        except Exception as ex2:
            error_msg                       = "CLI run into trouble: found error:\n\n\t" + str(ex) + "\n\n" \
                                                + "To make things worse, when trying to produce an error log file with a "\
                                                + "stack trace, run into an additional error:\n\n\t" + str(ex2)
        # GOTCHA
        #       Use print, not click.echo or click exception because they don't correctly display styling
        #       (colors, underlines, etc.). So use vanilla Python print and then exit
        print(error_msg)
        _sys.exit()
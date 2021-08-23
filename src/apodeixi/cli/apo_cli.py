import sys                                  as _sys
import os                                   as _os
from apodeixi.cli.cli_utils import CLI_Utils
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

        my_trace                            = root_trace.doing("Creating summary of manifests created/updated/etc")
        rep                                 = AsDataframe_Representer()

        # TODO: Need to also do it for updated, deleted, unchanged, etc., not just created
        description_table                   = []
        description_headers                 = ["Manifest", "Event", "Entity count"]
        for manifest_handle in response.createdManifests(): 
            loop_trace                      = my_trace.doing("Creating summary for 1 manifest",
                                                        data = {"manifest handle": manifest_handle.display(my_trace)})
            manifest_dict, manifest_path    = kb_session.store.retrieveManifest(loop_trace, manifest_handle)
            # TODO: make this code more generic by using manifest_handle.apiVersion & kind to locate a class
            # (like a controller, but for manifests instead of for postings) that would make this more generic
            # and not hard-coding awareness of contents_path as this POC has it
            #
            # ALTERNATIVELY: if we only support 1 entity per level, we can look for the "unique subdictionary"
            # under "assertion" to create the rest of the contents path
            manifest_file                   = _os.path.split(manifest_path)[1]

            # First get the assertion. We will search for the unique entity within it
            check, explanations             = DictionaryUtils().validate_path(  parent_trace        = loop_trace, 
                                                                                root_dict           = manifest_dict, 
                                                                                root_dict_name      = manifest_file,
                                                                                path_list           = ["assertion"], 
                                                                                valid_types         = [dict])
            if not check:
                raise ApodeixiError(loop_trace, "Corrupted manifest: no assertion sub-tree found at expected path_list",
                                                data = {"path_list":            str(["assertion"]),
                                                        "explanations":         str(explanations),
                                                        "manifest_handle":      manifest_handle.display(loop_trace)})
            
            assertion_dict                  = DictionaryUtils().get_val(        parent_trace        = loop_trace, 
                                                                                root_dict           = manifest_dict, 
                                                                                root_dict_name      = manifest_file, 
                                                                                path_list           = ["assertion"], 
                                                                                valid_types         = [dict])
            entities                        = [key for key in assertion_dict.keys() if type(assertion_dict[key])==dict]
            if len(entities) != 1:
                raise ApodeixiError(loop_trace, "Corrupted manifest: expected exactly 1 entity, not " + str(len(entities)),
                                                data = {    "entities found":   str(entities)})

            entity                              = entities[0]
            # Now that we know the entity, we can search for the manifest contents
            path_list                       = ["assertion", entity]
            check, explanations             = DictionaryUtils().validate_path(  parent_trace        = loop_trace, 
                                                                                root_dict           = manifest_dict, 
                                                                                root_dict_name      = manifest_file,
                                                                                path_list           = path_list, 
                                                                                valid_types         = [dict])
            if not check:
                raise ApodeixiError(loop_trace, "Corrupted manifest: no content sub-tree found at expected path_list",
                                                data = {"path_list":            str(path_list),
                                                        "explanations":         str(explanations),
                                                        "manifest_handle":      manifest_handle.display(loop_trace)})
            content_dict                    = DictionaryUtils().get_val(        parent_trace        = loop_trace, 
                                                                                root_dict           = manifest_dict, 
                                                                                root_dict_name      = manifest_file, 
                                                                                path_list           = path_list, 
                                                                                valid_types         = [dict])

            contents_path                   = ".".join(path_list)
            manifest_df                     = rep.dict_2_df(    parent_trace        = loop_trace, 
                                                                content_dict        = content_dict, 
                                                                contents_path       = contents_path, 
                                                                sparse              = False)
            nb_entities                     = len(list(manifest_df[Interval.UID].unique()))

            description_table.append([manifest_file, "created", nb_entities])
            #manifests_description           += "CREATED " + manifest_file + "; #entities=" + str(nb_entities) + "\n"

        manifests_description               = "\nKnowledgeBase activity:\n\n"
        manifests_description               += tabulate(description_table, headers=description_headers)
        manifests_description               += "\n"
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




from datetime import datetime
import os                                                           as _os
import re                                                           as _re

from tabulate                                                       import tabulate
import pandas                                                       as _pd
import xlsxwriter

from apodeixi.cli.error_reporting                                   import CLI_ErrorReporting
from apodeixi.controllers.admin.static_data.static_data_validator   import StaticDataValidator

from apodeixi.knowledge_base.manifest_utils                         import ManifestUtils
from apodeixi.knowledge_base.kb_environment                         import File_KBEnv_Impl
from apodeixi.text_layout.excel_layout                              import Palette
from apodeixi.util.a6i_error                                        import ApodeixiError
from apodeixi.util.formatting_utils                                 import StringUtils
from apodeixi.util.path_utils                                       import PathUtils
from apodeixi.util.performance_utils                                import ApodeixiTimer
from apodeixi.util.dictionary_utils                                 import DictionaryUtils
from apodeixi.util.reporting_utils                                  import ReportWriterUtils

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
    PREFIX_EXPECTED                 = "Using sandbox '"
    SANDBOX_NAME_LENGTH             = len("210821.142725_sandbox")    
    SUFFIX_EXPECTED                 = "'..."
    
    SANDBOX_SUFFIX                  = "_sandbox"

    #Statics identifying possible environment filters
    ONLY_BASE_ENV_FILTER            = "ONLY_BASE_ENV_FILTER"
    ANY_ENV_FILTER                  = "ANY_ENV_FILTER"
    SPECIFIC_SANDBOX_ENV_FILTER     = "SPECIFIC_SANDBOX_ENV_FILTER"

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
            if output_txt == None:
                return None

            output_lines                            = output_txt.split('\n')
            ANNOUNCEMENT_IDX                        = 0
            # Remove the timestamp before checking that the output lines match our expectations
            assert len(output_lines) >= ANNOUNCEMENT_IDX+1
            dry_run_msg                             = output_lines[ANNOUNCEMENT_IDX]
            try:
                sandbox_name = CLI_Utils().parse_sandbox_announcement(  parent_trace    = parent_trace, 
                                                                        announcement    = dry_run_msg)
                cleaned_txt                         = _re.sub(          pattern         =sandbox_name, 
                                                                        repl="<MASKED>"+ CLI_Utils.SANDBOX_SUFFIX, 
                                                                        string=output_txt)

            except ApodeixiError as ex:
                if ex.msg.startswith("Announcement is not in the expected form"):
                    # This is not really an error - it just means that there was no announcement, possibly because
                    # we are not running in a sandbox anyway
                    cleaned_txt                         = output_txt
                else:
                    # If the error arises from something else, then probably something is wrong. So error out
                    raise ex

            return cleaned_txt

        return _mask_lambda

    def combined_mask(self, parent_trace, a6i_config):
        MASK_SANDBOX                = self.mask_sandbox_lambda(parent_trace)
        MASK_PATH                   = PathUtils().get_mask_lambda(parent_trace, a6i_config)
        MASK_TIMER                  = ApodeixiTimer().get_mask_lambda(parent_trace)
        def MASK_COMBINED(txt1):
            if txt1 == None:
                return None
            txt2                    = MASK_PATH(txt1)
            txt3                    = MASK_SANDBOX(txt2)
            txt4                    = MASK_TIMER(txt3)
            txt5                    = _re.sub(pattern="[0-9]{6}", repl="<MASKED>", string=txt4)
            return txt5
        return MASK_COMBINED

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

    def describe_post_response(self, parent_trace, post_response, store):
        '''
        Returns a string suitable for display in the Apodeixi CLI.

        The string is formatted as a table that provides information on what Apodeixi did in response to a user
        initiated posting.

        The table has a row per manifest that was involved, with a description of what changed, if anything.
        '''
        description_table                   = []
        description_headers                 = ["Manifest", "Event", "Entities added", "Entities removed",
                                                    "Entities changed", "Entities unchanged", "Namespace", "Name"]
        for manifest_handle in post_response.allManifests(parent_trace): 
            loop_trace                      = parent_trace.doing("Creating summary for 1 manifest",
                                                        data = {"manifest handle": manifest_handle.display(parent_trace)})
            description                     = ManifestUtils().describe_manifest(    loop_trace, 
                                                                                    manifest_handle     = manifest_handle, 
                                                                                    store               = store, 
                                                                                    post_response       = post_response)
            # Important: order in list must match the order of the headers in `description_headers`. Required by
            # the tabulate Python package.
            description_table.append([      description.manifest_filename, 
                                            description.event, 
                                            description.entities_added_desc, 
                                            description.entities_removed_desc, 
                                            description.entities_changed_desc, 
                                            description.entities_unchanged_desc,
                                            description.namespace,
                                            description.name])

        manifests_description               = "\nKnowledgeBase activity:\n\n"
        manifests_description               += tabulate(description_table, headers=description_headers)
        manifests_description               += "\n"

        return manifests_description

    def describe_req_form_response(self, parent_trace, form_request_response, store, representer):
        '''
        Returns a string suitable for display in the Apodeixi CLI.

        The string is formatted as a table that provides information on what Apodeixi did in response to a user
        requesting a form, by highlighting certain properties of the generated form.

        The table has a row for each highlighted property.
        '''
        description_table                   = []
        description_headers                 = ["Property", "Value"]

        # Important: order in list must match the order of the headers in `description_headers`. Required by
        # the tabulate Python package.
        clientURL                           = form_request_response.clientURL(parent_trace)
        filing_coords_txt                   = str(form_request_response.filing_coords(parent_trace))
        filename                            = form_request_response.filename(parent_trace)
        manifest_idx_txt                    = ", ".join(form_request_response.manifest_identifiers(parent_trace))
        posting_api                         = form_request_response.posting_api(parent_trace)

        description_table.append(["Filing Coordinates", filing_coords_txt])
        description_table.append(["Filename", filename])
        description_table.append(["Manifests Included", manifest_idx_txt])
        description_table.append(["Posting API", posting_api])

        for manifest_id in form_request_response.manifest_identifiers(parent_trace):
            kind, nb                        = manifest_id.split(".")
            excel_range                     = representer.label_ctx['data.range.'    + str(nb)]
            excel_sheet                     = representer.label_ctx['data.sheet.'    + str(nb)]
            READ_ONLY                       = 'readOnly.'+ str(nb)
            if READ_ONLY in representer.label_ctx.keys() and representer.label_ctx[READ_ONLY] == True:
                description_table.append(["Read-only Excel range for '" + kind + "'", 
                                        excel_sheet + "!" + excel_range])
            else:
                PRIOR_VERSION               = "priorVersion." + str(nb)
                if PRIOR_VERSION in representer.label_ctx.keys():
                    last_version            = representer.label_ctx[PRIOR_VERSION]
                    next_version            = last_version + 1
                    description_table.append(["Excel range for updating '" + kind + "' to version " + str(next_version), 
                                            excel_sheet + "!" + excel_range])
                else:
                    next_version            = 1
                    description_table.append(["Excel range for creating first version of '" + kind + "'", 
                                            excel_sheet + "!" + excel_range])


        form_description                    = "\nGenerated Excel form in this area:\n\n"
        form_description                    += clientURL + "\n\n"
        form_description                    += tabulate(description_table, headers=description_headers)
        form_description                    += "\n"

        return form_description

    def describe_diff_response(self, parent_trace, kb_session, diff_result):
        '''
        Returns a string suitable for display in the Apodeixi CLI.

        Also persists the same information as an Excel file in the reports area of the KnowledgeBase.

        The string is formatted as a table that provides information on what Apodeixi did in response to a user
        requesting a diff between two versions of a manifest

        The table has a row for each noteworthy difference.

        @param diff_result A ManifestDiffResult object encapsulating all the differences
        '''
        my_trace                            = parent_trace.doing("Constructing the diff report's data")
        if True:
            description_table                   = []
            description_headers                 = ["Diff Type", "Entity", "Field", "Original Value", "New Value"]
            headers_widths                      = [20,          50,         25,     40,                 40]

            # Important: order in list must match the order of the headers in `description_headers`. Required by
            # the tabulate Python package.
            for entity_desc in diff_result.added_entities_description(parent_trace):
                description_table.append(["ENTITY ADDED", entity_desc, "", "", ""])

            for entity_desc in diff_result.removed_entities_description(parent_trace):
                description_table.append(["ENTITY REMOVED", entity_desc, "", "", ""])

            changed_entities_dict               = diff_result.changed_entities_description_dict(parent_trace)
            for entity_desc in changed_entities_dict.keys():
                entity_diff                     = changed_entities_dict[entity_desc]

                for field in entity_diff.added_fields:
                    description_table.append(["FIELD ADDED", entity_desc, field, "", ""])
                for field in entity_diff.removed_fields:
                    description_table.append(["FIELD REMOVED", entity_desc, field, "", ""])
                for changed_value in entity_diff.changed_fields:
                    description_table.append(["FIELD CHANGED", entity_desc, changed_value.field, 
                                                                        changed_value.old_value, 
                                                                        changed_value.new_value])

            diff_description                    = "\n" + diff_result.short_description + ":\n\n"

            diff_description                    += tabulate(description_table, headers=description_headers)
            diff_description                    += "\n"

        # Save the report
        my_trace                            = parent_trace.doing("Saving diff report")
        if True:
            reports_folder                      = kb_session.kb_rootdir + "/" + File_KBEnv_Impl.REPORTS_FOLDER
            
            REPORT_FILENAME                     = kb_session.timestamp + "_" + diff_result.short_description.replace(" ", "_") \
                                                                                + "_diff.xlsx"
            PathUtils().create_path_if_needed(parent_trace, reports_folder)

            '''
            report_df                           = _pd.DataFrame(data=description_table, columns=description_headers)
            report_df.to_excel(reports_folder + "/" + REPORT_FILENAME)
            '''
            self._write_report( parent_trace    = my_trace, 
                                data            = description_table, 
                                columns         = description_headers, 
                                column_widths   = headers_widths, 
                                path            = reports_folder + "/" + REPORT_FILENAME, 
                                description     = diff_result.long_description)

        # Append pointer to report
        #
        my_trace                            = parent_trace.doing("Adding link to diff report")
        if True:
            cli_reporter                        = CLI_ErrorReporting(kb_session)
            diff_description                    += cli_reporter.POINTERS("\n\nRetrieve Excel report at ")
            diff_description                    += cli_reporter.POINTERS(cli_reporter.UNDERLINE("file:///" + reports_folder
                                                                                                    + "/" + REPORT_FILENAME))

        return diff_description

    def _write_report(self, parent_trace, data, columns, column_widths, path, description):
        '''
        Creates an Excel file  based on the content in `data`, with headers taken from `columns`

        @param data A list of list. The inner lists correspond to the rows to be written to Excel, and
            they are all have the same length, which should equal the number of elements in `columns`.
            The values of the inner list should be scalars so that each of them can be displayed in Excel, such
            as a string, int, or float.
        @param columns A list of strings, corresponding to the column headers for the data to be written to Excel.
        @param column_widths: A list of floats, whose length must equal the number of elements in `columns`.
            They determine how wide each of the Excel columns should be
        @param path A string, corresponding to the full path to which the Excel file must be saved (i.e., full
            directory and filename)
        @param description A string, used to give a description of the report. Example: "big-rock_v1-v2_diff".
        '''
        workbook                        = xlsxwriter.Workbook(path)
        my_trace                        = parent_trace.doing("Populating the report's content") 
        report_content_df               = _pd.DataFrame(data=data, columns=columns)
        ReportWriterUtils().write_report(   parent_trace            = my_trace, 
                                            report_df               = report_content_df, 
                                            column_widths           = column_widths, 
                                            workbook                = workbook, 
                                            sheet                   = "Report", 
                                            description             = description)

        my_trace                        = parent_trace.doing("Saving the report") 
        try:
            workbook.close()
        except Exception as ex:
            raise ApodeixiError(my_trace, "Encountered a problem saving the Excel spreadsheet",
                            data = {"error": str(ex), "path": path})

    def get_namespaces(self, parent_trace, kb_session):
        '''
        Returns a nicely formatted string, suitable for CLI output. It displays the valid namespaces of the system.
        '''
        expected_organization           = kb_session.a6i_config.getOrganization(parent_trace)
        allowed_kb_areas                = kb_session.a6i_config.getKnowledgeBaseAreas(parent_trace)

        FMT                             = StringUtils().format_as_yaml_fieldname
        description_table               = [[FMT(expected_organization + "." + kb_area)] for kb_area in allowed_kb_areas]
        description_headers             = ["Namespace"]

        description                     = "\n\n"
        description                     += tabulate(description_table, headers=description_headers)
        description                     += "\n"

        return description

    def get_products(self, parent_trace, kb_session, environment_filter):
        '''
        Returns a nicely formatted string, suitable for CLI output. It displays all valid products of the system.

        @param environment_filter A lambda function, that takes a string argument and returns True or False.
            Its purposes is to filte out which KnowledgeBase store's environments to include when searching
            for products. If it is None, then all environments are included
        '''
        expected_organization           = kb_session.a6i_config.getOrganization(parent_trace)
        allowed_kb_areas                = kb_session.a6i_config.getKnowledgeBaseAreas(parent_trace)

        FMT                             = StringUtils().format_as_yaml_fieldname
        namespaces                      = [FMT(expected_organization + "."+ kb_area) for kb_area in allowed_kb_areas]

        description_table               = []
        description_headers             = ["Product", "Namespace", "Environment"]

        environments                    = []
        environments.append(kb_session.store.base_environment(parent_trace).name(parent_trace))
        environments.extend(self._sandboxes_names_list(parent_trace, kb_session))

        if environment_filter != None:
            environments                = [e for e in environments if environment_filter(e) == True]

        original_env_name               = kb_session.store.current_environment(parent_trace).name(parent_trace)
        for env_name in environments:
            kb_session.store.activate(parent_trace, env_name)
            for ns in namespaces:
                validator                   = StaticDataValidator(parent_trace, kb_session.store, kb_session.a6i_config)
                try:
                    product_list                = validator.allProductCodes(parent_trace, ns)
                    for prod in product_list:
                        description_table.append([prod, ns, env_name])
                except ApodeixiError as ex:
                    if ex.msg.startswith("Static data of type 'product' is not configured for namespace"):
                        # If so just ignore this error, since perhaps that namespace has no products but maybe other namespaces
                        # do
                        continue
                    else:
                        raise ex
            
        kb_session.store.activate(parent_trace, original_env_name)

        description                     = "\n\n"
        description                     += tabulate(description_table, headers=description_headers)
        description                     += "\n"

        return description

    def get_scoring_cycles(self, parent_trace, kb_session, environment_filter):
        '''
        Returns a nicely formatted string, suitable for CLI output. It displays all valid scoring cycles of the system.

        @param environment_filter A lambda function, that takes a string argument and returns True or False.
            Its purposes is to filte out which KnowledgeBase store's environments to include when searching
            for scoring cycles. If it is None, then all environments are included.
        '''
        JOURNEY_COL                     = 'journey'
        SCORING_CYCLE_COL               = 'Scoring Cycle'
        SCENARIO_COL                    = 'Scenario'

        expected_organization           = kb_session.a6i_config.getOrganization(parent_trace)
        allowed_kb_areas                = kb_session.a6i_config.getKnowledgeBaseAreas(parent_trace)

        FMT                             = StringUtils().format_as_yaml_fieldname
        namespaces                      = [FMT(expected_organization + "."+ kb_area) for kb_area in allowed_kb_areas]

        description_table               = []
        description_headers             = ["Journey", "Scoring cycle", "Scenario", "Namespace", "Environment"]

        environments                    = []
        environments.append(kb_session.store.base_environment(parent_trace).name(parent_trace))
        environments.extend(self._sandboxes_names_list(parent_trace, kb_session))

        if environment_filter != None:
            environments                = [e for e in environments if environment_filter(e) == True]

        original_env_name               = kb_session.store.current_environment(parent_trace).name(parent_trace)
        for env_name in environments:
            kb_session.store.activate(parent_trace, env_name)
            for ns in namespaces:
                validator                   = StaticDataValidator(parent_trace, kb_session.store, kb_session.a6i_config)
                try:
                    sc_df                   = validator.getScoringCycles(parent_trace, ns)
                    for row in sc_df.iterrows():
                        description_table.append([row[1][JOURNEY_COL], row[1][SCORING_CYCLE_COL], 
                                                    row[1][SCENARIO_COL], ns, env_name])
                except ApodeixiError as ex:
                    if ex.msg.startswith("Static data of type 'scoring-cycle' is not configured for namespace"):
                        # If so just ignore this error, since perhaps that namespace has no products but maybe 
                        # other namespaces do
                        continue
                    else:
                        raise ex
            
        kb_session.store.activate(parent_trace, original_env_name)

        description                     = "\n\n"
        description                     += tabulate(description_table, headers=description_headers)
        description                     += "\n"

        return description

    def _sandboxes_names_list(self, parent_trace, kb_session):
        '''
        Internal helper method. Returns a list of strings, corresponding to all the sandboxes of the system
        '''
        root_dir                    = _os.path.dirname(kb_session.store.base_environment(parent_trace).manifestsURL(parent_trace))
        envs_dir                    = root_dir + "/" + File_KBEnv_Impl.ENVS_FOLDER

        sandboxes                   = []
        if _os.path.isdir(envs_dir):
            for candidate in _os.listdir(envs_dir):
                if _os.path.isdir(envs_dir + "/" + candidate) and candidate.endswith(CLI_Utils.SANDBOX_SUFFIX):
                    sandboxes.append(candidate)

        return sandboxes

    def get_environments(self, parent_trace, kb_session):
        '''
        Returns a nicely formatted string, suitable for CLI output. It displays all sandboxes that currently
        exist
        '''
        sandboxes                       = self._sandboxes_names_list(parent_trace, kb_session)

        description_table               = []
        description_headers             = ["Environment"]
        base_env_name                   = kb_session.store.base_environment(parent_trace).name(parent_trace)
        description_table.append([base_env_name])
        for sb in sandboxes:
            description_table.append([sb])

        description                     = "\n\n"
        description                     += tabulate(description_table, headers=description_headers)
        description                     += "\n"

        return description

    def get_apodeixi_apis(self, parent_trace, kb_session):
        '''
        Returns a nicely formatted string, suitable for CLI output. It displays all posting APIs that the
        KnowledgeBase currenly supports.
        '''
        description_table               = []
        description_headers             = ["Posting API", "Postings filing scheme", 
                                                "Manifest API for posted manifests", 
                                                "Manifest kinds for posted manifests"]
        for posting_api in kb_session.kb.get_posting_apis():
            ctrl                        = kb_session.kb.findController(parent_trace, posting_api)
            manifest_api                = ctrl.getManifestAPI()
            supported_versions          = ctrl.getSupportedVersions()
            supported_kinds             = ctrl.getSupportedKinds()
            filing_class                = kb_session.store.getFilingClass(parent_trace, posting_api)

            manifest_api_name           = manifest_api.apiName()
            manifest_api_txt            = manifest_api_name + "/" + ", ".join([v for v in supported_versions])
            supported_kinds_txt         = ", ".join(supported_kinds)
            if filing_class == None:
                filing_class_txt        = "None"
            else:
                filing_class_txt        = filing_class.__name__

            description_table.append([posting_api, filing_class_txt, manifest_api_txt, supported_kinds_txt])

        description                     = "\n\n"
        description                     += tabulate(description_table, headers=description_headers)
        description                     += "\n"

        return description

    def _get_all_kinds(self, parent_trace, kb_session):

        all_kinds                       = []
        for posting_api in kb_session.kb.get_posting_apis():
            ctrl                        = kb_session.kb.findController(parent_trace, posting_api)
            supported_kinds             = ctrl.getSupportedKinds()
            all_kinds.extend(supported_kinds)
        # Remove duplicates
        all_kinds                       = list(set(all_kinds))
        return all_kinds

    def manifests_description(self, parent_trace, kb_session, kinds_of_interest, labels_of_interest, environment_filter):
        '''
        Returns a nicely formatted string, suitable for CLI output. 
        
        It displays summary information for all manifests that the
        KnowledgeBase currenly supports whose kind is one of the `kinds_of_interest` and
        which have all the labels of interest.

        @param kinds_of_interest A list of strings, corresponding to manifest kinds we seek. If null, then
            we will collect all kinds known to the system.
        @param labels_of_interest A list of strings of the form "<field>=<value>", which constrains
            while manifests are returned by forcing that each of them has <field> as a label with value <value>.
            If set to None, then all manifests are included.

        @param environment_filter A lambda function, that takes a string argument and returns True or False.
            Its purposes is to filte out which KnowledgeBase store's environments to include when searching
            for products. If it is None, then all environments are included
        '''
        FMT                             = StringUtils().format_as_yaml_fieldname

        description_table               = []
        description_headers             = ["Kind", "Version", "Estimated on", "Recorded by", "Namespace", "Name", "Environment"]

        environments                    = []
        environments.append(kb_session.store.base_environment(parent_trace).name(parent_trace))
        environments.extend(self._sandboxes_names_list(parent_trace, kb_session))

        if environment_filter != None:
            environments                = [e for e in environments if environment_filter(e) == True]

        if kinds_of_interest == None:
            kinds_of_interest           = self._get_all_kinds(parent_trace, kb_session)

        original_env_name               = kb_session.store.current_environment(parent_trace).name(parent_trace)
        for env_name in environments:
            kb_session.store.activate(parent_trace, env_name)

            def _manifest_filter(parent_trace, manifest_dict):
                #TODO For now we just approve everything. Later will need to filter on labels
                return True

            manifest_dict_list          = kb_session.store.searchManifests(parent_trace, kinds_of_interest, 
                                                                                manifest_filter = _manifest_filter)
            # ["Kind", "Version", "Estimated on", "Namespace", "Name", "Environment"]
            GET                         = DictionaryUtils().get_val
            for m_dict in manifest_dict_list:
                kind                = GET(parent_trace, m_dict, "Manifest", ["kind"], [str])
                version             = GET(parent_trace, m_dict, "Manifest", ["metadata", "version"], [int])
                estimated_on        = GET(parent_trace, m_dict, "Manifest", ["assertion", "estimatedOn"], [datetime])
                recorded_by         = GET(parent_trace, m_dict, "Manifest", ["assertion", "recordedBy"], [datetime])
                namespace           = GET(parent_trace, m_dict, "Manifest", ["metadata", "namespace"], [str])
                name                = GET(parent_trace, m_dict, "Manifest", ["metadata", "name"], [str])

                description_table.append([kind, version, estimated_on, recorded_by,  namespace, name, env_name])
            
        # To ensure output to be predictable (e.g., for regression tests) we sort the description table. We found that
        # otherwise some tests that pass in Windows will fail when run in a Linux container.
        #
        KIND_IDX                    = 0
        VERSION_IDX                 = 1
        description_table           = sorted(description_table, key=lambda entry: entry[KIND_IDX] + str(entry[VERSION_IDX]))

        kb_session.store.activate(parent_trace, original_env_name)

        description                     = "\n\n"
        description                     += tabulate(description_table, headers=description_headers)
        description                     += "\n"

        return description


    def get_environment_filter(self, parent_trace, kb_session, filter_type, sandbox):
        '''
        Returns a lambda that can be used as a filter for environments, whenver searching for objects
        across the KnowledgeBaseStore.

        @param filter_type A string. Must be one of: 
            * CLI_Utils.ONLY_BASE_ENV_FILTER
            * CLI_Utils.ANY_ENV_FILTER
            * CLI_Utils.SPECIFIC_SANDBOX_ENV_FILTER

        @param sandbox A string, possibly null, corresponding to the name of a sandbox environment.
            It is only relevant for filter_type=CLI_Utils.SPECIFIC_SANDBOX_ENV_FILTER, to denote
            the sandbox that is allowed.
        '''

        # Define the possible environment filters
        def _only_base_env_filter(env_name):
            if env_name == kb_session.store.base_environment(parent_trace).name(parent_trace):
                return True
            return False

        def _any_env_filter(env_name):
            return True

        def _specific_sandbox_env_filter(env_name):
            if env_name == sandbox:
                return True
            return False
        if filter_type == CLI_Utils.ONLY_BASE_ENV_FILTER:
            return _only_base_env_filter
        elif filter_type == CLI_Utils.ANY_ENV_FILTER:
            return _any_env_filter
        elif filter_type == CLI_Utils.SPECIFIC_SANDBOX_ENV_FILTER:
            return _specific_sandbox_env_filter
        else:
            raise ApodeixiError(parent_trace, "Unknown filter type '" + str(filter_type) + "'",
                                            data = {"allowed filter types": str([CLI_Utils.ONLY_BASE_ENV_FILTER,
                                                                            CLI_Utils.ANY_ENV_FILTER,
                                                                            CLI_Utils.SPECIFIC_SANDBOX_ENV_FILTER])})


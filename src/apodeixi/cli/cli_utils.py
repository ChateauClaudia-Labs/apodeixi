import os                                                           as _os
import re                                                           as _re
from tabulate                                                       import tabulate

from apodeixi.controllers.admin.static_data.static_data_validator   import StaticDataValidator

from apodeixi.knowledge_base.knowledge_base_util                    import ManifestUtils
from apodeixi.knowledge_base.kb_environment                         import File_KBEnv_Impl
from apodeixi.util.a6i_error                                        import ApodeixiError
from apodeixi.util.formatting_utils                                 import StringUtils
from apodeixi.util.path_utils                                       import PathUtils

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
        def MASK_COMBINED(txt1):
            if txt1 == None:
                return None
            txt2                    = MASK_PATH(txt1)
            txt3                    = MASK_SANDBOX(txt2)
            txt4                    = _re.sub(pattern="[0-9]{6}", repl="<MASKED>", string=txt3)
            return txt4
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
                                            description.entities_added, 
                                            description.entities_removed, 
                                            description.entities_changed, 
                                            description.entities_unchanged,
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
        requesting a form

        The table has a row per manifest that was involved, with a description of what changed, if anything.
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
            kind, nb            = manifest_id.split(".")
            excel_range         = representer.label_ctx['data.range.'    + str(nb)]
            excel_sheet         = representer.label_ctx['data.sheet.'    + str(nb)]
            READ_ONLY           = 'readOnly.'+ str(nb)
            if READ_ONLY in representer.label_ctx.keys() and representer.label_ctx[READ_ONLY] == True:
                description_table.append(["Read-only Excel range for '" + kind + "'", 
                                        excel_sheet + "!" + excel_range])
            else:
                PRIOR_VERSION       = "priorVersion." + str(nb)
                if PRIOR_VERSION in representer.label_ctx.keys():
                    last_version    = representer.label_ctx[PRIOR_VERSION]
                    next_version    = last_version + 1
                    description_table.append(["Excel range for updating '" + kind + "' to version " + str(next_version), 
                                            excel_sheet + "!" + excel_range])
                else:
                    next_version    = 1
                    description_table.append(["Excel range for creating first version of '" + kind + "'", 
                                            excel_sheet + "!" + excel_range])


        manifests_description               = "\nGenerated Excel form in this area:\n\n"
        manifests_description               += clientURL + "\n\n"
        manifests_description               += tabulate(description_table, headers=description_headers)
        manifests_description               += "\n"

        return manifests_description


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

        @environment_filter A lambda function, that takes a string argument and returns True or False.
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

        @environment_filter A lambda function, that takes a string argument and returns True or False.
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
        description_headers             = ["Journey", "Scoring cycle", "Scenario", "Namespace"]

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
                                                    row[1][SCENARIO_COL], ns])
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

    def get_sandboxes(self, parent_trace, kb_session):
        '''
        Returns a nicely formatted string, suitable for CLI output. It displays all sandboxes that currently
        exist
        '''
        sandboxes                       = self._sandboxes_names_list(parent_trace, kb_session)

        description_table               = []
        description_headers             = ["Sandbox"]
        for sb in sandboxes:
            description_table.append([sb])

        description                     = "\n\n"
        description                     += tabulate(description_table, headers=description_headers)
        description                     += "\n"

        return description

    def get_posting_apis(self, parent_trace, kb_session):
        '''
        Returns a nicely formatted string, suitable for CLI output. It displays all posting APIs that the
        KnowledgeBase currenly supports.
        '''
        sandboxes                       = self._sandboxes_names_list(parent_trace, kb_session)

        description_table               = []
        description_headers             = ["Posting API"]
        for api in kb_session.kb.get_posting_apis():
            description_table.append([api])

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


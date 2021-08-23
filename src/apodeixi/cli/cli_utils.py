import os                                                           as _os
from tabulate                                                       import tabulate

from apodeixi.controllers.admin.static_data.static_data_validator   import StaticDataValidator

from apodeixi.knowledge_base.knowledge_base_util                    import ManifestUtils
from apodeixi.knowledge_base.kb_environment                         import File_KBEnv_Impl
from apodeixi.util.a6i_error                                        import ApodeixiError

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
    
    SANDBOX_SUFFIX              = "_sandbox"

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
            try:
                sandbox_name = CLI_Utils().parse_sandbox_announcement(  parent_trace    = parent_trace, 
                                                                        announcement    = dry_run_msg)
                cleaned_output_lines                    = output_lines.copy()
                cleaned_output_lines[ANNOUNCEMENT_IDX]  = CLI_Utils().sandox_announcement("<MASKED>") 

                cleaned_txt                             = '\n'.join(cleaned_output_lines)
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

    def describe_response(self, parent_trace, post_response, store):
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

    def get_namespaces(self, parent_trace, kb_session):
        '''
        Returns a nicely formatted string, suitable for CLI output. It displays the valid namespaces of the system.
        '''
        expected_organization           = kb_session.a6i_config.getOrganization(parent_trace)
        allowed_kb_areas                = kb_session.a6i_config.getKnowledgeBaseAreas(parent_trace)

        description_table               = [[expected_organization + "." + kb_area] for kb_area in allowed_kb_areas]
        description_headers             = ["Namespace"]

        description                     = "\n\n"
        description                     += tabulate(description_table, headers=description_headers)
        description                     += "\n"

        return description

    def get_products(self, parent_trace, kb_session):
        '''
        Returns a nicely formatted string, suitable for CLI output. It displays all valid products of the system.

        '''
        expected_organization           = kb_session.a6i_config.getOrganization(parent_trace)
        allowed_kb_areas                = kb_session.a6i_config.getKnowledgeBaseAreas(parent_trace)

        namespaces                      = [expected_organization + "." + kb_area for kb_area in allowed_kb_areas]

        description_table               = []
        description_headers             = ["Product", "Namespace", "Environment"]

        environments                    = []
        environments.append(kb_session.store.base_environment(parent_trace).name(parent_trace))
        environments.extend(self._sandboxes_names_list(parent_trace, kb_session))

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
        description_table.append(sandboxes)

        description                     = "\n\n"
        description                     += tabulate(description_table, headers=description_headers)
        description                     += "\n"

        return description






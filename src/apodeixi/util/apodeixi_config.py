import os                                           as _os
import toml                                         as _toml

from apodeixi.util.a6i_error                        import ApodeixiError

from apodeixi.util.dictionary_utils     import DictionaryUtils # Temporary - will refactor to upstream

class ApodeixiConfig():
    '''
    Data structure to load and hold in memory the configuration settings for the apodeixi runtime
    '''
    def __init__(self, parent_trace):
        
        CONFIG_FILE                 = self._get_config_filename(parent_trace)
        CONFIG_FOLDER               = self._get_config_folder(parent_trace)

        my_trace                    = parent_trace.doing("Attempting to load Apodeixi configuration",
                                                            data = {'CONFIG_FOLDER': CONFIG_FOLDER, 'CONFIG_FILE': CONFIG_FILE})
        try:
            with open(CONFIG_FOLDER + '/' + CONFIG_FILE, 'r') as file:
                config_txt            = str(file.read())
            config_dict = _toml.loads(config_txt)
        except Exception as ex:
            raise ApodeixiError(my_trace, "Was not able to retrieve Apodeixi configuration due to: " + str(ex))

        self.config_dict            = config_dict

        my_trace                    = parent_trace.doing("Checking for any includes")
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi_config',
                                                                path_list       = ['include', 'file'],
                                                                valid_types     = [str])
        if check:
            INCLUDE_FILE            = config_dict['include']['file']
            try:
                my_trace                    = parent_trace.doing("Attemping to load include file referenced in Apodeixi configuration",
                                                                    data = {'include.file': INCLUDE_FILE})
                with open(CONFIG_FOLDER + '/' + INCLUDE_FILE, 'r') as file:
                    file_to_include_txt            = str(file.read())
                file_to_include_dict = _toml.loads(file_to_include_txt)
            except Exception as ex:
                raise ApodeixiError(my_trace, "Was not able to retrieve include file referenced inApodeixi configuration due to: " 
                                                + str(ex),
                                                data = {'include.file': INCLUDE_FILE})

            self.config_dict        = file_to_include_dict | self.config_dict

        # Determines wheter referential integrity checks are enforced. Should be True in production but
        # unit tests may choose to turn it off.
        self.enforce_referential_integrity  = True

        # This flag will be set by test cases to assist with masking non-deterministic information about the
        # location of the test database. It is used in the masking function that hides parts of paths from regression
        # output, to avoid non-deterministic test output. When not using the test regression suite, this flag plays no role.
        self.test_db_dir                    = None

    def _get_config_folder(self, parent_trace):
        APODEIXI_CONFIG_DIRECTORY                           = _os.environ.get('APODEIXI_CONFIG_DIRECTORY')

        if APODEIXI_CONFIG_DIRECTORY == None or len(APODEIXI_CONFIG_DIRECTORY.strip())==0:
            raise ApodeixiError(parent_trace, "Environment variable $APODEIXI_CONFIG_DIRECTORY is not set, so can't " 
                                                + "figure out from which folder to load the Apodeixi configuration")

        if not _os.path.isdir(APODEIXI_CONFIG_DIRECTORY):
            raise ApodeixiError(parent_trace, "Environment variable $APODEIXI_CONFIG_DIRECTORY does not point to a valid directory: '"
                                                + str(APODEIXI_CONFIG_DIRECTORY) + "'")

        return APODEIXI_CONFIG_DIRECTORY

    def _get_config_filename(self, parent_trace):
        '''
        Should be extended by derived classes to change where the configuration file should come from
        '''
        return 'apodeixi_config.toml'

    def get_static_data_api(self, parent_trace):
        '''
        Returns the Manifest API for static data. Typical usage is for code that needs to retrieve static
        data manifests.
        '''
        # This is hard-coded on purpose. Other systems that extend Apodeixi may have different APIs for static
        # data, so by making this a function that is overwritable by derived non-Apodeixi classes, we ensure
        # that Apodeixi code like the StaticDataValidator still works, since it can query this method to find
        # out what manifest API corresponds to static data.
        STATIC_DATA_API     = 'static-data.admin.a6i.io'
        return STATIC_DATA_API

    def getSecretsFolder(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving the secrets' folder from the Apodeixi Configuration ")
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi_config',
                                                                path_list       = ['secrets', 'folder'],
                                                                valid_types     = [str])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate secrets' folder: " + explanation)
        
        # Expand any environment variables in the path
        return _os.path.expandvars(self.config_dict['secrets']['folder'])    

    def get_KB_RootFolder(self, parent_trace): 
        my_trace            = parent_trace.doing("Retrieving Knowledge Base's root folder from the Apodeixi Configuration ")
        KB                  = 'knowledge-base'
        ROOT_FOLDER         = 'knowledge-base-root-folder'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [KB, ROOT_FOLDER],
                                                                valid_types     = [str])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate root folder for Knowledge Base: " + explanation)
        
        # Expand any environment variables in the path
        return _os.path.expandvars(self.config_dict[KB][ROOT_FOLDER])

    def get_ExternalCollaborationFolder(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving external collaboration root folder from the "
                                                    + "Apodeixi Configuration ")
        KB                  = 'knowledge-base'
        EXTERNAL_FOLDER     = 'external-collaboration-folder'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [KB, EXTERNAL_FOLDER],
                                                                valid_types     = [str])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate external collaboration folder: " + explanation)
        
        # Expand any environment variables in the path
        return _os.path.expandvars(self.config_dict[KB][EXTERNAL_FOLDER])

    def getMonthFiscalYearStarts(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving Knowledge Base's fiscal year start from the Apodeixi Configuration ")
        SETTINGS            = 'organization-settings'
        FY_START            = 'month-fiscal-year-starts'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [SETTINGS, FY_START],
                                                                valid_types     = [int])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate Knowledge Base's fiscal year start: " + explanation)
        
        return self.config_dict[SETTINGS][FY_START]

    def getOrganization(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving Knowledge Base's organization from the Apodeixi Configuration ")
        SETTINGS            = 'organization-settings'
        ORGANIZATION        = 'organization'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [SETTINGS, ORGANIZATION],
                                                                valid_types     = [str])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate Knowledge Base's organization: " + explanation)
        
        return self.config_dict[SETTINGS][ORGANIZATION]

    def getKnowledgeBaseAreas(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving Knowledge Base's areas from the Apodeixi Configuration ")
        SETTINGS            = 'organization-settings'
        ORGANIZATION        = 'knowledge-base-areas'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [SETTINGS, ORGANIZATION],
                                                                valid_types     = [list])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate Knowledge Base's areas: " + explanation)
        
        return self.config_dict[SETTINGS][ORGANIZATION]

    def get_CLI_InitializerClassname(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving Knowledge Base's CLI initializer classname from the Apodeixi Configuration ")
        CLI                 = 'cli'
        CLASSNAME           = 'initializer-classname'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [CLI, CLASSNAME],
                                                                valid_types     = [str])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate Knowledge Base's areas: " + explanation)
        
        return self.config_dict[CLI][CLASSNAME]

    def getGrandfatheredScoringCycles(self, parent_trace):
        '''
        Returns a list of strings, corresponding to manually configured scoring cycles that are considered
        valid.
        This method exists for backward compatibility reasons, to not invalidate data created before Apodeixi started
        enforcing that scoring cycles must be strings that can be successfully parsed into FY_Quarter objects.
        '''
        my_trace            = parent_trace.doing("Retrieving grandfathered scorcing cycles from the Apodeixi Configuration ")
        BACK_COMPATIBILITY  = 'backward-compabitility'
        GRANDFATHERED_SC    = 'grandfathered_scoring_cycles'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [BACK_COMPATIBILITY, GRANDFATHERED_SC],
                                                                valid_types     = [list])
        if not check:
            # If nothing is grandfathered, that is good. It means this deployment will only use modern
            # scoring cycles that can be converted to FY_Quarter objects
            return []
        
        return self.config_dict[BACK_COMPATIBILITY][GRANDFATHERED_SC]
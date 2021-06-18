import yaml                                         as _yaml
import os                                           as _os
import inspect                                      as _inspect
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

    def _get_config_folder(self, parent_trace):
        APODEIXI_CONFIG_DIRECTORY                           = _os.environ.get('APODEIXI_CONFIG_DIRECTORY')

        if APODEIXI_CONFIG_DIRECTORY == None or len(APODEIXI_CONFIG_DIRECTORY.strip())==0:
            raise ApodeixiError(parent_trace, "Environment variable $APODEIXI_CONFIG_DIRECTORY is not set, so can't " 
                                                + "figure out from which folder to load the Apodeixi configuration")

        if not _os.path.isdir(APODEIXI_CONFIG_DIRECTORY):
            raise ApodeixiError(parent_trace, "Environment variable $APODEIXI_CONFIG_DIRECTORY does not point to a valid directory",
                                                data = {'$APODEIXI_CONFIG_DIRECTORY', str(APODEIXI_CONFIG_DIRECTORY)})

        return APODEIXI_CONFIG_DIRECTORY

    def _get_config_filename(self, parent_trace):
        '''
        Should be extended by derived classes to change where the configuration file should come from
        '''
        return 'apodeixi_config.toml'

    def getSecretsFolder(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving the secrets' folder from the Apodeixi Configuration ")
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi_config',
                                                                path_list       = ['secrets', 'folder'],
                                                                valid_types     = [str])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate secrets' folder: " + explanation)
        
        return self.config_dict['secrets']['folder']      

    def get_KB_PostingsRootFolder(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving Knowledge Base's root postings folder from the Apodeixi Configuration ")
        KB                  = 'knowledge-base'
        POSTINGS_FOLDER     = 'postings-root-folder'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [KB, POSTINGS_FOLDER],
                                                                valid_types     = [str])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate root folder for postings: " + explanation)
        
        return self.config_dict[KB][POSTINGS_FOLDER]

    def get_KB_ManifestsRootFolder(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving Knowledge Base's root manifests folder from the Apodeixi Configuration ")
        KB                  = 'knowledge-base'
        MANIFESTS_FOLDER    = 'manifests-root-folder'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [KB, MANIFESTS_FOLDER],
                                                                valid_types     = [str])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate root folder for manifests: " + explanation)
        
        return self.config_dict[KB][MANIFESTS_FOLDER]

    def getMonthFiscalYearStarts(self, parent_trace):
        my_trace            = parent_trace.doing("Retrieving Knowledge Base's root postings folder from the Apodeixi Configuration ")
        SETTINGS            = 'organization-settings'
        FY_START            = 'month-fiscal-year-starts'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [SETTINGS, FY_START],
                                                                valid_types     = [int])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate root folder for postings: " + explanation)
        
        return self.config_dict[SETTINGS][FY_START]

    def getProducts(self, parent_trace):
        '''
        Returns list of ProductInfo objects populated from the Apodeixi Configuration.
        '''
        my_trace            = parent_trace.doing("Retrieving product short namesfrom the Apodeixi Configuration ")
        PRODUCTS            = 'products'
        NAME                = 'name'
        SHORT_NAME          = 'short-name'
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = self.config_dict, 
                                                                root_dict_name  = 'apodeixi',
                                                                path_list       = [PRODUCTS],
                                                                valid_types     = [dict])
        if not check:
            raise ApodeixiError(my_trace, "Can't locate products: " + explanation)

        products_dict       = self.config_dict[PRODUCTS]
        product_list        = []

        for lob in products_dict.keys():
            loop_trace      = my_trace.doing("Validating configuration for LOB", data = {'LOB': lob})
            if True:
                check, explanation = DictionaryUtils().validate_path(   parent_trace    = loop_trace, 
                                                                        root_dict       = products_dict, 
                                                                        root_dict_name  = 'config[' + PRODUCTS + ']',
                                                                        path_list       = [lob],
                                                                        valid_types     = [dict])        
                if not check:
                    raise ApodeixiError(loop_trace, "Invalid LOB product configuration: " + explanation)

                check, explanation = DictionaryUtils().validate_path(   parent_trace    = loop_trace, 
                                                                        root_dict       = products_dict, 
                                                                        root_dict_name  = 'config[' + PRODUCTS + ']',
                                                                        path_list       = [lob, NAME],
                                                                        valid_types     = [str])        
                if not check:
                    raise ApodeixiError(loop_trace, "Invalid LOB product configuration: " + explanation)

            lob_dict        = products_dict[lob]
            lob_name        = lob_dict[NAME]
            product_keys    = [key for key in lob_dict.keys() if type(lob_dict[key]) == dict]
            for pk in product_keys:
                
                inner_loop_trace      = my_trace.doing("Getting short-name for product", data = {'product key': pk})
                check, explanation = DictionaryUtils().validate_path(   parent_trace    = loop_trace, 
                                                                        root_dict       = lob_dict, 
                                                                        root_dict_name  = 'config[' + PRODUCTS + '][' + lob + ']',
                                                                        path_list       = [pk, SHORT_NAME],
                                                                        valid_types     = [str])  
                if not check:
                    raise ApodeixiError(inner_loop_trace, "Can't get product short-name: " + explanation)    
                product_list.append(    ProductInfo(    lob         = lob_name, 
                                                        short_name  = lob_dict[pk][SHORT_NAME], 
                                                        name        = lob_dict[pk][NAME])
                    
                    )   

        return product_list   

class ProductInfo():
    '''
    Helper class with the properties of a product
    '''
    def __init__(self, lob, short_name, name):
        self.lob            = lob
        self.short_name     = short_name
        self.name           = name

    def __eq__(self, obj):
        if not type(obj) == ProductInfo:
            return False
        return  self.lob            == obj.lob      and \
                self.short_name     == short_name   and \
                self.name           == obj.name

    def __format__(self, format_spec):
        msg     = "LOB: " + self.lob + "; Short Name: " + self.short_name + "; Name: " + self.name

        return msg

    def __str__(self):
        msg     = str(self.lob) + "." + str(self.short_name) + " (" + str(self.name) + ")"
        return msg

    def to_dict(self, parent_trace):
        '''
        Returns a dictionary representation of self built only from scalars. Useful to display in test output files.
        '''
        return {'lob': self.lob, 'short_name': self.short_name, 'name': self.name}        
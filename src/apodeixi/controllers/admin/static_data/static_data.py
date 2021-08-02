from apodeixi.util.a6i_error                                    import FunctionalTrace, ApodeixiError

from apodeixi.controllers.util.manifest_api                     import ManifestAPI
from apodeixi.controllers.util.skeleton_controller              import SkeletonController
from apodeixi.controllers.admin.static_data.static_data_coords  import StaticDataFilingCoordinates
from apodeixi.knowledge_base.knowledge_base_util                import FormRequest


#from apodeixi.text_layout.excel_layout                          import AsExcel_Config_Table, ManifestXLConfig

from apodeixi.util.formatting_utils                             import StringUtils
from apodeixi.xli.posting_controller_utils                      import UpdatePolicy, PostingConfig
from apodeixi.xli.interval                                      import GreedyIntervalSpec

class StaticData_Controller(SkeletonController):
    '''
    Abstract class.

    Implements common controller functionality across different types of static data. It is intended for simple
    controllers that support just one kind of manifest.
    '''
    def __init__(self, parent_trace, store):
        super().__init__(parent_trace, store)

        self.MANIFEST_API = ManifestAPI(    parent_trace    = parent_trace,
                                            subdomain       = StaticData_Controller._STATIC_DATA, 
                                            domain          = 'admin', 
                                            api_publisher   = 'a6i',
                                            extension       = 'io')

    _STATIC_DATA                        = 'static-data' 
    def getManifestAPI(self):
        return self.MANIFEST_API

    def getPostingConfig(self, parent_trace, kind, manifest_nb):
        '''
        Return a PostingConfig, corresponding to the configuration that this concrete controller supports.
        '''
        CONFIG_CLASS                    = self.getPostingConfigClass(parent_trace)
        if kind in self.SUPPORTED_KINDS:
            update_policy               = UpdatePolicy(reuse_uids=True, merge=False)
            config                      = StaticData_Controller._StaticDataConfig(  kind            = kind, 
                                                                                    update_policy   = update_policy,
                                                                                    manifest_nb     = manifest_nb, 
                                                                                    controller      = self)
        else:
            raise ApodeixiError(parent_trace, "Invalid domain object '" + kind + "' - should be one of "
                                                + ", ".join(self.SUPPORTED_KINDS),
                                                origination = {'signaled_from': __file__})

        return config 

    def getPostingLabel(self, parent_trace):
        '''
        Returns a PostingLabel, corresponding to the what is expected by this concrete controller class.
        '''
        ME                              = StaticData_Controller
        return ME._MyPostingLabel(parent_trace, controller = self)



    def _buildAllManifests(self, parent_trace, posting_label_handle):

        all_manifests_dict, label              = super()._buildAllManifests(parent_trace, posting_label_handle)

        return all_manifests_dict, label

    def manifestNameFromLabel(self, parent_trace, label):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        label
        '''
        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(StaticData_Controller._STATIC_DATA)
        return name

    def manifestNameFromCoords(self, parent_trace, subnamespace, coords):
        '''
        Helper method that returns what the 'name' field should be in the manifest to be created with the given
        filing coords, possibly complemented by the subnamespace.

        Example: consider a manifest name like "modernization.default.dec-2020.fusionopus"
                in namespace "my-corp.production". 

                To build such a name, this method must receive "modernization" as the subnamespace, and
                filing coords from which to infer "default", "dec-20220", and "fusionopus".

        @param subnamespace A string, which is allowed to be None. If not null, this is a further partioning of
                        the namespace into finer slices, and a manifest's name is supposed to identify the slice
                        in which the manifest resides.

        @param coords A FilingCoords object corresponding to this controller. It is used, possibly along with the
                        `subnamespace` parameter, to build a manifest name.
        '''
        FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability
        name                            = FMT(StaticData_Controller._STATIC_DATA)
        return name
        
    def _buildOneManifest(self, parent_trace, posting_data_handle, label):
        '''
        Helper function, amenable to unit testing, unlike the enveloping controller `apply` function that require a 
        knowledge base structure
        '''
        manifest_dict                   = super()._buildOneManifest(parent_trace, posting_data_handle, label)
           
        return manifest_dict

    def createTemplate(self, parent_trace, form_request, kind):
        '''
        Returns a "template" for a manifest, i.e., a dict that has the basic fields (with empty or mocked-up
        content) to support a ManifestRepresenter to create an Excel spreadsheet with that information.

        It is intended to support the processing of blind form requests.

        For reasons of convenience (to avoid going back and forth between DataFrames and YAML), it returns
        the template as a tuple of two data structures:

        * template_dict This is a dictionary of the non-assertion part of the "fake" manifest
        * template_df   This is a DataFrame for the assertion part of the "fake" manifest
        '''
        template_dict, template_df      = super().createTemplate(parent_trace, form_request, kind)

        return template_dict, template_df

    class _StaticDataConfig(PostingConfig):
        '''
        Codifies the schema and integrity expectations for products.
        '''
        def __init__(self, kind, manifest_nb, update_policy, controller):
            ME                          = StaticData_Controller._StaticDataConfig
            super().__init__(   kind                = kind, 
                                update_policy       = update_policy, 
                                manifest_nb         = manifest_nb,
                                controller          = controller)
        
            interval_spec       = GreedyIntervalSpec(   parent_trace        = None, 
                                                        entity_name         = kind
                                                        )

            self.interval_spec  = interval_spec
            self.entity_name    = kind

        def entity_as_yaml_fieldname(self):
            return StringUtils().format_as_yaml_fieldname(self.entity_name)

        def preflightPostingValidation(self, parent_trace, posted_content_df):
            '''
            Method performs some initial validation of the `dataframe`, which is intended to be a DataFrame representation of the
            data posted in Excel.

            The intention for this preflight validation is to provide the user with more user-friendly error messages that
            educate the user on what he/she should change in the posting for it to be valid. In the absence of this 
            preflight validation, the posting error from the user would eventually be caught deeper in the parsing logic,
            by which time the error generated might not be too user friendly.

            Thus this method is not so much to avoid corruption of the data, since downstream logic will prevent corruption
            anyway. Rather, it is to provide usability by outputting high-level user-meaningful error messages.
            '''

            # GOTCHA: A mandatory column like "Big Rocks" might become "big-rocks" after the first posting, i.e.,
            #           the generated form used for updates will have a column called "big-rocks", not "Big Rocks".
            #           To avoid erroring out when the situation is rather innocent, the check below does
            #           not compare "raw column names", but "formatted columns names" using a formatter that
            #           converts things like "Big Rocks" to "big-rocks"
            FMT                             = StringUtils().format_as_yaml_fieldname # Abbreviation for readability

            posted_cols                     = [FMT(col) for col in posted_content_df.columns]
            mandatory_cols                  = [FMT(self.entity_name)]
            missing_cols                    = [col for col in mandatory_cols if not col in posted_cols]
            if len(missing_cols) > 0:
                raise ApodeixiError(parent_trace, "Posting lacks some mandatory columns",
                                                    data = {    'Missing columns':    missing_cols,
                                                                'Posted columns':     posted_cols})
        def entity_name(self):
            self.entity_name

    class _MyPostingLabel(SkeletonController._MyPostingLabel):
        '''
        Codifies the schema expectations for the posting label when posting big rocks estimates. 
        '''
        def __init__(self, parent_trace, controller):
            # Shortcut to reference class static variables
            ME = StaticData_Controller._MyPostingLabel

            super().__init__(   parent_trace        = parent_trace,
                                controller          = controller,

                                mandatory_fields    = [], 

                                date_fields         = [])

        def read(self, parent_trace, posting_label_handle):
            '''
            '''
            super().read(parent_trace, posting_label_handle)

        def infer(self, parent_trace, manifest_dict, manifest_key):
            '''
            Used in the context of generating a form to build the posting label information that should be
            embedded in the generated form.

            Accomplishes this by extracting the necesssary information from the manifest given by the `manifest_dict`

            Returns a list of the fields that may be editable

            @param manifest_dict A dict object containing the information of a manifest (such as obtained after loading
                                a manifest YAML file into a dict)
            @param manifest_key A string that identifies this manifest among others. For example, "big-rock.0". Typically
                        it should be in the format <kind>.<number>
            '''
            editable_fields     = super().infer(parent_trace, manifest_dict, manifest_key)

            return editable_fields
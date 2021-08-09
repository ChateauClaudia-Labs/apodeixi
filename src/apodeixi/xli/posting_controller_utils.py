import re                                       as _re
import math                                     as _math
from collections                                import Counter
import datetime                                 as _datetime

from apodeixi.xli.xlimporter                    import SchemaUtils, ExcelTableReader, ManifestXLReadConfig
from apodeixi.xli.breakdown_builder             import UID_Store, BreakdownTree
from apodeixi.xli.interval                      import IntervalUtils

from apodeixi.controllers.util.manifest_api     import ManifestAPIVersion

from apodeixi.tree_math.link_table              import LinkTable

from apodeixi.util.dictionary_utils             import DictionaryUtils
from apodeixi.util.dataframe_utils              import DataFrameUtils
from apodeixi.util.a6i_error                    import ApodeixiError

class PostingController():
    '''
    Abstract parent class for controllers that parse Excel spreadsheet to create manifests in the KnowledgeBase

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    @param a6i_config The ApodeixiConfig instance for the Python process in which we are running.
    '''
    def __init__(self, parent_trace, store, a6i_config):
        self.store              = store
        self.a6i_config         = a6i_config
        self.init_link_table(parent_trace)
        self.show_your_work     = PostingCtrl_ShowYourWork(parent_trace)
        return

    def init_link_table(self, parent_trace):
        '''
        Initializes / resets the LinkTable used by this controller. 
        
        This should be called each time the controller switches to processing a different posting (i.e., 
        a different Excel file) since different Excel files may end up having the same UIDs for the same
        kind of manifests, and that will be rejected by the LinkTable if we use the same LinkTable across
        all Excel spreadsheets.s.
        '''
        self.link_table         = LinkTable(parent_trace)

    def apply(self, parent_trace, posting_label_handle):
        '''
        Main entry point to the controller. Retrieves an Excel, parses its content, creates the YAML manifest and saves it.

        Returns a PostResponse.

        It is an abstract method that must be implemented by derived classes.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'apply' in concrete class",
                                            origination = {'concrete class': str(self.__class__.__name__), 
                                                            'signaled_from': __file__})

    def generateForm(self, parent_trace, form_request):
        '''
        Generates and saves an Excel spreadsheet that the caller can complete and then submit
        as a posting

        Returns a FormRequestResponse object, as well as a string corresponding the log made during the processing.

        It is an abstract method that must be implemented by derived classes.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'generateForm' in concrete class",
                                            origination = {'concrete class': str(self.__class__.__name__), 
                                                            'signaled_from': __file__})

    def createTemplate(self, parent_trace, form_request, kind):
        '''
        Abstract method
        Returns a "template" for a manifest, i.e., a dict that has the basic fields (with empty or mocked-up
        content) to support a ManifestRepresenter to create an Excel spreadsheet with that information.

        It is intended to support the processing of blind form requests.

        For reasons of convenience (to avoid going back and forth between DataFrames and YAML), it returns
        the template as a tuple of two data structures:

        * template_dict This is a dictionary of the non-assertion part of the "fake" manifest
        * template_df   This is a DataFrame for the assertion part of the "fake" manifest
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'createTemplate' in concrete class",
                                            origination = {'concrete class': str(self.__class__.__name__), 
                                                            'signaled_from': __file__})

    def initialize_UID_Store(self, parent_trace, posting_data_handle, xlr_config):
        '''
        Abstract method

        Creates and returns a UID_Store object.

        It also initializes it to contain all UIDs that might have been used previously by the preceding version
        of the manifest being updated by the posting referenced by `posting_data_handel`, if such a prior
        version exists and if `config`'s update policy is set to reuse UIDs.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'initialize_UID_Store' in concrete class",
                                            origination = {'concrete class': str(self.__class__.__name__), 
                                                            'signaled_from': __file__})

    def _xl_2_tree(self, parent_trace, data_handle, xlr_config):
        '''
        Processes an Excel posting and creates a BreakoutTree out of it, and returns that BreakoutTree.

        It records some intermediate computations in self.link_table. In particular, it records the UID of
        the last node in each of the tree's branches (and a branch corresponds to a row in Excel, so basically it is
        the UID of the rightmost column in that Excel row that is for an entity)

        @xlr_config A PostingConfig object whose posting_label attribute has been previously set
        '''
        df                      = self.store.loadPostingData(parent_trace, data_handle, xlr_config)

        cols=list(df.columns)

        # Clean up df's columns by removing anything in parenthesis
        GIST_OF                 = IntervalUtils().without_comments_in_parenthesis # Intentional abbreviation for clarity/readability
        df.columns              = [GIST_OF(parent_trace, col) for col in df.columns]

        my_trace                = parent_trace.doing("Sanity check that user complied with right schema")

        xlr_config.preflightPostingValidation(parent_trace = my_trace, posted_content_df = df)
        

        
        store                   = self.initialize_UID_Store(parent_trace, data_handle, xlr_config=xlr_config)
        tree                    = BreakdownTree(uid_store = store, entity_type=xlr_config.entity_name(), parent_UID=None)
        
        # If we are supposed to use user-generated UIDs (when available) instead of generating them,
        # tell the tree's UID store to keep them. 
        #
        # At most one UID column per interval, hence the loop so that uniqueness of UID column per interval can be enforced
        for interval in xlr_config.buildIntervals(my_trace, list(df.columns)):
            tree.reserve_user_provided_uids(parent_trace, xlr_config, df[interval.columns], interval.entity_name)  

        rows                    = list(df.iterrows())
        my_trace                = parent_trace.doing("Processing DataFrame", data={ 'tree.entity_type'  : tree.entity_type,
                                                                                    'columns'           : list(df.columns)},
                                                            origination = {                   
                                                                                    'signaled_from': __file__,
                                                                                    })
        
        for idx in range(len(rows)):
            last_uid            = None # Will represent the 
            for interval in xlr_config.buildIntervals(my_trace, list(df.columns)):
                loop_trace      = my_trace.doing(   activity="Processing fragment", 
                                                    data={  'excel row': ExcelTableReader.df_2_xl_row(  
                                                                            parent_trace    = my_trace, 
                                                                            df_row_nb       = idx, 
                                                                            excel_range     = data_handle.excel_range), 
                                                            'interval': interval.columns},
                                                    origination = {
                                                            'signaled_from': __file__,
                                                             })
                a_uid           = tree.readDataframeFragment(interval=interval, row=rows[idx], parent_trace=loop_trace, 
                                                                xlr_config=xlr_config, all_rows=rows)
                if a_uid != None: # Improve our working hypothesis of last_uid
                    last_uid = a_uid
            # By now full_uid would be set to the UID of the last node added (i.e., the one added for the last interval)
            if last_uid != None: # last_uid will be None if we just processed an empty row, so this check is needed
                self.link_table.keep_row_last_UID(  parent_trace            = my_trace, 
                                                    manifest_identifier     = xlr_config.kind, 
                                                    row_nb                  = idx, 
                                                    uid                     = last_uid)

        return tree

    def getManifestAPI(self):
        '''
        Implemented by concrete classes.
        Must return a ManifestAPI object
        '''
        raise NotImplementedError("Class " + str(self.__class__) + " forgot to implement method getManifestAPI") 

    def getPostingAPI(self):
        '''
        Implemented by concrete classes.
        Must return a string corresponding to the posting API supported by this controller.
        '''
        raise NotImplementedError("Class " + str(self.__class__) + " forgot to implement method getPostingAPI")

    def getSupportedVersions(self):
        '''
        Implemented by concrete classes.
        Must return a list of strings, corresponding to the ManifestAPI versions that this controller supports.
        It is recommended that the most recent version be listed last, to ensure it will be used when creating manifests.
        The prior versions should ideally only be used for backward compatibility reasons, when reading (not writing) manifests.
        '''
        raise NotImplementedError("Class " + str(self.__class__) + " forgot to implement method getSupportedVersions") 

    def getSupportedKinds(self):
        '''
        Implemented by concrete classes.
        Must return a list of strings, corresponding to the kinds of domain objects that this controller supports.
        For example, ['capability-hierarchy'] if this controller can process postings for capability hierarchy objects.
        '''
        raise NotImplementedError("Class " + str(self.__class__) + " forgot to implement method getSupportedKinds") 

    def api_version(self, parent_trace):
        '''
        Returns a string that can be used as the value for the 'apiVersion' field in manifests. For example, 
        'capability-hierarchy.kernel.a6i.xlsx/v1a'

        '''
        allowed_versions        = self.getSupportedVersions()
        if len(allowed_versions)==0:
            raise NotImplementedError("Class " + str(self.__class__) + " incorrectly implemented method getSupportedVersions: " 
                                        + "it returns an empty list. Need at least 1 supported version") 
        last_version            = allowed_versions[-1]
        api_version             = ManifestAPIVersion(parent_trace, self.getManifestAPI(), last_version)
        return api_version.apiVersion()
        
class PostingCtrl_ShowYourWork():
    '''
    Helper class used by PostingControllers to record some intermediate calculations for later reference in
    subsequent processing steps by a PostingController.

    For example, when the controller loads a PostingLabel, it will parse information around how many
    manifests are expected to be in the posting. To make it easier later for the controller to access that
    information when looping through all the manifest-creating-tasks, the PostingLabel information can be
    packaged in this class right after the PostingLabel is loaded. The "packaging" of the information is 
    intended to make it easier to support manifest-by-manifest loops later.

    Logically speaking, data is kept as follows

    * self.manifest_props_dict maps 
    
        * <manifest number> => {manifest metadata, as key-value pairs, for kind, excel range, excel sheet}

    '''
    def __init__(self, parent_trace):

        '''
        '''
        self.manifest_props_dict                       = {}
        return

    _DATA_KIND              = '_DATA_KIND'
    _DATA_RANGE             = '_DATA_RANGE'
    _DATA_SHEET             = '_DATA_SHEET'

    def as_dict(self, parent_trace):
        '''
        Intended to help regression tests, by getting the contents of this object as a dict.
        '''
        information_dict    = {}
        #Put a prefix to make it easier to tell what this was in regression tests
        for key in self.manifest_props_dict:
            information_dict["MANIFEST_META::" + str(key)]  = self.manifest_props_dict[key]
        return information_dict

    def manifest_metas(self):
        '''
        Returns a list of lists [manifest_nb, kind, excel_range, excel_sheet]

        Each of them is extracted from the internal representation whereby 

            * self.manifest_props_dict[manifest_nb][_DATA_KIND]     = kind
            * self.manifest_props_dict[manifest_nb][_DATA_RANGE]    = excel_range
            * self.manifest_props_dict[manifest_nb][_DATA_SHEET]    = excel_sheet
        '''
        ME                              = PostingCtrl_ShowYourWork
        result                          = []
        meta_dict                       = self.manifest_props_dict
        for manifest_nb in meta_dict.keys():
            kind                        = meta_dict[manifest_nb][ME._DATA_KIND]
            excel_range                 = meta_dict[manifest_nb][ME._DATA_RANGE]
            excel_sheet                 = meta_dict[manifest_nb][ME._DATA_SHEET]
            result.append ([manifest_nb, kind, excel_range, excel_sheet])
        return result

    def keep_manifest_meta(self, parent_trace, manifest_nb, kind, excel_range, excel_sheet):
        '''
        Causes this to happen: 
        
        * self.manifest_props_dict[manifest_nb][_DATA_KIND]     = kind
        * self.manifest_props_dict[manifest_nb][_DATA_RANGE]    = excel_range
        * self.manifest_props_dict[manifest_nb][_EXCEL_SHEET]   = excel_sheet

        More details:

        Intention is to keep an enumeration of manifest identification information. This supports then looking up
        information about a manifest during processing, especially when one does not know a priory the kinds or ranges.
        '''
        ME                                          = PostingCtrl_ShowYourWork
        meta_dict                                   = self.manifest_props_dict
        if not manifest_nb in meta_dict.keys():
            meta_dict[manifest_nb]                  = {}

        meta_dict[manifest_nb][ME._DATA_KIND]       = kind
        meta_dict[manifest_nb][ME._DATA_RANGE]      = excel_range
        meta_dict[manifest_nb][ME._DATA_SHEET]      = excel_sheet   

    def get_excel_range(self, parent_trace, manifest_nb):
        ME                      = PostingCtrl_ShowYourWork
        path_list               = [manifest_nb, ME._DATA_RANGE]
        check, explanations     = DictionaryUtils().validate_path(  parent_trace        = parent_trace, 
                                                                    root_dict           = self.manifest_props_dict, 
                                                                    root_dict_name      = 'context_dict', 
                                                                    path_list           = path_list, 
                                                                    valid_types         = [str])

        excel_range             = self.manifest_props_dict[manifest_nb][ME._DATA_RANGE]
        return excel_range  

    def get_excel_sheet(self, parent_trace, manifest_nb):
        ME                      = PostingCtrl_ShowYourWork
        path_list               = [manifest_nb, ME._DATA_SHEET]
        check, explanations     = DictionaryUtils().validate_path(  parent_trace        = parent_trace, 
                                                                    root_dict           = self.manifest_props_dict, 
                                                                    root_dict_name      = 'context_dict', 
                                                                    path_list           = path_list, 
                                                                    valid_types         = [str])

        excel_range             = self.manifest_props_dict[manifest_nb][ME._DATA_SHEET]
        return excel_range    

class PostingLabel():
    '''
    When posting data via the Excel API, each Excel spreadsheet must contain some meta-information to describe what the 
    content is and where it is within the spreadsheet. This metadata must be situated in a dedicated block with the spreadsheet
    and is usually labelled "Posting Label".

    When procesing an Excel posting, Apodeixi will first look at the posting label's "manifestAPI" field. That will determine
    what kind of controller to use when processing the spreadsheet's contents.

    The controller will use a helper class, derived from this `PostingLabel` class, to complete reading the posting label
    by enforcing fields specific to that controller. These fields would typically be unique identifiers and/or metadata
    for the Apodeixi manifest object being created as a result of parsing the spreadsheet in question.

    So this class is not expected to be used directly, but as a parent class to controller-specific concrete classes.

    @param controller   A PostingController for which this PostingLabel class is associated. Needed to enforce controller-level
                        constraints, such as what APIs and versions are allowed in a PostingLabel.
    @param mandatory_fields List of strings for all the field names that must exist in the spreadsheet's range containing the
                                posting label information.
    @param date_fields      List of strings in the spreadsheet's posting labels that are dates. Dates need special parsing so need
                                this information to know which fields require it.
    '''
    def __init__(self, parent_trace, controller, mandatory_fields, optional_fields = [], date_fields = []):
        if mandatory_fields == None:
            raise ApodeixiError(parent_trace, "Can't create a PostingLabel with a null list of mandatory fields")
        self.controller             = controller
        self.mandatory_fields       = mandatory_fields
        self.optional_fields        = optional_fields
        self.date_fields            = date_fields
        self.ctx                    = None

        '''
        Explaining self.sightings dictionary

        When the self.read method parses the posting label section of an Excel spreadsheet, it will see a number
        of fields that become columns of a DataFrame produced by the parsing, often called something like 'label_df'. 
        
        Normally, for a mandatory field such as 'environment', there is exactly one column in 'label_df' called
        'environment'.

        However, sometimes an Excel spreadsheet may contain a single posting label for multiple manifests. In that case,
        a mandatory field like 'data.kind' may appear multiple times in the Excel posting label area, with integer
        suffixes to distinguish the various manifests it applies to. Thus, label_df might have columns like
        'data.kind.0', 'data.kind.1', 'data.kind.2'.

        The parsing process (the self.read method) will record this information in the self.sightings dictionary.
        It will keep an array for all the "sightings" of a field. The array is empty if there is only one sighting.
        In the two examples above, this means:

        self.sightings['environment'] = []
        self.sightings['data.kind]    = [0, 1, 2]

        If a field X is not appearing in the label_df, then X is not a key of self.sightings. So this dictionary's
        keys also inform on what are the fields that did appear in the Excel's posting label area.
        '''
        self.sightings      = None 

    def read(self, parent_trace, posting_label_handle):

        def _val_is_null(val):
            '''
            Helper method that returns a boolean. Returns true if val "is null" in the broad sense of the word, meaning
            any of:
                * val is None
                * If val is a float, val is nan
                * If val is a string, it has zero length after stripping
            '''
            if type(val) == float and _math.isnan(val):
                return True
            if type(val) == str and len(val.strip())==0:
                return True
            # If we get this far we haven't found anything problematic
                return False

        def _missing_fields(parent_trace, expected_fields, sightings, row):
            '''
            Helper method that returns a list of fields that are in the `expected_fields` but missing in the sightings.
            
            More accurately, it returns a list of columns in `row` that are missing or have missing values.
            For example, if 'kind' is in `expected_fields` and sightings['kind'] = [1, 2, 3] but row['kind.3'] is blank,
            then it 'kind.3' will be in the list that is returned.
            '''
            missing_fields                  = []
            for field in expected_fields:
                if not field in sightings.keys():
                    missing_fields.append(field)
                    continue

                idx_list                    = sightings[field]
                if len(idx_list) ==  0: # Empty index list, that means that field is a column name in the row
                    if _val_is_null(row[field]):
                        missing_fields.append(field)
                else: # There are multiple columns in row
                    for idx in idx_list:
                        col                 = field + "." + str(idx)
                        if _val_is_null(row[col]):
                            missing_fields.append(col)
            # If we get this far we haven't found anything problematic
            return missing_fields

        label_df                    = self.controller.store.loadPostingLabel(parent_trace, posting_label_handle)
        
        # Check context has the right number of rows (which are columns in Excel, since we transposed)
        excel_range                 = posting_label_handle.excel_range
        excel_range                 = excel_range.upper()
        if len(label_df.index) != 1:
            raise ApodeixiError(parent_trace, "Bad Excel range provided: " + excel_range
                            + "\nShould contain exactly two columns: keys and values", 
                            origination = {'signaled_from' : __file__})

        # Check that that context has no column that appears more than once, as that would corrupt the logic below
        # which assumes exactly 1 occurrence of each column (if not, logic will attribute that there is a "Pandas Series" value
        # in the unique row for such columns, instead of a scalar, which will lead to obstruse failures downstream such
        # as errors when we manipulate a string that is not really a string, but a Pandas Series).
        count_dict = Counter(label_df.columns)
        duplicates = [col for col in count_dict.keys() if count_dict[col] > 1]
        if len(duplicates) > 0:
            # Create a nice useful message like "data.kind.1 (appears 2 times)" if "data.kind.1" is in duplicates
            duplicate_msgs = [col + " (appears " + str(count_dict[col]) + " times)" for col in duplicates]
            raise ApodeixiError(parent_trace, "Bad Posting Label in Excel range: " + excel_range
                            + "\nSome fields appear more than once",
                            data = {'Duplicate fields': ', '.join(duplicate_msgs)}, 
                            origination = {'signaled_from' : __file__})
        
        appearances, sightings = self._fields_found(    expected_fields         = self.mandatory_fields, 
                                                        optional_fields         = self.optional_fields, 
                                                        label_df                = label_df)

        my_trace        = parent_trace.doing("Checking if fields are missing or spurious",
                                                data = {"excel range": excel_range})
        spurious_fields     = [col for col in label_df.columns if col not in appearances]
        missing_fields = _missing_fields(   parent_trace        = my_trace,
                                            expected_fields     = self.mandatory_fields, 
                                            sightings           = sightings, 
                                            row                 = label_df.loc[0])

        if len(missing_fields) > 0:
            missing_txt = ", ".join(["'" + field + "'" for field in missing_fields])
            if len(spurious_fields) > 0:
                missing_txt += "\nPerhaps you have a typo, since these other fields are not valid: " \
                                + ", ".join(["'" + field + "'" for field in spurious_fields])
            raise ApodeixiError(parent_trace, "PostingLabel in range '" + excel_range + "' lacks at least one mandatory fields: "
                            + missing_txt,
                            origination = {'signaled_from' : __file__})

        if len(spurious_fields) > 0:
            spurious_txt = ", ".join(["'" + field + "'" for field in spurious_fields])
            raise ApodeixiError(parent_trace, "PostingLabel in range '" + excel_range + "' has these invalid fields: "
                            + spurious_txt,
                            origination = {'signaled_from' : __file__})

        ctx = {}

        for appearance in appearances:
            val                 = label_df.iloc[0][appearance] # label_df has exactly one row (we checked earlier in this function)
            clean_val           = DataFrameUtils().clean(val) # Get rid of nan, etc.
            ctx[appearance]     = clean_val
            
            
        # Special validations for date fields - we only support "one appearance" for such fields. I.e.,
        # don't currently support something like "posted-on.0", "posted-on.1", "posted-on.2". Only support "posted-on"
        for field in self.date_fields:
            BAD_SCHEMA_MSG      = "Incorrect schema for field '" + field + "' when processing the context in range '" \
                                    + excel_range + "'."
            #CLEANED                                         = DataFrameUtils().clean
            val                 = ctx[field]
            clean_val           = SchemaUtils.to_yaml_date(val, BAD_SCHEMA_MSG)
            #clean_val           = CLEANED(val)
            ctx[field]          = clean_val
        
        self.ctx                = ctx 
        self.sightings  = sightings

    def checkFilingCoordsConsistency(self, parent_trace, posting_api, posted_coords):
        '''
        '''
        my_trace                        = parent_trace.doing("Validating filing coordinates align with Posting Label")               
        filing_class                    = self.controller.store.getFilingClass( my_trace, posting_api)
        if filing_class == None:
            raise ApodeixiError(my_trace, "Can't build filing coordinates from a null filing class")
        my_trace                        = my_trace.doing("Validating that posting is in the right folder structure "
                                                                + "within the Knowledge Base")
        expected_coords                 = filing_class().infer_from_label(  parent_trace    = my_trace, 
                                                                            posting_label   = self)
        if posted_coords != expected_coords:
            raise ApodeixiError(my_trace, "Inconsistency in posting: filing coordinates don't match Posting Label",
                                            data = {    "Expected": str(expected_coords),
                                                        "Posted": str(posted_coords)})

    def  checkReferentialIntegrity(self, parent_trace):
        '''
        Abstract method.

        Used to check that the values of Posting Label fields are valid. Does not return a value, but will
        raise an exception if any field is "invalid".

        Sometimes this validation might be against data configured in the ApodeixiConfig. Example: "organization"

        In other situations the validation is against the existence of static data objects which the label
        references. Example: "product" in the case of the Journeys domain.

        NOTE: This method is intended to be called *after* label.read(-) has completed, including any label.read(-)
        implemented by derived classes. 
        That is why it can't be called within label.read(-) at the PostingLabel parent class level,
        and why the design choice was made to have the calling code invoke this check right after calling label.read()
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'checkReferentialIntegrity' in concrete class",
                                            origination = {'concrete class': str(self.__class__.__name__), 
                                                            'signaled_from': __file__})

    def infer(self, parent_trace, manifest_dict, manifest_key):
        '''
        Abstract method

        Used in the context of generating a form to build the posting label information that should be
        embedded in the generated form.

        Accomplishes this by extracting the necesssary information from the manifest given by the `manifest_dict`

        Returns a list of the fields that may be editable

        @param manifest_dict A dict object containing the information of a manifest (such as obtained after loading
                            a manifest YAML file into a dict)
        @param manifest_key A string that identifies this manifest among others. For example, "big-rock.0". Typically
                    it should be in the format <kind>.<number>
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'infer' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})        
        

    def _fields_found(self, expected_fields, optional_fields, label_df):
        '''
        Helper method that "sort of" looks to see if all the expected_fields appear in the columns of label_df.
        We say "sort_of" because sometimes a field in expected_fields really corresponds to an integer-indexed set of fields.

        For example, perhaps a PostingLabel has data for multiple manifests, so label_df might have columns like
        'data.kind.0', 'data.kind.1', 'data.kind.2'. On the other hand, expected fields might contain 'data.kind'.
        In this case, we say that the expected field "appears" in the columns of label_df, and each of '
        data.kind.0', 'data.kind.1', 'data.kind.2' is an "appearance" of the expected field 'data.kind' (so 3
        appearances for 1 expected field).

        This method returns two objects: 
        
        * a list of all the columns in label_df that are "appearances" of expected fields.
        * a dictionary that maps expected_fields to a list of integers (appearance numbers). No entry exists for
          expected fields for which there is no "appearance". If there is only one apperance with no integer suffix,
          then there is an entry with an empty list. Otherwise, the list are the integer suffixes for the entry.
          For example, if the columns are 'data.kind.0', 'data.kind.1', 'data.kind.2', then the dictionary
          would contain an entry with key='data.kind' and value=[0, 1, 2]

        '''
        appearances_in_label                = []  # Will grow in loop. Subset of label_df.columns
        sightings                           = {} # Keys are from expected_fields, and values are a (possibly empty) list of integers

        REGEX                               = "^(.+)\.([0-9]+)$"  # Matches things like 'data.kind.5', with groups 'data.kind' and '5'
        pattern                             = _re.compile(REGEX)

        for col in label_df.columns:
            # If col='data.kind.5', then we'll field='data.kind' and appearance_nb='5'
            field                           = None
            appearance_nb                   = None
            g = pattern.match(col)
            if g==None or len(g.groups()) != 2: # Simple case. Maybe col='data.kind'
                field                       = col
            else:
                # The complex case. If col='data.kind.5', then g.group(1)='data.kind' and g.group(2)='5'
                field                       = g.group(1)
                appearance_nb               = g.group(2)

            schema_fields                   = expected_fields.copy()
            schema_fields.extend(optional_fields)
            if field != None and field in schema_fields:
                appearances_in_label            .append(col)

                # Now add to the list of integers associated with this field
                if not field in sightings.keys():
                    sightings[field] = []
                if appearance_nb != None:
                    sightings[field].append(appearance_nb)

        

        return appearances_in_label, sightings

    def _getField(self, parent_trace, fieldname):
        if self.ctx==None:
            raise ApodeixiError(parent_trace, "PostingLabel's context is not yet initialized, so can't read '" + fieldname + "'")
        
        if not fieldname in self.ctx.keys():
            raise ApodeixiError(parent_trace, "PostingLabel's context does not contain '" + fieldname + "'")
        
        return self.ctx[fieldname]

    def _inferField(self, parent_trace, fieldname, path_list, manifest_dict):
        '''
        Populates the `fieldname` field of `self.ctx` identified by extracting a property from `manifest_dict`
        which is identified by the `path_list`

        @param fieldname A string, corresponding to a valid entry in self.ctx for this PostingLabel object
        @param  path_list A list of strings, corresponding to the successive keys (like a "path") to navigate
                    the nested dict structure of `manifest_dict`
        @param manifest_dict A dict object containing the information of a manifest (such as obtained after loading
                    a manifest YAML file into a dict)
        '''
        my_trace                    = parent_trace.doing("Retrieving field value from manifest dictionary",
                                            data = {    "fieldname":        str(fieldname),
                                                        "path_list":        str(path_list)})
        if self.ctx == None:
            raise ApodeixiError(my_trace, "Can't infer field from manifest because ctx has not been initialized")
            
        val                         = DictionaryUtils().get_val(        parent_trace        = my_trace,
                                                                        root_dict           = manifest_dict,
                                                                        root_dict_name      = "manifest", 
                                                                        path_list           = path_list, 
                                                                        valid_types         = [str, _datetime.datetime, 
                                                                                                int, float])
        self.ctx[fieldname]         = val
                                                                        
class PostingConfig(ManifestXLReadConfig):
    '''
    Helper class serving as a container for various configurations settings impacting how a BreakdownTree is to be
    built from an Excel file

    @param update_policy    An UpdatePolicy object used to determine how to resolve conflicts between what is read
                            from Excel and what might be pre-existing in the BreakdownTree, as might happen if the BreakdownTree
                            was created by loading a pre-existing manifest.
    @param intervals        A list of lists of Interval objects, enumerated in the order in which they are expected to appear in the
                            Excel to be read. This enforces that the Excel is formatted as was expected.
    @param kind             A string identifying the manifest kind being posted
    @param manifest_nb      An integer identifying the specific manifest being procssed among other manifests
                            that are part of the same posting. 
                            Recommended numbering starting with 1, 2, 3, ...
    @param horizontally     States whether the Excel data is to be read row-by-row (horizontally=True) or 
                            column-by-column (horizontally=False)
    '''
    def __init__(self, kind, manifest_nb, update_policy, controller):
        super().__init__()
        self.update_policy          = update_policy
        self.interval_spec          = None # Should be initialized in constructor of concrete derived class
        self.kind                   = kind
        self.manifest_nb            = manifest_nb
        self.controller             = controller
        

    def preflightPostingValidation(self, parent_trace, posted_content_df):
        '''
        Abstract function implemented by concrete derived classes.

        It does some initial validation of the `posted_content_df`, which is intended to be a DataFrame representation of the
        data posted in Excel.

        The intention for this preflight validation is to provide the user with more user-friendly error messages that
        educate the user on what he/she should change in the posting for it to be valid. In the absence of this 
        preflight validation, the posting error from the user would eventually be caught deeper in the parsing logic,
        by which time the error generated might not be too user friendly.

        Thus this method is not so much to avoid corruption of the data, since downstream logic will ensure that. Rather,
        it is to provide usability by outputting high-level user-meaningful error messages.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'preflightPostingValidation' in concrete class",
                                                origination = {'concrete class': str(self.__class__.__name__), 
                                                                'signaled_from': __file__})

    def preprocessReadFragment(self, parent_trace, interval, dataframe_row):
        '''
        This is called by the BreakdownTree's readDataframeFragment method before attempting to parse a fragment
        from a row in a DataFrame.

        This method is offered as a "hook" to derived classes in case they want to "enrich" the input to the parser,
        by overwriting this method with the appropriate "enriching" logic.

        It returns "improved" versions of the `interval` and `dataframe_row` parameters.

        An example of where such "enriching" functionality is needed:
        some posting APIs choose to present the users with an Excel template that hides some information
        from the user. An example is the API for posting big rocks estimates: the "Effort" column is not included
        in the Excel spreadsheet in cases where the user chose the "explained" variant, since in that case the "Effort"
        is "implied" from the entries at multiple time buckets. Such examples make the Excel spreadsheet more user
        friendly but cause a side-effect problem for the parser: if it does not see a column like "Effort" in the
        row, which is mandatory since it is the "entity" for that row, the parser would raise an error. To address 
        this, the concrete PostingConfig class for the big rocks controller can take advantage of this method
        and implement it to "enrich" the `dataframe_row` with a synthetic "Effort" property that was not present 
        in the Excel input provided by the user.

        @param interval         An Interval object, corresponding to the columns in `row` that pertain to an entity being 
                                processed in readDataframeFragment
        @param dataframe_row    A tuple `(idx, series)` representing a row in a larger Pandas Dataframe as yielded by
                                the Dataframe `iterrows()` iterator.
        @returns                A pair: 1) an Interval object, and 2) tuple `(idx, series)` that may pass for a Pandas row
        '''
        return interval, dataframe_row

    def cleanFragmentValue(self, parent_trace, field_name, raw_value, data_series):
        '''
        Method to "clean up" a value read from a Pandas DataFrame just before it is inserted into
        the parsed tree created by the BreakdownTree's readDataframeFragment method.

        For example, a Pandas DataFrame may put some "garbage values" like nan, NaT, etc. That will later
        cause problems in the YAML created to represent manifests. In such cases, this method simply
        "cleans up the value" and replaces it with an appropriate default. For nan, that would be an empty string.

        Derived classes can overwrite this method and do additional "cleaning up". For example, a concrete
        class may know that the field in question represents a number, so may decide to replace any empty string
        by 0. Such "cleaning up" is important if later other processing code will attempt to do arithmetic on such
        values on the assumption that they are numbers - encountering an empty string will likely cause such code to
        error out. Better to pre-empt such situations by cleaning up the values at source, at the moment right before
        they are inserted into the BreakdownTree from which the manifest will later be built.

        @field_name A string, representing a column name of the DataFrame being processed. This is the column
                    where the val came from, and provides a hint to implementing code on how such a value should
                    be "cleaned up". For example, for columns of numbers an empty string should be replaced by a 0.
        @raw_value A datum, representing a particular cell value in the DataFrame being processed.
        @data_series A Pandas Series representing a "row" in a DataFrame from where the val came from.
        '''
        cleaned_val     = DataFrameUtils().clean(raw_value) # Get rid of nan, bad dates, NaT, etc
        return cleaned_val

    def excel_row_nb(self, parent_trace, dataframe_row_nb):
        show_your_work          = self.controller.show_your_work  
        manifest_nb             = self.manifest_nb  
        excel_range             = show_your_work.get_excel_range(   parent_trace        = parent_trace, 
                                                                    manifest_nb         = manifest_nb)
        excel_row_nb            = ExcelTableReader.df_2_xl_row(     parent_trace        = parent_trace, 
                                                                    df_row_nb           = dataframe_row_nb, 
                                                                    excel_range         = excel_range) 
        return excel_row_nb 

    def excel_sheet(self, parent_trace):
        show_your_work          = self.controller.show_your_work  
        manifest_nb             = self.manifest_nb  
        excel_sheet             = show_your_work.get_excel_sheet(   parent_trace        = parent_trace, 
                                                                    manifest_nb         = manifest_nb) 
        return excel_sheet 

    def buildIntervals(self, parent_trace, linear_space):
        '''
        Returns a list of Interval objects, constructed from the self.interval_spec by applying those "interval specs"
        to the specificity of the linear_space given.

        Example: Say an interval spec is: 
        
        "One interval is the list of all columns up to A (non inclusive, then columns from A to F, not inclusive, and the remaining
        columns form the last interval". 
        
        Then if the linear space is
        [Q, R, A, T, Y, U, F, G, W], the application of the spec to the linear space yields these 3 Intervals:
        
        * [Q, R]
        * [A, T, Y, U]
        * [F, G, W]
        '''
        return self.interval_spec.buildIntervals(parent_trace, linear_space)

class UpdatePolicy():
    '''
    Helper configuration used by the BreakdownTree when reading fragments and applying them to the BreakdownTree.

    It addresses the question of how to treat updates when processing fragments that already come with UIDs. For example,
    suppose the tree's parent_UID is S1.W4, and we are processing a row that has a column called "UID" with a value
    of E2.AC1, and two entity intervals keyed on "Expectations" and "Acceptance Criteria". In that case, it would seem that
    the data in question had been read in the past, and the user's posting is an update, not a create.
    So one would like to mantain those pre-exising UIDs, which in full would be: S1.W4.E2 for the "Expectations" interval
    and S1.W4.E2.AC1 for the 'Acceptance Criteria" interval.

    A related question is how to handle *missing* rows in what the user submitted. For example, if the tree was
    created by loading a previous posting an entry like S1.W4.E5.AC12 but there is no such entry being posted now, does it
    mean that we should remove the previous posting, or do we leave it as is?

    Those are the questions that this configuration object determines.
    @param reuse_uids: a boolean that if true means that we aim to re-use any UIDs that were included in the posting, as long
                        as they are topologically consistent with the posting, i.e.:
                        * If the posting is for two entities ("Expectation" and "Acceptance Criteria") then we expect a UID
                          of depth 2 (e.g., E2.AC1). Posting E2 or E2.AC1.V7 would be "illegal" and trigger an error if
                          reuse_uids = True
                        * The acronyms in the UIDs coincide with previously chosen acronyms for the entities in question.
    @param merge: a boolean that determines whether we delete all prior paths under self.parent_UID and replace them by 
                    the current posting, or whether we keep previous postings that have URIs different from the ones being
                    posted. This is useful if the user is just "patching" a bit of information, with no intention to replace
                    most of what the user previously posted.
    '''
    def __init__(self, reuse_uids, merge):
        self.reuse_uids         = reuse_uids
        self.merge              = merge
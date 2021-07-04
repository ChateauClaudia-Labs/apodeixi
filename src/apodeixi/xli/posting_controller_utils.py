import re                                       as _re
import math                                     as _math
from collections                                import Counter

from apodeixi.xli.xlimporter                    import SchemaUtils, ExcelTableReader
from apodeixi.xli.breakdown_builder             import UID_Store, BreakdownTree
from apodeixi.xli.interval                      import IntervalUtils

from apodeixi.controllers.util.manifest_api     import ManifestAPIVersion

from apodeixi.util.dictionary_utils             import DictionaryUtils
from apodeixi.util.dataframe_utils              import DataFrameUtils
from apodeixi.util.a6i_error                    import ApodeixiError

class PostingController():
    '''
    Abstract parent class for controllers that parse Excel spreadsheet to create manifests in the KnowledgeBase

    @param store A KnowledgeBaseStore instance. Handles all I/O of postings and manifests for this controller.
    '''
    def __init__(self, parent_trace, store):
        self.store              = store
        self.show_your_work     = PostingCtrl_ShowYourWork(parent_trace)
        return

    def apply(self, parent_trace, posting_label_handle):
        '''
        Main entry point to the controller. Retrieves an Excel, parses its content, creates the YAML manifest and saves it.

        Returns a PostResponse.

        It is an abstract method that must be implemented by derived classes.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'apply' in concrete class",
                                            origination = {'signaled_from': __file__})

    def _xl_2_tree(self, parent_trace, data_handle, config):
        '''
        Processes an Excel posting and creates a BreakoutTree out of it, and returns that BreakoutTree.

        It records some intermediate computations in self.show_your_work. In particular, it records the UID of
        the last node in each of the tree's branches (and a branch corresponds to a row in Excel, so basically it is
        the UID of the rightmost column in that Excel row that is for an entity)
        '''
        path                    = data_handle.getFullPath(parent_trace)
        sheet                   = data_handle.excel_sheet
        excel_range             = data_handle.excel_range
        r                       = ExcelTableReader(path, sheet,excel_range = excel_range, horizontally = config.horizontally)
        my_trace                = parent_trace.doing("Loading Excel posting data into a DataFrame",
                                                        data = {"path": path, "excel range": excel_range})
        df                      = r.read(my_trace)

        cols=list(df.columns)

        # Clean up df's columns by removing anything in parenthesis
        GIST_OF                 = IntervalUtils().without_comments_in_parenthesis # Intentional abbreviation for clarity/readability
        df.columns              = [GIST_OF(parent_trace, col) for col in df.columns]

        my_trace                = parent_trace.doing("Sanity check that user complied with right schema",
                                                        data = {"posting's path"         : str(path),
                                                                "excel range examined"  : str(excel_range)})

        config.preflightPostingValidation(parent_trace = my_trace, posted_content_df = df)
        
        store                   = UID_Store(parent_trace)
        tree                    = BreakdownTree(uid_store = store, entity_type=config.entity_name(), parent_UID=None)
        
        rows                    = list(df.iterrows())
        my_trace                = parent_trace.doing("Processing DataFrame", data={ 'tree.entity_type'  : tree.entity_type,
                                                                                    'columns'           : list(df.columns)},
                                                            origination = {                   
                                                                                    'signaled_from': __file__,
                                                                                    })
        
        for idx in range(len(rows)):
            last_uid            = None # Will represent the 
            for interval in config.buildIntervals(my_trace, list(df.columns)):
                loop_trace      = my_trace.doing(   activity="Processing fragment", 
                                                    data={  'excel row': ExcelTableReader.df_2_xl_row(  parent_trace    = my_trace, 
                                                                                                        df_row_nb       = idx, 
                                                                                                        excel_range     = r.excel_range), 
                                                            'interval': interval.columns},
                                                    origination = {
                                                            'signaled_from': __file__,
                                                             })
                a_uid           = tree.readDataframeFragment(interval=interval, row=rows[idx], parent_trace=loop_trace, 
                                                                config=config, all_rows=rows)
                if a_uid != None: # Improve our working hypothesis of last_uid
                    last_uid = a_uid
            # By now full_uid would be set to the UID of the last node added (i.e., the one added for the last interval)
            self.show_your_work.keep_row_last_UID(  parent_trace        = my_trace, 
                                                    kind                = config.kind, 
                                                    row_nb              = idx, 
                                                    uid                 = last_uid)

        return tree

    def format_as_yaml_fieldname(txt):
        '''
        Returns a re-formatting of the string `txt` to adhere to the standards controller apply to field names.
        Specifically, no spaces and all lower case. Internal spaces are replaced by a hyphen
        '''
        tyt     = txt
        if type(txt) == float and _math.isnan(txt):
            tyt = ''
        else:
            tyt = str(txt) # Precaution in case somebody passes a non-string, like a float (Pandas might put a 0.0 on an empty field instead of '')
        
        return tyt.strip().lower().replace(' ', '-')

    def getManifestAPI(self):
        '''
        Implemented by concrete classes.
        Must return a ManifestAPI object
        '''
        raise NotImplementedError("Class " + str(self.__class__) + " forgot to implement method getManifestAPI") 

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

    For example, a PostingController might create multiple manifests based on multiple Excel ranges, and they
    may need to be joined. Typically the join is determined based on Excel: if branch B1 of manifest M1 lies in the
    same Excel row as branch B2 of manifest M2, then it is possible and natural (for example) for B2 to be enriched with a
    foreign key pointing to B1. In order to make this enrichment, given B2 one must find the B1 that lies in the same
    row. This PostingCrl_ShowYourWork class supports that, by remembering the Excel row in which the UID of B1, B2 appeared, hence
    they can be matched based on that Excel row number at a stage of the computation when Excel is no longer being 
    processed, thanks to the PostingCrl_ShowYourWork object that remembered that information when it was available earlier
    in the processing.

    There are multiple data structure used to record intermediate calculations, either because the information is really 
    different or because we need to access it from a different "primary key".

    Each data structure is a (possibly nested) dictionary representing a mapping from "primary keys" to content".
    Logically speaking:

    * self.context_dict maps 
    
        * <"_MANIFEST_METADATA", manifest number> => {manifest metadata, as key-value pairs}

    * self.worklog maps

        * <kind, dataframe_row_nb> => {intermediate computations while processing such row as key-value pairs}

        * In particular, the last_UID of each row (i.e., UID for the last non-blank)

    '''
    def __init__(self, parent_trace):

        '''
        Nested dictionary of dictionaries. The leaf dictionary are at the granularity of a dataframe row for a particular manifest.
        That leaf dictionary holds
        all intermediate values that the controller chose to remember in the process of computing that particular
        manifest:

        * self.worklog[<kind>][dataframe_row_nb] if the PostingLabel has multiple manifests of the same kind.

        '''
        self.worklog                            = {}
        self.context_dict                       = {}

        ME                                      = PostingCtrl_ShowYourWork
        self.context_dict[ME._MANIFEST_META]    = {}

        return

    _ROW_WORK               = '_ROW_WORK'
    _LAST_UID               = '_LAST_UID'
    _DATA_KIND              = '_DATA_KIND'
    _DATA_RANGE             = '_DATA_RANGE'
    _DATA_SHEET             = '_DATA_SHEET'
    _MANIFEST_META          = '_MANIFEST_META'

    def keep_row_last_UID(self, parent_trace, kind, row_nb, uid, posting_label_field=None):
        '''
        Causes this to happen: self.worklog[kind][posting_label_field][row_nb][_LAST_UID] = uid
        '''
        ME                          = PostingCtrl_ShowYourWork

        path_list                   = [kind, row_nb, ME._LAST_UID]
        DictionaryUtils().set_val(  parent_trace        = parent_trace,
                                    root_dict           = self.worklog, 
                                    root_dict_name      = 'worklog', 
                                    path_list           = path_list, 
                                    val                 = uid)

    def as_dict(self, parent_trace):

        return self.context_dict | self.worklog

    def uid_from_row(self, parent_trace, kind, dataframe_row_nb):
        '''
        Finds and returns the last (i.e., most granular) UID for the given row.
        If we think of the DataFrame's row as a branch in a tree, the UID returned corresponds to the leaf
        of the branch.

        '''
        ME                          = PostingCtrl_ShowYourWork
        path_list               = [kind, dataframe_row_nb, ME._LAST_UID]
        check, explanations     = DictionaryUtils().validate_path(  parent_trace        = parent_trace, 
                                                                    root_dict           = self.worklog, 
                                                                    root_dict_name      = 'worklog', 
                                                                    path_list           = path_list, 
                                                                    valid_types         = [str])
        if not check:
            raise ApodeixiError(parent_trace, "Last UID for this row has not been recorded",
                                        data = {'kind': kind, 'dataframe_row_nb': dataframe_row_nb})
        
        return self.worklog[kind][dataframe_row_nb][ME._LAST_UID]

    def row_from_uid(self, parent_trace, kind, uid):
        '''
        This is the inverse function to uid_from_row.

        It finds and returns the unique dataframe row number for the row that contains the given uid as its
        last UID.

        If we think of the DataFrame rows as branches in a tree, then this returns the branch number given
        the UID of the branch's leaf node.
        '''
        ME                      = PostingCtrl_ShowYourWork
        my_trace                = parent_trace.doing("Computing row number from last uid",
                                                        data = {'kind': str(kind), 'uid': str(uid)})
        path_list               = [kind, DictionaryUtils.WILDCARD, ME._LAST_UID]

        def _filter_lambda(val):
            return val == uid

        filtered_dict           = DictionaryUtils().filter( parent_trace        = parent_trace, 
                                                            root_dict           = self.worklog, 
                                                            root_dict_name      = 'worklog', 
                                                            path_list           = path_list,
                                                            filter_lambda       = _filter_lambda)

        path_list               = [kind]
        check, explanations     = DictionaryUtils().validate_path(  parent_trace        = parent_trace, 
                                                                    root_dict           = filtered_dict, 
                                                                    root_dict_name      = 'worklog', 
                                                                    path_list           = path_list, 
                                                                    valid_types         = [dict])
        if not check:
            raise ApodeixiError(parent_trace, "UID has not been previously recorded for this kind of manifest",
                                        data = {'kind': str(kind), 'uid': str(uid)})
        
        matches                 = list(filtered_dict[kind].keys())

        if len(matches) != 1:
            raise ApodeixiError(my_trace, "Expected exactly 1 Excel rows with the give UID for this kind of manifest "
                                            + " - found " + str(len(matches)),
                                            data = {'kind' : kind,    
                                                    'uid'  : uid,     'rows' : str(matches)})
        return matches[0]

    def find_referenced_uid(self, parent_trace, kind1, kind2, uid1):
        '''
        Finds a uid2 such that the following is true:

        Define row_nb as the unique integer where uid1 appears for <kind1>:
        
        * self.worklog[kind1][row_nb][_LAST_UID] = uid1

        Then use the same row_nb but for <kind2>, and get uid2 as

        * self.worklog[kind2][row_nb][_LAST_UID] = uid2
        '''
        my_trace                    = parent_trace.doing("Doing row_from_uid for referencing manifest",
                                                        data = {'kind1': kind1, 'uid1': uid1})

        row_nb                      = self.row_from_uid(    parent_trace        = my_trace,
                                                            kind                = kind1,
                                                            uid                 = uid1)
        
        my_trace                    = parent_trace.doing("Doing uid_from_row for referenced manifest",
                                                        data = {'kind2': kind2, 'row_nb': row_nb})

        uid2                        = self.uid_from_row(    parent_trace        = my_trace,
                                                            kind                = kind2,
                                                            dataframe_row_nb    = row_nb)

        return uid2

    def manifest_metas(self):
        '''
        Returns a list of lists [manifest_nb, kind, excel_range, excel_sheet]

        Each of them is extracted from the internal representation whereby 

            * self.worklog[_MANIFEST_META][manifest_nb][_DATA_KIND]     = kind
            * self.worklog[_MANIFEST_META][manifest_nb][_DATA_RANGE]    = excel_range
            * self.worklog[_MANIFEST_META][manifest_nb][_DATA_SHEET]    = excel_sheet
        '''
        ME                              = PostingCtrl_ShowYourWork
        result                          = []
        meta_dict                       = self.context_dict[ME._MANIFEST_META]
        for manifest_nb in meta_dict.keys():
            kind                        = meta_dict[manifest_nb][ME._DATA_KIND]
            excel_range                 = meta_dict[manifest_nb][ME._DATA_RANGE]
            excel_sheet                 = meta_dict[manifest_nb][ME._DATA_SHEET]
            result.append ([manifest_nb, kind, excel_range, excel_sheet])
        return result

    def keep_manifest_meta(self, parent_trace, manifest_nb, kind, excel_range, excel_sheet):
        '''
        Causes this to happen: 
        
        * self.worklog[_MANIFEST_META][manifest_nb][_DATA_KIND]     = kind
        * self.worklog[_MANIFEST_META][manifest_nb][_DATA_RANGE]    = excel_range
        * self.worklog[_MANIFEST_META][manifest_nb][_EXCEL_SHEET]   = excel_sheet

        More details:

        Intention is to keep an enumeration of manifest identification information. This supports then looking up
        information about a manifest during processing, especially when one does not know a priory the kinds or ranges.
        '''
        ME                                          = PostingCtrl_ShowYourWork
        meta_dict                                   = self.context_dict[ME._MANIFEST_META]
        if not manifest_nb in meta_dict.keys():
            meta_dict[manifest_nb]                  = {}

        meta_dict[manifest_nb][ME._DATA_KIND]       = kind
        meta_dict[manifest_nb][ME._DATA_RANGE]      = excel_range
        meta_dict[manifest_nb][ME._DATA_SHEET]      = excel_sheet   

    def get_excel_range(self, parent_trace, manifest_nb):
        ME                      = PostingCtrl_ShowYourWork
        path_list               = [ME._MANIFEST_META, manifest_nb, ME._DATA_RANGE]
        check, explanations     = DictionaryUtils().validate_path(  parent_trace        = parent_trace, 
                                                                    root_dict           = self.context_dict, 
                                                                    root_dict_name      = 'context_dict', 
                                                                    path_list           = path_list, 
                                                                    valid_types         = [str])

        excel_range             = self.context_dict[ME._MANIFEST_META][manifest_nb][ME._DATA_RANGE]
        return excel_range  

    def get_excel_sheet(self, parent_trace, manifest_nb):
        ME                      = PostingCtrl_ShowYourWork
        path_list               = [ME._MANIFEST_META, manifest_nb, ME._DATA_SHEET]
        check, explanations     = DictionaryUtils().validate_path(  parent_trace        = parent_trace, 
                                                                    root_dict           = self.context_dict, 
                                                                    root_dict_name      = 'context_dict', 
                                                                    path_list           = path_list, 
                                                                    valid_types         = [str])

        excel_range             = self.context_dict[ME._MANIFEST_META][manifest_nb][ME._DATA_SHEET]
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

        excel_range                 = posting_label_handle.excel_range

        excel_range    = excel_range.upper()
        path            = posting_label_handle.getFullPath(parent_trace)
        sheet           = posting_label_handle.excel_sheet
        reader         = ExcelTableReader(path, sheet, excel_range, horizontally=False)
        my_trace       = parent_trace.doing("Loading Posting Label data from Excel into a DataFrame",
                                                data = {"path": path, "excel range": excel_range})
        label_df       = reader.read(my_trace)
        
        # Check context has the right number of rows (which are columns in Excel, since we transposed)
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
                                                data = {"path": path, "excel range": excel_range})
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
            ctx[appearance]     = label_df.iloc[0][appearance] # label_df has exactly one row (we checked earlier in this function)
            
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

class PostingConfig():
    '''
    Helper class serving as a container for various configurations settings impacting how a BreakdownTree is to be
    built from an Excel file

    @param update_policy    An UpdatePolicy object used to determine how to resolve conflicts between what is read
                            from Excel and what might be pre-existing in the BreakdownTree, as might happen if the BreakdownTree
                            was created by loading a pre-existing manifest.
    @param intervals        A list of lists of Interval objects, enumerated in the order in which they are expected to appear in the
                            Excel to be read. This enforces that the Excel is formatted as was expected.
    @param kind             A string identifying the manifest kind being posted
    @param horizontally     States whether the Excel data is to be read row-by-row (horizontally=True) or column-by-column (horizontally=False)
    '''
    def __init__(self, kind, manifest_nb, update_policy, controller):
        self.update_policy          = update_policy
        self.interval_spec          = None # Should be initialized in constructor of concrete derived class
        self.kind                   = kind
        self.manifest_nb            = manifest_nb
        self.controller             = controller
        self.horizontally           = True

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
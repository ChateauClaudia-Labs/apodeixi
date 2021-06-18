import re                                       as _re
import math                                     as _math
from collections                                import Counter

from apodeixi.xli.xlimporter                    import SchemaUtils, ExcelTableReader
from apodeixi.xli.breakdown_builder             import UID_Store, BreakdownTree
from apodeixi.xli.interval                      import IntervalUtils

from apodeixi.controllers.util.manifest_api     import ManifestAPIVersion

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

    def apply(self, parent_trace, excel_filename, excel_sheet, ctx_range, version):
        '''
        Main entry point to the controller. Retrieves an Excel, parses its content, creates the YAML manifest and saves it.

        Returns a PostingResponse.

        It is an abstract method that must be implemented by derived classes.
        '''
        raise ApodeixiError(parent_trace, "Someone forgot to implement abstract method 'apply' in concrete class",
                                            origination = {'signaled_from': __file__})

    def _xl_2_tree(self, parent_trace, url, excel_range, config):
        '''
        Processes an Excel posting and creates a BreakoutTree out of it, and returns that BreakoutTree.

        It records some intermediate computations in self.show_your_work. In particular, it records the UID of
        the last node in each of the tree's branches (and a branch corresponds to a row in Excel, so basically it is
        the UID of the rightmost column in that Excel row that is for an entity)
        '''
        r                       = ExcelTableReader(url = url,excel_range = excel_range, horizontally = config.horizontally)
        df                      = r.read()

        # Clean up df's columns by removing anything in parenthesis
        GIST_OF                 = IntervalUtils().without_comments_in_parenthesis # Intentional abbreviation for clarity/readability
        df.columns              = [GIST_OF(parent_trace, col) for col in df.columns]
        
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
                loop_trace      = my_trace.doing(activity="Processing fragment", data={ 'row': idx, 
                                                                                        'interval': interval.columns},
                                                                    origination = {
                                                                                        'signaled_from': __file__,
                                                                                        })
                a_uid           = tree.readDataframeFragment(interval=interval, row=rows[idx], parent_trace=loop_trace, 
                                                                config=config)
                if a_uid != None: # Improve our working hypothesis of last_uid
                    last_uid = a_uid
            # By now full_uid would be set to the UID of the last node added (i.e., the one added for the last interval)
            self.show_your_work.keep_row_last_UID(  parent_trace        = my_trace, 
                                                    kind                = config.kind, 
                                                    row_nb              = idx, 
                                                    uid                 = last_uid, 
                                                    posting_label_field = None)

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
    '''
    def __init__(self, parent_trace):

        '''
        Nested dictionary of dictionaries. The leaf dictionary are at the granularity of a manifest: it holds
        all intermediate values that the controller chose to remember in the process of computing that particular
        manifest.

        That manifest-specific dictionary is 2 levels from the root. Either:

        * or self.workloca[<kind>][<posting label field>] if the PostingLabel has multiple manifests of the same kind.

        For example, if a PostingLabel has two 'big-rock' manifests with labels 'data.kind.1' and 'data.kind.2', then
        the controller records intermediate values for the first manifest in self.worklog['big-rock]['data.kind.1']
        and for the second manifest in self.worklog['big-rock]['data.kind.2']

        A different PostingLabel that has only one 'big-rock' manifest would simply record intermediate
        '''
        self.worklog                        = {}

        ME                                  = PostingCtrl_ShowYourWork
        self.worklog[ME._MANIFEST_META]     = {}

        return

    _ROW_WORK               = '_ROW_WORK'
    _LAST_UID               = '_LAST_UID'
    _DATA_KIND              = '_DATA_KIND'
    _DATA_RANGE             = '_DATA_RANGE'
    _DATA_SHEET             = '_DATA_SHEET'
    _MANIFEST_META          = '_MANIFEST_META'

    def include(self, parent_trace, manifest_kind, posting_label_field):
        '''
        Causes this to dictionary to exist: self.worklog[manifest_kind][posting_label_field]

        More in detail:

        Used to include the intermediate data items that the associated controller computes in the process of creating
        the manifest in question. Usually the kind of a manifest is enough to uniquely identify it among all other manifests
        covered in the same posting. But to anticipate the possibility that a posting includes multiple postings of the
        same kind, optionally a posting label field can serve as identifier as well (such as "data.kind.2", i.e., the field in 
        the Posting Label whose value is the manifest kind).
        '''
        if manifest_kind == None:
            raise ApodeixiError(parent_trace, "Can't initialize the show-your-work area because kind is null")
        if posting_label_field == None:
            raise ApodeixiError(parent_trace, "Can't initialize the show-your-work area because the posting label field is null")

        if not manifest_kind in self.worklog.keys():
            self.worklog[manifest_kind]     = {}

        kind_dict = self.worklog[manifest_kind]
        if not posting_label_field in kind_dict.keys():
            kind_dict[posting_label_field]  = {}        
        return

    def find_referenced_uid(self, parent_trace, kind1, kind2, uid1, posting_label_field1=None, posting_label_field2=None):
        '''
        Finds a uid2 such that the following is true:

        Define row_nb as the unique integer where uid1 appears for <kind1, posting_label_field1>:
        
        * self.worklog[kind1][posting_label_field1][row_nb][_LAST_UID] = uid1

        Then use the same row_nb but for <kind2, posting_label_field2>, and get uid2 as

        * self.worklog[kind2][posting_label_field2][row_nb][_LAST_UID] = uid2
        '''
        my_trace                    = parent_trace.doing("Retrieving show-my-work for referencing manifest",
                                                        data = {'kind1': kind1, 'posting_label_field1': posting_label_field1})
        all_rows_dict1              = self._getAllRowsDict( parent_trace        = my_trace, 
                                                            kind                = kind1, 
                                                            posting_label_field = posting_label_field1)

        ME                          = PostingCtrl_ShowYourWork

        my_trace                    = parent_trace.doing("Searching for Excel row for referencing manifests's branch",
                                                        data = {'kind1' : kind1, 'posting_label_field1': posting_label_field1,
                                                                'uid1'  : uid1})
        matches1                    = [row_nb for row_nb in all_rows_dict1.keys() if all_rows_dict1[row_nb][ME._LAST_UID] == uid1]
        if len(matches1) == 0:
            raise ApodeixiError(my_trace, "Found no Excel rows for referencing manifest's branch - there should have been exactly 1",
                                            data = {'kind1' : kind1, 'posting_label_field1': posting_label_field1,
                                                    'uid1'  : uid1})
        if len(matches1) > 1:
            raise ApodeixiError(my_trace, "Found multiple Excel rows for referencing manifest's branch - there should have been exactly 1",
                                            data = {'kind1' : kind1,    'posting_label_field1'  : posting_label_field1,
                                                    'uid1'  : uid1,     'matches1'              : str(matches1)})

        joining_row                 = matches1[0]
        my_trace                    = parent_trace.doing("Retrieving joining row for referenced manifest",
                                                        data = {'kind2': kind2, 'posting_label_field2': posting_label_field2})
        row_dict2                   = self._getRowDict( parent_trace        = my_trace,
                                                        row_nb              = joining_row,
                                                        kind                = kind2, 
                                                        posting_label_field = posting_label_field2)

        if not ME._LAST_UID in row_dict2.keys():
            raise ApodeixiError(my_trace, "Reference manifest has no UID in show-your-work for joining row",
                                            data = {    'kind2'                 : kind2, 
                                                        'posting_label_field2'  : posting_label_field2,
                                                        'joining_row'           : joining_row})
            

        return row_dict2[ME._LAST_UID]

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
        meta_dict                       = self.worklog[ME._MANIFEST_META]
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
        * self.worklog[_MANIFEST_META][manifest_nb][_EXCEL_RANGE]   = excel_sheet

        More details:

        Intention is to keep an enumeration of manifest identification information. This supports then looking up
        information about a manifest during processing, especially when one does not know a priory the kinds or ranges.
        '''
        ME                                          = PostingCtrl_ShowYourWork
        meta_dict                                   = self.worklog[ME._MANIFEST_META]
        if not manifest_nb in meta_dict.keys():
            meta_dict[manifest_nb]                  = {}

        meta_dict[manifest_nb][ME._DATA_KIND]       = kind
        meta_dict[manifest_nb][ME._DATA_RANGE]      = excel_range
        meta_dict[manifest_nb][ME._DATA_SHEET]      = excel_sheet

    def keep_row_last_UID(self, parent_trace, kind, row_nb, uid, posting_label_field=None):
        '''
        Causes this to happen: self.worklog[kind][posting_label_field][row_nb][_LAST_UID] = uid
        '''
        ME                  = PostingCtrl_ShowYourWork
        self.keep_row_work(parent_trace, kind, row_nb, ME._LAST_UID, uid, posting_label_field=None)

    def keep_row_work(self, parent_trace, kind, row_nb, thing_to_remember, value, posting_label_field=None):
        '''
        Causes this to happen: self.worklog[kind][posting_label_field][row_nb][thing_to_remember] = value
        '''
        row_dict                        = self._getRowDict(parent_trace, row_nb, kind, posting_label_field)
        row_dict[thing_to_remember]     = value

    def keep(self, parent_trace, kind, thing_to_remember, value, posting_label_field=None):
        '''
        Causes this to happen: self.worklog[kind][posting_label_field][thing_to_remember] = value

        More in detail:
        Remembers the value for the given thing_to_remember for the manifest identified by the kind and posting_field_label.
        If posting_field_label is None, and if self.worklog[kind] has only one child, then that child is assumed to
        be the posting_field_label that was intended.
        This defaulting behavior is added for usability, so that callers only have to remember the kind of manifest
        in situations where the PostingLabel does not include multiple manifests of the same kind, which is the most
        frequent situation.
        '''
        my_trace                            = parent_trade.doing("Retrieving show-your-work area previously set up "
                                                                    +" to remember work for this manifest",
                                                                    data = {'kind': kind, 'posting_label_field': posting_label_field})
        work_dict                           = self._getWorkDict(my_trace, kind, posting_label_field)
        
        if work_dict == None:
            raise ApodeixiError(parent_trace, "Incorrectly set show-your-work area for manifest: it is null",
                                                data = {'kind': kind, 'posting_label_field': posting_label_field})
        # Now for the real work
        work_dict[thing_to_remember] = value

    def _getAllRowsDict(self, parent_trace, kind, posting_label_field):
        '''
        Helper function to return the dictionary under

            self.worklog[kind][posting_label_field]
        '''
        work_dict                   = self._getWorkDict(parent_trace, kind, posting_label_field)
        ME                          = PostingCtrl_ShowYourWork
        if not ME._ROW_WORK in work_dict.keys():
            work_dict[ME._ROW_WORK] = {} # Keys will be integer row numbers, and values will be dictionaries for thing_to_remember/value
        
        all_rows_dict               = work_dict[ME._ROW_WORK]
        return all_rows_dict

    def _getRowDict(self, parent_trace, row_nb, kind, posting_label_field):
        '''
        Helper function to return the dictionary under

            self.worklog[kind][posting_label_field][row_nb]
        '''
        all_rows_dict               = self._getAllRowsDict(parent_trace, kind, posting_label_field)
        if not row_nb in all_rows_dict.keys():
            all_rows_dict[row_nb]   = {} # Keys will be properties, values their value
        
        row_dict                    = all_rows_dict[row_nb]
        return row_dict

    def _getWorkDict(self, parent_trace, kind, posting_label_field):
        if not kind in self.worklog.keys():
            raise ApodeixiError(parent_trace, "Can't retrieve show-your-work area because the requested kind was not "\
                                            + "previously initialized. Sounds like include(-) was not called in advance",
                                            data = {'kind': kind})
                                            
        kind_dict                           = self.worklog[kind]
        label_fields                        = list(kind_dict.keys())
        if len(label_fields) == 0:
            raise ApodeixiError(parent_trace, "Can't retrieve show-your-work area because no labels were "
                                            + "previously initialized for the given kind. "
                                            + "Sounds like include(-) was not called in advance",
                                            data = {'kind': kind})

        if posting_label_field == None:
            # Check if there is only one child, and so return it
            if len(label_fields) == 1:
                return kind_dict[label_fields[0]]
            # 
            raise ApodeixiError(parent_trace, "Can't retrieve show-your-work area since a null posting label field was given, "
                                                + " and there are multiple fields to previously included, so can't failover to a unique "
                                                + " default",
                                                data = {'kind': kind, 'previously included labels': str(label_fields)})
                
        if not posting_label_field in kind_dict.keys():
            raise ApodeixiError(parent_trace, "Can't retrieve show-your-work area because the requested label was not "
                                            + "previously initialized under the requested kind. "
                                            + "Sounds like include(-) was not called in advance",
                                            data = {'kind': kind, 'posting_label_field': posting_label_field})
            
        # All is good, so finally retrieve the work in question
        return kind_dict[posting_label_field]

class PostingLabel():
    '''
    When posting data via the Excel API, each Excel spreadsheet must contain some meta-information to describe what the 
    content is and where it is within the spreadsheet. This metadata must be situated in a dedicated block with the spreadsheet
    and is usually labelled "Posting Label".

    When procesing an Excel posting, Apodeixi will first look at the posting label's "excelAPI" field. That will determine
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

    def __init__(self, parent_trace, controller, mandatory_fields, date_fields):
        if mandatory_fields == None:
            raise ApodeixiError(parent_trace, "Can't create a PostingLabel with a null list of mandatory fields")
        self.controller             = controller
        self.mandatory_fields       = mandatory_fields
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

    def read(self, parent_trace, url, excel_range):

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

        def _missing_fields(expected_fields, sightings, row):
            '''
            Helper method that returns a list of fields that are in the `expected_fields` but missing in the sightings.
            
            More accurately, it returns a list of columns in `row` that are missing or have missing values.
            For example, if 'kind' is in `expected_fields` and sightings['kind'] = [1, 2, 3] but row['kind.3'] is blank,
            then it 'kind.3' will be in the list that is returned.
            '''
            missing_fields                  = []
            for field in expected_fields:
                if not field in sightings.keys():
                    missing_fields.append[field]
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

        excel_range    = excel_range.upper()
        reader         = ExcelTableReader(url, excel_range, horizontally=False)
        label_df       = reader.read()
        
        # Check context has the right number of rows (which are columns in Excel, since we transposed)
        if len(label_df.index) != 1:
            raise ApodeixiError(parent_trace, "Bad Excel range provided: " + excel_range
                            + "\nShould contain exactly two columns: keys and values")

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
                            data = {'Duplicate fields': ', '.join(duplicate_msgs)})
        
        appearances, sightings = self._fields_found(self.mandatory_fields, label_df)
        #missing_fields = [field for field in self.mandatory_fields if field not in sightings.keys()]
        missing_fields = _missing_fields(   expected_fields     = self.mandatory_fields, 
                                            sightings           = sightings, 
                                            row                 = label_df.loc[0])

        if len(missing_fields) > 0:
            missing_txt = ", ".join(["'" + field + "'" for field in missing_fields])
            raise ApodeixiError(parent_trace, "PostingLabel in range '" + excel_range + "' lacks at least one entry mandatory fields: "
                            + missing_txt)
                       
        ctx = {}

        for appearance in appearances:
            ctx[appearance]     = label_df.iloc[0][appearance] # label_df has exactly one row (we checked earlier in this function)
            
        # Special validations for date fields - we only support "one appearance" for such fields. I.e.,
        # don't currently support something like "posted-on.0", "posted-on.1", "posted-on.2". Only support "posted-on"
        for field in self.date_fields:
            BAD_SCHEMA_MSG      = "Incorrect schema for field '" + field + "' when processing the context in range '" \
                                    + excel_range + "'."
            ctx[field]          = SchemaUtils.to_yaml_date(ctx[field], BAD_SCHEMA_MSG)
        
        self.ctx                = ctx 
        self.sightings  = sightings

    def _fields_found(self, expected_fields, label_df):
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

            if field != None and field in expected_fields:
                appearances_in_label            .append(col)

                # Now add to the list of integers associated with this field
                if not field in sightings.keys():
                    sightings[field] = []
                if appearance_nb != None:
                    sightings[field].append(appearance_nb)

        

        return appearances_in_label, sightings

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
    def __init__(self, kind):
        self.update_policy          = None
        self.interval_spec          = None
        self.kind                   = kind
        self.horizontally           = True

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
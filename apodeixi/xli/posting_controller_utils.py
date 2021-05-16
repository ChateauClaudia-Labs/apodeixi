import re                                       as _re

from apodeixi.xli.xlimporter                    import SchemaUtils, ExcelTableReader
from apodeixi.xli.breakdown_builder             import UID_Store, BreakdownTree
from apodeixi.controllers.util.manifest_api     import ManifestAPIVersion

from apodeixi.util.a6i_error                    import ApodeixiError

class PostingController():
    '''
    Parent class for controllers that parse Excel spreadsheet to create manifests in the KnowledgeBase
    '''
    def __init__(self):
        return

    def _xl_2_tree(self, parent_trace, url, excel_range, config):
        '''
        Processes an Excel posting and creates a BreakoutTree out of it. It returns a tuple `(tree, ctx)` where 
        `tree` is the BreakoutTree and `ctx` is the `PostingLabel` object from the Excel.
        '''
        r                       = ExcelTableReader(url = url,excel_range = excel_range)
        df                      = r.read()
        
        store                   = UID_Store()
        tree                    = BreakdownTree(uid_store = store, entity_type=config.entity_name(), parent_UID=None)
        
        rows                    = list(df.iterrows())
        my_trace                = parent_trace.doing("Processing DataFrame", data={'tree.entity_type'  : tree.entity_type,
                                                                                            'columns'           : list(df.columns)})
        for idx in range(len(rows)):
            for interval in config.intervals:
                loop_trace        = my_trace.doing(activity="Processing fragment", data={'row': idx, 'interval': interval})
                tree.readDataframeFragment(interval=interval, row=rows[idx], parent_trace=loop_trace, update_policy=config.update_policy)
        
        return tree

    def format_as_yaml_fieldname(txt):
        '''
        Returns a re-formatting of the string `txt` to adhere to the standards controller apply to field names.
        Specifically, no spaces and all lower case. Internal spaces are replaced by a hyphen
        '''
        return txt.strip().lower().replace(' ', '-')

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
        excel_range    = excel_range.upper()
        reader         = ExcelTableReader(url, excel_range, horizontally=False)
        label_df     = reader.read()
        
        # Check context has the right number of rows (which are columns in Excel, since we transposed)
        if len(label_df.index) != 1:
            raise ApodeixiError(parent_trace, "Bad Excel range provided: " + excel_range
                            + "\nShould contain exactly two columns: keys and values")
        
        appearances, sightings = self._fields_found(self.mandatory_fields, label_df)
        missing_fields = [field for field in self.mandatory_fields if field not in sightings.keys()]
        if len(missing_fields) > 0:
            missing_txt = ", ".join(["'" + field + "'" for field in missing_fields])
            raise ApodeixiError(parent_trace, "PostingLabel in range '" + excel_range + "' lacks these mandatory fields: "
                            + missing_txt)
                       
        ctx = {}

        for appearance in appearances:
            ctx[appearance]     = label_df.iloc[0][appearance] # labe_df has exactly one row (we checked earlier in this function)
            
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

    '''
    def __init__(self):
        self.update_policy          = None
        self.intervals              = []

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
from apodeixi.xli.xlimporter        import SchemaUtils, ExcelTableReader
from apodeixi.xli.breakdown_builder import UID_Store, BreakdownTree
from apodeixi.util.a6i_error        import ApodeixiError

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

    @param mandatory_fields List of strings for all the field names that must exist in the spreadsheet's range containing the
                                posting label information.
    @param date_fields      List of strings in the spreadsheet's posting labels that are dates. Dates need special parsing so need
                                this information to know which fields require it.
    '''

    def __init__(self, mandatory_fields, date_fields):
        self.mandatory_fields       = mandatory_fields
        self.date_fields            = date_fields
        self.ctx                    = None

    def read(self, parent_trace, url, excel_range):
        excel_range    = excel_range.upper()
        reader         = ExcelTableReader(url, excel_range, horizontally=False)
        context_df     = reader.read()
        
        # Check context has the right number of rows (which are columns in Excel, since we transposed)
        if len(context_df.index) != 1:
            raise ApodeixiError(parent_trace, "Bad Excel range provided: " + excel_range
                            + "\nShould contain exactly two columns: keys and values")
        
        missing_cols = set(self.mandatory_fields).difference(set(context_df.columns))
        if len(missing_cols) > 0:
            missing_txt = ", ".join(["'" + col + "'" for col in missing_cols])
            raise ApodeixiError(parent_trace, "Range '" + excel_range + "' lacks these mandatory context fields: "
                            + missing_txt)
                       
        ctx = {}
        for field in self.mandatory_fields:
            ctx[field] = context_df.iloc[0][field]
            
        # Validations for some fields
        for field in self.date_fields:
            BAD_SCHEMA_MSG      = "Incorrect schema for field '" + field + "' when processing the context in range '" \
                                    + excel_range + "'."
            ctx[field]  = SchemaUtils.to_yaml_date(ctx[field], BAD_SCHEMA_MSG)
        
        self.ctx            = ctx 

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
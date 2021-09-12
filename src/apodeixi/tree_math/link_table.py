from apodeixi.util.a6i_error                    import ApodeixiError
from apodeixi.util.formatting_utils             import StringUtils

class LinkTable():
    '''
    This class implement the link table concept for Apodeixi. Refer to the documentation of AssertionTree in
    assertion_tree.py for background on this concept.

    This implementation is intended to support the PostingController  and ManifestRepresenter objects as they
    read / write (respectively) Excel spreadsheets representations of YAML manifests. These processes
    may involve expressing multiple manifests in the same Excel worksheet, possibly with joins. 
    The LinkTable class supports such joins by keeping track of the alignment between rows numbers and UIDs for
    the various manifests involved in a join.

    The LinkTable supports going back and forth between row numbers and UIDs for a given manifest.

    The normal usage for client code (a PostingController or ManifestRepresenter) is this:

    1. When processing a manifest's dataset, it will record in the LinkTable the association of row numbers
       to manifest UIDs for that 1st manifest.
    2. Later when processing a 2nd manifest's dataset that links to the 1st manifest's dataset, the 
       LinkTable is queried. The direction of the query differs between controllers and representers:
        a. For a PostingController, it uses the row number to figure out the 1st manifest's UID that must
            be included as a foreign key in the 2nd manifest
        b. For a ManifestRepresenter, it uses a foreign key UID (i.e., a UID for the 1st manifest) to search for 
            a row number in which to lay out data for the 2nd manifest so that it aligns with the 1st manifest.

    NOTE: The concept of "row number" is up to the client code to determine. 
    
    1)  PostingControllers normally choose to use DataFrame row numbers, which means that they are at 
        an offset to Excel row number. 
        That's because PostingController code is typically manipulating a DataFrame previously loaded from Excel. 
    2)  In contrast, ManifestRepresenters usually use an Excel row number.
        That's because they are manipulating directly an Excel worksheet data structure as they populate it.
    '''
    def __init__(self, parent_trace):

        '''
        A dictionary. Keys are manifest identifiers and values are _Row_UID_Links objects recording an
        association between row numbers and UIDs for that manifest.

        A "manifest identifier" is up to the caller to determine, but typically it would be a string
        in the format of <kind>.<manifest_row_nb>. For example, "big-rock.1"
        '''
        self.links_dict                             = {}

        return

    def keep_row_last_UID(self, parent_trace, manifest_identifier, row_nb, uid):
        '''
        Establishes a link between the row number and the UID
        '''
        if not manifest_identifier in self.links_dict.keys():
            links                                   = LinkTable._Row_UID_Links(parent_trace)
            self.links_dict[manifest_identifier]    = links

        links                                       = self.links_dict[manifest_identifier]
        links.addLink(parent_trace, row_number=row_nb, uid=uid)

    def as_dict(self, parent_trace):

        information_dict                            = {}
        for manifest_identifier in self.links_dict.keys():
            links                                   = self.links_dict[manifest_identifier]
            key                                     = "ROW_2_UID_LINK::" + manifest_identifier
            information_dict[key]                   = links.row_2_uid

        return information_dict

    def uid_from_row(self, parent_trace, manifest_identifier, row_number):
        '''
        Finds and returns the last (i.e., most granular) UID for the given row number.
        If we think of the DataFrame's row as a branch in a tree, the UID returned corresponds to the leaf
        of the branch.
        '''
        if not manifest_identifier in self.links_dict.keys():
            raise ApodeixiError(parent_trace, "Can't retrieve UID from row number because manifest has no links "
                                                + "associated with it",
                                                data = {    "manifest_identifier":      str(manifest_identifier),
                                                            "row_number":               str(row_number)})

        links                                       = self.links_dict[manifest_identifier]
        uid                                         = links.find_uid(parent_trace, row_number)
        return uid

    def row_from_uid(self, parent_trace, manifest_identifier, uid):
        '''
        This is the inverse function to uid_from_row.

        It finds and returns the unique dataframe row number for the row that contains the given uid as its
        last UID.

        If we think of the DataFrame rows as branches in a tree, then this returns the branch number given
        the UID of the branch's leaf node.
        '''
        if not manifest_identifier in self.links_dict.keys():
            raise ApodeixiError(parent_trace, "Can't retrieve row number from UID because manifest has no links "
                                                + "associated with it",
                                                data = {    "manifest_identifier":      str(manifest_identifier),
                                                            "uid":               str(uid)})

        links                                       = self.links_dict[manifest_identifier]
        row_number                                  = links.find_row_number(parent_trace, uid)
        return row_number

    def last_row_number(self, parent_trace, manifest_identifier):
        '''
        Returns the biggest row number know to this LikeTable for the given manifest identifier. If there
        are no rows returns None
        '''
        if not manifest_identifier in self.links_dict.keys():
            raise ApodeixiError(parent_trace, "Can't retrieve largest row number because manifest has no links "
                                                + "associated with it",
                                                data = {    "manifest_identifier":      str(manifest_identifier)})
        links                                       = self.links_dict[manifest_identifier]
        row_number                                  = links.last_row_number(parent_trace)
        return row_number

    def find_foreign_uid(self, parent_trace, our_manifest_id, foreign_manifest_id, our_manifest_uid, many_to_one):
        '''
        Used to establish joins between manifest by determining the foreign key to use in the join, i.e.,
        a way for "our manifest" to reference a "foreign manifest".

        Specifically, it assumes a link exists in this LinkTable between one of our manifest's UIDs and
        one of the foreign manifest's and finds and return's that foreign manifest's UIDs that our UID is linked to.

        @param many_to_one A boolean. If True, it is that multiple rows of our manifest correspond to the same
                                row of the foreign manifest, and only the first such row would have displayed
                                the foreign UID. That triggers a need to "search" for earlier row numbers
        '''
        row_nb              = self.row_from_uid(    parent_trace            = parent_trace,
                                                    manifest_identifier     = our_manifest_id,
                                                    uid                     = our_manifest_uid)

        if many_to_one == False: # search only in row_nb
            foreign_uid     = self.uid_from_row(    parent_trace            = parent_trace,
                                                    manifest_identifier     = foreign_manifest_id,
                                                    row_number              = row_nb)
        else: # search first in row_nb, and if nothing is found keep looking in earlier rows
            foreign_uid     = None
            for current_row in reversed(range(row_nb + 1)):
                foreign_uid = self.uid_from_row(    parent_trace            = parent_trace,
                                                    manifest_identifier     = foreign_manifest_id,
                                                    row_number              = current_row)
                if foreign_uid != None:
                    break

        return foreign_uid

    def knows_manifest(self, parent_trace, manifest_identifier):
        '''
        Returns a boolean: True if `manifest_identifier` is known to this links object, and False otherwise
        '''
        if manifest_identifier in self.links_dict.keys():
            return True
        else:
            return False

    def all_uids(self, parent_trace, manifest_identifier):
        '''
        Returns a list consisting of all the UIDs known to this class for the given manifest_identifier.
        If none exists, returns an empty list.
        '''
        if not manifest_identifier in self.links_dict.keys():
            '''
            Don't error out because there are situations where we are displaying a template involving a
            referencing manifest and a reference manifest. The template would not have caused any links
            to be put in for the referenced manifest, so if we call this method with the `manifest_identifier`
            set to the referenced attribute, we'll probably find that it is not a key in the links_dict (yet).
            So just return an empty list in that case
            '''
            return []
            '''
            raise ApodeixiError(parent_trace, "Can't retrieve all UIDs because manifest has no links "
                                                + "associated with it",
                                                data = {    "manifest_identifier":      str(manifest_identifier)})
            '''
        links                                       = self.links_dict[manifest_identifier]
        return list(links.uid_2_row.keys())

    class _Row_UID_Links():
        '''
        Helper class that assists LinkTable objects with tracking 1-1 mappings between row numbers and UIDs
        '''
        def __init__(self, parent_trace):

            '''
            Dictionary whose keys are row numbers (type: int) and values are UIDs (type: string).
            Represents the inverse mapping to uid_2_row.
            '''
            self.row_2_uid           = {}

            '''
            Dictionary whose keys are row numbers (type: int) and values are UIDs (type: string).
            Represents the inverse mapping to row_2_uid
            '''
            self.uid_2_row           = {}

        def addLink(self, parent_trace, row_number, uid):
            '''
            Remembers an association between the row_number and the uid

            @param row_number An int representing a row number in a tabular representation of a manifest's data. For 
                                example, and Excel row number of DataFrame row number.
            @param uid A string representing a unique identifier of a node in a manifest's assertion tree. For example,
                        "P4.C5"
            '''
            if type(row_number) != int:
                raise ApodeixiError(parent_trace, "Can't add a link with a row number that is not an int",
                                data = {    "type(row_number)": str(type(row_number))})

            if type(uid) != str:
                raise ApodeixiError(parent_trace, "Can't add a link with a uid that is not an string",
                                data = {    "type(uid)": str(type(uid))})

            if StringUtils().is_blank(uid):
                raise ApodeixiError(parent_trace, "Can't add a link with a blank uid",
                                data = {    "uid": str(uid)})

            # If we get this far, all checks passed. So add the link
            self.row_2_uid[row_number]      = uid
            self.uid_2_row[uid]             = row_number

        def find_row_number(self, parent_trace, uid):
            '''
            Returns the row number (an int) associated with the uid. If no such link is already recorded,
            returns None.

            @param uid A string representing a UID. Example: "P3.C5"
            '''
            if type(uid) != str:
                raise ApodeixiError(parent_trace, "Can't retrieve a row number for uid that is not an string",
                                data = {    "type(uid)": str(type(uid))})

            if uid in self.uid_2_row.keys():
                row_number              = self.uid_2_row[uid]
                return row_number
            else:
                return None

        def find_uid(self, parent_trace, row_number):
            '''
            Returns the UID (a string) associated with the given row number. If no such link is already recorded,
            returns None

            @param row_number An int representing a row number in a tabular representation of a manifest.
            '''
            if type(row_number) != int:
                raise ApodeixiError(parent_trace, "Can't retrieve a UID for a row number that is not an int",
                        data = {    "type(row_number)": str(type(row_number))})

            if row_number in self.row_2_uid.keys():
                uid                     = self.row_2_uid[row_number]
                return uid
            else:
                return None

        def last_row_number(self, parent_trace):
            '''
            Returns the largest row number known to this object
            '''
            row_list            = list(self.row_2_uid.keys())
            if len(row_list) == 0:
                return None
            else:
                return max(row_list)
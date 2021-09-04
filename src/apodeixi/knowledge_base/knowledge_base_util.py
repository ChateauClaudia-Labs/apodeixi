import os                                                       as _os
import copy
import pandas                                                   as _pd

from apodeixi.controllers.util.manifest_api                     import ManifestAPIVersion

from apodeixi.knowledge_base.filing_coordinates                 import TBD_FilingCoordinates
from apodeixi.representers.as_dataframe                         import AsDataframe_Representer

from apodeixi.xli.interval                                      import Interval, IntervalUtils
from apodeixi.xli.uid_store                                     import UID_Store

from apodeixi.util.dictionary_utils                             import DictionaryUtils
from apodeixi.util.formatting_utils                             import StringUtils
from apodeixi.util.a6i_error                                    import ApodeixiError
from apodeixi.util.dataframe_utils                              import DataFrameUtils


class PostingLabelHandle():
    '''
    Object with all the information needed to identify and retrieve the Posting Label information in a posting.

    It is not meant to be created directly - it should be created only by the KnowledgeBase store, and then passed around as needed.
    '''
    def __init__(self, parent_trace, posting_api, filing_coords, excel_filename, excel_sheet, excel_range):
        self.excel_filename         = excel_filename
        self.excel_sheet            = excel_sheet
        self.excel_range            = excel_range

        self.posting_api            = posting_api 
        self.filing_coords          = filing_coords 

    def copy(self, parent_trace):
        new_handle      = PostingLabelHandle(   parent_trace        = parent_trace, 
                                                posting_api         = self.posting_api, 
                                                filing_coords       = self.filing_coords, 
                                                excel_filename      = self.excel_filename, 
                                                excel_sheet         = self.excel_sheet, 
                                                excel_range         = self.excel_range)
        return new_handle                                              
        
    def display(self, parent_trace):
        '''
        Returns a string friendly representation of this PostingLabelHandle
        '''
        msg = "" \
            + "\n\t\t posting_api     = '" + self.posting_api + "'" \
            + "\n\t\t filing_coords   = '" + str(self.filing_coords) + "'" \
            + "\n\t\t excel_filename  = '" + self.excel_filename + "'" \
            + "\n\t\t excel_sheet     = '" + self.excel_sheet + "'" \
            + "\n\t\t excel_range     = '" + str(self.excel_range) + "'" 
        return msg

    def getPostingAPI(self, parent_trace):
        return self.posting_api

    def getRelativePath(self, parent_trace):

        if type(self.filing_coords) == TBD_FilingCoordinates: # Filing Coords haven't been set yet, so use place holder
            return self.filing_coords.getFullPath()
        else:
            parsed_tokens               = self.filing_coords.path_tokens(parent_trace)
            excel_path                  = '/'.join(parsed_tokens)
            return excel_path + "/" + self.excel_filename

    def createTaggedFilename(self, parent_trace):
        '''
        Returns a filename that should be used when creating "copies" of a posting Excel file as a result
        of processing it with this PostingLabelHandle.
        
        Regardless of what the original filename was for the Excel posting, this returns a string
        consiting of a "tag" prefix followed by the posting API.

        The "tag" depends on the self.filing_coords, and is used to distinguish multiple Excel files
        that would otherwise have the same name.
        
        Example: when JourneyFilingCoords are used, the tag is the product, creating filenames like

                    LedgerPro.big-rocks.journeys.a6i

        '''
        tag                         = self.filing_coords.getTag(parent_trace)
        if type(tag) == str and len(tag) > 0:
            filename                = tag + "." + self.posting_api + ".xlsx"
        else:
            filename                = self.posting_api + ".xlsx"

        return filename

    def buildDataHandle(self, parent_trace, manifest_nb, kind, excel_sheet, excel_range):
        '''
        Constructs a new PostingDataHandle and returns it. It shares with this PostingLabelHandle the information to
        locate the Excel spreadsheet, but (may) differ with the information internal to the Excel spreadsheet, such as
        worksheet and range. It also will populate data specific to the manifest associated to the PostingDataHandle being built
        '''
        data_handle             = PostingDataHandle(    parent_trace        = parent_trace,
                                                        manifest_nb         = manifest_nb,
                                                        kind                = kind,
                                                        filing_coords       = self.filing_coords,
                                                        excel_filename      = self.excel_filename,
                                                        excel_sheet         = excel_sheet,
                                                        excel_range         = excel_range)
        return data_handle

    def createUpdateForm(self, parent_trace, manifest_handles):
        '''
        Creates and returns a FormRequest that can be used by the user to request an Excel spreadsheet with 
        which to later update the data that is being submitted in this posting. The intention is that as this
        posting is processed, after processing the user will have the opportunity (possibly days or weeks later)
        to ammend it by submitting an "update" posting. For that the user will need an Excel spreadsheet
        that the KnowledgeBase understands is an update to a prior posting, so to obtain such a spreadsheet
        the user can give the KnowledgeBase the FormRequest object returned by this function.

        @param manifest_handles A list of ManifestHandle objects
        '''
        coords                  = self.filing_coords
        if type(coords) == TBD_FilingCoordinates:
            my_trace            = parent_trace.doing("Replacing TBD coordinates by the inferred ones")
            coords              = coords.inferred_coords(my_trace)

        form_request            = FormRequest(  parent_trace            = parent_trace, 
                                                posting_api             = self.posting_api, 
                                                filing_coords           = coords,
                                                scope                   = FormRequest.ExplicitScope(manifest_handles))
        return form_request

class PostingDataHandle():
    '''
    Object with all the information needed to identify and retrieve the content for a particulra manifest in a posting.

    It is not meant to be created directly - it should be created only by the PostingLabelHandle, and then passed around as needed.
    '''
    def __init__(self, parent_trace, manifest_nb, kind, filing_coords, excel_filename, excel_sheet, excel_range):
        self.excel_filename         = excel_filename

        self.filing_coords          = filing_coords
        self.excel_sheet            = excel_sheet
        self.excel_range            = excel_range
        self.manifest_nb            = manifest_nb
        self.kind                   = kind

    def getRelativePath(self, parent_trace):
        if type(self.filing_coords) == TBD_FilingCoordinates: # Filing Coords' tokens don't correspond to the path
            return self.filing_coords.getFullPath()
        else:
            parsed_tokens               = self.filing_coords.path_tokens(parent_trace)
            excel_path                  = '/'.join(parsed_tokens)
            return excel_path + "/" + self.excel_filename

class ManifestUtils():
    def __init__(self):
        return

    def set_manifest_version(self, parent_trace, manifest_dict, manifest_version):
        _VERSION                            = "version" # Refers to the version of the manifest, not of the posting
        _METADATA                           = "metadata"
        _LABELS                             = "labels"

        my_trace                            = parent_trace.doing("Validating manifest dictionary structure before setting version")
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = manifest_dict, 
                                                                root_dict_name  = 'manifest_dict',
                                                                path_list       = [_METADATA, _LABELS],
                                                                valid_types     = [dict])
        if not check:
            raise ApodeixiError(my_trace, "Can't set manifest version because it is not structured correctly",
                                        data = {'explanation': explanation})

        metadata_dict                       = manifest_dict[_METADATA]
        metadata_dict[_VERSION]             = manifest_version
        metadata_dict[_LABELS][_VERSION]    = manifest_version

    def get_manifest_version(self, parent_trace, manifest_dict):
        _VERSION                            = "version" # Refers to the version of the manifest, not of the posting
        _METADATA                           = "metadata"
        _LABELS                             = "labels"

        my_trace                            = parent_trace.doing("Validating manifest dictionary structure before getting version")
        check, explanation = DictionaryUtils().validate_path(   parent_trace    = my_trace, 
                                                                root_dict       = manifest_dict, 
                                                                root_dict_name  = 'manifest_dict',
                                                                path_list       = [_METADATA, _VERSION],
                                                                valid_types     = [int])
        if not check:
            raise ApodeixiError(my_trace, "Can't get manifest version because it is not structured correctly",
                                        data = {'explanation': explanation})

        metadata_dict                       = manifest_dict[_METADATA]
        manifest_version                    = metadata_dict[_VERSION] 
        return manifest_version
    
    def inferHandle(self, parent_trace, manifest_dict):
        '''
        Figures out and returns the ManifestHandle implied by the given manifest_dict. If the manifest_dict is not well
        formed it raises an error.
        '''
        if not type(manifest_dict) == dict:
            raise ApodeixiError(parent_trace, "Can't record manifest creation because manifest was not passed as a dictionary. "
                                                "Instead was given a " + str(type(manifest_dict)),
                                                origination = {'signaled_from': __file__})
        VERSION                     = 'version'
        NAME                        = 'name'
        NAMESPACE                   = 'namespace'
        KIND                        = 'kind'
        METADATA                    = 'metadata'

        REQUIRED_KEYS               = [ManifestAPIVersion.API_VERSION, METADATA, KIND]

        REQUIRED_METADATA_SUBKEYS   = [NAME, NAMESPACE, VERSION]

        missed_keys                 = [key for key in REQUIRED_KEYS if not key in manifest_dict.keys()]
        if len(missed_keys) > 0:
            raise ApodeixiError(parent_trace, "Can't infer manifest handle because these mandatory fields were absent in the "
                                                "manifest: " + str(missed_keys),
                                                origination = {'signaled_from': __file__})

        metadata_dict               = manifest_dict[METADATA]
        missed_metadata_subkeys     = [key for key in REQUIRED_METADATA_SUBKEYS if not key in metadata_dict.keys()]
        if len(missed_metadata_subkeys) > 0:
            raise ApodeixiError(parent_trace, "Can't infer manifest handle because these mandatory fields were absent in the "
                                                "manifest's metadata: " + str(missed_metadata_subkeys),
                                                origination = {'signaled_from': __file__})
        api_version                 = ManifestAPIVersion.parse(parent_trace, manifest_dict[ManifestAPIVersion.API_VERSION])
        manifest_api                = api_version.api.apiName()
        handle                      = ManifestHandle(   manifest_api    = manifest_api,
                                                        namespace       = metadata_dict[NAMESPACE], 
                                                        name            = metadata_dict[NAME], 
                                                        kind            = manifest_dict[KIND],
                                                        version         = metadata_dict[VERSION])
        return handle

    def get_manifest_apiversion(self, parent_trace, manifest_dict):
        '''
        Examines the manifest content in `manifest_dict` and returns the manifest API inside it,
        parsed as two separate strings: the API itself, and the version suffix

        For example, if the apiVersion field inside the manifest_dict is 
        
                        "delivery-planning.journeys.a6i.io/v1a",

        this method will return:

                        ("delivery-planning.journeys.a6i.io", "v1a")
        '''
        DictionaryUtils().validate_path(parent_trace    = parent_trace, 
                                        root_dict       = manifest_dict, 
                                        root_dict_name  = "manifest_dct", 
                                        path_list       = [ManifestAPIVersion.API_VERSION], 
                                        valid_types     = [str])
        # Example of apiVersion: "delivery-planning.journeys.a6i.io/v1a"
        apiVersion                      = manifest_dict[ManifestAPIVersion.API_VERSION] 
        api_tokens                      = apiVersion.split("/")
        if len(api_tokens) != 2:
            raise ApodeixiError(parent_trace, "Encountered corrupted api version in YAML file",
                            data = {"bad api version":  apiVersion,
                                    "Example of good structure":   "delivery-planning.journeys.a6i.io/v1a"})
        api_found                       = api_tokens[0]
        api_suffix_found                = api_tokens[1]  
        return api_found, api_suffix_found      

    def infer_entity(self, parent_trace, manifest_dict, manifest_nickname):
        '''
        Finds and retrieves the root entity for the `manifest_dict`, defined as the unique X such that

        * X is a key in manifest_dict["assertion"]
        * X is the unique key in manifest_dict["assertion"] such that manifest_dict["assertion"][X] is a dict
        '''      
        assertion_dict                  = DictionaryUtils().get_val(        parent_trace        = parent_trace, 
                                                                            root_dict           = manifest_dict, 
                                                                            root_dict_name      = manifest_nickname, 
                                                                            path_list           = ["assertion"], 
                                                                            valid_types         = [dict])
        entities                        = [key for key in assertion_dict.keys() if type(assertion_dict[key])==dict]
        if len(entities) != 1:
            raise ApodeixiError(parent_trace, "Corrupted manifest: expected exactly 1 entity, not " + str(len(entities)),
                                            data = {    "entities found":   str(entities)})

        entity                              = entities[0]
        return entity

    def diff_manifest(self, parent_trace, manifest_api_name, namespace, name, kind, version1, version2, store):
        '''
        Creates and returns a ManifestDiffResult object that explains what changed with a manifest
        between `version1` and `version2`.

        The diff is expressed using `version1` as the baseline. For example, the entities listed in the
        result as "added" are entities that are in `version2` but not `version1`

        @param manifest_api_name  A string, representing the manifest API for the manifest to diff.
        @param namespace  A string, representing the KnowledgeBase store's namespace containing the manifest to diff.
        @param name       A string, representing name (within the namespace) under which is filed the manifest to diff
        @param kind      A string, representing the "object type" in the Apodeixi domain model for the manifest to diff.
        @param version1         An int, representing the version of the manifest used as a baseline for the comparison
        @param version2         An int, representing the version of the manifest whose differences to the baseline are returned
        @param store            The KnowledgeBaseStore instance where the manifest in question is persisted

        '''
        if type(version1) != int or type(version2) != int:
            raise ApodeixiError(parent_trace, "Can't compute manifest diff because was provided a non-integer version",
                                                data = {"type(version1)":   str(type(version1)),
                                                        "type(version2)":   str(type(version2))})

        manifest_handle1                = ManifestHandle(manifest_api = manifest_api_name, kind=kind, namespace=namespace,
        name=name, version=version1)

        my_trace                        = parent_trace.doing("Retrieving manifest from KnowledgeBaseStore",
                                                    data = {"manifest handle": manifest_handle1.display(parent_trace)})
        manifest_dict, manifest_path    = store.retrieveManifest(my_trace, manifest_handle1)



        manifest_file                   = _os.path.split(manifest_path)[1]

        my_trace                        = parent_trace.doing("Extracting manifest's content as a DataFrame",
                                                    data = {"manifest": str(manifest_file)})
        contents_df, entity_name        = self.extract_manifest_content_as_df(my_trace, manifest_dict, manifest_file,
                                                                                        abbreviate_uids=False)
        
        my_trace                        = parent_trace.doing("Determining the manifest lifecycle event",
                                                    data = {"manifest": str(manifest_file)})

        entities_added_desc         = ""
        entities_removed_desc       = ""
        entities_changed_desc       = ""
        entities_unchanged_desc     = ""

        my_trace                        = parent_trace.doing("Determining if there's an earlier version for manifest",
                                                    data = {"manifest": str(manifest_file)})
        version                         = self.get_manifest_version(my_trace, manifest_dict)
        if True:
            # We need to load the prior version of the manifest, but check version is indeed bigger than 1
            if version <= 1:
                raise ApodeixiError("Inconsistent post response: claims to have updated manifest, but its version is low",
                                        data = {"version": str(version), "manifest kind": str(manifest_handle1.kind)})

            inner_trace                 = my_trace.doing("Retrieving prior version of manifest to describe an update lifecycle event")
            prior_handle                = copy.copy(manifest_handle1)
            prior_handle.version        = version - 1
            prior_manifest_dict, prior_manifest_path    = store.retrieveManifest(inner_trace, prior_handle)
            prior_contents_df, prior_e  = self.extract_manifest_content_as_df(inner_trace, prior_manifest_dict, 
                                                                                manifest_file, abbreviate_uids=False)

            inner_trace                 = my_trace.doing("Validating updated manifest is consistent with prior version")
            if prior_e != entity_name:
                raise ApodeixiError(inner_trace, "Manifest's entity name changed between versions. That is not allowed",
                                            data = {"new entity":       str(entity_name),
                                                    "new version":      str(version),
                                                    "prior entity":     str(prior_e),
                                                    "prior_version":    str(version-1)})
            interval_list               = self._infer_intervals(inner_trace, contents_df)
            prior_interval_list         = self._infer_intervals(inner_trace, prior_contents_df)
            
            # Verify that the new version is an extension of the prior one, since Apodeixi only allows adding
            # new entites *after* previously created entities.
            if len(prior_interval_list) > len(interval_list):
                raise ApodeixiError(inner_trace, "Invalid manifest update: can't delete UID columns present in prior manifest")
            for idx in range(len(prior_interval_list)):
                prior_interval          = prior_interval_list[idx]
                interval                = interval_list[idx]
                #Ensure intervals align by comparing the acronyms, which our helper method put into the entity_name field
                if prior_interval.entity_name != interval.entity_name:
                    raise ApodeixiError(inner_trace, "Invalid manifest update: the leaf acronyms don't match in UID columns "
                                                        + " where a match was expected",
                                                        data = {"UID column (prior)":     str(prior_interval.columns[0]),
                                                                "prior acronym":    str(prior_interval.entity_name),
                                                                "UID column (new)":     str(interval.columns[0]),
                                                                "new acronym":    str(interval.entity_name)})

            inner_trace                     = my_trace.doing("Computing lifecycle stats",
                                                        data = {"manifest": str(manifest_file)})
            added_acronym_counts            = []
            removed_acronym_counts          = []
            changed_acronym_counts          = []
            unchanged_acronym_counts        = []

            # First section: process the intervals that were there before
            for idx in range(len(prior_interval_list)):
                prior_interval              = prior_interval_list[idx]
                interval                    = interval_list[idx]
                acronym                     = prior_interval.entity_name # We already check it matches interval's
                loop_trace                  = inner_trace.doing("Counting differences for interval",
                                                                data = {"prior interval": str(prior_interval.columns),
                                                                        "new inteval": str(interval.columns)})
                UID_COLUMN                  = prior_interval.columns[0]

                prior_entities              = DataFrameUtils().safe_unique(loop_trace, prior_contents_df,   UID_COLUMN)
                entities                    = DataFrameUtils().safe_unique(loop_trace, contents_df,         UID_COLUMN)          
        
                entities_added              = [e for e in entities if not e in prior_entities]
                entities_removed            = [e for e in prior_entities if not e in entities]
                common_entities             = [e for e in entities if e in prior_entities]
                entities_changed            = [e for e in common_entities if not self.interval_values_match(
                                                                                        parent_trace  = loop_trace, 
                                                                                        entity_uid      = e, 
                                                                                        interval1       = interval, 
                                                                                        interval2       = prior_interval,
                                                                                        contents_df1    = contents_df, 
                                                                                        contents_df2    = prior_contents_df)]
                entities_unchanged          = [e for e in common_entities if self.interval_values_match(
                                                                                        parent_trace  = loop_trace, 
                                                                                        entity_uid      = e, 
                                                                                        interval1       = interval, 
                                                                                        interval2       = prior_interval, 
                                                                                        contents_df1    = contents_df, 
                                                                                        contents_df2    = prior_contents_df)]
                added_acronym_counts.       append(acronym + "(" + str(len(entities_added)) + ")")
                removed_acronym_counts.     append(acronym + "(" + str(len(entities_removed)) + ")")
                changed_acronym_counts.     append(acronym + "(" + str(len(entities_changed)) + ")")
                unchanged_acronym_counts.   append(acronym + "(" + str(len(entities_unchanged)) + ")")


            # Now process the rest of the differences: arising from new intervals that were not there before
            for idx in range(len(prior_interval_list), len(interval_list)):
                interval                    = interval_list[idx]
                acronym                     = interval.entity_name 
                loop_trace                  = inner_trace.doing("Count acronyms for newly added interval",
                                                                data = {"new inteval": str(interval.columns)})
                uid_col                     = interval.columns[0]
                uid_vals                    = [u for u in DataFrameUtils().safe_unique(loop_trace, contents_df, uid_col) 
                                                        if not StringUtils().is_blank(u)]
                uid_nb                      = len(uid_vals)
                added_acronym_counts.       append(acronym + "(" + str(uid_nb) + ")")
                # Nothing to apped to the other lists for removed, changed, unchanged, since this interval didn't
                # exist in prior_contents_df

            entities_added_desc         = ", ".join(added_acronym_counts)
            entities_removed_desc       = ", ".join(removed_acronym_counts)
            entities_changed_desc       = ", ".join(changed_acronym_counts)
            entities_unchanged_desc     = ", ".join(unchanged_acronym_counts)    

    

    def describe_manifest(self, parent_trace, manifest_handle, store, post_response):
        '''
        Creates and returns a ManifestEventDescription object that succintly describes what happened
        to a manifest during a lifecycle event

        @param manifest_handle  A ManifestHandle object for the manifest for which a description is sought
        @param store            The KnowledgeBaseStore instance where the manifest in question is persisted
        @param post_response A PostResponse object summarizing the outcome of a lifecycle event

        '''
        my_trace                        = parent_trace.doing("Retrieving manifest from KnowledgeBaseStore",
                                                    data = {"manifest handle": manifest_handle.display(parent_trace)})
        manifest_dict, manifest_path    = store.retrieveManifest(my_trace, manifest_handle)

        manifest_file                   = _os.path.split(manifest_path)[1]

        my_trace                        = parent_trace.doing("Extracting manifest's content as a DataFrame",
                                                    data = {"manifest": str(manifest_file)})
        contents_df, entity_name        = self.extract_manifest_content_as_df(my_trace, manifest_dict, manifest_file,
                                                                                        abbreviate_uids=False)
        
        my_trace                        = parent_trace.doing("Determining the manifest lifecycle event",
                                                    data = {"manifest": str(manifest_file)})
        if manifest_handle in post_response.createdManifests():
            manifest_event              = PostResponse.CREATED
        elif manifest_handle in post_response.updatedManifests():
            manifest_event              = PostResponse.UPDATED
        elif manifest_handle in post_response.deletedManifests():
            manifest_event              = PostResponse.DELETED
        elif manifest_handle in post_response.unchangedManifests():
            manifest_event              = PostResponse.UNCHANGED
        else:
            raise ApodeixiError(my_trace, "Manifest '" + str(manifest_file) + "' was not a part of the post being described")

        entities_added_desc         = ""
        entities_removed_desc       = ""
        entities_changed_desc       = ""
        entities_unchanged_desc     = ""

        my_trace                        = parent_trace.doing("Determining if there's an earlier version for manifest",
                                                    data = {"manifest": str(manifest_file)})
        version                         = self.get_manifest_version(my_trace, manifest_dict)
        if manifest_event == PostResponse.UPDATED:
            # We need to load the prior version of the manifest, but check version is indeed bigger than 1
            if version <= 1:
                raise ApodeixiError("Inconsistent post response: claims to have updated manifest, but its version is low",
                                        data = {"version": str(version), "manifest kind": str(manifest_handle.kind)})

            inner_trace                 = my_trace.doing("Retrieving prior version of manifest to describe an update lifecycle event")
            prior_handle                = copy.copy(manifest_handle)
            prior_handle.version        = version - 1
            prior_manifest_dict, prior_manifest_path    = store.retrieveManifest(inner_trace, prior_handle)
            prior_contents_df, prior_e  = self.extract_manifest_content_as_df(inner_trace, prior_manifest_dict, 
                                                                                manifest_file, abbreviate_uids=False)

            inner_trace                 = my_trace.doing("Validating updated manifest is consistent with prior version")
            if prior_e != entity_name:
                raise ApodeixiError(inner_trace, "Manifest's entity name changed between versions. That is not allowed",
                                            data = {"new entity":       str(entity_name),
                                                    "new version":      str(version),
                                                    "prior entity":     str(prior_e),
                                                    "prior_version":    str(version-1)})
            interval_list               = self._infer_intervals(inner_trace, contents_df)
            prior_interval_list         = self._infer_intervals(inner_trace, prior_contents_df)
            
            # Verify that the new version is an extension of the prior one, since Apodeixi only allows adding
            # new entites *after* previously created entities.
            if len(prior_interval_list) > len(interval_list):
                raise ApodeixiError(inner_trace, "Invalid manifest update: can't delete UID columns present in prior manifest")
            for idx in range(len(prior_interval_list)):
                prior_interval          = prior_interval_list[idx]
                interval                = interval_list[idx]
                #Ensure intervals align by comparing the acronyms, which our helper method put into the entity_name field
                if prior_interval.entity_name != interval.entity_name:
                    raise ApodeixiError(inner_trace, "Invalid manifest update: the leaf acronyms don't match in UID columns "
                                                        + " where a match was expected",
                                                        data = {"UID column (prior)":     str(prior_interval.columns[0]),
                                                                "prior acronym":    str(prior_interval.entity_name),
                                                                "UID column (new)":     str(interval.columns[0]),
                                                                "new acronym":    str(interval.entity_name)})

            inner_trace                     = my_trace.doing("Computing lifecycle stats",
                                                        data = {"manifest": str(manifest_file)})
            added_acronym_counts            = []
            removed_acronym_counts          = []
            changed_acronym_counts          = []
            unchanged_acronym_counts        = []

            # First section: process the intervals that were there before
            for idx in range(len(prior_interval_list)):
                prior_interval              = prior_interval_list[idx]
                interval                    = interval_list[idx]
                acronym                     = prior_interval.entity_name # We already check it matches interval's
                loop_trace                  = inner_trace.doing("Counting differences for interval",
                                                                data = {"prior interval": str(prior_interval.columns),
                                                                        "new inteval": str(interval.columns)})
                UID_COLUMN                  = prior_interval.columns[0]

                prior_entities              = DataFrameUtils().safe_unique(loop_trace, prior_contents_df, UID_COLUMN)
                entities                    = DataFrameUtils().safe_unique(loop_trace, contents_df, UID_COLUMN)
            
        
                entities_added              = [e for e in entities if not e in prior_entities]
                entities_removed            = [e for e in prior_entities if not e in entities]
                common_entities             = [e for e in entities if e in prior_entities]
                entities_changed            = [e for e in common_entities if not self.interval_values_match(
                                                                                        parent_trace  = loop_trace, 
                                                                                        entity_uid      = e, 
                                                                                        interval1       = interval, 
                                                                                        interval2       = prior_interval,
                                                                                        contents_df1    = contents_df, 
                                                                                        contents_df2    = prior_contents_df)]
                entities_unchanged          = [e for e in common_entities if self.interval_values_match(
                                                                                        parent_trace  = loop_trace, 
                                                                                        entity_uid      = e, 
                                                                                        interval1       = interval, 
                                                                                        interval2       = prior_interval, 
                                                                                        contents_df1    = contents_df, 
                                                                                        contents_df2    = prior_contents_df)]
                added_acronym_counts.       append(acronym + "(" + str(len(entities_added)) + ")")
                removed_acronym_counts.     append(acronym + "(" + str(len(entities_removed)) + ")")
                changed_acronym_counts.     append(acronym + "(" + str(len(entities_changed)) + ")")
                unchanged_acronym_counts.   append(acronym + "(" + str(len(entities_unchanged)) + ")")


            # Now process the rest of the differences: arising from new intervals that were not there before
            for idx in range(len(prior_interval_list), len(interval_list)):
                interval                    = interval_list[idx]
                acronym                     = interval.entity_name 
                loop_trace                  = inner_trace.doing("Count acronyms for newly added interval",
                                                                data = {"new inteval": str(interval.columns)})
                uid_col                     = interval.columns[0]
                uid_vals                    = [u for u in DataFrameUtils().safe_unique(loop_trace, contents_df, uid_col) 
                                                        if not StringUtils().is_blank(u)]
                uid_nb                      = len(uid_vals)
                added_acronym_counts.       append(acronym + "(" + str(uid_nb) + ")")
                # Nothing to apped to the other lists for removed, changed, unchanged, since this interval didn't
                # exist in prior_contents_df

            entities_added_desc         = ", ".join(added_acronym_counts)
            entities_removed_desc       = ", ".join(removed_acronym_counts)
            entities_changed_desc       = ", ".join(changed_acronym_counts)
            entities_unchanged_desc     = ", ".join(unchanged_acronym_counts)

        else: # Easy case, all UIDs go to exactly one bucket, depending on the type of event
            acronym_counts              = self._acronym_counts(my_trace, contents_df)

            entities_added_desc         = ""
            entities_removed_desc       = ""
            entities_changed_desc       = ""
            entities_unchanged_desc     = ""

            if manifest_event == PostResponse.CREATED: 
                entities_added_desc         = ", ".join(acronym_counts)

            elif manifest_event == PostResponse.UNCHANGED: 
                entities_unchanged_desc     = ", ".join(acronym_counts)

            elif manifest_event == PostResponse.DELETED: 
                entities_removed_desc       = ", ".join(acronym_counts)


        description                     = ManifestEventDescription( manifest_filename           = manifest_file, 
                                                                    event                       = manifest_event, 
                                                                    entities_added_desc         = entities_added_desc, 
                                                                    entities_removed_desc       = entities_removed_desc, 
                                                                    entities_changed_desc       = entities_changed_desc, 
                                                                    entities_unchanged_desc     = entities_unchanged_desc, 
                                                                    namespace                   = manifest_handle.namespace, 
                                                                    name                        = manifest_handle.name)

        return description

    def _acronym_counts(self, parent_trace, contents_df):
        '''
        Helper method that returns a list consisting of acronym counts for all UIDs in a manifest.

        For example, it might return something like 
        
                    [BR(3), MR(2), SR(2)]

        @param contents_df A DataFrame, corresponding to the contents of a manifest. For example, if a manifest's
                            DataFrame representation is manifest_dict, content_df is a DataFrame representation
                            of manifest_dict["assertions"][<entity name>]
        '''
        interval_list               = self._infer_intervals(parent_trace, contents_df)
        acronym_counts              = []
        for interval in interval_list:
            acronym                 = interval.entity_name
            loop_trace              = parent_trace.doing("Processing acronym '" + str(acronym) + "'")
            uid_col                 = interval.columns[0]
            uid_vals                = [u for u in DataFrameUtils().safe_unique(loop_trace, contents_df, uid_col) 
                                                if not StringUtils().is_blank(u)]
            uid_nb                  = len(uid_vals)
            acronym_counts.append(acronym + "(" + str(uid_nb) + ")")

        return acronym_counts

    def extract_manifest_content_as_df(self, parent_trace, manifest_dict, manifest_nickname, abbreviate_uids):
        '''
        Returns two things:

        * A Pandas DataFrame
        * A string

        The string corresponds to the entity of `manifest_dict`, defined as the unique key <entity> in
        `manifest_dict` such that manifest_dict["assertion"][<entity>] is a dict
        
        The DataFrame corresponds to the content of the `manifest_dict`, i.e., a DataFrame representation
        of manifest_dict["assertion"][<entity>]

        @param abbreviate_uids A boolean. If True, UIDs will only keep the top acronym. For example, 
                    a UID like "BR2.MR2.SM4" in the manifest would be transformed to "BR2.2.4" in the
                    DataFrame returned by this method
        '''
        my_trace                        = parent_trace.doing("Identifying manifest's entity",
                                                    data = {"manifest": str(manifest_nickname)})
        entity                          = self.infer_entity(my_trace, manifest_dict, manifest_nickname=manifest_nickname)

        my_trace                        = parent_trace.doing("Extracting manifest's content as a DataFrame",
                                                    data = {"manifest": str(manifest_nickname)})
        path_list                       = ["assertion", entity]
        content_dict                    = DictionaryUtils().get_val(        parent_trace        = my_trace, 
                                                                            root_dict           = manifest_dict, 
                                                                            root_dict_name      = manifest_nickname, 
                                                                            path_list           = path_list, 
                                                                            valid_types         = [dict])

        contents_path                   = ".".join(path_list)
        rep                             = AsDataframe_Representer()
        contents_df                     = rep.dict_2_df(    parent_trace        = my_trace, 
                                                            content_dict        = content_dict, 
                                                            contents_path       = contents_path, 
                                                            sparse              = False,
                                                            abbreviate_uids     = abbreviate_uids)
        return contents_df, entity

    def interval_values_match(self, parent_trace, entity_uid, interval1, interval2, contents_df1, contents_df2):
        '''
        Returns a boolean. 
        
        If interval1 != interval2, then it returns False.

        Else, it gets the rows of `contents_df1`, `contents_df2` for which the "UID" column 
        is equal to `entity_uid`. Then it compares to see if those rows have the same value for the columns
        in interval1 (= interval2). Also checks that those rows are all "the same", since they have a common UID.

        Returns True if the values match.

        @param entity_uid A string representing a UID in a manifest. Example: "BR3.B2"
        @param interval1 An Interval object representing a subset of columns in contents_df1
        @param interval2 An Interval representing a subset of columns in contents_df2
        @param contents_df1: A DataFrame with the contents of a manifest. 
        @param contents_df2: A DataFrame with the contents of a manifest
        '''
        if type(interval1) != Interval or type(interval2) != Interval:
            raise ApodeixiError(parent_trace, "Can't see if intervals match because at least of of them is the right type",
                                            data = {"Expected type": Interval.__name__,
                                                    "type(interval1)":  str(type(interval1)),
                                                    "type(interval2)":  str(type(interval2))})
        if len(interval1.columns) == 0 or len(interval2.columns) == 0:
            raise ApodeixiError(parent_trace, "Can't see if intervals match because at least of of them is empty",
                                            data = {"interval1":    str(interval1.columns),
                                                    "interval2":    str(interval2.columns)})
        if not set(interval1.columns).issubset(set(contents_df1.columns)):
            raise ApodeixiError(parent_trace, "Interval provided is not a subset of DataFrame's columns",
                                                data = {"interval": str(interval1.columns),
                                                        "df columns": str(list(contents_df1.columns))})
        if not set(interval2.columns).issubset(set(contents_df2.columns)):
            raise ApodeixiError(parent_trace, "Interval provided is not a subset of DataFrame's columns",
                                                data = {"interval": str(interval2.columns),
                                                        "df columns": str(list(contents_df2.columns))})


        if interval1.columns != interval2.columns:
            return False

        UID_COL                         = interval1.columns[0]
        rows_df1                        = contents_df1[contents_df1[UID_COL] == entity_uid]
        rows_df2                        = contents_df2[contents_df2[UID_COL] == entity_uid]

        vals1                           = DataFrameUtils().safely_drop_duplicates(parent_trace, rows_df1[interval1.columns])
        vals2                           = DataFrameUtils().safely_drop_duplicates(parent_trace, rows_df2[interval2.columns])

        if len(vals1) != 1 or len(vals2) != 1:
            raise ApodeixiError(parent_trace, "Can't assess if two manifests' entity values match because "
                                                + " they don't have a unique row for the given entity_uid",
                                                data = {"entity_uid":       str(entity_uid),
                                                        "rows 1":           str(vals1),
                                                        "rows 2":           str(vals2)})
        val1                            = list(vals1.iloc[0])
        val2                            = list(vals2.iloc[0])
        return val1 == val2

    def _infer_intervals(self, parent_trace, contents_df):
        '''
        Helper method that partitions the columns of a manifest's contents_df DataFrame into a list of Intervals,
        which if concatenated would yield the columns in the right order.

        It creates an Interval for each UID it finds, and an interval is defined as the columns starting
        at a UID column and stretching to the right until the last column before another UID, or the end of 
        the DataFrame columns, whichever happens first.

        The "entity" for the Interval is set to be the acronym for the UID values. While not a "real" entity,
        it maps one-to-one to real entities and so the caller can use it for comparison of alignment between
        different manifest versions, which is what this helper method is for.

        Requires that the first column be an UID column.

        @param contents_df A DataFrame for the contents of a manifset. The first
                    column must be "UID"
        '''
        def _IS_UID(col):
            return IntervalUtils().is_a_UID_column(parent_trace, col)

        if type(contents_df) != _pd.DataFrame:
            raise ApodeixiError(parent_trace, "Invalid columns provided to infer intervals: expected a DataFrame, not a '"
                                                + type(contents_df).__name__ + "'")

        columns = list(contents_df.columns)
        if len(columns) == 0:
            raise ApodeixiError(parent_trace, "Invalid columns provided to infer intervals: the column list is empty")

        if not _IS_UID(columns[0]):
            raise ApodeixiError(parent_trace, "Invalid columns provided to infer intervals: first column is not a UID",
                                                data = {"columns": str(columns)})
        uid_idxs                    = [idx for idx in range(len(columns)) if _IS_UID(columns[idx])]
        start_idx                   = 0
        result                      = []
        #Add a "point at infinity" to make loop logic easier (spares us special logic on last loop)
        POINT_AT_INFINITY           = len(columns)
        uid_idxs.append(POINT_AT_INFINITY)
        my_trace                    = parent_trace.doing("Inferring entity intervals from a manifest's DataFrame")
        for next_start_idx in uid_idxs[1:]: # next_start_idx is not for the interval processed in the loop, but the one after
            loop_trace                    = my_trace.doing("Building interval starting at " + str(columns[start_idx]))
            # First, get the acronym for the entity whose UIDs are at column start_idx
            full_uid_list           = DataFrameUtils().safe_unique(loop_trace, contents_df, columns[start_idx])

            # If some rows had blanks for this column, we want to ignore then since they are not valid UIDs
            # and would cause the UID parser below to error out
            full_uid_list           = [u for u in full_uid_list if not StringUtils().is_blank(u)]
            leaf_uid_list           = [full_uid.split(".")[-1] for full_uid in full_uid_list]
            uid_parser              = UID_Store._TokenTree(parent_trace = loop_trace, level = 0)
            acronym_list            = [uid_parser.parseToken(loop_trace, leaf_uid)[0] for leaf_uid in leaf_uid_list]
            # The same acronym may apper multiple times, so remove duplicates by transforming to a set and back
            acronym_list            = list(set(acronym_list))
            if len(acronym_list) != 1:
                raise ApodeixiError(loop_trace, "Didn't find a unique leaf acronym in column",
                                                data = {"column": str(columns[start_idx]),
                                                         "UIDs in column": str(full_uid_list)})
            acronym                 = acronym_list[0]
            interval                = Interval(loop_trace, columns=columns[start_idx:next_start_idx], entity_name=acronym)

            result.append(interval)
            start_idx               = next_start_idx # Initializes next loop

        return result

class ManifestDiffResult():
    '''
    Class used as a data structure to hold the differences between two versions of the same manifest.

    Differences are expressed as lists of UIDs, such as:

        [BR8, BR8.MR1, BR8.MR2]

    Several such UID lists are kept, depending on whether the UID in questions are for entities added, removed,
    changed, or unchanged.

    An entity is considered "changed" by looking at its properties, and if any property either changed value, or
        if some properties were added or removed, then the entity is regarded as having changed.

    @param entities_added A list of the UIDs for entities that were added.
    @param entities_removed A list of the UIDs for entities that were removed.
    @param entities_changed A list of the UIDs for entities that were changed.
    @param entities_unchanged A list of the UIDs for entities that were unchanged

    '''
    def __init__(self, entities_added, entities_removed, entities_changed, entities_unchanged):
        self.entities_added        = entities_added
        self.entities_removed      = entities_removed
        self.entities_changed      = entities_changed
        self.entities_unchanged    = entities_unchanged


class ManifestEventDescription():
    '''
    Class used as a data structure for a few key properties around manifest lifecycle events, short enough
    to be presentable to the user in the CLI by way of response of a CLI post command from the user

    @param event A string. One of PostResponse.CREATED, PostResponse.UPDATED, PostResponse.DELETED, or
                        PostResponse.UNCHANGED
    @param entities_added_desc A comma-separated string that describes the acronyms of entities that were added, with a count
                        in parenthesis. Example: "BR(2), MR(2)"
    @param entities_removed_desc A comma-separated string that describes the acronyms of entities that were removed, with a count
                        in parenthesis. Example: "BR(2), MR(2)"
    @param entities_changed_desc A comma-separated string that describes the acronyms of entities that were changed, with a count
                        in parenthesis. Example: "BR(2), MR(2)"
    @param entities_unchanged_desc A comma-separated string that describes the acronyms of entities that were not changed, with a count
                        in parenthesis. Example: "BR(2), MR(2)"
    @namespace A string. The namespace containing the manifest whose lifecycle event is described by this object.
    @name A string. The name within the namespace under which is filed the manifest whose lifecycle event is described by 
                    this object.
    '''
    def __init__(self, manifest_filename, event, 
                                entities_added_desc, entities_removed_desc, entities_changed_desc, entities_unchanged_desc, 
                                namespace, name):
        self.manifest_filename          = manifest_filename
        self.event                      = event
        self.entities_added_desc        = entities_added_desc
        self.entities_removed_desc      = entities_removed_desc
        self.entities_changed_desc      = entities_changed_desc
        self.entities_unchanged_desc    = entities_unchanged_desc
        self.namespace                  = namespace
        self.name                       = name

class ManifestHandle():
    '''
    Object that uniquely identifies a manifest in an Apodeixi knowledge base

    @param manifest_api_name    A string. Example: "delivery-planning.journeys.a6i.io"
    @param namespace            A string. Example: "my-corp.production"
    @param name                 A string. Example: "modernization.default.dec-2020.opus"
    @param kind                 A string. Example: "big-rock"
    '''
    def __init__(self, manifest_api, kind, namespace, name, version):
        self.manifest_api     = manifest_api
        self.kind           = kind
        self.namespace      = namespace
        self.name           = name
        self.version        = version
        
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __copy__(self):
            return ManifestHandle(manifest_api = self.manifest_api, kind = self.kind, namespace = self.namespace, 
                                    name = self.name, version = self.version)

    def __ne__(self, other):
        return not self.__eq__(other)

    def display(self, parent_trace, indentation=""):
        msg = "" \
            + "\n\t\t" + indentation + " manifest_api   = '" + str(self.manifest_api) + "'" \
            + "\n\t\t" + indentation + " namespace      = '" + str(self.namespace) + "'" \
            + "\n\t\t" + indentation + " kind           = '" + str(self.kind) + "'" \
            + "\n\t\t" + indentation + " name           = '" + str(self.name) + "'" \
            + "\n\t\t" + indentation + " version        = '" + str(self.version) + "'" \

        return msg

class Response():
    '''
    Abstract class used to represent the schema response from the KnowledgeBase to a request.

    @internal manifest_handles_dict A dictionary explaining what changed as a consequence of processing this request
                                    in the manifests section of the store.
                                    Keys are Response.CREATED, Response.UPDATED, and Response.DELETED. 
                                    Also supports key Response.UNCHANGED, for manifests (such as reference manifests
                                    used in joins by other manifests being created or updated within a single posting)
                                    that were involved in the processing by the controller, but were not saved.
                                    Values are (possibly empty) dictionaries where keys are integers that uniquely
                                    identify a manifest for the controller that generated the response, and the values
                                    are ManifestHandle objects for such manifest.
                                    There is one such entry in for each manifest that was processed by the controller and
                                    either created, updated, deleted or unchanged by the request in quesion.
    @internal posting_handles_dict A dictionary explaining what changed as a consequence of processing this request
                                    in the postings section of the store. 
                                    Keys are: Response.ARCHIVED. 
                                    Values are lists (possibly empty) of a 2-sized list of
                                    PostingLabelHandle objects, such as [handle_1, handle_2] where handle_1 was the
                                    handle for the posting submitted and has now been removed, and handle_2 for the 
                                    archived copy of the posting that has been created. In cases where the posting
                                    was submitted from outside the store (e.g., as from some random location in
                                    the file system external to the store), then handle1 is set to None.
    @internal form_requests_dict A dictionary explaining the next steps that a user might need to take as a consequence
                                    of having just finished processing this request.
                                    Keys are: Response.OPTIONAL_FORMS, Response.MANDATORY_FORMS.
                                    Values are lists (possibly empty) with FormRequest objects, one for each
                                    (future) posting that the user may want to do as follow-up to this request. For example,
                                    typically the FormRequests under Response.OPTIONAL_FORMS are for making updates
                                    to the same posting just submitted in this request (i.e., same posting APIs). By contrast, the FormRequests
                                    under Response.MANDATORY_FORMS typically are for other posting APIs where the 
                                    KnowledgeBase has detected that previously provided information (if any) is now
                                    inconsistent or incomplete as a result of having processed this request. For example,
                                    if the user just updated a posting for a Big Rocks plan by adding another rock,
                                    it may be that the user is asked in Response.MANDATORY_FORMS to update the
                                    Milestones manifests to indicate the milestone containing that new rock.
    '''
    def __init__(self):
        self.manifest_handles_dict          = { Response.CREATED: {},   Response.UPDATED: {}, 
                                                Response.DELETED: {},   Response.UNCHANGED: {}}
        self.posting_handles_dict           = {Response.ARCHIVED: []}
        self.clientURL_handles_dict         = {Response.CREATED: []}
        self.form_requests_dict             = {Response.OPTIONAL_FORMS: [], Response.MANDATORY_FORMS: []}

    CREATED                                 = 'CREATED' 
    UPDATED                                 = 'UPDATED' 
    DELETED                                 = 'DELETED'  
    UNCHANGED                               = 'UNCHANGED'

    ARCHIVED                                = 'ARCHIVED'   

    OPTIONAL_FORMS                          = 'OPTIONAL_FORMS'  
    MANDATORY_FORMS                         = 'MANDATORY_FORMS'  

    def createdManifests(self):
        return list(self.manifest_handles_dict[Response.CREATED].values())

    def updatedManifests(self):
        return list(self.manifest_handles_dict[Response.UPDATED].values())

    def deletedManifests(self):
        return list(self.manifest_handles_dict[Response.DELETED].values())

    def unchangedManifests(self):
        return list(self.manifest_handles_dict[Response.UNCHANGED].values())

    def allActiveManifests(self, parent_trace):
        '''
        Returns a list of ManifestHandles in this response corresponding to create, update, or unchanged
        events (so it does not include deletes, since those are not "active").

        Typical use case is for the caller to want such list in order to assemble a list of forms that
        are needed if in the future the user wants to update the manifests manipulated by the controller
        that produced this response.

        For deterministic reasons (so that caller can process them in the right sequence of dependencies),
        the list of ManifestHandles is *sorted* based on the manifest_nb that was passed to this Response
        object when the manifest was recorded into the response.
        '''
        all_handles_dict    = self.manifest_handles_dict[Response.CREATED] | self.manifest_handles_dict[Response.UPDATED] \
                                | self.manifest_handles_dict[Response.UNCHANGED]
        all_manifest_nbs    = list(all_handles_dict.keys())
        all_manifest_nbs.sort()
        result              = []
        for nb in all_manifest_nbs:
            result.append(all_handles_dict[nb])
        return result

    def allManifests(self, parent_trace):
        '''
        Returns a list of ManifestHandles in this response corresponding to create, delete, update, or unchanged
        events (so unlike the allActiveManifests method, this method includes deletes).
        
        One use case where this is used is in the Apodeixi CLI, to provide input to user's on the outcome of
        a user-initiated posting.
        '''
        all_handles_dict    = self.manifest_handles_dict[Response.CREATED] \
                                | self.manifest_handles_dict[Response.UPDATED] \
                                | self.manifest_handles_dict[Response.DELETED] \
                                | self.manifest_handles_dict[Response.UNCHANGED]
        all_manifest_nbs    = list(all_handles_dict.keys())
        all_manifest_nbs.sort()
        result              = []
        for nb in all_manifest_nbs:
            result.append(all_handles_dict[nb])
        return result

    def archivedPostings(self):
        return self.posting_handles_dict[Response.ARCHIVED]   
        
    def createdForms(self):
        return self.clientURL_handles_dict[Response.CREATED]

    def optionalForms(self):
        return self.form_requests_dict[Response.OPTIONAL_FORMS]

    def mandatoryForms(self):
        return self.form_requests_dict[Response.MANDATORY_FORMS]

class PostResponse(Response):
    '''
    Data structure used as a response to a post request on the knowledge base
    '''
    def __init__(self):
        super().__init__()

    def recordCreation(self, parent_trace, manifest_dict, manifest_nb):
        '''
        Used to enrich the content of this PostResponse by recording that a manifest was created

        @param manifest_dict A dictionary representation of a manifest. It must have 'metadata.name', 'metadata.namespace' and 'kind'
                                since those are mandatory fields for all manifests.
        '''
        handle                  = ManifestUtils().inferHandle(parent_trace, manifest_dict)
        self.manifest_handles_dict[Response.CREATED][manifest_nb] = handle

    def recordUpdate(self, parent_trace, manifest_dict, manifest_nb):
        '''
        Used to enrich the content of this PostResponse by recording that a manifest was updated

        @param manifest_dict A dictionary representation of a manifest. It must have 'metadata.name', 
                                'metadata.namespace' and 'kind'
                                since those are mandatory fields for all manifests.
        '''
        handle                  = ManifestUtils().inferHandle(parent_trace, manifest_dict)
        self.manifest_handles_dict[Response.UPDATED][manifest_nb] = handle

    def recordUnchanged(self, parent_trace, manifest_dict, manifest_nb):
        '''
        Used to enrich the content of this PostResponse by recording that a manifest was not changed

        @param manifest_dict A dictionary representation of a manifest. It must have 'metadata.name', 
                                'metadata.namespace' and 'kind'
                                since those are mandatory fields for all manifests.
        '''
        handle                  = ManifestUtils().inferHandle(parent_trace, manifest_dict)
        self.manifest_handles_dict[Response.UNCHANGED][manifest_nb] = handle

    def recordArchival(self, parent_trace, original_handle, archival_handle):
        self.posting_handles_dict[Response.ARCHIVED].append([original_handle, archival_handle])

    def recordOptionalForm(self, parent_trace, form_request):
        self.form_requests_dict[Response.OPTIONAL_FORMS].append(form_request)

class FormRequestResponse(Response):
    '''
    Data structure used as a response to a FormRequest request on the knowledge base

    @param clientURL A string corresponding to the root path of the client area (such as a SharePoint folder)
                        under which the form was saved in response to the FormRequest.
    @param posting_api A string, corresponding to the posting API for which this form was requested.
    @param filing_coords A FilingCoords object indicating where the form was persisted below the client URL directory.
    @param filename A string corresponding to the name of the file used to save the Excel form.
    @param path_mask A function that takes as tring argument and returns a string. Normally it is None, but
                it is used in situations (such as in regression testing) when observability should not
                report the paths "as is", but with a mask. For example, this can be used in regression
                tests to hide the user-dependent portion of paths, so that logs would otherwise display a path
                like:

                'C:/Users/aleja/Documents/Code/chateauclaudia-labs/apodeixi/test-knowledge-base/envs/big_rocks_posting_ENV/excel-postings'

                instead display a "masked" path where the user-specific prefix is masked, so that only the
                logical portion of the path (logical as in: it is the structure mandated by the KnowledgeStore)
                is displayed. In the above example, that might become:

                '<KNOWLEDGE_BASE>/envs/big_rocks_posting_ENV/excel-postings    
    @param manifest_identifiers A list of strings, corresponding to the identifiers or all manifest data sets
                in the form. 
                Example: 
                            ['big-rock.0', 'big-rock-estimates.1', 'investment.2']
    '''
    def __init__(self, clientURL, posting_api, filing_coords, filename, path_mask, manifest_identifiers):
        super().__init__()
        self._clientURL             = clientURL
        self._posting_api           = posting_api 
        self._filing_coords         = filing_coords 
        self._filename              = filename
        self._path_mask             = path_mask
        self._manifest_identifiers  = manifest_identifiers

    def clientURL(self, parent_trace):
        return self._clientURL

    def posting_api(self, parent_trace):
        return self._posting_api

    def filing_coords(self, parent_trace):
        return self._filing_coords

    def filename(self, parent_trace):
        return self._filename

    def manifest_identifiers(self, parent_trace):
        return self._manifest_identifiers

    def applyMask(self, parent_trace, original_txt):
        if self._path_mask != None:
            return self._path_mask(original_txt)
        else:
            return original_txt


    def recordClientURLCreation(self, parent_trace, response_handle):
        '''
        Used to enrich the content of this FormRequestResponse by recording that a form was created

        @param response_handle A PostingLabelHandle for the form that was created'
        '''
        self.clientURL_handles_dict[Response.CREATED].append(response_handle)

    def getRelativePath(self, parent_trace):
        '''
        Returns the relative path within the Knowledge Store's external collaboration area where the 
        form (an Excel spreadsheet) can be found. This is the form generated in the processing for
        which this class is the response.
        '''
        parsed_tokens               = self._filing_coords.path_tokens(parent_trace)
        tag                         = self._filing_coords.getTag(parent_trace)
        if type(tag) == str and len(tag) > 0:
            filename                = tag + "." + self._posting_api + ".xlsx"
        else:
            filename                = self._posting_api + ".xlsx"
        excel_path                  = '/'.join(parsed_tokens)
        return excel_path + "/" + filename

    def getManifestIdentifiers(self, parent_trace):
        return self._manifest_identifiers

class FormRequest():
    '''
    Object that allows the user to request a form (i.e., an Excel spreadsheet template) to the Knowledge Base.
    This form is intended to allow the user to make a posting.

    Upon receiving such a request, the Knowledge Base would:

    * Create an Excel spreadsheet in an area of the Knowledge Base's store determined by this FormRequest
    * The spreadsheet would have a pre-populated Posting Label area as determined by this FormRequest
    * The spreadsheet would be for a posting API determined by this FormRequest
    * The form would be pre-populated with content from "manifests in scope", i.e., the manifest instances
      whose updates are supposed to included in the posting.

    The user can subsequently make use of the generated form to enter any missing data (or update existing data)
    in the spreadsheet and submit it to the Knowledge Base as a posting. 
    
    Such submission would entail the creation of a PostingLabelHandle for the posting, resulting in the creation 
    or update of the manifests in scope for the form.
    
    A FormRequest may be "blind". This refers to the situation where the FormRequest does not explicity
    state which manifests are in scope. This can happen in two situations:

    * The user is requesting a form for creating manifests for the first time. So there are no "manifests
      in scope"
    * The user is requesting a form to update "whatever manifests are associated to a posting" without having
      or knowing ManifestHandles for them. In that case the processing controller will have to search
      in the KnowledgeBase store for the manifests that are in scope given the other parameters of the form
      request and what the concrete controller knows about the kind of manifests it deals with. 

    @param scope Object that specifies how to determine the manifests in scope. It must be of one of two types:
            1) An instance of FormRequest.ExplicitScope, for the case where the request is not blind.
                In this case, the scope contains a list of manifest handles.
            2) An instance of FormRequest.SearchScope, for the case where the request is blind.
                In this case, the scope contains a namespace to which to delimit the search

    '''
    def __init__(self, parent_trace, posting_api, filing_coords, scope):

        self._posting_api           = posting_api 
        self._filing_coords         = filing_coords 

        if type(scope) == FormRequest.ExplicitScope or type(scope) == FormRequest.SearchScope:
            self._scope                 = scope
        else:
            raise ApodeixiError("Invalid type of scope in FormRequest",
                                data = {"type(scope)": str(type(scope)),
                                        "valid types": str["FormRequest.ExplicitScope", "FormRequest.SearchScope"]})
       
    def display(self, parent_trace):
        '''
        Returns a string friendly representation of this FormRequest
        '''
        msg = "" \
            + "\n\t\t posting_api     = '" + self._posting_api + "'" \
            + "\n\t\t filing_coords   = '" + str(self._filing_coords) + "'" 

        msg += self._scope.display(parent_trace)

        return msg

    def getPostingAPI(self, parent_trace):
        return self._posting_api

    def getFilingCoords(self, parent_trace):
        return self._filing_coords

    def getScope(self, parent_trace):
        return self._scope


    def getRelativePath(self, parent_trace):
        '''
        Returns the relative path within the Knowledge Store's postings area where the form (an Excel spreadsheet)
        should reside
        '''
        parsed_tokens               = self._filing_coords.path_tokens(parent_trace)
        tag                         = self._filing_coords.getTag(parent_trace)
        if type(tag) == str and len(tag) > 0:
            filename                = tag + "." + self._posting_api + ".xlsx"
        else:
            filename                = self._posting_api + ".xlsx"

        excel_path                  = '/'.join(parsed_tokens)
        return excel_path + "/" + filename

    class ExplicitScope():
        '''
        Helper class for a FormRequest. It codifies the fact that the manifest scope is explicitly known 
        as a list of manifest handles

        @param manifest_handle_list: a list of ManifestHandle objects, for the manifests in scope for the request. If it 
                        is an empty list or None then this is interpreted a blind request. 
        '''
        def __init__(self, manifest_handle_list):
            self._manifest_handle_list  = manifest_handle_list

        def manifestHandles(self, parent_trace):
            '''
            Used to obtain the ManifestHandles for the manifests in the scope of this FormRequest, assuming it is not
            a blind request.

            Specifically, it returns a dictionary whose keys are strings that uniquely identify each ManifestHandle in 
            this FormRequest, and the values are the corresponding ManifestHandle

            If ManifestHandles have not been configured in this FormRequest, returns None as this FormRequest is
            then interpreted to be a blind request.
            '''
            if self._manifest_handle_list != None and len(self._manifest_handle_list) > 0:
                result_dict                         = {}
                for idx in range(len(self._manifest_handle_list)):
                    manifest_handle                 = self._manifest_handle_list[idx]
                    kind                            = manifest_handle.kind
                    manifest_key                    = str(kind) + "." + str(idx)
                    result_dict[manifest_key]       = manifest_handle

                return result_dict
            else:
                return None

        def display(self, parent_trace):
            '''
            Returns a string friendly representation of this FormRequest scope
            '''
            msg = ""
            
            for handle in self._manifest_handle_list:
                msg += "\n\t\t *** A ManifestHandle ***"
                msg += handle.display(parent_trace, indentation="\t")

            return msg

    class SearchScope():
        '''
        Helper class to a FormRequest. It codifies the fact that the manifest scope is not explicity known
        so the controller will have to determine it by searching the store.
        To assist in that search, this class delimits the search to a particular namespace. That gives the
        controller the "missing hint" for the search, as the controller can determine other search parameters
        from other information in the FormRequest (such as the filing coordinates) or information known
        to the controller (such as what kinds it supports).

        @param namespace A string, representing a namespace in the KnowledgeBase store's manifests are that
                        delimits the scope for searching for manfiests in scope of this FormRequest.
                        Example: "my-corp.production"

        @param subnamespace An optional string representing a slice of the namespace that further restricts
                        the manifest names to search. If set to None, not subspace is assumed.
                        Example: in the manifest name "modernization.default.dec-2020.fusionopus", the
                                token "modernization" is the subnamespace. The other tokens come from filing coordinates
                                for the posting from whence the manifest arose.
        '''
        def __init__(self, namespace, subnamespace):
            self.namespace      = namespace
            self.subnamespace   = subnamespace
        
        def display(self, parent_trace):
            '''
            Returns a string friendly representation of this FormRequest scope
            '''
            msg = "\n\t\t scope namespace = '" + str(self.namespace) + "'" \
                   + "\n\t\t scope subnamespace = '" + str(self.subnamespace) + "'"

            return msg
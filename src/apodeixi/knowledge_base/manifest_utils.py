import os                                                       as _os
import pandas                                                   as _pd

from apodeixi.controllers.util.manifest_api                     import ManifestAPIVersion

# To avoid circular import dependencies, we don't import ManifetHandle or PostResponse directly.
# So in this module we refer to them as kb_utils.Manifest_Handle and kb_utils.PostResponse
import apodeixi.knowledge_base.knowledge_base_util              as kb_utils 

from apodeixi.representers.as_dataframe                         import AsDataframe_Representer, UID_Info

from apodeixi.xli.interval                                      import Interval, IntervalUtils
from apodeixi.xli.uid_store                                     import UID_Utils

from apodeixi.util.dictionary_utils                             import DictionaryUtils
from apodeixi.util.formatting_utils                             import StringUtils
from apodeixi.util.a6i_error                                    import ApodeixiError
from apodeixi.util.dataframe_utils                              import DataFrameUtils, TupleColumnUtils
from apodeixi.util.rollover_utils                               import RolloverUtils

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
            raise ApodeixiError(parent_trace, "Can't infer ManifestHandle because manifest was not passed as a dictionary. "
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
        handle                      = kb_utils.ManifestHandle(  manifest_api    = manifest_api,
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

    def diff_manifest(self, parent_trace, store, manifest_api_name, namespace, name, kind, version1=None, version2=None):
        '''
        Creates and returns a ManifestDiffResult object that explains what changed with a manifest
        between `version1` and `version2`.

        If `version2` is null then it is assumed to be the latest version of the manifest.

        If `version1` is null then it is assumed to be "the prior version", i.e., version1 = version2 -1

        The diff is expressed using `version1` as the baseline. For example, the entities listed in the
        result as "added" are entities that are in `version2` but not `version1`.

        The parameters `manifest_api`, `namespace`, `name`, and `kind` uniquely identify (up to version) a specific
        manifest object in the KnowledgeBase.

        @param manifest_api_name    A string. Example: "delivery-planning.journeys.a6i.io"
        @param namespace            A string. Example: "my-corp.production"
        @param name                 A string. Example: "modernization.default.dec-2020.opus"
        @param kind                 A string. Example: "big-rock"
        @param version1             An int, representing the version of the manifest used as a baseline for the comparison
        @param version2             An int, representing the version of the manifest whose differences to the baseline are returned
        @param store                The KnowledgeBaseStore instance where the manifest in question is persisted

        '''
        if (version1 != None and type(version1) != int) or (version2 != None and type(version2) != int):
            raise ApodeixiError(parent_trace, "Can't compute manifest diff because was provided a non-integer version",
                                                data = {"type(version1)":   str(type(version1)),
                                                        "type(version2)":   str(type(version2))})

        my_trace                        = parent_trace.doing("Ensuring version1 is before version2")
        # We re-sort the versions in case they are out of order. That is not considered user error, but the
        # algorithm below requires that version2 >= version1, and all variables with suffixes 1,2 will assume so
        if version1 != None and version2 != None and version1 > version2:
            smaller_version             = version2
            version2                    = version1
            version1                    = smaller_version

        my_trace                        = parent_trace.doing("Retrieving manifests to diff")
        if True:
            if version2 == None:
                manifest_dict2, manifest_path2 \
                                        = store.findLatestVersionManifest(  parent_trace        = my_trace, 
                                                                            manifest_api_name   = manifest_api_name, 
                                                                            namespace           = namespace, 
                                                                            name                = name, 
                                                                            kind                = kind)
                if manifest_dict2 == None:
                    raise ApodeixiError(my_trace, "Unable to do diff because there is no manifest was found in the KnowledgeBase with these characteristics",
                                            data = {"Manifest API":         str(manifest_api_name),
                                                    "namespace":            str(namespace),
                                                    "name":                 str(name),
                                                    "kind":                 str(kind)})
                version2                = self.get_manifest_version(my_trace, manifest_dict2)
            else:
                manifest_handle2        = kb_utils.ManifestHandle(          manifest_api        = manifest_api_name, 
                                                                            kind                = kind, 
                                                                            namespace           = namespace,
                                                                            name                = name, 
                                                                            version             = version2)
                manifest_dict2, manifest_path2 \
                                        = store.retrieveManifest(           parent_trace        = my_trace, 
                                                                            manifest_handle     = manifest_handle2)
                if manifest_dict2 == None:
                    raise ApodeixiError(my_trace, "Unable to do diff because there is no manifest was found in the KnowledgeBase with these characteristics",
                                            data = {"Manifest API":         str(manifest_api_name),
                                                    "namespace":            str(namespace),
                                                    "name":                 str(name),
                                                    "kind":                 str(kind)})

            manifest_file2              = _os.path.split(manifest_path2)[1]
            if version1 == None:
                version1                        = version2 - 1

            if version1 < 1:
                raise ApodeixiError(my_trace, "Can't diff manifest across versions because version1 is below 1",
                                            data = {"version1": str(version1), "version2": str(version2),
                                                    "manifest2": str(manifest_file2)})

            # Check if we are in a rollover situation, because in that case we must modify the name with which
            # we attempt to retrive the previous manifest
            #
            # For example, when rolling from "FY 22" to "FY 23", we want to find the manifest's prior version by looking 
            #   in name 
            #                               "modernization.fy-22.astrea.official",  (which is given by label.rollFromName(-))
            #  instead of looking in name 
            #                               "modernization.fy-23.astrea.official",  (which is given by manifestNameFromLabel(-))
            # which would error out   
            #            
            roll_from_name              = RolloverUtils().get_rollFromName(parent_trace, manifest_dict2)
            if roll_from_name != None:
                name1                   = roll_from_name
            else:
                name1                   = name


            manifest_handle1            = kb_utils.ManifestHandle(          manifest_api        = manifest_api_name, 
                                                                            kind                = kind, 
                                                                            namespace           = namespace,
                                                                            name                = name1, 
                                                                            version             = version1)
            manifest_dict1, manifest_path1 \
                                        = store.retrieveManifest(           parent_trace        = my_trace, 
                                                                            manifest_handle     = manifest_handle1)
            manifest_file1              = _os.path.split(manifest_path1)[1]

        my_trace                        = parent_trace.doing("Extracting manifests' content as a DataFrame",
                                                    data = {"manifest1": str(manifest_file1),
                                                            "manifest2": str(manifest_file2)})
        if True:
            contents_df1, entity_name1, uid_info_list1 = self.extract_manifest_content_as_df(my_trace, 
                                                                                        manifest_dict1, manifest_file1,
                                                                                        abbreviate_uids = False)
            contents_df2, entity_name2, uid_info_list2 = self.extract_manifest_content_as_df(my_trace, 
                                                                                        manifest_dict2, manifest_file2,
                                                                                        abbreviate_uids = False)

        my_trace                        = parent_trace.doing("Validating manifest is consistent across boths version",
                                                        data = {"version1": str(version1), "version2": str(version2),
                                                                "manifest1": str(manifest_file1),
                                                                "manifest2": str(manifest_file2)})
        if True:                                                    
            if entity_name1 != entity_name2:
                raise ApodeixiError(my_trace, "Manifest's entity name changed between versions. That is not allowed",
                                            data = {"entity2":      str(entity_name2),
                                                    "version2":     str(version2),
                                                    "entity1":      str(entity_name1),
                                                    "version1":     str(version1)})

            interval_list1              = self._infer_intervals(my_trace, contents_df1)
            interval_list2              = self._infer_intervals(my_trace, contents_df2)
            
            # Verify that the new version is an extension of the prior one, since Apodeixi only allows adding
            # new entites *after* previously created entities.
            if len(interval_list1) > len(interval_list2):
                raise ApodeixiError(my_trace, "Invalid manifest update: can't delete UID columns present in prior manifest")
            for idx in range(len(interval_list1)):
                interval1                = interval_list1[idx]
                interval2                = interval_list2[idx]
                #Ensure intervals align by comparing the acronyms, which our helper method put into the entity_name field
                if interval1.entity_name != interval2.entity_name:
                    raise ApodeixiError(my_trace, "Invalid manifest dff: the leaf acronyms don't match in UID columns "
                                                        + "across versions, and a match is expected",
                                                        data = {"UID column (v1)":      str(interval1.columns[0]),
                                                                "acronym (v1)":         str(interval1.entity_name),
                                                                "UID column (v2)":      str(interval2.columns[0]),
                                                                "acronym (v2)":         str(interval2.entity_name)})

        my_trace                        = parent_trace.doing("Computing diff across versions",
                                                        data = {"version1": str(version1), "version2": str(version2),
                                                                "manifest1": str(manifest_file1),
                                                                "manifest2": str(manifest_file2)})
        if True:

            short_desc, long_desc       = self._tell_what_is_being_diffed(manifest_api_name, namespace, name, kind, version1, version2)
            result                      = ManifestDiffResult(short_desc, long_desc, 
                                                            contents_df1, uid_info_list1, 
                                                            contents_df2, uid_info_list2)

            # First section: process the intervals that were there before
            for idx in range(len(interval_list1)):
                interval1               = interval_list1[idx]
                interval2               = interval_list2[idx]
                acronym                 = interval1.entity_name # We already check it matches interval2's
                loop_trace              = my_trace.doing("Counting differences for interval",
                                                                data = {"interval1":    str(interval1.columns),
                                                                        "inteval2":     str(interval2.columns)})
                UID_COLUMN              = interval1.columns[0]

                entities1               = [uid for uid in DataFrameUtils().safe_unique(loop_trace, contents_df1,    UID_COLUMN)
                                            if not StringUtils().is_blank(uid)]
                entities2               = [uid for uid in DataFrameUtils().safe_unique(loop_trace, contents_df2,    UID_COLUMN) 
                                            if not StringUtils().is_blank(uid)]         
        
                entities_added          = [e for e in entities2 if not e in entities1]
                entities_removed        = [e for e in entities1 if not e in entities2]
                common_entities         = [e for e in entities2 if e in entities1]
                entities_changed        = [e for e in common_entities if not self.interval_values_match(
                                                                                        parent_trace  = loop_trace, 
                                                                                        entity_uid      = e, 
                                                                                        interval1       = interval1, 
                                                                                        interval2       = interval2,
                                                                                        contents_df1    = contents_df1, 
                                                                                        contents_df2    = contents_df2)]
                entities_unchanged      = [e for e in common_entities if self.interval_values_match(
                                                                                        parent_trace  = loop_trace, 
                                                                                        entity_uid      = e, 
                                                                                        interval1       = interval1, 
                                                                                        interval2       = interval2,
                                                                                        contents_df1    = contents_df1, 
                                                                                        contents_df2    = contents_df2)]
                result.record_entities_added    (loop_trace, acronym, entities_added)
                result.record_entities_removed  (loop_trace, acronym, entities_removed)

                # Build a list of _ChangedEntityDiff objects, one for each entity that changed. Unlike other
                # events, for CHANGEs we need to know more than a boolean status of whether a change occured or not:
                # need to know what fields changed, and how. Hence a list of _ChangedEntityDiff objects instead
                # of a list of UIDs.
                entities_changed_diffs  = []
                for uid in entities_changed:
                    entity_diff         = self.compute_entity_diff( parent_trace  = loop_trace, 
                                                                    entity_uid      = uid, 
                                                                    interval1       = interval1, 
                                                                    interval2       = interval2,
                                                                    contents_df1    = contents_df1, 
                                                                    contents_df2    = contents_df2)
                    entities_changed_diffs.append(entity_diff)

                result.record_entities_changed  (loop_trace, acronym, entities_changed_diffs)

                result.record_entities_unchanged(loop_trace, acronym, entities_unchanged)
            # Now process the rest of the differences: arising from new intervals that were not there before
            for idx in range(len(interval_list1), len(interval_list2)):
                interval2               = interval_list2[idx]
                acronym2                = interval2.entity_name
                loop_trace              = my_trace.doing("Collate UIDs for newly added interval",
                                                                data = {"new interval": str(interval2.columns)})
                UID_COLUMN              = interval2.columns[0]
                entities_added          = [uid for uid in DataFrameUtils().safe_unique(loop_trace, contents_df2,    UID_COLUMN)
                                            if not StringUtils().is_blank(uid)]
                result.record_entities_added    (loop_trace, acronym2, entities_added)
   
        
        return result

    def _tell_what_is_being_diffed(self, manifest_api_name, namespace, name, kind, version1, version2):
        '''
        Returns two friendly strings (a short description and a long description) that identifies what is being diff-ed
        '''
        short_description               = kind + " v" + str(version1) + "-v" + str(version2)
        long_description                = "Differences between v" + str(version1) + " and v" + str(version2) \
                                            + " for " + namespace + "/" + name + "/" + manifest_api_name + "::" + kind 
        return short_description, long_description

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
        contents_df, entity_name, uid_info_list     = self.extract_manifest_content_as_df(my_trace, 
                                                                                        manifest_dict, manifest_file,
                                                                                        abbreviate_uids=False)
        
        my_trace                        = parent_trace.doing("Determining the manifest lifecycle event",
                                                    data = {"manifest": str(manifest_file)})
        if manifest_handle in post_response.createdManifests():
            manifest_event              = kb_utils.PostResponse.CREATED
        elif manifest_handle in post_response.updatedManifests():
            manifest_event              = kb_utils.PostResponse.UPDATED
        elif manifest_handle in post_response.deletedManifests():
            manifest_event              = kb_utils.PostResponse.DELETED
        elif manifest_handle in post_response.unchangedManifests():
            manifest_event              = kb_utils.PostResponse.UNCHANGED
        else:
            raise ApodeixiError(my_trace, "Manifest '" + str(manifest_file) + "' was not a part of the post being described")

        entities_added_desc             = ""
        entities_removed_desc           = ""
        entities_changed_desc           = ""
        entities_unchanged_desc         = ""

        my_trace                        = parent_trace.doing("Determining what was changed during post event",
                                                    data = {"manifest": str(manifest_file),
                                                            "event":    str(manifest_event)})
        if manifest_event == kb_utils.PostResponse.UPDATED:
            diff                            = self.diff_manifest(   parent_trace        = my_trace, 
                                                                    store               = store, 
                                                                    manifest_api_name   = manifest_handle.manifest_api, 
                                                                    namespace           = manifest_handle.namespace, 
                                                                    name                = manifest_handle.name, 
                                                                    kind                = manifest_handle.kind, 
                                                                    version1=None, 
                                                                    version2            = manifest_handle.version)   

            entities_added_desc             = diff.added_entities_acronym_count(my_trace)
            entities_removed_desc           = diff.removed_entities_acronym_count(my_trace)
            entities_changed_desc           = diff.changed_entities_acronym_count(my_trace)
            entities_unchanged_desc         = diff.unchanged_entities_acronym_count(my_trace)

        else: # Easy case, all UIDs go to exactly one bucket, depending on the type of event
            acronym_counts              = self._acronym_counts(my_trace, contents_df)

            if manifest_event == kb_utils.PostResponse.CREATED: 
                entities_added_desc         = ", ".join(acronym_counts)

            elif manifest_event == kb_utils.PostResponse.UNCHANGED: 
                entities_unchanged_desc     = ", ".join(acronym_counts)

            elif manifest_event == kb_utils.PostResponse.DELETED: 
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
        Returns three things:

        * A Pandas DataFrame
        * A string
        * A list of UID_Info objects

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
        contents_df, uid_info_list      = rep.dict_2_df(    parent_trace        = my_trace, 
                                                            content_dict        = content_dict, 
                                                            contents_path       = contents_path, 
                                                            sparse              = False,
                                                            abbreviate_uids     = abbreviate_uids)
        return contents_df, entity, uid_info_list

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
        entity_diff                 = self.compute_entity_diff( parent_trace, 
                                                                entity_uid, 
                                                                interval1, 
                                                                interval2, 
                                                                contents_df1, 
                                                                contents_df2)
        return not entity_diff.has_differences()

    def compute_entity_diff(self, parent_trace, entity_uid, interval1, interval2, contents_df1, contents_df2):
        '''
        Returns a ManifestDiffResult._ChangedEntityDiff object, expressing how the entity defined by 
        `entity_uid` has changed.

        @param entity_uid A string representing a UID in a manifest. Example: "BR3.B2"
        @param interval1 An Interval object representing a subset of columns in contents_df1
        @param interval2 An Interval representing a subset of columns in contents_df2
        @param contents_df1: A DataFrame with the contents of a manifest. 
        @param contents_df2: A DataFrame with the contents of a manifest
        '''
        
        if type(interval1) != Interval or type(interval2) != Interval:
            raise ApodeixiError(parent_trace, "Can't diff intervals match because at least of of them is the right type",
                                            data = {"Expected type": Interval.__name__,
                                                    "type(interval1)":  str(type(interval1)),
                                                    "type(interval2)":  str(type(interval2))})
        
        if len(interval1.columns) == 0 or len(interval2.columns) == 0:
            raise ApodeixiError(parent_trace, "Can't diff intervals match because at least of of them is empty",
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
        

        entity_diff                     = ManifestDiffResult._ChangedEntityDiff(entity_uid)
        
        entity_diff.added_fields        = [field for field in interval2.columns if not field in interval1.columns]
        entity_diff.removed_fields      = [field for field in interval1.columns if not field in interval2.columns]

        common_fields                   = [field for field in interval1.columns if field in interval2.columns]

        UID_COL                         = interval1.columns[0]
        if not UID_COL in interval2.columns:
            raise ApodeixiError("Corrupted manifest: lacks UID '" + str(UID_COL) + "' in the new version",
                                    data = {"Interval in new version:" + str(interval2.columns)})

        rows_df1                        = contents_df1[contents_df1[UID_COL] == entity_uid]
        rows_df2                        = contents_df2[contents_df2[UID_COL] == entity_uid]

        # GOTCHA: when there are subproducts, some columns may be tuples, but the UID and
        #           entity columns are strings. This will cause Pandas to complain with hard-to-understand
        #           warnings, so to prevent that convert all columns to tuples
        rows_df1.columns                = TupleColumnUtils().homogenize_columns(parent_trace, 
                                                                                heterogeneous_columns   = rows_df1.columns)
        rows_df2.columns                = TupleColumnUtils().homogenize_columns(parent_trace, 
                                                                                heterogeneous_columns   = rows_df2.columns)
        common_fields                   = TupleColumnUtils().homogenize_columns(parent_trace, 
                                                                                heterogeneous_columns   = common_fields)

        vals1                           = DataFrameUtils().safely_drop_duplicates(parent_trace, rows_df1[common_fields])
        vals2                           = DataFrameUtils().safely_drop_duplicates(parent_trace, rows_df2[common_fields])
        
        if len(vals1) != 1 or len(vals2) != 1:
            raise ApodeixiError(parent_trace, "Can't assess if two manifests' entity values match because "
                                                + " they don't have a unique row for the given entity_uid",
                                                data = {"entity_uid":       str(entity_uid),
                                                        "rows 1":           str(vals1),
                                                        "rows 2":           str(vals2)})
        val1_row                        = vals1.iloc[0]
        val2_row                        = vals2.iloc[0]
        for col in common_fields:
            if val1_row[col] != val2_row[col]:
                entity_diff.changed_fields.append(ManifestDiffResult._ChangedValue( uid         = entity_uid,
                                                                                    field       = col,
                                                                                    old_value   = val1_row[col],
                                                                                    new_value   = val2_row[col]))

        return entity_diff

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
            
            acronym_list            = [UID_Utils().parseToken(loop_trace, leaf_uid)[0] for leaf_uid in leaf_uid_list]
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

    def sort_manifest_df_by_foreign_uid(self, parent_trace, manifest_df, foreign_uid_column):
        '''
        This method is used to help group a manifest's sparse DataFrame by a foreign entity, preserving the
        entity-subentity relationships that sparse DataFrames represent by empty strings.

        Such grouping is useful when rendering a form that must align the manifest rows to the foreign entity's rows.

        Example: consider the Product object, that references the Line-of-Business object. 

                UID   | product     | lineOfBusiness  | UID-1   |   Sub Product 
            ================================================================================         
            0   P1      MYPROD_A        LOB1                                                          
            1                                           P1.1        Prod A Enterprise  
            2                                           P1.2        Prod A Express        
            3   P2      MYPROD_B        LOB2                                                          
            4   P3      MYPROD_C        LOB1                                                          
            5                                           P3.1        Prod C Premium                                 
            6                                           P3.2        Prod C Basic   

        Intuitively, we want to "sort by line of business", so that the manifest is re-sorted into segments
        per LOB. Thus, P1 and P3 would appear in the first segment (for LOB1), followed by P2 (for LOB2).

        What is tricky is to maintain the relationship to children entities: moving the row where P3 appears, for example,
        should also move the rows where P3.1, P3.2 appears, so all of {P3, P3.1, P3.2} should appear before P2 after sorting.

        Additionally, parents should appear immediately before children (so the order should be <P3, P3.1, P3.2>, not
        <P3.1, P3, P3.2>, say)                     

        The correct output of this method would return a DataFrame that looks like this:

                UID   | product     | lineOfBusiness  | UID-1   |   Sub Product 
            ================================================================================         
            0   P1      MYPROD_A        LOB1                                                          
            1                                           P1.1        Prod A Enterprise  
            2                                           P1.2        Prod A Express        
            3   P3      MYPROD_C        LOB1                                                          
            4                                           P3.1        Prod C Premium                                 
            5                                           P3.2        Prod C Basic   
            6   P2      MYPROD_B        LOB2                                                                

        To accomplish this, the algorithm creates a "padded DataFrame" from the input, adding two columns in order
        to preserve orders, and then orders by those two columns. The 2nd one is the original order, to contiguous segments
        of parent-children relationships:

                UID   | product     | lineOfBusiness  | UID-1   |   Sub Product         | SortBy-1  | SortBy-2  
            ==============================================================================================================         
            0   P1      MYPROD_A        LOB1                                            |  LOB1     |  0       |              
            1                                           P1.1        Prod A Enterprise   |  LOB1     |  1       |     
            2                                           P1.2        Prod A Express      |  LOB1     |  2       |       
            3   P2      MYPROD_B        LOB2                                            |  LOB2     |  6       |                  
            4   P3      MYPROD_C        LOB1                                            |  LOB1     |  3       |                
            5                                           P3.1        Prod C Premium      |  LOB1     |  4       |                               
            6                                           P3.2        Prod C Basic        |  LOB1     |  5       |
        '''
        if not foreign_uid_column in manifest_df.columns:
            raise ApodeixiError(parent_trace, "Can't sort manifest DataFrame by foreign key since it lacks some required column",
                                                data = {"Required column":  str(foreign_uid_column),
                                                        "manifest columns": str(list(manifest_df.columns))})

        padded_df                   = self.pad_manifest_dataframe(parent_trace, manifest_df, padding_column=foreign_uid_column)
        padded_df                   = padded_df.reset_index()
        # At this point padded_df has this additional columns: foreign_uid_column + "_PADDED", and "index"
        # We sort using them        

        sorted_products_df          = padded_df.sort_values(by=[foreign_uid_column + "_PADDED", "index"], axis=0).reset_index()
            
        return sorted_products_df

    def pad_manifest_dataframe(self, parent_trace, manifest_df, padding_column):
        '''
        Returns a DataFrame that is based on a copy of `manifest_df` plus an additional column, populated in a non-sparse
        semantic from the `padding_column`. The additional column is named after the `padding_column` with a "_PADDED" suffix.

        Example: consider a manifest_df as per below, and suppose that the `padding_column` is "UID".

                UID   | product     | lineOfBusiness  | UID-1   |   Sub Product 
            ================================================================================         
            0   P1      MYPROD_A        LOB1                                                          
            1                                           P1.1        Prod A Enterprise  
            2                                           P1.2        Prod A Express        
            3   P3      MYPROD_C        LOB1                                                          
            4                                           P3.1        Prod C Premium                                 
            5                                           P3.2        Prod C Basic   
            6   P2      MYPROD_B        LOB2                                                                

        Then this method will return this other DataFrame, containing an additional column "UID_PADDED"

                UID   | product     | lineOfBusiness  | UID-1   |   Sub Product         | UID_PADDED
            ==========================================================================================         
            0   P1      MYPROD_A        LOB1                                            |   P1             
            1                                           P1.1        Prod A Enterprise   |   P1
            2                                           P1.2        Prod A Express      |   P1  
            3   P3      MYPROD_C        LOB1                                            |   P3              
            4                                           P3.1        Prod C Premium      |   P3                           
            5                                           P3.2        Prod C Basic        |   P3
            6   P2      MYPROD_B        LOB2                                            |   P2                     

        '''
        current_padded_val              = None
        PADDED_COL                      = padding_column + "_PADDED"
        padded_vals                     = []
        for row in manifest_df.iterrows():
            row_val                     = row[1][padding_column]
            if row_val != None and not StringUtils().is_blank(row_val) and row_val != current_padded_val: 
                # Entering a new segment
                current_padded_val = row_val

            if current_padded_val == None:
                raise ApodeixiError(parent_trace, "Can't pad UIDs for DataFrame because value for column " + str(padding_column)
                                                    + " is null in a row that should have a value",
                                            data = {"DataFrame row":    str(row[0])})
            padded_vals.append(current_padded_val)
        result_df                       = manifest_df.copy()
        result_df[PADDED_COL]           = padded_vals   
        return result_df

    def get_manifest_uids(self, parent_trace, manifest_dict):
        '''
        Returns a string of UIDs, co
        '''
        if not type(manifest_dict) == dict:
            raise ApodeixiError(parent_trace, "Can't determine manifest's UIDs because manifest was not passed as a dictionary. "
                                                "Instead was given a " + str(type(manifest_dict)),
                                                origination = {'signaled_from': __file__})

        content_df, entity_name, uid_info_list  = ManifestUtils().extract_manifest_content_as_df(   
                                                                                parent_trace        = parent_trace, 
                                                                                manifest_dict       = manifest_dict, 
                                                                                manifest_nickname   = "Given manifest", 
                                                                                abbreviate_uids     = False)
        uid_columns                         = [col for col in content_df.columns 
                                                    if IntervalUtils().is_a_UID_column(parent_trace, col)]
        valid_uids                          = []
        for uid_col in uid_columns:
            uid_list                        = list(content_df[uid_col])
            valid_uids.extend(uid_list)
        
        return valid_uids

class ManifestDiffResult():
    '''
    Class used as a data structure to hold the differences between two versions of the same manifest.

    Differences are expressed as lists of UIDs per acronym, such as:

        {BR: [BR8, BR7], MR: [BR8.MR1, BR8.MR2]}

    Several such UID lists are kept, depending on whether the UID in questions are for entities added, removed,
    changed, or unchanged.

    An entity is considered "changed" by looking at its properties, and if any property either changed value, or
        if some properties were added or removed, then the entity is regarded as having changed.

    @param short_description A short string with a friendly explanation of what diff is for, intended to be part
                    of filenames for diff reports. Example: "big-rock v1-v2". 
    @param long_description A string with a sentence or two describing the what the diff is for. Suitable for inclusion
                    as a preamble above a tabular diff report.
                        Example: "diff from version 1 to version 2 for fy-22.opus.mtp/big-rock"
    @param contents_df1 A DataFrame, for the manifest contents of the "first" version being compared
    @param uid_info_list1 A list of UID_Info objects, for the manifest of the "first" version being compared
    @param contents_df2 A DataFrame, for the manifest contents of the "second" version being compared
    @param uid_info_list2 A list of UID_Info objects, for the manifest of the "second" version being compared
    '''
    def __init__(self, short_description, long_description, contents_df1, uid_info_list1, contents_df2, uid_info_list2):

        self.short_description                  = short_description
        self.long_description                   = long_description
        self.contents_df1                       = contents_df1
        self.uid_info_list1                     = uid_info_list1
        self.contents_df2                       = contents_df2
        self.uid_info_list2                     = uid_info_list2

        # These will be populated by calling the record_entities_<EVENT> methods
        self.entities_added_dict                = {}
        self.entities_removed_dict              = {}
        self.entities_changed_dict              = {} 
        self.entities_unchanged_dict            = {}

    def record_entities_added(self, parent_trace, acronym, uid_list):
        self.entities_added_dict[acronym]       = uid_list

    def record_entities_removed(self, parent_trace, acronym, uid_list):
        self.entities_removed_dict[acronym]     = uid_list

    def record_entities_changed(self, parent_trace, acronym, entity_diff_list):
        self.entities_changed_dict[acronym]     = entity_diff_list

    def record_entities_unchanged(self, parent_trace, acronym, uid_list):
        self.entities_unchanged_dict[acronym]   = uid_list

    def added_entities_acronym_count(self, parent_trace):
        '''
        Returns a string with the acronyms for entites that have been added.
        The count of entities added per acronym is displayed in parenthesis right after each acronym.
        
        Example output: "BR(5), MR(3), SR(0)"
        '''
        return self._acronym_counts(parent_trace, self.entities_added_dict)

    def removed_entities_acronym_count(self, parent_trace):
        '''
        Returns a string with the acronyms for entites that have been removed.
        The count of entities removed per acronym is displayed in parenthesis right after each acronym.
        
        Example output: "BR(5), MR(3), SR(0)"
        '''
        return self._acronym_counts(parent_trace, self.entities_removed_dict)

    def changed_entities_acronym_count(self, parent_trace):
        '''
        Returns a string with the acronyms for entites that have been changed.
        The count of entities changed per acronym is displayed in parenthesis right after each acronym.
        
        Example output: "BR(5), MR(3), SR(0)"
        '''
        return self._acronym_counts(parent_trace, self.entities_changed_dict)

    def unchanged_entities_acronym_count(self, parent_trace):
        '''
        Returns a string with the acronyms for entites that have not been changed.
        The count of entities unchanged per acronym is displayed in parenthesis right after each acronym.
        
        Example output: "BR(5), MR(3), SR(0)"
        '''
        return self._acronym_counts(parent_trace, self.entities_unchanged_dict)

    def _acronym_counts(self, parent_trace, entities_dict):
        '''
        Helper method for common implementation of methods to get acronym counts. Returns a list
        '''
        acronym_counts              = []
        for acronym in entities_dict.keys():
            count                   = len(entities_dict[acronym])
            acronym_counts.append(str(acronym + "(" + str(count) + ")"))

        return ", ".join(acronym_counts)

    def added_entities_description(self, parent_trace):
        '''
        Returns a list of strings, one for each entity that was added.
        The description consists of the entity's UID followed by its name

        Example: ["BR4: Events", "MR3: Support UI"]
        '''
        return self._entities_in_diff(parent_trace, self.entities_added_dict)

    def removed_entities_description(self, parent_trace):
        '''
        Returns a list of strings, one for each entity that was removed.
        The description consists of the entity's UID followed by its name

        Example: ["BR4: Events", "MR3: Support UI"]
        '''
        return self._entities_in_diff(parent_trace, self.entities_removed_dict)

    def changed_entities_description_dict(self, parent_trace):
        '''
        Returns a dictionary, containing an entry for each entity that was changed.
        Each key is a string description, consisting of the entity's UID followed by its name.

        Each value is a corresponding _ChangedEntityDiff object that describes more fully what changed

        Example: {"BR4: Events": <_ChangedEntityDiff object>, "MR3: Support UI": <_ChangedEntityDiff object>}
        '''
        result_dict                                 = {}
        for acronym in self.entities_changed_dict.keys():
            entity_diff_list                        = self.entities_changed_dict[acronym]
            for entity_diff in entity_diff_list:
                uid_info                            = self._find_uid_info(parent_trace, entity_diff.uid)
                result_dict[uid_info.display()]     = entity_diff

        return result_dict

    def unchanged_entities_description(self, parent_trace):
        '''
        Returns a list of strings, one for each entity that was unchanged.
        The description consists of the entity's UID followed by its name

        Example: ["BR4: Events", "MR3: Support UI"]
        '''
        return self._entities_in_diff(parent_trace, self.entities_unchanged_dict)

    def _entities_in_diff(self, parent_trace, entities_dict):
        '''
        Helper method for common implementation to get a list of descriptions for entities that
        were flagged in a diff.
        Returns a list of strings
        '''
        result                      = []
        for acronym in entities_dict.keys():
            item_list                = entities_dict[acronym]
            for item in item_list:
                # Usually the item is a UID, except when this is for a CHANGED event, in which case it is a
                # _ChangedEntityDiff object, sinced CHANGED events need more detail than just a UID
                if type(item) == ManifestDiffResult._ChangedEntityDiff:
                    uid             = item.uid
                else:
                    uid             = item
                uid_info            = self._find_uid_info(parent_trace, uid)
                result.append(uid_info.display())
        return result

    def _find_uid_info(self, parent_trace, uid):
        '''
        Helper method, to return the unique UID_Info object that corresponds to the given uid.
        Raises an error if it doesn't find one.
        '''
        # First search in the "second version" of the manifest. There should be at most 1, and no match
        # is permitted since perhaps this uid was removed
        uid_info_matches    = [uid_info for uid_info in self.uid_info_list2 if uid_info.uid == uid]
        if len(uid_info_matches) == 1:
            return uid_info_matches[0]
        elif len(uid_info_matches) > 1:
            raise ApodeixiError(parent_trace, "Manifest seems corrupted: UID '" + str(uid) + "' seems to appear multiple times",
                                        data = {"Occurrences": str([uid_info.display() for uid_info in uid_info_matches])})

        # Didn't find it in the "second version", so try in the "first version"
        uid_info_matches    = [uid_info for uid_info in self.uid_info_list1 if uid_info.uid == uid]
        if len(uid_info_matches) == 1:
            return uid_info_matches[0]
        elif len(uid_info_matches) > 1:
            raise ApodeixiError(parent_trace, "Manifest seems corrupted: UID '" + str(uid) + "' seems to appear multiple times",
                                        data = {"Occurrences": str([uid_info.display() for uid_info in uid_info_matches])})
        else: # Didn't find it any where so error out
            raise ApodeixiError(parent_trace, "Manifest seems corrupted: UID '" + str(uid) + "' appears missing")

    class _ChangedEntityDiff():
        '''
        Helper data structured used by the ManifestDiffResult class to hold details about what fields changed for
        a particular entity
        '''
        def __init__(self, uid):
            '''
            '''
            self.uid                = uid
            self.added_fields       = [] # A list of strings, each string being a field name
            self.removed_fields     = [] # A list of strings, each string being a field name
            self.changed_fields     = [] # A list of ChangedValue objects

        def has_differences(self):
            '''
            Returns a boolean: True if this object has recorded differences, and False otherwise
            '''
            if len(self.added_fields) == 0 and len(self.removed_fields)==0 and len(self.changed_fields)==0:
                return False
            else:
                return True

    class _ChangedValue():
        '''
        Helper data structured used by the ManifestDiffResult class to hold information about a change in a field's
        value
        '''
        def __init__(self, uid, field, old_value, new_value):
            self.uid                = uid
            self.field              = field
            self.old_value          = old_value
            self.new_value          = new_value

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

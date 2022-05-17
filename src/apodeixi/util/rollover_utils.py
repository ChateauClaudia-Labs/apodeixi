import copy

from apodeixi.util.dictionary_utils                             import DictionaryUtils

class RolloverUtils():

    def __init__(self):
        pass

    # This field is present only in rollover situations, i.e., when we are loading the last manifest for a scoring cycle
    # (e.g., for FY 22) and using it as basis for the next scoring cycle (e.g., FY 23).
    #
    # In such situations, the concrete class's implementation of self::rollover was called and 
    # loaded "last year's latest manifest" and it then "enriched" the loaded in-memory manifest_dict with this extra label.
    #
    # In those cases, the name of the "prior year manifest" must be remembered in the PostingLabel so that 
    # if a form is posted, then when self.initialize_UID_Store knows tries to validate version integrity.
    # This would error out if the current year's name is used instead of the prior year's.
    #
    # For example, when rolling from "FY 22" to "FY 23", we want to do version integrity by looking if a prior version
    #   exists in name 
    #                               "modernization.fy-22.astrea.official", 
    #  instead of looking in name 
    #                               "modernization.fy-23.astrea.official", 
    # where we wouldn't find one.
    #
    ROLL_FROM_NAME              = "rollFromName"    

    # This field is present only in rollover situations, i.e., when we are loading the last manifest for a scoring cycle
    # (e.g., for FY 22) and using it as basis for the next scoring cycle (e.g., FY 23).
    # In such situations, the function journeys_controller::rollover was called and loaded "last year's latest manifest"
    # and it then "enriched" the loaded in-memory manifest_dict with this extra label.
    #
    #   So when a manifest has labels
    #                                   _SCORING_CYCLE="FY 22" & _ROLL_TO_SCORING_CYCLE="FY 23"
    #
    # that  is used as a "hint" in self.infer to set the posting label's _SCORING_CYCLE to "FY 23", not "FY 22"
    #
    ROLL_TO_SCORING_CYCLE     = "rollToScoringCycle"

    ROLL_FROM_SCORING_CYCLE     = "rollFromScoringCycle"


    def get_rollFromName(self, parent_trace, manifest_dict):
        '''
        If the manifest_dict is for a rollover situation, then it returns the manifest name we are rolling from.

        Otherwise returns None
        '''
        roll_from_name          = None
        dict_path               = ["metadata",    "labels",       RolloverUtils.ROLL_FROM_NAME,      ]
        check, explanation = DictionaryUtils().validate_path(parent_trace, manifest_dict, "Dict Name", 
                                            dict_path, 
                                            valid_types = ['str'])
        if check:
            roll_from_name      = DictionaryUtils().get_val(parent_trace, manifest_dict, "Dict Name", 
                                            dict_path, 
                                            valid_types = ['str'])
        return roll_from_name

    def switch_to_post_rollover(self, parent_trace, manifest_dict):
        '''
        Returns a dict which is modified from manifest_dict by replacing a label with field
        ROLL_FROM_NAME (if it exists) with the different label POST_ROLL_FROM_NAME.
        
        This is meant to be called in the context of generating forms when a manifest is loaded successfully
        as part of getting the data for the form. To prevent the form from thinking it has to be for a roll-over when
        a roll-over already happened in the past, we switch the label.
        '''
        # GOTCHA
        # Remove rolling hint if we no longer need it:
        #
        # When we are rolling from a year to another (e.g., "FY 22" to "FY 23"), we have logic to insert an
        # additional field in the Posting Label: RolloverUtils.ROLL_FROM_NAME (see for example the detailed
        # comments in self.infer.)
        #
        # That extra field plays a temporary role, and once its mission is fulfilled, it must be removed to prevent
        # errors.
        #
        # Specifically:
        #   1. When we first get a form for a new year (like "FY 23", if rolling from "FY 22"), if rollover behavior
        #      is supported by the concrete controller class then a "get form" will create an Excel with a PostingLabel
        #      where the field RolloverUtils.ROLL_FROM_NAME has a value like
        #
        #                               "modernization.fy-22.astrea.official", 
        #
        #   2. As a result of such field, if then a "post" is done on that Excel file, the RolloverUtils.ROLL_FROM_NAME
        #      field will be used by Apodeixi to check version integrity and do diffs against the "previous" version
        #      of the manifest. That, is, the "previous version" will be searched under the name
        #
        #                               "modernization.fy-22.astrea.official", 
        #      instead of looking in name 
        #                               "modernization.fy-23.astrea.official", 
        # 
        #      which would error out, since no prior FY 23 manifest exists.
        #
        #   3. The post will then succeed and a manifest will be created with name "modernization.fy-23.astrea.official",
        #      since the scoring cycle is "FY 23", not "FY 22". It is tempting to save the manifest with a label 
        #      field of RolloverUtils.ROLL_FROM_NAME with value "modernization.fy-22.astrea.official" as a way to
        #      "tag" that the manifest has a "FY 22" lineage even if it is a "FY 23" manifest. 
        #       => However, that will cause problems in Step 5 below unless we do something different.
        #
        #   4. Say we then do a "get form" is requested. If in Step 3 we saved the manifest with field RolloverUtils.ROLL_FROM_NAME
        #      then it will reappears in the Posting Label because of the logic in skeleton_controller::infer,
        #      logic that was needed in step 1 but which now becomes toxic because it will make step 5 to fail (read below)
        # 
        #   5. Say we do a "post". If in step 4 we still have the post field RolloverUtils.ROLL_FROM_NAME, then
        #      the post will fail. This failure happens as in this example:
        #      a. Say the last "FY 22" version for the manifest is version 4
        #      b. Then step 2 will create version 5 in "FY 23", looking for a "prior version" 4 in "FY 22"
        #      c. If we then "get Form" and it still has the field RolloverUtils.ROLL_FROM_NAME, then a "post" would
        #         attempt to create version 6 in "FY 23" and will erroneously look for version 5 in "FY 22"
        #         (because of the field RolloverUtils.ROLL_FROM_NAME). Instead, the correct behaviour now that
        #         rollover is behind us would be to look for version 5 in "FY 23" (where it does exist) instead of
        #         in "FY 22" (where it does not exist, and hence error out)
        #
        #   UPSHOT: To prevent Step 5 from failing, we must change the Step 4 and do this:
        #       a. Load the manifest (since it exists)
        #       b. Immediately after, remove the label RolloverUtils.ROLL_FROM_NAME.  
        #   This will prevent the PostingLabel in Step 4 form having a RolloverUtils.ROLL_FROM_NAME field,
        #   thereby preventing Step 5 from erroring out.
        #
        #   That removal in b) is what this function switch_to_post_rollover is all about.
        #


        if manifest_dict == None:
            return # Nothing to do

        # GOTCHA
        #       Make a *deep* copy of the manifest_dict.
        #
        #   Otherwise, we will modify the `manifest_dict` object that was passed to us, and since Apodeixi uses
        #   a cache for Yaml manifests (see apodeixi.util.yaml_utils), we will probably de mutating the contents of the
        #   cache, which is buggy since they are supposed to be immutable.
        #
        #   That would result in weird bugs such as trying to load a particular manifest (e.g., version 2 of big rocks)
        #   that is supposed to contain a rollFromName (e.g., if version 1 was in FY 22 and version 2 is the first version of
        #   FY 23), but it wouldn't because if someone did a "generate form" to get an Excel to create version 3, in the
        #   process the loaded dictionary was probably passed to this function as `manifest_dict` to "clean up" (i.e. remove)
        #   the ROLL_FROM_NAME label so that version 3 of the big-rocks won't have such a label.
        #
        #   But if we don't do a deep copy here, as a side effect we will also confuse the cache into thinking that we did
        #   the clean up not only for the yet-to-be version 3 of big-rock, but (buggy) for the already persisted version 2.
        #
        #   As a result, attempts to load version 2 will be retrieved without the ROLL_FROM_NAME label (from the cache), even
        #   though it exists in disk with such a label.
        #
        modified_manifest_dict      = copy.deepcopy(manifest_dict)
        
        labels_dict                 = modified_manifest_dict["metadata"]["labels"]
        roll_from_name              = labels_dict.pop(RolloverUtils().ROLL_FROM_NAME, None)

        return modified_manifest_dict


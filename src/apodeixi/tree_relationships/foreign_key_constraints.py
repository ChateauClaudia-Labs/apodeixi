
from apodeixi.knowledge_base.knowledge_base_util                    import ManifestHandle
from apodeixi.knowledge_base.knowledge_base_store                   import KnowledgeBaseStore
from apodeixi.knowledge_base.manifest_utils                         import ManifestUtils

from apodeixi.util.a6i_error                                        import ApodeixiError
from apodeixi.util.dictionary_utils                                 import DictionaryUtils

from apodeixi.xli.uid_store                                         import UID_Utils

class ForeignKeyConstraintsRegistry():
    '''
    This class is used to register foreign-key constraints among manifests.

    This is pertinent in the context where manifest B references a UID in another manifest A.

    For example, consider the way how the `modernization-milestone` manifests reference UIDs in `big-rock` manifests.
    This is captured in a `modernization-milestone` YAML by a construct such as this:

            assertion:
            entity_type: Milestone
            estimatedBy: gato.felix@salga.ar
            estimatedOn: &id001 2021-10-02 00:00:00
            milestone:
                M1:
                Date for Premium: Q4 FY 22
                Date for Professional: Q4 FY 22
                Date for State: Q4 FY 22
                Theme: Lo basico
                UID: M1
                big-rock:
                - BR1.MR1
                - BR2.MR1
                name: MVP Premium
                M1-name: MVP Premium
                ...
            ...

    If milestones_dict denotes the modernization-milestone manifest in the example, then we have

        milestones_dict["assertion"]["milestone"]["M1"]["big-rock"] = ["BR1.MR1"]["BR2.MR1"]

    where "BR1.MR1" and "BR2.MR2" are foreign keys in some big-rock manifest

    This class is designed to support the following referential integrity semantics:

    1. The registry can represent a linkage between a manifest B that references a manifest A
    2. Manifests A, B are identified by their ManifestHandles, which are used as keys in the registry's data structure.
    3. The link from B to A is expressed in the registry by an entry that captures the path in B to the UIDs of A.
        The path is a list of strings. In the example above, the path would be 

            ["assertion", "milestone", "M1", "big-rock"] 

    4. The value in manifest B for such link's path is either a string (a UID for manifest A) or a list of UIDs for manifest A
    5. It is up to the controller for manifest A to maintain the lifecycle of entries in the registry. I.e., create an entry,
        remove an entry.
    6. Referential integrity means that no manifest B should reference UIDs of a manifest A that no longer exist. This class
       enforces referential integrity for any relationship that is entered in this class's registry.
    6. Recommended policy is for cross-manifest relationships to be expressed in the registry for manifests captured in 
        *different* posting APIs and not for cross-manifest relationships for manifests captured in the *same* posting APIs.
        The reasons for this are: 
        a. If manifests A, B are captured via different posting APIs and B references A, then we want to prevent the user to
           remove UIDs from A that might be referenced by B. The software should therefore error out if the user attempts
           to remove such UIDs from A without first doing a prepatory posting to remove the referencing to such UIDs from B's
           manifest.
        b. In the other case where both A, B are from the same posting API, it becomes a usability annoyance to force the
           user to request the same Excel form twice: once to remove references from B to A, and again to then remove the UIDs from
           B. This is not user-friendly because both A and B are present in the same Excel form and typically the linkage
           is expressed in Excel by having alignment-by-row without displaying A's UIDs. So it is not obvious to the user that
           the referencing is happening. Thus, it is better to let the user simply delete (say) an entire Excel row that would
           simutaneously remove the A and B UIDs that are linked, and then post that. The posting will have temporary incoherences,
           since moving from A v1 to A v2 will remove UIDs in A that are referenced by B v1. But as soon as B v2 is saved, that 
           is corrected since B v2 will not reference the A UIDs that were removed. And since the posting is transactional, we know
           that the knowledge base won't be corrupted: either both A v2 and B v2 post successfully, or none does. Thus, it is better
           not to register the relationship from B to A in this class's registry because if we did, the software would not allow
           saving A v2 unless B v2 is saved first, which is cumbersome for the user and unnecessary to protect against
           referential integrity problems as long as the only means to change A and B is via their common posting API.

    @param store A KnowledgeBaseStore
    '''
    def __init__(self, store):

        # This dictionary has the contents of the registry.
        #   * Each key is a ManifestHandle object, corresponding to a manifest that is referenced by other manifests.
        #   * Each value is a ForeignKeyConstraintEntries object, recording the links that pertain to that key
        #
        self.registry                       = {}
        self.store                          = store
        
    def registerEntries(self, parent_trace, entries):
        '''
        @param entries A ForeignKeyConstraintEntries object
        '''
        if type(entries) != ForeignKeyConstraintEntries:
            raise ApodeixiError(parent_trace, "Invalid foreign key constraint entries: expected a 'ForeignKeyConstraintEntries', "
                                            + "and instead was given a '" + str(type(entries)) + "'")
        key                                 = entries.referenced_handle

        if key in self.registry.keys():
            prior_entries                   = self.registry[key]
            prior_entries.merge(parent_trace, entries)
        else:
            self.registry[key]              = entries

    def check_foreign_key_constraints(self, parent_trace, manifest_dict):
        '''
        This method is intended to be used as a check before updating a manifest in the store, to ensure that the
        updated version of a manifest does not remove any UIDs that are referenced by some other manifest.

        If such an integrity violation is found, this method raises an ApodeixiError. Otherwise it silently returns.

        Integrity checks are done against all the links that have been registered with this class against the manifest
        in question.
        '''
        handle                                      = ManifestUtils().inferHandle(parent_trace, manifest_dict)
        if handle.version == 0:
            return # This is a create, not an update, so nothing to check

        prior_handle                                = handle.copy()
        prior_handle.version                        = handle.version -1

        if not prior_handle in self.registry.keys():
            return # There are no constraints registered against this manifest
        
        manifest_uids                               = ManifestUtils().get_manifest_uids(parent_trace, manifest_dict)

        prior_dict, prior_path                      = self.store.retrieveManifest(parent_trace, prior_handle)
        prior_uids                                  = ManifestUtils().get_manifest_uids(parent_trace, prior_dict)

        deleted_uids                                = [uid for uid in prior_uids if not uid in manifest_uids]
        
        constraint_entries                          = self.registry[prior_handle]

        # Filter the links in the constraint_entries to be the latest version of each referencing manifest
        if True:
            handle_types                                = [link.referencing_handle.getManifestType() 
                                                                for link in constraint_entries.links]
            #Remove duplicates
            handle_types                                = list(set(handle_types))

            filtered_links                              = []
            for ht in handle_types:
                matching_links                          = [link for link in constraint_entries.links if
                                                            link.referencing_handle.getManifestType()== ht]
                latest_version                          = max([link.referencing_handle.version for link in matching_links])
                latest_links                            = [link for link in matching_links if
                                                            link.referencing_handle.version == latest_version]
                # GOTCHA: while there is only one ManifestType in this loop, there might be multiple links since a
                # single referencing manifest instance has a link per path. So we use extend, not a append,
                # since there are multiple links to add, not 1
                filtered_links.extend(latest_links)

        # We will aggregate all foreign key constraint violations (if any) in a dictionary where the keys
        # are ManifestHandles for the referencing manifests, and the values are lists of UIDs that were removed
        # but are relied upon by those referencing manifests
        violations                                  = {}
        for link in filtered_links: #constraint_entries.links:
            referenced_uids                         = link.referenced_uids
            link_violations                         = [uid for uid in deleted_uids if uid in referenced_uids]
            if len(link_violations)  > 0:
                violations[link.referencing_handle] = link_violations

        if len(violations) > 0:
            violation_uids                          = []
            for ref_handle in violations.keys():
                violation_uids.extend(violations[ref_handle])
            # For the message, remove duplicate among the referencing handles. This happens since a referencing handle gets
            # a link for every path in the referencing manifest that contains UIDs from the referenced manifest.
            # So we create a set to remove duplicates, and then re-create a list from it
            referencing_handles                     = list(set(violations.keys()))
            ref_handle_msg                          = "\n".join([ref_handle.display(parent_trace) for ref_handle in referencing_handles])
            raise ApodeixiError(parent_trace, "Foreign key violation for manifest: there are " + str(len(violations)) 
                                                + " other manifests that reference UIDs that were removed from manifest",
                                            data = {"Manifest": handle.display(parent_trace),
                                                    "Problem UIDs": str(violation_uids),
                                                    "Referencing manifests": ref_handle_msg})

    def to_persistent_dict(self, parent_trace):
        '''
        Returns a dictionary with the data that should be persisted. This is a slimmed-down version of self.registry,
        removing transient or referential state that shouldn't be persisted.
        '''
        result_dict                         = {}

        for key in self.registry.keys():
            entries                         = self.registry[key]
            slimmed_links                   = [link.to_persistent_dict(parent_trace) for link in entries.links]
            result_dict[key]                = slimmed_links

        return result_dict

    def from_persisted_dict(parent_trace, persisted_dict, store):
        '''
        Creates and returns a ForeignKeyConstraintsRegistry that is built from the `persisted_dict`

        @param store A KnowledgeBaseStore object
        '''
        
        registry                            = {}
        for key in persisted_dict.keys():
            slimmed_links                   = persisted_dict[key]
            links                           = [ForeignKeyLink.from_persisted_dict(parent_trace, slim_link_dict, store) 
                                                            for slim_link_dict in slimmed_links]
            entries                         = ForeignKeyConstraintEntries(parent_trace, key, store)
            entries.links                   = links
            registry[key]                   = entries
    
        result                              = ForeignKeyConstraintsRegistry(store = store)
        result.registry                     = registry
        return result

class ForeignKeyConstraintEntries():
    '''
    This class serves as a supportive data structure to ForeignKeyConstraintsRegistry.

    An instance of this class has two properties:

    * The ManifestHandle of a manifest that is referenced by others, called the `referenced handle`
    * A list of ForeignKeyLink objects, all of them referencing the referenced handle

    @param referenced_handle A ManifestHandle corresponding to the referenced handle for this instance.
    @param store A KnowledgeBaseStore instance, giving access to the store in which the referenced_handle is a valid
                identifier for a a manifest.
    '''
    def __init__(self, parent_trace, referenced_handle, store):
        self.referenced_handle              = referenced_handle
        self.links                          = [] # A list of ForeignKeyLinks
        self.store                          = store

        # Load and remember the manifest. It will never go stale even if the user "updates" the manifest, since
        # manifests are immutable in the store: an update from the user would create a new YAML object in the store, with
        # a higher version number, which would not be the one referenced by the version number of
        # self.referenced_handle. So this "cached" manifest dictionary will always be the "correct" data that
        # self.referenced_handle points to
        #
        self.referenced_dict, ref_path      = self.store.retrieveManifest(parent_trace, self.referenced_handle)

    def addLink(self, parent_trace, link):
        '''
        @param link A ForeignKeyLink instance that references self.referenced_handle's UIDs
        '''
        if type(link) != ForeignKeyLink:
            raise ApodeixiError(parent_trace, "Can't add a foreign key constraint because link is not a ForeignKeyLink",
                                                data = {"type of link":     str(type(link))})
            
        referenced_uids                     = link.referenced_uids

        # Validate that referenced_uids are UIDs that exist in the referenced manifest
        my_trace                            = parent_trace.doing("Validating that referenced UIDs point to real UIDs")
        valid_uids                          = ManifestUtils().get_manifest_uids(parent_trace, manifest_dict = self.referenced_dict)

        missing_uids                        = [uid for uid in referenced_uids if not uid in valid_uids]
        if len(missing_uids) > 0:
            raise ApodeixiError(my_trace, "Can't add a foreign key constraint because the link provided mentions invalid UIDs "
                                            + "that don't exist in the referenced manifest",
                                            data = {"invalid UIDs": str(missing_uids)})
        # If we get this far, then the link is "good": it references UIDs that do exist in the referenced manifest.
        # So now we can safely add the link
        #
        self.links.append(link)

    def merge(self, parent_trace, other_entries):
        '''
        Modifies self.links by extending it with the links contained in `other_entries`

        @param other_entries A ForeignKeyConstraintEntries object
        '''
        if type(other_entries) != ForeignKeyConstraintEntries:
            raise ApodeixiError(parent_trace, "Invalid foreign key constraint entries: expected a 'ForeignKeyConstraintEntries', "
                                            + "and instead was given a '" + str(type(other_entries)) + "'")
        if self.referenced_handle != other_entries.referenced_handle:
            raise ApodeixiError("Can't merge two ForeignKeyConstraintEntries because they are for different referenced manifests",
                                    data = {"referenced handle 1":      str(self.referenced_handle),
                                            "referenced handle 2":      str(other_entries.referenced_handle)})
        self.links.extend(other_entries.links)

class ForeignKeyLink():
    '''
    This class serves as a supportive data structure to the ForeignKeyConstraintEntries class.

    It represents the information around a Manifest that references another. Specifically:

    * The ManifestHandle of the referencing manifest
    * The path in the referencing manifest for the UIDs of the referenced manifest

    As part of creating a ForeignKeyLink instance, the referenced UIDs are identified and rememembered in that
    ForeignKeyLink instance.

    NOTE: 
    
    Manifests are immutable (any update corresponds to a new version number, hence a different Manifest YAML object in 
    the store). Therefore, ForeignKeyLinks are also immutable and the referenced UIDs they remember are always valid, even
    if subsequent manifest updates "remove UIDs", since such removal would be done against manifests with a different
    handle with a different version number than self.referencing_handle's version.

    In other words, the UIDs remembered in this class "never go stale" - they are not a "temporary in-memory cache" of 
    what the store has, since the store is immutable with regards to them, so they are an "always correct cache".

    @param referencing_handle A ManifestHandle instance
    @param referencing_path A list of strings, corresponding to a path in the manifest that is identified by 
                the referencing_handle. This path must have a value that is either a UID or a list of UIDs.
    @param store A KnowledgeBaseStore instance, giving access to the store in which the referencing_handle is a valid
                identifier for a a manifest.
    '''
    def __init__(self, parent_trace, referencing_handle, referencing_path, store):

        # First validation link is well-formed: types are right
        if type(referencing_handle) != ManifestHandle:
            raise ApodeixiError(parent_trace, "Can't create a ForeignLink because the referencing handle is not a ManifestHandle",
                                                data = {"referencing handle type":   str(type(referencing_handle))})
        if type(referencing_path) != list or len([p for p in referencing_path if type(p) != str]) > 0:
            raise ApodeixiError(parent_trace, "Can't create a ForeignLink because the referencing path is not a list of strings",
                                                data = {"referencing_path":     str(referencing_path)})
        if type(store) != KnowledgeBaseStore:
            raise ApodeixiError(parent_trace, "Can't create a ForeignLink because the store parameter is not a KnowledgeBaseStore",
                                                data = {"store":   str(type(store))})

        self.referencing_handle             = referencing_handle
        self.referencing_path               = referencing_path
        self.store                          = store

        # Second validation link is well-formed: the path is valid and it points to UIDs, and remember those UIDs
        my_trace                            = parent_trace.doing("Getting the UIDs referenced by referencing manifest")
        referenced_uids                     = self._retrieve_referenced_uids(my_trace)

        self.referenced_uids                = referenced_uids

    def _retrieve_referenced_uids(self, parent_trace):
        '''
        Returns a list of UID strings that the referencing manifest (i.e., the manifest identified by 
        self.referencing_handle) has in the path given by self.referencing_path.

        If the path is not valid or if it points to something that is not a UID or list of UIDs, this method raises an
        ApodeixiError
        '''
        referencing_dict, ref_path          = self.store.retrieveManifest(parent_trace, self.referencing_handle)
        val                                 = DictionaryUtils().get_val(parent_trace            = parent_trace,
                                                                        root_dict               = referencing_dict, 
                                                                        root_dict_name          = "Referencing Manifest",
                                                                        path_list               = self.referencing_path,
                                                                        valid_types             = [str, list])
        my_trace                            = parent_trace.doing("Validating referenced UIDs are well-formed")
        # To make a uniform check, operate on lists regardless of whether val is str (1 UID) or a list (multiple UIDs)
        if type(val) == str:
            alleged_uids                    = [val]
        else:
            alleged_uids                    = val

        # We leverage the UID_Utils method tokenize to validate that UIDs are well formed
        for au in alleged_uids:
            loop_trace                      = my_trace.doing("Validating that '" + str(au) + "' is a well-formed UID")
            au_tokens                       = UID_Utils().tokenize(loop_trace, au) # Will error out if au is not well formed

        # If we get this far without erroring out, the UIDs are all well-formed, so we can return them
        return alleged_uids

    def to_persistent_dict(self, parent_trace):
        '''
        Returns a dictionary with the data that should be persisted. This is a slimmed-down version of self.registry,
        removing transient or referential state that shouldn't be persisted.
        '''
        result_dict                         = {}

        result_dict["referencing_handle"]   = self.referencing_handle
        result_dict["referencing_path"]     = self.referencing_path
        result_dict["referenced_uids"]      = self.referenced_uids

        return result_dict        

    def from_persisted_dict(parent_trace, persisted_dict, store):
        '''
        Creates and returns a ForeignKeyLink that is built from the `persisted_dict`
        '''
        referencing_handle                  = persisted_dict["referencing_handle"]
        referencing_path                    = persisted_dict["referencing_path"] 

        result                              = ForeignKeyLink(parent_trace, referencing_handle, referencing_path, store)
    
        return result
    
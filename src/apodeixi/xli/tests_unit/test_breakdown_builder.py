import sys                                      as _sys
import pandas                                   as _pd
import yaml                                     as _yaml

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace

from apodeixi.xli.breakdown_builder             import BreakdownTree, UID_Store, Interval
from apodeixi.xli.posting_controller_utils      import PostingConfig
from apodeixi.xli                               import UpdatePolicy

class Test_BreakoutTree(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()



    def _create_df(self):
        columns         = ['A',     'color',    'size',     'B',    'height',   'coolness',     'C']
        row0            = ['a1',    'brown',    "32in",     'b1',   "5' 8''",   'so-so',        'c1']
        row1            = ['',      '',         "",         'b2',   "6' 1''",   'awesome',      'c2']
        row2            = ['',      '',         "",         '',     "",         '',             'c3']
        row3            = ['a2',    'red hair', "29in",     'b3',   "165cm",    'cool cat',     'c4']

        df              = _pd.DataFrame(columns=columns, data = [row0, row1, row2, row3])
        return          df

    def _create_df2(self):
        columns         = ['Expectation',           'Description',          'Acceptance Criteria',      'Artifact']
        row0            = ['Segmentation model',    'Tier/Geo/Vertical',    'Analysis',                 'Tree model']
        row1            = ['',                      '',                     'Market Validation',        'Analysists data']
        row2            = ['Jobs to be done model', 'Understand buying',    'Timeline clear',           'BPMN diagram']
        row3            = ['',                      '',                     'Behavior clear',           'Sequence diagram']

        df2              = _pd.DataFrame(columns=columns, data = [row0, row1, row2, row3])
        return          df2

    def test_read_df_fragment(self):  
        result_dict                 = None
        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Reading df fragment")  
        try:
            tree                    = self._create_breakdown_tree()
            result_dict             = tree.as_dicts()
        except ApodeixiError as ex:
            print(ex.trace_message())

        
        self._compare_to_expected_yaml(root_trace, result_dict, test_output_name = 'read_df_fragment', save_output_dict=True)

    def test_find(self):    
        UID_TO_FIND                 = 'A2.B1.C1'   
        NAME_OF_ENTITY_TO_FIND      = 'c4'

        entity_instance             = None
        try:
            tree                    = self._create_breakdown_tree()
            my_trace                = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Finding uid='" + UID_TO_FIND + "'")
            entity_instance         = tree.find (UID_TO_FIND, my_trace)
        except ApodeixiError as ex:
            print(ex.trace_message())

        self.assertEqual(entity_instance.name, NAME_OF_ENTITY_TO_FIND)

    def test_docking_1(self):
        DOCKING_UID           = 'A2.B1'   
        ENTITY_TO_DOCK        = "Costs"
        
        columns         = [ENTITY_TO_DOCK,          'Purpose']
        row0            = ["Charlie's per diem",    'Customer Visit']
        df              = _pd.DataFrame(columns=columns, data = [row0])

        DATA_TO_ATTACH  = next(df.iterrows())[1]
        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Tesing docking")

        entity_instance             = None
        try:
            tree                    = self._create_breakdown_tree()
            xlr_config              = self._create_posting_config()
            my_trace                = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Docking uid='" + DOCKING_UID + "'")
            tree.dockEntityData (   full_docking_uid    = DOCKING_UID, 
                                    entity_type         = ENTITY_TO_DOCK, 
                                    data_to_attach      = DATA_TO_ATTACH, 
                                    parent_trace        = my_trace,
                                    uid_to_overwrite    = None,
                                    xlr_config          = xlr_config)
            result_dict             = tree.as_dicts()
        except ApodeixiError as ex:
            print(ex.trace_message())
        self._compare_to_expected_yaml(root_trace, result_dict, test_output_name = 'docking_1', save_output_dict=True)

    def test_docking_2(self):
        DOCKING_UID           = 'A2.B1'   
        ENTITY_TO_DOCK        = "C"
        
        columns         = [ENTITY_TO_DOCK,      'Typo']
        row0            = ["Immueble rojo",          'Residencial']
        df              = _pd.DataFrame(columns=columns, data = [row0])

        DATA_TO_ATTACH  = next(df.iterrows())[1]
        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing docking")

        entity_instance             = None
        try:
            tree                    = self._create_breakdown_tree()
            xlr_config              = self._create_posting_config()
            my_trace                = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Docking uid='" + DOCKING_UID + "'")
            tree.dockEntityData (   full_docking_uid    = DOCKING_UID, 
                                    entity_type         = ENTITY_TO_DOCK, 
                                    data_to_attach      = DATA_TO_ATTACH,
                                    uid_to_overwrite    = None, 
                                    parent_trace        = my_trace,
                                    xlr_config          = xlr_config)
            result_dict             = tree.as_dicts()
        except ApodeixiError as ex:
            print(ex.trace_message())
        self._compare_to_expected_yaml(root_trace, result_dict, test_output_name = 'docking_2', save_output_dict=True)

    def test_acronyms(self):   
        entities                    = ['Costs', 'Cost Models', "Ferries", 'Carry Mirrors', 'CO', 'Costs']
        EXPECTED                    = ['CO', 'CM', 'F', 'CAMI', 'COC', 'CO']
        try:
            tree                    = self._create_breakdown_tree()
            result                  = []
            my_trace                = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing acronym generation")
            for e in entities:
                result.append(tree.getAcronym(my_trace, e))

        except ApodeixiError as ex:
            print(ex.trace_message())
        self.assertEqual(result, EXPECTED)

    def test_attach_subtree(self):  
        result_dict                 = None  
        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Attaching subtree")
        try:
            tree1                   = self._create_breakdown_tree()
            subtree_df              = self._create_df2()
            xlr_config              = self._create_posting_config()
            subtree_intervals = [   Interval(None, ['Expectation', 'Description']), 
                                    Interval(None, [ 'Acceptance Criteria', 'Artifact'])]
            self._attach_subtree(   df_to_attach            = subtree_df, 
                                    intervals               = subtree_intervals, 
                                    tree_to_attach_to       = tree1, 
                                    docking_uid             = 'A2.B1.C1', 
                                    xlr_config              = xlr_config)
            result_dict             = tree1.as_dicts()
        except ApodeixiError as ex:
            print(ex.trace_message())

        self._compare_to_expected_yaml(root_trace, result_dict, test_output_name = 'attach_subtree', save_output_dict=True)

    def _create_breakdown_tree(self):
        root_trace      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Creating UID Store")
        store           = UID_Store(root_trace)
        xlr_config      = self._create_posting_config()
        entity_type     = 'A'
        parent_UID      = None
        root_trace      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Creating BreakdownTree", data={  'entity_type'   : entity_type,
                                                                                        'parent_UID'    : parent_UID})        
        tree            = BreakdownTree(uid_store = store, entity_type=entity_type, parent_UID=parent_UID)
        df              = self._create_df()

        root_trace      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Creating intervals", data={'tree.entity_type'  : tree.entity_type,
                                                                                    'columns'           : list(df.columns)})        
        interval_A      = Interval(root_trace, ['A',     'color',    'size'])
        interval_B      = Interval(root_trace, ['B',    'height',   'coolness'])
        interval_C      = Interval(root_trace, ['C'])

        rows            = list(df.iterrows())
        intervals       = [interval_A, interval_B, interval_C]
        root_trace      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Processing DataFrame", data={'tree.entity_type'  : tree.entity_type,
                                                                                    'columns'           : list(df.columns)})

        for idx in range(len(rows)):
            for interval in intervals:
                my_trace        = root_trace.doing(activity="Processing fragment", data={'row': idx, 
                                                                                            'interval': interval.columns},
                                                                origination = {
                                                                                            'signaled_from': __file__})
                tree.readDataframeFragment( interval            = interval, 
                                            row                 = rows[idx], 
                                            parent_trace        = my_trace, 
                                            all_rows            = rows, 
                                            xlr_config          = xlr_config)

        return tree

    def _create_posting_config(self):
        '''
        Returns a dummy PostingConfig object. Needed only because some of the functions we test in this module
        require it as a parameter, though all that they require is an UpdatePolicy object within the PostingConfig
        '''
        update_policy       = UpdatePolicy(reuse_uids=True, merge=False)
        xlr_config          = PostingConfig(    kind            = None, 
                                                manifest_nb     = None, 
                                                update_policy   = update_policy, 
                                                controller      = None)
        return xlr_config

    def _attach_subtree(self, df_to_attach, intervals, tree_to_attach_to, docking_uid, xlr_config):
        store           = tree_to_attach_to.uid_store
        entity_type     = intervals[0].entity_name
        subtree         = BreakdownTree(uid_store = store, entity_type=entity_type, parent_UID=docking_uid)
         
        rows            = list(df_to_attach.iterrows())
        root_trace      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Populating subtree", data={'subtree.entity_type'  : entity_type,
                                                                                    'columns'           : list(df_to_attach.columns)},
                                                                            origination = {
                                                                                    'signaled_from': __file__})

        for idx in range(len(rows)):
            for interval in intervals:
                my_trace        = root_trace.doing(activity="Processing fragment", data={'row': idx, 'interval': interval})
                subtree.readDataframeFragment(  interval            = interval, 
                                                row                 = rows[idx],    
                                                parent_trace        = my_trace, 
                                                all_rows            = rows, 
                                                xlr_config          = xlr_config)

        root_trace      = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Attaching subtree", data = {"docking UID"   : "'" + subtree.parent_UID + "'",
                                                                                    "entity_type"  : "'" + entity_type + "'"})
        tree_to_attach_to.dock_subtree(entity_type, subtree, root_trace)

        

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        what_to_do = args[1]

        T = Test_BreakoutTree()
        T.setUp()
        if what_to_do=='read_df_fragment':
            T.test_read_df_fragment()
        if what_to_do=='find':
            T.test_find()
        if what_to_do=='attach_subtree':
            T.test_attach_subtree()

    main(_sys.argv)
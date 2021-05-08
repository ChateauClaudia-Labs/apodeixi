import sys                          as _sys

from apodeixi.util.a6i_unit_test import ApodeixiUnitTest
from apodeixi.xli.breakdown_builder import UID_Store

class Test_UIDStore(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()
        self.store = UID_Store()
        
    def attempt_tokenize(self, uid):
        try:
            x = self.store._tokenize(uid)
        except ValueError as ex:
            x = 'error'
        return x
    def test_tokenize(self):
        # Each scenario is a pair of [input, expected output]
        scenarios = [['av45.p1.e12', ['av45', 'p1', 'e12']],
                     ['w0',          ['w0']],
                     ['eq3.q',       'error'],
                     ['WE4.T3x',      'error']
                    ] 
        for (uid, expected) in scenarios:
            result = self.attempt_tokenize(uid)
            self.assertEqual(result, expected)
            
    def attempt_generateUID(self, parent_uid, acronym):
        try:
            x = self.store.generateUID(parent_uid, acronym)
        except ValueError as ex:
            x = 'error'
        return x
    def test_generateUID(self):
        # Each scenario is a triple of [parent uid input, acronym input, expected output]
        scenarios = [[None, 'FRA', ('FRA1', 'FRA1')],
                     [None, 'W', ('W1', 'W1')],
                     ['W1', 'PO', ('W1.PO1', 'PO1')],
                     ['FRA1', 'USD', ('FRA1.USD1', 'USD1')],
                     [None, 'FRA', ('FRA2', 'FRA2')],
                     ['FRA1', 'USD',  ('FRA1.USD2', 'USD2')],
                     ['FRA1.USD2', 'NY', ('FRA1.USD2.NY1', 'NY1')],
                     ['FRA1.USD3', 'NY', 'error']
                    ] 
        for (parent_uid, acronym, expected) in scenarios:
            result = self.attempt_generateUID(parent_uid, acronym)
            self.assertEqual(result, expected)


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_UIDStore()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='tokenize':
            T.test_tokenize()
        if what_to_do=='generateUID':
            T.test_generateUID()

    main(_sys.argv)
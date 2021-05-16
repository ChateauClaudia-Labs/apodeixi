import sys                          as _sys

from apodeixi.util.a6i_unit_test    import ApodeixiUnitTest
from apodeixi.util.a6i_error        import ApodeixiError, FunctionalTrace

from apodeixi.xli.breakdown_builder import UID_Store

class Test_UIDStore(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()
        my_trace                = FunctionalTrace(None).doing("Creating a UID Store")
        self.store = UID_Store(my_trace)
        
    def attempt_tokenize(self, parent_trace, uid):
        my_trace      = parent_trace.doing("Attempting to tokenize '" + uid + "'")
        try:
            x = self.store._tokenize(parent_trace, uid)
        except ApodeixiError as ex:
            x = 'error'
        return x
    def test_tokenize(self):
        # Each scenario is a pair of [input, expected output]
        root_trace      = FunctionalTrace(None).doing("Testing tokenize")
        scenarios = [['av45.p1.e12', ['av45', 'p1', 'e12']],
                     ['w0',          ['w0']],
                     ['eq3.q',       'error'],
                     ['WE4.T3x',      'error']
                    ] 
        try:
            for (uid, expected) in scenarios:
                result = self.attempt_tokenize(root_trace, uid)
                self.assertEqual(result, expected)
        except ApodeixiError as ex:
            print(ex.trace_message())
                
    def attempt_generateUID(self, parent_trace, parent_uid, acronym):
        my_trace      = parent_trace.doing("Attempting to generateUID",
                                            data = {'parent_uid': parent_uid, 'acronym': acronym})
        try:
            x = self.store.generateUID(parent_trace, parent_uid, acronym)
        except ApodeixiError as ex:
            x = 'error'
        return x
    def test_generateUID(self):
        # Each scenario is a triple of [parent uid input, acronym input, expected output]
        root_trace      = FunctionalTrace(None).doing("Testing generateUID")
        scenarios = [[None, 'FRA', ('FRA1', 'FRA1')],
                     [None, 'W', ('W1', 'W1')],
                     ['W1', 'PO', ('W1.PO1', 'PO1')],
                     ['FRA1', 'USD', ('FRA1.USD1', 'USD1')],
                     [None, 'FRA', ('FRA2', 'FRA2')],
                     ['FRA1', 'USD',  ('FRA1.USD2', 'USD2')],
                     ['FRA1.USD2', 'NY', ('FRA1.USD2.NY1', 'NY1')],
                     ['FRA1.USD3', 'NY', 'error']
                    ] 
        try:
            for (parent_uid, acronym, expected) in scenarios:
                result = self.attempt_generateUID(root_trace, parent_uid, acronym)
                self.assertEqual(result, expected)
        except ApodeixiError as ex:
            print(ex.trace_message())
            


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
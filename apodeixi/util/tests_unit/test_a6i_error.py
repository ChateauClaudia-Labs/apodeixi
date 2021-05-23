import sys                              as _sys

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.util.a6i_error            import ApodeixiError, FunctionalTrace

class Test_ApodeixiError(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

        self.expected               = {}
        self.root                   = FunctionalTrace(parent_trace=None)
        self.step1                  = self.root.doing(activity="Processing Step 1", flow_stage=None, data=None)
        self.expected['step1']      = [{'activity': 'Processing Step 1', 'flow_stage': '', 'data': {}}]

        self.step2                  = self.root.doing(activity="Processing Step 2", flow_stage='Got past Step 1', data=None)
        self.expected['step2']      = [{'activity': 'Processing Step 2', 'flow_stage': 'Got past Step 1', 'data': {}}]

        for idx in range(5):
            if idx==3:
                self.step2i                 = self.step2.doing(activity     = "In loop cycle Step 2-" + str(idx),
                                                                flow_stage  = "Loop inside Step 2", 
                                                                data        = {'idx': idx, 'comment': 'Merrily processing loop'})
        self.expected['step2i']     = [{'activity': 'Processing Step 2', 'flow_stage': 'Got past Step 1', 'data': {}}, 
                                        {'activity': 'In loop cycle Step 2-3', 'flow_stage': 'Loop inside Step 2', 
                                                'data': {'idx': 3, 'comment': 'Merrily processing loop'}}]

        # Temp - to see what output is while writing this test
        self._save_output(self.step1.examine())

    def test_functional_trace(self):

        self.assertEqual(self.step1.examine(),      self.expected['step1'])
        self.assertEqual(self.step2.examine(),      self.expected['step2'])
        self.assertEqual(self.step2i.examine(),     self.expected['step2i'])

    def test_a61_error(self):
        MSG                                         = "Error with horrible consequences for you"
        try:
            raise ApodeixiError(self.step2i, MSG)
        except ApodeixiError as                     ex:
            trace                                   = ex.functional_trace
            msg                                     = ex.msg
            self.assertEqual(msg,                   MSG)
            self.assertEqual(trace.examine(),       self.expected['step2i'])            


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_ApodeixiError()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='functional_trace':
            T.test_functional_trade()

    main(_sys.argv)
import sys                              as _sys

from apodeixi.testing_framework.a6i_unit_test           import ApodeixiUnitTest
from apodeixi.util.a6i_error            import ApodeixiError, FunctionalTrace

class Test_ApodeixiError(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

        self.root                   = FunctionalTrace(parent_trace=None)
        self.step1                  = self.root.doing(activity="Processing Step 1", flow_stage=None, data={'fun fact': '-'},
                                                                                origination={'secret origin': '-'})

        self.step2                  = self.root.doing(activity="Processing Step 2", flow_stage='Got past Step 1', data=None)

        for idx in range(5):
            if idx==3:
                self.step2i                 = self.step2.doing(activity     = "In loop cycle Step 2-" + str(idx),
                                                                flow_stage  = "Loop inside Step 2", 
                                                                data        = {'idx': idx, 'comment': 'Merrily processing loop'},
                                                                origination = {'concrete class': str(self.__class__.__name__)})

    def test_functional_trace(self):

        output = "================== Step 1 =============\n\n" \
                + '\n\n'.join([str(trace_level) for trace_level in self.step1.examine(as_string=True,)]) \
                + "\n\n\n================== Step 2 =============\n\n" \
                + '\n\n'.join([str(trace_level) for trace_level in self.step2.examine(as_string=True,)]) \
                + "\n\n\n================== Step 2i =============\n\n" \
                + '\n\n'.join([str(trace_level) for trace_level in self.step2i.examine(as_string=True,)]) \

        self._compare_to_expected_txt(output, 'functional_trace', save_output_txt=True)

    def test_a6i_error(self):
        MSG                                         = "Error with horrible consequences for you"
        try:
            raise ApodeixiError(self.step2i, MSG)
        except ApodeixiError as                     ex:
            trace                                   = ex.functional_trace
            msg                                     = ex.msg
            output = msg + "\n\n" \
                    + '\n\n'.join([str(trace_level) for trace_level in trace.examine(as_string=True,)]) \

            self._compare_to_expected_txt(output, 'a6i_error', save_output_txt=True)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_ApodeixiError()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='functional_trace':
            T.test_functional_trace()

    main(_sys.argv)
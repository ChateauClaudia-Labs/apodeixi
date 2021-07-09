import sys                                      as _sys
import pandas                                   as _pd

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace

from apodeixi.text_layout.excel_layout          import PostingLayout

class Test_PostingLayout(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_validate_layout(self):

        outputs     = [] 
        expected    = []
        try:
            root_trace          = FunctionalTrace(parent_trace=None).doing("Testing layout validation")
            outputs             = []
            layout              = PostingLayout("good-layout")

            layout.addHeader(   root_trace, xInterval=[1,9], y=1,               mode='r')
            layout.addBody(     root_trace, xInterval=[1,1], yInterval=[2, 19], mode='r')
            layout.addBody(     root_trace, xInterval=[2,3], yInterval=[2, 19], mode='w')
            layout.addBody(     root_trace, xInterval=[4,4], yInterval=[2, 19], mode='r')
            layout.addBody(     root_trace, xInterval=[5,5], yInterval=[2, 19], mode='w')            
            layout.addBody(     root_trace, xInterval=[6,6], yInterval=[2, 19], mode='r')
            layout.addBody(     root_trace, xInterval=[7,7], yInterval=[2, 19], mode='w')
            layout.addBody(     root_trace, xInterval=[8,8], yInterval=[2, 19], mode='r')
            layout.addBody(     root_trace, xInterval=[9,9], yInterval=[2, 19], mode='w')

            # Check a good layout validates OK
            try:
                outputs.append("====================== Validating " + layout.name)
                layout.validate(root_trace)
                outputs.append("Successfully validated " + layout.name)
            except ApodeixiError as ex:
                outputs.append(ex.trace_message())
            # Check an empty layout validates NOT OK
            try:
                bad_layout = PostingLayout("empty blocks list")
                outputs.append("====================== Validating " + bad_layout.name)
                bad_layout.validate(root_trace)
                outputs.append("Test failure: should have thrown exception for '" + bad_layout.name + "', but didn't")
            except ApodeixiError as ex:
                outputs.append(ex.trace_message(exclude_stack_trace = True)) # Don't print stack trace - code line numbers volatile
            # Check an incomplete layout validates NOT OK
            try:
                bad_layout = PostingLayout("with gaps")
                outputs.append("====================== Validating " + bad_layout.name)
                bad_layout.addHeader(   root_trace, xInterval=[1,3], y=1,               mode='r')
                bad_layout.addBody(     root_trace, xInterval=[1,1], yInterval=[2, 3], mode='r')                
                bad_layout.validate(root_trace)
                outputs.append("Test failure: should have thrown exception for '" + bad_layout.name + "', but didn't")            
            except ApodeixiError as ex:
                outputs.append(ex.trace_message(exclude_stack_trace = True)) # Don't print stack trace - code line numbers volatile
            # Check an layout with overlapping blocks validates NOT OK
            try:
                bad_layout = PostingLayout("with overlaps")
                outputs.append("====================== Validating " + bad_layout.name)
                bad_layout.addHeader(   root_trace, xInterval=[1,4], y=1,               mode='r')
                bad_layout.addHeader(   root_trace, xInterval=[3,5], y=1,               mode='r')
                bad_layout.validate(root_trace)
                outputs.append("Test failure: should have thrown exception for '" + bad_layout.name + "', but didn't")
            except ApodeixiError as ex:
                outputs.append(ex.trace_message(exclude_stack_trace = True)) # Don't print stack trace - code line numbers volatile
            output_as_str = '\n'.join(outputs)
            with open(self.output_data + '/'  'test_validate_layout_OUTPUT.txt', 'w') as file:
                file            .write(output_as_str)
            with open(self.output_data + '/'  'test_validate_layout_EXPECTED.txt', 'r') as file:
                expected     = file.read()
        except ApodeixiError as ex:
            print(ex.trace_message())                                                                                       

        self.assertEqual(output_as_str, expected)


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_PostingLayout()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='validate_layout':
            T.test_validate_layout()

    main(_sys.argv)
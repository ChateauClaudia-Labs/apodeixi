import sys                                      as _sys
import pandas                                   as _pd

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace

from apodeixi.text_layout.text_processor        import TextProcessor

class Test_TextProcessor(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_small_text(self):

        TEXT        = "-123456789-123456789-123456789-123456789-123456789-123456789-123456789-123456789"\
                        + "Pauline Rojas’s high school in San Antonio is open. But like many of her classmates, she "\
                        + "has not returned, and has little interest in doing so."\
                        + "****AND**FOR*fun****we***put***a******super********long*****word*******"\
                        + "During the coronavirus pandemic, she started working 20 to 40 hours per week at Raising Cane’s, "\
                        + "a fast-food restaurant, and has used the money to help pay her family’s internet bill, buy clothes and"\
                        + "save for a car." # (c) New York Times on May 9, 2021
        widths      = [20, 40, 80] # Units of width is: 1 character is 1 unit of width
        outputs     = {} # Key is a width, and output is an array of strings corresponding to laying out TEXT within that width
        expected    = {}
        try:
            for w in widths:
                processor           = TextProcessor(w)
                processor           .processText(TEXT)
                outputs[w]          = '\n'.join(processor.lines)
                with open(self.output_data + '/'  'test_small_text_' + str(w) + '_OUTPUT.txt', 'w') as file:
                    file            .write(outputs[w])
                with open(self.output_data + '/'  'test_small_text_' + str(w) + '_EXPECTED.txt', 'r') as file:
                    expected[w]     = file.read()
        except ApodeixiError as ex:
            print(ex.trace_message())                                                                                        

        self.assertEqual(outputs, expected)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_TextProcessor()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='small_text':
            T.test_small_text()


    main(_sys.argv)
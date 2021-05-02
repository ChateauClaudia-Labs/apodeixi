import unittest
import sys as _sys
import os as _os
import inspect

class ApodeixiUnitTest(unittest.TestCase):
    '''
    Parent class for unit tests in Apodeixi
    '''

    def setUp(self):
        super().setUp()

        # We can't rely on Python's built-in '__file__' property to find the location of the concrete class
        # that is running, since we are in the parent class and we will get the parent class's filename, not the concrete class's.
        # So instead we rely on the inspect package
        me__file__                  = inspect.getfile(self.__class__)
        # self.input_data             = _os.path.join(_os.path.dirname(__file__), 'input_data') # Doesn't work - use inpectt instead
        self.input_data             = _os.path.join(_os.path.dirname(me__file__), 'input_data') # Works ! :-) Thanks inspect!
        # self.output_data            = _os.path.join(_os.path.dirname(__file__), 'output_data') # Doesn't work - use inpectt instead
        self.output_data            = _os.path.join(_os.path.dirname(me__file__), 'output_data') # Works ! :-) Thanks inspect!


    def _save_output(self, output):
        '''
        Helper class used while developing test cases. Test cases will produce some output that needs to be compared
        to an expected output. When first written, one needs to capture the generated output somewhere in order to copy-and-paste
        it into the test case's code as the expected output. This method is used in such situations by temporarily calling
        it at the end of a test case in order to save the output to a text file. The text file's contents can then be pasted
        in the test case as the 'expected output'. Once that is done the test case should pass, and one can remove the line
        that called this method.
        '''
        with open(self.output_data + '/' + 'tmp.txt', 'w') as file:
            file.write(str(output))
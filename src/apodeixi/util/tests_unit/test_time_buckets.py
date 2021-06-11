import sys                                      as _sys
import datetime                                 as _datetime
#import pandas                                  as _pd

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace

from apodeixi.util.time_buckets                 import FY_Quarter

class Test_FY_Quarter(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_fy_quarter(self):

        Q1                          = FY_Quarter(2021, 1, month_fiscal_year_starts=6)
        Q2                          = FY_Quarter(2021, 2, month_fiscal_year_starts=6)
        Q3                          = FY_Quarter(2021, 3, month_fiscal_year_starts=6)
        Q4                          = FY_Quarter(2021, 4, month_fiscal_year_starts=6)

        output                      = ''
        output                      += '------------------------ Checking quarter\'s month to start and ------------------------'
        output                      += '\n  First integer is the month of the year'
        output                      += '\n  Second integer is -1 or 0, depending on whether it is a month in the previous calendar year'
        output                      += '\n'
        output                      += '\nQ1._starts_on_month() = ' + str(Q1._starts_on_month()) + '; Q1._ends_on_month() = ' + str(Q1._ends_on_month())
        output                      += '\nQ2._starts_on_month() = ' + str(Q2._starts_on_month()) + '; Q2._ends_on_month() = ' + str(Q2._ends_on_month())
        output                      += '\nQ3._starts_on_month() = ' + str(Q3._starts_on_month()) + '; Q3._ends_on_month() = ' + str(Q3._ends_on_month())
        output                      += '\nQ4._starts_on_month() = ' + str(Q4._starts_on_month()) + '; Q4._ends_on_month() = ' + str(Q4._ends_on_month())


        output                      += '\n\n------------------------ Checking quarter\'s day to start and end ------------------------'
        output                      += '\n'
        output                      += '\nQ1.first_day() = ' + str(Q1.first_day()) + '; Q1.last_day() = ' + str(Q1.last_day())
        output                      += '\nQ2.first_day() = ' + str(Q2.first_day()) + '; Q2.last_day() = ' + str(Q2.last_day())
        output                      += '\nQ3.first_day() = ' + str(Q3.first_day()) + '; Q3.last_day() = ' + str(Q3.last_day())
        output                      += '\nQ4.first_day() = ' + str(Q4.first_day()) + '; Q4.last_day() = ' + str(Q4.last_day())

        output                      += '\n\n------------------------ Checking quarter\'s display ------------------------'
        output                      += '\n'
        output                      += '\nQ1.displayFY() = ' + str(Q1.displayFY()) + '; Q1.displayQuarter() = ' + str(Q1.displayQuarter())
        output                      += '\nQ2.displayFY() = ' + str(Q2.displayFY()) + '; Q2.displayQuarter() = ' + str(Q2.displayQuarter())
        output                      += '\nQ3.displayFY() = ' + str(Q3.displayFY()) + '; Q3.displayQuarter() = ' + str(Q3.displayQuarter())
        output                      += '\nQ4.displayFY() = ' + str(Q4.displayFY()) + '; Q4.displayQuarter() = ' + str(Q4.displayQuarter())

        d1                          = _datetime.date(2021,1,14)
        d2                          = _datetime.date(2020,2,1)
        d3                          = _datetime.date(2021,2,1)
        d4                          = _datetime.date(2022,2,1)
        d5                          = _datetime.date(2021,1,31)
        d6                          = _datetime.date(2021,2,28)
        d7                          = _datetime.date(2021,3,1)
        d8                          = _datetime.date(2021,5,12)
        output                      += '\n\n------------------------ Checking quarter\'s contains ------------------------'
        output                      += '\n'
        for d in [d1, d2, d3, d4, d5, d6, d7, d8]:
            d_fmt                   = d.strftime('%d-%B-%Y')
            output                  += '\n\nQ2.contains(' + d_fmt + ')         = ' + str(Q2.contains(d)) \
                                        + '\nQ3.contains(' + d_fmt + ')    = ' + str(Q3.contains(d)) \
                                        + '\nQ4.contains(' + d_fmt + ')    = ' + str(Q4.contains(d))


        self._compare_to_expected_txt(  output_txt      = output, 
                                        test_case_name  = 'test_fy_quarter', 
                                        save_output_txt = True)

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_Aha_Importer()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='fy_quarter':
            T.test_fy_quarter()


    main(_sys.argv)
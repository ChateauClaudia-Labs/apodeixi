import sys                                      as _sys
import datetime                                 as _datetime

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace

from apodeixi.util.time_buckets                 import FY_Quarter

class Test_FY_Quarter(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_fy_quarter(self):

        root_trace                  = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing quarter time buckets")
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


        self._compare_to_expected_txt(  parent_trace        = root_trace,
                                        output_txt          = output, 
                                        test_output_name    = 'test_fy_quarter', 
                                        save_output_txt     = True)

    def test_time_bucket_parser(self):

        root_trace          = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing parser for quarter time buckets")

        tests               = ["Q3 FY23", "Q3 FY 23", " Q3 FY 23 ", "FY23", "FY 25", "FY 2026", "Q 4 FY 29" ]

        output              = ""
        for idx in range(len(tests)):
            time_bucket     = FY_Quarter.build_FY_Quarter(root_trace, tests[idx], month_fiscal_year_starts=4)

            output          += "\n'" + tests[idx] + "' was parsed as:\t\t" + time_bucket.display()

        self._compare_to_expected_txt(  parent_trace        = root_trace,
                                        output_txt          = output, 
                                        test_output_name    = 'test_time_bucket_parse', 
                                        save_output_txt     = True)

    def test_time_bucket_comparison(self):

        root_trace          = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing parser for quarter time buckets")

        tests               = [
                                FY_Quarter(2021, 1, month_fiscal_year_starts=6),
                                FY_Quarter(2021, 4, month_fiscal_year_starts=6),
                                FY_Quarter(2021, 2, month_fiscal_year_starts=6),
                                FY_Quarter(2024, 1, month_fiscal_year_starts=6),
                                FY_Quarter(2019, 4, month_fiscal_year_starts=6),
                                FY_Quarter(2019, 1, month_fiscal_year_starts=1),
                                FY_Quarter(2018, 4, month_fiscal_year_starts=6),
                                FY_Quarter(2019, 4, month_fiscal_year_starts=6),
        ]

        output              = ""
        for idx in range(1, len(tests)):
            time_bucket_1   = tests[idx-1]
            time_bucket_2   = tests[idx]

            last_day_1      = time_bucket_1.last_day().strftime("%d %B %Y")
            last_day_2      = time_bucket_2.last_day().strftime("%d %B %Y")

            comparison      = time_bucket_1.less_than(root_trace, time_bucket_2)
            output          += "\n" + time_bucket_1.display() + " < " + time_bucket_2.display() + " ?\t" \
                                + str(comparison) + "\t\tReason: last days are: " + last_day_1 + ", " + last_day_2 + ")"

        self._compare_to_expected_txt(  parent_trace        = root_trace,
                                        output_txt          = output, 
                                        test_output_name    = 'test_time_bucket_compare', 
                                        save_output_txt     = True)


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_FY_Quarter()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='fy_quarter':
            T.test_fy_quarter()


    main(_sys.argv)
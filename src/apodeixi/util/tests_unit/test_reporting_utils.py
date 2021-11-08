import sys                                      as _sys
import datetime                                 as _datetime

import pandas                                   as _pd

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace
from apodeixi.util.apodeixi_config              import ApodeixiConfig
from apodeixi.util.reporting_utils              import ReportWriterUtils

from apodeixi.util.time_buckets                 import FY_Quarter

class Test_Reporting_Utils(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_standardize_timebucket_column(self):

        root_trace              = FunctionalTrace(parent_trace=None, path_mask=self._path_mask)\
                                                                        .doing("Testing parser for quarter time buckets")
        a6i_config              = ApodeixiConfig(root_trace)

        tests                   = ["Q3 FY23", ("Q3 FY 23"), (" Q3 ", "FY 23 "), ("Metrics", "FY23"), ("Perro", "casa"), "nata",
                                ("FY 25", "Actuals"), ("Metrics", "Q2", "FY 2026", "Target"), ("Q 4 ", " FY 29"),
                                2023, "Q3 FY23.1", (" Q3 ", "FY 23.2 "), ("Metrics", "Q2", "FY 2026.3", "Target.4"),
                                (),
        ]

        output                      = ""
        for idx in range(len(tests)):
            raw_col                 = tests[idx]
            timebucket              = None
            try:
                col_result, timebucket, collapsed_indices = \
                                    ReportWriterUtils().standardize_timebucket_column(root_trace, raw_col, a6i_config)
            except ApodeixiError as ex:
                col_result          = str(ex)
                timebucket          = None
                collapsed_indices   = []

            output                  += "\n\n'" + str(tests[idx]) + "' was parsed as:..........................." \
                                                        + str(col_result) + " " + str(collapsed_indices)

            if timebucket != None:
                output      += " (a FY_Quarter)"
            if type(col_result) == tuple:
                output      += " (a tuple)"

        self._compare_to_expected_txt(  parent_trace        = root_trace,
                                        output_txt          = output, 
                                        test_output_name    = 'test_standardize_timebucket_column', 
                                        save_output_txt     = True)

    def test_to_timebucket_columns_1(self):

        TEST_NAME           = "test_to_timebucket_columns_1_df"
        header              = [0,1]
        index_col           = [0]

        self._impl_test(TEST_NAME, header, index_col)

    def test_to_timebucket_columns_2(self):

        TEST_NAME           = "test_to_timebucket_columns_2_df"
        header              = [0,1,2]
        index_col           = [0]

        self._impl_test(TEST_NAME, header, index_col)

    def _impl_test(self, TEST_NAME, HEADER, INDEX_COL):

        try:
            root_trace          = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing DataFrame timebucket tidying up")
            a6i_config          = ApodeixiConfig(root_trace)

            INPUT_FULL_PATH     = self.input_data + "/" + TEST_NAME + ".xlsx"

            input_df            = _pd.read_excel(io=INPUT_FULL_PATH, header=HEADER, index_col=INDEX_COL)

            output_df           = ReportWriterUtils().to_timebucket_columns(root_trace, a6i_config, input_df)

            self._compare_to_expected_df(  parent_trace         = root_trace,
                                            output_df           = output_df, 
                                            test_output_name    = TEST_NAME)

        except ApodeixiError as ex:
            print(ex.trace_message())
            raise ex

if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_Reporting_Utils()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=="to_timebucket_columns_1":
            T.test_to_timebucket_columns_1()
        if what_to_do=="to_timebucket_columns_2":
            T.test_to_timebucket_columns_2()

    main(_sys.argv)
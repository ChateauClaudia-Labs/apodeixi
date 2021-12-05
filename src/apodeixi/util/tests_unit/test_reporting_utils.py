import sys                                      as _sys
import pandas                                   as _pd

from apodeixi.testing_framework.a6i_unit_test   import ApodeixiUnitTest
from apodeixi.util.a6i_error                    import ApodeixiError, FunctionalTrace
from apodeixi.util.apodeixi_config              import ApodeixiConfig
from apodeixi.util.reporting_utils              import TimebucketStandardizer, TimebucketDataFrameJoiner

class Test_Reporting_Utils(ApodeixiUnitTest):

    def setUp(self):
        super().setUp()

    def test_standardizeOneTimebucketColumn(self):

        root_trace              = FunctionalTrace(parent_trace=None, path_mask=self._path_mask)\
                                                                        .doing("Testing parser for quarter time buckets")
        a6i_config              = ApodeixiConfig(root_trace)

        tests                   = ["Q3 FY23", ("Q3 FY 23"), (" Q3 ", "FY 23 "), ("Metrics", "FY23"), ("Perro", "casa"), "nata",
                                ("FY 25", "Actuals"), ("Metrics", "Q2", "FY 2026", "Target"), ("Q 4 ", " FY 29"),
                                2023, "Q3 FY23.1", (" Q3 ", "FY 23.2 "), ("Metrics", "Q2", "FY 2026.3", "Target.4"),
                                (), ("Q1 FY24", "Actuals")
        ]

        output                      = ""
        for idx in range(len(tests)):
            raw_col                 = tests[idx]
            timebucket              = None
            try:
                col_result, timebucket, timebucket_indices = \
                                    TimebucketStandardizer().standardizeOneTimebucketColumn(root_trace, raw_col, a6i_config)
            except ApodeixiError as ex:
                col_result          = str(ex)
                timebucket          = None
                timebucket_indices   = []

            output                  += "\n\n'" + str(tests[idx]) + "' was parsed as:..........................." \
                                                        + str(col_result) + " " + str(timebucket_indices)

            if timebucket != None:
                output      += " (a FY_Quarter)"
            if type(col_result) == tuple:
                output      += " (a tuple)"

        self._compare_to_expected_txt(  parent_trace        = root_trace,
                                        output_txt          = output, 
                                        test_output_name    = 'test_standardizeOneTimebucketColumn', 
                                        save_output_txt     = True)

    def test_to_timebucket_columns_1(self):

        TEST_NAME           = "test_to_timebucket_columns_1_df"
        header              = [0,1]
        index_col           = [0]

        self._impl_timebucket_standardization_test(TEST_NAME, header, index_col)

    def test_to_timebucket_columns_2(self):

        TEST_NAME           = "test_to_timebucket_columns_2_df"
        header              = [0,1,2]
        index_col           = [0]

        self._impl_timebucket_standardization_test(TEST_NAME, header, index_col)

    def test_to_timebucket_columns_3(self):

        TEST_NAME           = "test_to_timebucket_columns_3_df"
        header              = [0,1]
        index_col           = [0]

        self._impl_timebucket_standardization_test(TEST_NAME, header, index_col)

    def test_to_timebucket_columns_4(self):

        TEST_NAME           = "test_to_timebucket_columns_4_df"
        header              = [0,1,2]
        index_col           = [0]

        # Ensure that "Target" columns appear to the left of "Actual"
        def _sorting_key(column_subtuple):
            if column_subtuple == ("Target",): # GOTCHA: Put a "," in tuple, or else Python treats it as a string
                return 0.1
            elif column_subtuple == ("Actual",):
                return 0.2
            else:
                return 99 # This shouldn't happen for our input dataset

        self._impl_timebucket_standardization_test(TEST_NAME, header, index_col, lower_level_key=_sorting_key)

    def _impl_timebucket_standardization_test(self, TEST_NAME, HEADER, INDEX_COL, lower_level_key=None):

        try:
            root_trace          = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing DataFrame timebucket tidying up")
            a6i_config          = ApodeixiConfig(root_trace)

            INPUT_FULL_PATH     = self.input_data + "/" + TEST_NAME + ".xlsx"

            input_df            = _pd.read_excel(io=INPUT_FULL_PATH, header=HEADER, index_col=INDEX_COL)

            output_df, info     = TimebucketStandardizer().standardizeAllTimebucketColumns(root_trace, 
                                                                                            a6i_config, 
                                                                                            input_df, 
                                                                                            lower_level_key)

            self._compare_to_expected_df(  parent_trace         = root_trace,
                                            output_df           = output_df, 
                                            test_output_name    = TEST_NAME)

        except ApodeixiError as ex:
            print(ex.trace_message())
            raise ex

    def _percent(parent_trace, series1, series2):
        result = _pd.Series(data=[0.0]*len(series1.index), index=series1.index) # Ensure index is of right type
        for idx in series1.index:
            result[idx] = float(series2[idx])/float(series1[idx])
        return result

    def _cum_sum(parent_trace, series1, series2):
        # series1 is the accumulated sum so far; series2 is the next DataFrame column to add to the accumulated sum
        # Therefore, series1 is null for the first cycle in loop calling this, which is why we need to check for that
        result = _pd.Series(data=[0.0]*len(series2.index), index=series2.index) # Ensure index is of right type
        for idx in series2.index:
            if series1 is not None: 
                result[idx] = float(series2[idx]) + float(series1[idx])
            else:
                result[idx] = float(series2[idx])
        return result

    def test_timebucket_joins_1(self):

        TEST_NAME           = "ts_join_1"
        header              = [0,1]
        LOWER_TAGS          = ['Target', 'Actual']
        UPPER_TAGS          = None

        self._impl_ts_join_test(TEST_NAME, header, LOWER_TAGS, UPPER_TAGS, 
                                    func            = None, 
                                    operation_type  = None,  
                                    ref_column      = None) 

    def test_timebucket_joins_2(self):

        TEST_NAME           = "ts_join_2"
        header              = [0,1]

        LOWER_TAGS          = ['Target', 'Actual']
        UPPER_TAGS          = ['Product Sales', 'Service Sales']

        self._impl_ts_join_test(TEST_NAME, header, LOWER_TAGS, UPPER_TAGS, 
                                    func            = Test_Reporting_Utils._percent, 
                                    operation_type  = TimebucketDataFrameJoiner.UNARY_OPERATION,
                                    ref_column      = 'Multi-year') 

    def test_timebucket_joins_3(self):

        TEST_NAME           = "ts_join_3"
        header              = [0,1,2]

        LOWER_TAGS          = ['Target', 'Actual']
        UPPER_TAGS          = None

        self._impl_ts_join_test(TEST_NAME, header, LOWER_TAGS, UPPER_TAGS, 
                                    func            = Test_Reporting_Utils._percent, 
                                    operation_type  = TimebucketDataFrameJoiner.BINARY_OPERATION, 
                                    ref_column      = None) 

    def test_timebucket_joins_4(self):

        TEST_NAME           = "ts_join_4"
        header              = [0,1]

        LOWER_TAGS          = ['Target']
        UPPER_TAGS          = None

        self._impl_ts_join_test(TEST_NAME, header, LOWER_TAGS, UPPER_TAGS, 
                                    func            = Test_Reporting_Utils._cum_sum, 
                                    operation_type  = TimebucketDataFrameJoiner.CUMULATIVE_OPERATION, 
                                    ref_column      = None)


    def _impl_ts_join_test(self, TEST_NAME, HEADER, LOWER_TAGS, UPPER_TAGS, func, operation_type, ref_column):
        '''
        '''
        try:
            root_trace          = FunctionalTrace(parent_trace=None, path_mask=self._path_mask).doing("Testing TimebucketDataFrameJoiner")
            a6i_config          = ApodeixiConfig(root_trace)

            REF_FULL_PATH       = self.input_data + "/" + TEST_NAME + "_ref.xlsx"
            reference_df        = _pd.read_excel(io=REF_FULL_PATH)

            DF_B_FULL_PATH      = self.input_data + "/" + TEST_NAME + "_b.xlsx"
            b_df                = _pd.read_excel(io=DF_B_FULL_PATH, header=HEADER)

            if operation_type != TimebucketDataFrameJoiner.CUMULATIVE_OPERATION:
                DF_A_FULL_PATH  = self.input_data + "/" + TEST_NAME + "_a.xlsx"
                a_df            = _pd.read_excel(io=DF_A_FULL_PATH, header=HEADER)
                timebucket_df_list  = [a_df, b_df]
            else:
                timebucket_df_list  = [b_df]



            joiner              = TimebucketDataFrameJoiner(root_trace, 
                                                    reference_df                = reference_df, 
                                                    link_field                  = 'Country', 
                                                    timebucket_df_list          = timebucket_df_list, 
                                                    timebucket_df_lower_tags    = LOWER_TAGS, 
                                                    timebucket_df_upper_tags    = UPPER_TAGS, 
                                                    a6i_config                  = a6i_config)

            if func != None:
                if operation_type == TimebucketDataFrameJoiner.BINARY_OPERATION:
                    joiner.enrich_with_tb_binary_operation(root_trace, 
                                                            a_ltag              = LOWER_TAGS[0], 
                                                            b_ltag              = LOWER_TAGS[1], 
                                                            c_ltag              = "% Target", 
                                                            func                = func)
                elif operation_type == TimebucketDataFrameJoiner.UNARY_OPERATION:
                    joiner.enrich_with_tb_unary_operation(root_trace, 
                                                            ref_column          = ref_column, 
                                                            b_ltag              = LOWER_TAGS[0], 
                                                            c_ltag              = "% Target", 
                                                            func                = func)
                elif operation_type == TimebucketDataFrameJoiner.CUMULATIVE_OPERATION:
                    joiner.enrich_with_tb_cumulative_operation(root_trace, 
                                                            b_ltag              = LOWER_TAGS[0], 
                                                            c_ltag              = "Cum Target", 
                                                            func                = func)

            output_df           = joiner.join_dataframes(root_trace)

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
        if what_to_do=="to_timebucket_columns_3":
            T.test_to_timebucket_columns_3()
        if what_to_do=="timebucket_joins_1":
            T.test_timebucket_joins_1()
        if what_to_do=="timebucket_joins_2":
            T.test_timebucket_joins_2()
        if what_to_do=="timebucket_joins_3":
            T.test_timebucket_joins_3()
        if what_to_do=="timebucket_joins_4":
            T.test_timebucket_joins_4()

    main(_sys.argv)
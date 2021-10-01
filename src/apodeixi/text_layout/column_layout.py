import pandas                               as _pd
import re                                   as _re

from apodeixi.util.a6i_error                import ApodeixiError

from apodeixi.text_layout.text_processor    import TextProcessor

class ColumnWidthCalculator:
    '''
    Helper class used when writing an Pandas DataFrame to a formatted Excel spreadsheet. This class applies
    some heuristics to determine the width that each column should have.
    
    For a dataframe with N columns, it returns a dictionary with N entries, where the keys are the dataframe's
    columns and the values are integers corresponding to the widths per column.
    
    Algorithm
    =========
    
    We compute various scenarios, successively compacting "wide columns" adhereing to some principles:
    1. No column should take more than 50% the viewport_width. So if any column does that, we simply reduce its width.
    2. As we iterate through compacting actions we always track how many lines a column needs.
    3. No row should require more lines than 30% id the viewport_height. When that happens, we no longer
    compact any column if doing so would add more lines than is allowed.
    4. We try to ensure each word fits within a single line. So if a word "qualifies" (it is less than 20 characters),
    we will never compact the column where it appears to less than the word length, or 20, whatever is less.
    5. When compacting, we compact one column at a time as long as it "qualifies" (i.e., that compacting it would not
    violate invariants listed above). 
    6. The column we select for each compacting cycle is chosed based on a "what if". For each column we ask: what if we
    compact the column so as to make it need one more line? And if we did that, how much will we gain in reducing the
    column's width? The column with the greatest width gain is the chosen one.
    7. The algorithm stops when either of two conditions are met:
    8a. Either the total width of the entire data set now fits within the viewport_width
    8b. Or we have no more qualified columns, as the invariants would be violated.
    
    @param data_df DataFrame that we envision to write out to Excel, for which we need to determine Excel column widths
    @param viewport_width Maximum width of the portion of the Excel spreadsheet that is visible at a given
                            point in time. It is an integer corresponding to the maximum number of characters
                            visible at a time. For example, if viewport_width=200 and one has 10 columns to
                            populate, then if one makes them all 20 characters wide they will still fit without
                            triggering a need for the user to scroll horizontally.
    @param viewport_height Maximum number of single-line rowsin the Excel spreadsheet that are visible at a given
                            moment.
    @param max_word_length Algorithm will try to prevent columns shrink so much that a word doesn't fit in a single line.
                           The exception is for "ridiculously long" words. This parameter sets the limit after which
                           a word is considered "ridiculously long" and will not be protected from requiring it to appear
                           in more than 1 line.
    @param column_formatters A dictionary, possibly empty. Keys would be columns and the values are formatters
                            for that column, i.e., a function that takes as input a column value and returns a
                            string. This is used when Excel spreadsheets are created by using formatters, such as
                            when we format dates or doubles in Excel.
                            Such Excel formatting would result in a word or column line being rendered with a 
                            different number of characters than the underlying value. 
                            Since we want to compute the appropriate widths of columns
                            for rendering purposes, when such formatters are used to populate Excel columns we
                            need to take them into account so that we correctly size the columns.
    '''
    def __init__(self, data_df, viewport_width=200, viewport_height=40, max_word_length=20,
                        column_formatters = {}):
        self.data_df                = data_df

        # Ensure that columns are strings (or, in the case of a MultiIndex a tuple of strings), in case they are integers 
        # (can happen if caller is using a transpose,
        # so caller's row indices become column headers by the time this function is called)
        def _stringify_column(col):
            if type(col) == tuple:
                result             = tuple([str(x) for x in col])
            else:
                result              = str(col)
            return result

        self.data_df.columns         = [_stringify_column(col) for col in self.data_df.columns]

        self.viewport_width         = viewport_width
        self.viewport_height        = viewport_height
        
        # During our calculations we will be building a dataframe of information
        # Columns will be 'worst_case_width'
        #self.analysis_df             = None    
        
        self.MAX_WORD_LENGTH        = max_word_length
        self.MAX_COL_WIDTH          = self.viewport_width * 0.50
        self.MAX_ROW_HEIGHT         = self.viewport_height * 0.30
        self.explanations           = None # Computed by self.calc()
        self.analysis_df            = None # Computed by self.calc()

        # Dictionary of formatters per column. Not all columns need to have one, only when a column's values are
        # to be rendered in a non-literal way (e.g., dates, or doubles with decimals or commas for thousands, etc.)
        self.column_formatters      = column_formatters
        return
    
    def calc(self, parent_trace):
        # Initialize our helper DataFrame to guide our decisions
        df                      = self._analyze_widths(parent_trace)
        
        gen                    = _ScenarioGenerator(parent_trace        = parent_trace,
                                                    working_df          = df, 
                                                    viewport_width      = self.viewport_width,
                                                    col_width_limit     = self.MAX_COL_WIDTH,
                                                    row_height_limit    = self.MAX_ROW_HEIGHT,
                                                    word_size_limit     = self.MAX_WORD_LENGTH,
                                            )
        # Now run the iterative algorithm that "guesses" column widths and systematically searches for an optimium
        for candidate, width, PRIOR, NEXT, explanations in gen:
            self._applyScenario(parent_trace        = parent_trace,
                                analysis_df         = df,
                                column_to_resize    = candidate,
                                width_val           = width,
                                prior_scenario      = PRIOR,
                                next_scenario       = NEXT)

        # Persist intermediate values from calculation in case we need to inspect how we got to the answer 
        self.explanations       = gen.explanations
        self.analysis_df        = df

        # Now assemble the results, which are held in the columns of self.analysis_df corresponding to last scenario
        W_COL                   = ColumnWidthCalculator._scenarioWidthColumn
        NB_COL                  = ColumnWidthCalculator._scenarioNbLinesColumn
        
        FINAL_WIDTH             = W_COL(NEXT)
        FINAL_NB_LINES          = NB_COL(NEXT)

        # Keys will be columns of self.data_df, and values will be a dictionary with two entries: width and nb_lines
        final_result                = {} 
        for row in self.analysis_df.iterrows():
            col                 = row[1]['Column']

            width               = row[1][FINAL_WIDTH]
            nb_lines            = row[1][FINAL_NB_LINES]
            final_result[col]   = {'width': width, 'nb_lines': nb_lines}

        return final_result    
        
    def _applyScenario(self, parent_trace, analysis_df, column_to_resize, width_val, prior_scenario, next_scenario):
        def _new_val(row_label, prior_column, new_val):
            def inner_function(row):
                if row['Column'] == row_label:
                    return new_val
                else:
                    return row[prior_column]
            return inner_function
        
        W_COL           = ColumnWidthCalculator._scenarioWidthColumn
        NB_COL          = ColumnWidthCalculator._scenarioNbLinesColumn
        
        PRIOR_WIDTH     = W_COL(prior_scenario)
        NEXT_WIDTH      = W_COL(next_scenario)
        NEXT_NB_LINES   = NB_COL(next_scenario)
               
        analysis_df[NEXT_WIDTH]    = analysis_df.apply(_new_val(column_to_resize, PRIOR_WIDTH, width_val), 
                                                              axis=1)
        HEIGHT_ESTIMATOR = ColumnWidthCalculator._estimate_nb_lines
        analysis_df[NEXT_NB_LINES] = analysis_df.apply(HEIGHT_ESTIMATOR(parent_trace=parent_trace,
                                                                        column_with_widths= NEXT_WIDTH), 
                                                              axis=1)       
       
    def _scenarioWidthColumn(scenario):
        return scenario + ' width'
    def _scenarioNbLinesColumn(scenario):
        return scenario + ' Nb of lines'

    def _estimate_nb_lines(parent_trace, column_with_widths):
        '''
        Helper method that returns an anonymous function that can be used to estimate
        how many lines it takes to express the text for a column in self.data_df.
        
        This is called in the context of a working datframe, usually called working_df,
        which this class uses as a pad on which to keep calculations.
        Working_df has one row for each column in self.data_df, and maintains some computations
        as this class iterates several scenarios looking for ideal column widths for self.data_df.
        
        In this context, working_df has columns dedicated to each scenario maintaining a proposed
        width for each self.data_df column (i.e., rows in working_df).
        
        The anonymous function returned can be used in a working_df.apply(--) call to populate a
        new column for the scenario in question, indicating how many lines of text are needed
        for each column of self.data_df (i.e., rows in working_df)
        
        @param column_with_widths Column in working_df containing the scenario's column widths,
                                   for the scenario for which we seek to see how many lines of text
                                   it would take in data_df.
        '''
        def estimate_row(row_in_working_df):
            column            = row_in_working_df["Column"]
            
            proposed_width    = row_in_working_df[column_with_widths]
            
            # A list, one per row in data_df, for this column of data_df
            list_of_word_lists = row_in_working_df["Words per row"] 
            
            return ColumnWidthCalculator._whatif_nb_lines(  parent_trace            = parent_trace, 
                                                            list_of_word_lists      = list_of_word_lists, 
                                                            proposed_width          = proposed_width)

        return estimate_row
        
    def _whatif_nb_lines(parent_trace, list_of_word_lists, proposed_width):
        '''
        Helper method that returns an integer, corresponding to the maximum number of lines needed to
        represent each of the word lists in list_of_word_lists within the proposed_width
        '''
        nb_lines_list   = [] 
        for word_list in list_of_word_lists: # Each cycle is for a different row in data_df[column]
            #word_list = row_in_analysis_df['']
            processor = TextProcessor(proposed_width)
            text      = ' '.join(word_list)
            processor.processText(parent_trace=parent_trace, text=text)
            nb_lines_list.append(len(processor.lines))

        # So in the event that column is set to a width of `width`, the maximal number of lines in
        # a row of data_df as a result of such a decision is this max:
        max_nb_lines = max(nb_lines_list)
        return max_nb_lines
    
    def _word_is_acceptable(self, word, width):
        return len(word) <= width and len(word) <= self.MAX_WORD_LENGTH
        
    def _words_per_row(self, parent_trace, column):
        my_trace            = parent_trace.doing("Getting a list of words per row for column '" + str(column) + "'")
        #rendered_tokenstokens_per_column   = self.data_df[column].apply(lambda x: _re.split(r"\s", str(x).strip()))
         
        if column in self.column_formatters.keys():
            formatter       = self.column_formatters[column]

            rendered_tokens   = self.data_df[column].apply(lambda x: [formatter(my_trace, x)]) # A list of 1 formatted string per row

        else:
            rendered_tokens   = self.data_df[column].apply(lambda x: _re.split(r"\s", str(x).strip()))

        return rendered_tokens
    
    def _all_words(self, parent_trace, column):
        my_trace            = parent_trace.doing("Getting all words in column '" + str(column) + "'")
        tokens_merged       = []
        tokens_per_column   = self._words_per_row(my_trace, column)
        for tokens in tokens_per_column:
            tokens_merged.extend(tokens)
        return tokens_merged

    def _longest_word(self, parent_trace, column):
        my_trace            = parent_trace.doing("Getting longest word in column '" + str(column) + "'")
        all_words           = self._all_words(my_trace, column)
        # The column header will the "the longest word by default", unless we find a longer word in the rows below the header
        # GOTCHA:
        #       Must handle the case where the column is a tuple. It can happen for MultiLevel indices in the DataFrames
        #   representing manifests. For example, the big-rock-estimate DataFrame uses a MultiIndex when there are
        #   subproducts, in which case the columns look like
        #
        #       (<subproduct 1>, "Q1"), (<subproduct 1>, "Q2"), ..., (<subproduct 2>, "Q1"), (<subproduct 2>, "Q2"), ...
        #
        #   In that case the default_answer should the the longest member of tuple representing the column, not the column itself
        if type(column) == tuple:
            candidates          = list(column)
            candidates_length   = [len(c) for c in candidates]
            max_length          = max(candidates_length)
            default_answer      = [c for c in candidates if len(c)==max_length][0] # Pick one that has largest length
        else:
            default_answer      = column 
        
        if len(all_words)==0:
            return default_answer
        max_length          = max([len(str(x)) for x in all_words])
        longests            = [x for x in all_words if len(x)==max_length]
        possible_answer     = longests[0] # Guaranteed to exist since all_words is non-empty (we checked)
        
        # Return the longest: either the header, or the longest word in the body
        if len(possible_answer) > len(default_answer):
            return possible_answer
        else:
            return default_answer
    
    def _1l_widths_per_row(self, parent_trace, column):
        '''
        Helper method that returns a list of floats, corresponding to the widths for each row in a column, 
        if a row has only 1 line
        '''
        if column in self.column_formatters.keys():
            formatter       = self.column_formatters[column]
        else:
            def _cast_to_str(parent_trace, x):
                return str(x)
            formatter       = _cast_to_str  # Just cast to a string, if no formatter was configured

        # The following code is more verbose than doing something like
        #
        #   return self.data_df[column].apply(lambda x: len(formatter(parent_trace, x)))
        #
        # but we do it this way so that we can add tracing information row-by-row, so that when errors
        # occur we can tell the caller what row was the problem
        result              = []
        for row in self.data_df.iterrows():
            loop_trace = parent_trace.doing("Computing the width for a row",
                                            data = {"column":   str(column),
                                                    "row number in dataset": str(row[0]),
                                                    "row data": str(row[1])})
            # We format the row data so that we measure its length the way it would be displayed in Excel
            # to the user. That way our width computations match the width the user would experience
            width       = len(formatter(loop_trace, row[1][column]))
            result.append(width)
        return result
                                            

    def _max_1l_width(self, parent_trace, column):
        '''
        Helper function that returns the width of the widest row for a column if the row has only 1 line
        '''
        my_trace            = parent_trace.doing("Computing width of largest single-line row for column",
                                            data = {"column": str(column)})
        header_width      = len(str(column))
        return max(header_width, max(self._1l_widths_per_row(my_trace, column)))
        
    def _analyze_widths(self, parent_trace):

        my_trace                = parent_trace.doing("Computing width stats for all DataFrame columns")
        
        columns                 = self.data_df.columns
        
        max_1l_widths           = [self._max_1l_width       (my_trace, col) for col in columns]  
        words_per_row           = [self._words_per_row      (my_trace, col) for col in columns]
        all_words               = [self._all_words          (my_trace, col) for col in columns]
        longest_words           = [self._longest_word       (my_trace, col) for col in columns]
        longest_word_lengths    = [len(w) for w in longest_words]
        widths_df               = _pd.DataFrame({'Column':                columns, 
                                              'Max 1-line width':      max_1l_widths,
                                              'Longest word':          longest_words,
                                              'Longest word length':   longest_word_lengths,
                                              'All words':             all_words,
                                              'Words per row':         words_per_row})
        return widths_df

class _ScenarioGenerator(): 
    '''
    Helper class to assist ColumnWidthCalculator by giving it an iterator interface to loop through the plausible moves
    to successively shrink columns in search for an optimal layout.

    To that end, this class is a Generator to yield the next column to try to shrink. It returns the name of the column and the
    suggested size as well as unique identifiers to the prior and next scenarios,
    to differentiate previously generated scenarios. Also returns an array of string explanations for the reasons why
    column width reduction stops (i.e., what invariant or rule would be broken if a column shrinks further)
    These explanations are useful for debugging and regression tests.
    '''
    def __init__(self, parent_trace, working_df, viewport_width, col_width_limit, row_height_limit, word_size_limit):
        
        self.parent_trace           = parent_trace
        self.working_df             = working_df
        self.viewport_width         = viewport_width
        self.col_width_limit        = col_width_limit
        self.row_height_limit       = row_height_limit
        self.word_size_limit        = word_size_limit

        self.scenario_nb            = 0
                    
        self.explanations           = [] # Explanatinos for last iteration only
        
    def __iter__(self):
        
        W_COL           = ColumnWidthCalculator._scenarioWidthColumn
        NB_COL          = ColumnWidthCalculator._scenarioNbLinesColumn
            
        if self.scenario_nb == 0: # Initialize: pick any column and set it to the size it already has
            PRIOR           = 'Max 1-line'
            NEXT            = 'S0'
            candidate       = self.working_df['Column'].iloc[0]
            current_width   = self.working_df[W_COL(PRIOR)].iloc[0]
            yield candidate, current_width, PRIOR, NEXT, []
            
        # Past this stage we can assume there is always a "prior" scenario as we do the "next" scenario
        
        # To avoid infinite loops, put a limit
        while self.scenario_nb < 100:
            self.scenario_nb += 1
            #self.explanations = []
            
            PRIOR           = 'S' + str(self.scenario_nb-1)
            NEXT            = 'S' + str(self.scenario_nb)
            # First seniority for optimizations:
            # Try for width limit violations
            #'''
            candidate = self._next_column_over_limit()
            if candidate != None:
                yield candidate, self.col_width_limit, PRIOR, NEXT, []
                continue
            #'''
            # By the time we get here, all columns are now within limits, so additional wins are to
            # come from reducing some column's widths at the expense of adding 1 additional row.
            # This only makes sense to attempt when we don't fit in the viewport_horizontal
            current_width   = self.working_df[W_COL(PRIOR)].sum()
            #current_height  = self.working_df[NB_COL(PRIOR)].min() # Something can still grow, hence min
            if current_width > self.viewport_width: 
                candidate, width, explanations = self._next_column_what_if()
                
                #self.explanations.extend(explanations)
                self.explanations = explanations
                if candidate != None:
                    yield candidate, width, PRIOR, NEXT, explanations
                    continue
            
            # Didn't find a candidate, so we are done optimizing
            break
        return    
    
    def _next_column_over_limit(self):
        W_COL           = ColumnWidthCalculator._scenarioWidthColumn
        
        PRIOR           = 'S' + str(self.scenario_nb -1)
        tmp_df          = self.working_df[self.working_df[W_COL(PRIOR)] > self.col_width_limit]
        
        if len(tmp_df.index) > 0:
            # Return the data_df column listed in the first row of tmp_df
            return tmp_df.iloc[0]['Column']

        return None
    
    def _next_column_what_if(self):
        '''
        Returns a triple: column, proposed_width, failure_explanations.
        
        `failure_explanations` is list of strings. It is empty when the method succeeds, and in that case we get
        the name of a column that could be shrunk to the proposed width and result in only
        1 additional line of text for some row in that column.
        
        On failure, `failure_explanation` is a string describing why it is not possible to
        optimize further (i.e., what invariant of our spec would be violated if we did)
        In such cases it returns None, None, failure_explanation
        '''
        W_COL           = ColumnWidthCalculator._scenarioWidthColumn
        NB_COL          = ColumnWidthCalculator._scenarioNbLinesColumn
        
        PRIOR           = 'S' + str(self.scenario_nb-1)
        NEXT            = 'S' + str(self.scenario_nb)
        
        # Find the maximal number of lines at present
        prior_max_width = self.working_df[W_COL(PRIOR)].max()
        
        candidates      = [] # Column names in data_df that would benefit from shrinking
        widths          = [] # Will be of same size as candidates
        
        explanations    = [] # Will be set only if we abort, to explain why
        
        for row in self.working_df.iterrows(): # Each row is for a column in data_df
            column             = row[1]["Column"]        
            prior_width        = row[1][W_COL(PRIOR)]
            #prior_nb_lines     = row[1][NB_COL(PRIOR)]
            
            
                
            # Try to never shrink below the size needed for longest word, unless the word is ridiculously long
            # and exceeds limit
            #longest_word_length = min(row[1]['Longest word length'], self.word_size_limit)
            longest_word =row[1]['Longest word']
                            
            list_of_word_lists = row[1]["Words per row"]
            what_ifs           = []
            data_df_row_nb     = -1
            for word_list in list_of_word_lists: # Each cycle is for a different row in data_df[column]
                data_df_row_nb  += 1
                EXPLANATION_PREFIX = NEXT + ": (column, row)=(" + str(column) + ", " + str(data_df_row_nb) + ") - "
                text                             = ' '.join(word_list)
                # Find how many lines this used to take
                processor                        = TextProcessor(prior_width)
                processor.processText(parent_trace=self.parent_trace, text=text)
                prior_nb_lines                   = len(processor.lines)
                
                if prior_nb_lines >= self.row_height_limit:
                    explanations.append(EXPLANATION_PREFIX 
                                        + "Row height rule: height=" + str(prior_nb_lines)
                                        + " and should not exceed "
                                        + str(self.row_height_limit) + " for text='" + text + "'") 
                    break # Give up on this column of data_df
                what_if_width, what_if_nb_lines, explanation = self._what_if_width(text, 
                                                                        prior_width, 
                                                                        prior_nb_lines, 
                                                                        longest_word)
                    
                if not what_if_width < prior_width:
                    # We didn't shrink, no there is no optimization here, try  next row in data_df[column]
                    explanations.append(EXPLANATION_PREFIX + explanation)
                    break
                
                elif what_if_nb_lines <= self.row_height_limit:
                # We haven't violated a global minimum, so this is a good candidate                    
                    what_ifs.append(what_if_width)
                else:
                    explanations.append(EXPLANATION_PREFIX 
                                        + "Violated row_height_limit=" 
                                        + str(self.row_height_limit) + " for text='" + text + "'")
                    
            OUTER_LOOP_EXPLANATION_PREFIX = NEXT + ": column='" + str(column) + "' - "
            # See if this column in data_df found a way to shrink
            if len(what_ifs) > 0:
                best_found         = max(what_ifs) # They are all acceptable minima conditions to meet, hence max

                if best_found < prior_max_width: # Sounds like we can shrink this column, but check row heights
                    HEIGHT_ESTIMATOR   = ColumnWidthCalculator._whatif_nb_lines
                    w_df               = self.working_df
                    list_of_word_lists = w_df[w_df['Column'] ==column].iloc[0]['Words per row']
                    
                    max_height = HEIGHT_ESTIMATOR(  parent_trace            = self.parent_trace, 
                                                    list_of_word_lists      = list_of_word_lists, 
                                                    proposed_width          = best_found)

                    if max_height <= self.row_height_limit:
                        candidates.append(column)
                        widths.append(best_found)
                    else:
                        explanations.append(OUTER_LOOP_EXPLANATION_PREFIX  
                                            + "Row height rule: at least one row would have " + str(max_height)
                                            + " lines if column shrinks, but limit is "
                                            + str(self.row_height_limit))
                else:
                    explanations.append(OUTER_LOOP_EXPLANATION_PREFIX 
                                        + "at least one row can't shrink below prior_max_width="
                                        + str(prior_max_width) + ". Per-row what-ifs are: " + str(what_ifs))
            else:
                explanations.append(OUTER_LOOP_EXPLANATION_PREFIX
                                    + "Can't shrink because no row had a successful what-if")                    
        
        if len(candidates) > 0: # Choose the one with longest width, since that probably needs most help
            best_idx           = widths.index(max(widths))
            return candidates[best_idx], widths[best_idx], explanations
        else:
            return None, None, explanations

    def _what_if_width(self, text, prior_width, prior_nb_lines, longest_word):
        '''
        Helper method that computes and returns a 'what if' width number, defined as the smallest width
        for which the column would fit in 1 more line than before, while never shrinking below
        the longest_word_length.
        
        It also returns the number of lines that would correspond to that, an a string explanation 
        in case it couldn't shrink
        '''
        longest_word_length = min(len(longest_word), self.word_size_limit) 
        what_if_width       = prior_width
        what_if_nb_lines    = prior_nb_lines
        explanation         = "Longest word rule: can't reduce width(" + str(prior_width) + ")  and still fit '" \
                                + longest_word + "'"
        while what_if_width > longest_word_length: # Keep shrinking width until it is optimal
            next_what_if_width    = what_if_width - 1
            processor             = TextProcessor(next_what_if_width)
            processor.processText(parent_trace=self.parent_trace, text=text)
            next_what_if_nb_lines = len(processor.lines)
            if next_what_if_nb_lines > prior_nb_lines + 1: 
                # Reached an invalid option - grew line nb too much, so exit loop and use last what if
                # Unless this was the first cycle of loop, in which case we need an explanation for
                # failure
                if what_if_width == prior_width:
                    explanation       = "Can't shrink column below width=" + str(what_if_width) \
                                        + " because doing so increases number of lines (" \
                                        + str(prior_nb_lines) + ") by more than 1 for text='" + text + "'"
                break 
            else:
                what_if_width     = next_what_if_width
                what_if_nb_lines  = next_what_if_nb_lines
                explanation       = None
                
        return what_if_width, what_if_nb_lines, explanation

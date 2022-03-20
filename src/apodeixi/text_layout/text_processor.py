import re                                   as _re

from apodeixi.util.a6i_error                import ApodeixiError

# This class is called easily a million times, because of the many nested loops (for each posting request, for each
# manifest, for each column, for each row, for each scenario at guessing a width for such column)
#
# So as a performance improvement we cache results if they were previously computed
#
_TOKENS_CACHE = {} # Keys are strings (the text that is passed to self.processText), values is a list of tokens

_PROCESSOR_LINES_CACHE = {} # Keys are tuples (text, line_width) and values integers (number of lines after processing)


class TextProcessor(): # Represents a list of text lines being written to, tracking how much remains in current line
    def __init__(self, line_width):
        self._line_width        = line_width
        self._consumed          = 0
        
        self._lines             = ['']
        self._current_line_idx  = 0
        self.nb_lines           = 1
    
    def processText(self, parent_trace, text):
        '''
        Processes the `text` appending into the lines of this object (self._lines)
        '''
        try:
            if (text, self._line_width) in _PROCESSOR_LINES_CACHE.keys():
                self.nb_lines               = _PROCESSOR_LINES_CACHE[(text, self._line_width)]
                return

            cleaned_txt                     = str(text).strip()
            if cleaned_txt in _TOKENS_CACHE:
                tokens                      = _TOKENS_CACHE[cleaned_txt]
            else:
                tokens                      = _re.split(r"\s", cleaned_txt)
                _TOKENS_CACHE[cleaned_txt]  = tokens
            gen                             = TextProcessor._WorkGenerator(word_list        = tokens, 
                                                                            line_width      = self._line_width, 
                                                                            text_processor  = self)
            for task in gen:
                gen.text_processor._consume(task) # Equivalent to self._consume(task)

            self.nb_lines                   = len(self._lines)
            _PROCESSOR_LINES_CACHE[(text, self._line_width)]    = self.nb_lines
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Problem with justification algorithm for given text",
                                        data = {"text":     str(text),
                                                "error":    str(ex)})

    
    def _consume(self, fit_word): # A 'fit_word' is one not exceeding the line_width. TODO: raise Exception if not fit
        available = self._line_width - self._consumed
        if self._consumed > 0: # Not at start of line, so need to put a space
            candidate_to_place   = ' ' + fit_word
        else:
            candidate_to_place   = fit_word
        
        if available >= len(candidate_to_place):
            self._consumed += len(candidate_to_place)
            self._lines[self._current_line_idx] += candidate_to_place
        else:
            # Need to move to a new line
            self._lines.append('')
            self._current_line_idx += 1
            self._consumed       = 0
            self._consume(fit_word)
            
    def _split_for_fitness(self, word): 
        '''
        Returns a list of two strings, head and tail, where word = head + tail and head
        is the maximal size possible such that head is considered "fit"
        '''
        if len(word) <= self._line_width:
            return [word, '']
        else:
            #GOTCHA
            #   Code below will crash if we use self._line_width as an index, since it sometimes is a float,
            # and float are not allowed as indices.
            # For example, it would crash with self._line_width=23.0 and word="Operations-Optimizations"
            # So convert to an int
            LW_as_int           = int(self._line_width)
            return [word[0:LW_as_int], word[LW_as_int:len(word)]]
        
    class _WorkGenerator(): # A word may lead to "multiple works" if we have to split it
        '''
        Generator used to iterate through the "work". Normally a unit of "work" would be a word,
        but if the word is too long it would have to be split. Hence we use a special generator
        that produces a list of "fit words", i.e., words or portions thereof that are "fit"
        '''
        def __init__(self, word_list, line_width, text_processor):
            self.line_width         = line_width
            self.word_list          = word_list

            self.text_processor     = text_processor

        def __iter__(self):
            for word in self.word_list:
                unprocessed = word
                while len(unprocessed)>0:
                    head, unprocessed = self.text_processor._split_for_fitness(unprocessed)
                    yield head
            return
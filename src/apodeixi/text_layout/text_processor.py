import re                                   as _re

class TextProcessor(): # Represents a list of text lines being written to, tracking how much remains in current line
    def __init__(self, line_width):
        self.line_width       = line_width
        self.consumed         = 0
        
        self.lines            = ['']
        self.current_line_idx = 0
    
    def processText(self, text):
        '''
        Processes the `text` appending into the lines of this object (self.lines)
        '''
        tokens        = _re.split(r"\s", str(text).strip())
        gen           = TextProcessor._WorkGenerator(word_list   = tokens, 
                                                line_width  = self.line_width, 
                                                text_lines  = self)
        for task in gen:
            gen.lines._consume(task) # Equivalent to self._consume(task)
    
    def _consume(self, fit_word): # A 'fit_word' is one not exceeding the line_width. TODO: raise Exception if not fit
        available = self.line_width - self.consumed
        if self.consumed > 0: # Not at start of line, so need to put a space
            candidate_to_place   = ' ' + fit_word
        else:
            candidate_to_place   = fit_word
        
        if available >= len(candidate_to_place):
            self.consumed += len(candidate_to_place)
            self.lines[self.current_line_idx] += candidate_to_place
        else:
            # Need to move to a new line
            self.lines.append('')
            self.current_line_idx += 1
            self.consumed       = 0
            self._consume(fit_word)
            
    def _split_for_fitness(self, word): 
        '''
        Returns a list of two strings, head and tail, where word = head + tail and head
        is the maximal size possible such that head is considered "fit"
        '''
        if len(word) <= self.line_width:
            return [word, '']
        else:
            return [word[0:self.line_width], word[self.line_width:len(word)]]
        
    class _WorkGenerator(): # A word may lead to "multiple works" if we have to split it
        '''
        Generator used to iterate through the "work". Normally a unit of "work" would be a word,
        but if the word is too long it would have to be split. Hence we use a special generator
        that produces a list of "fit words", i.e., words or portions thereof that are "fit"
        '''
        def __init__(self, word_list, line_width, text_lines):
            self.line_width = line_width
            self.word_list = word_list

            self.lines   = text_lines

        def __iter__(self):
            for word in self.word_list:
                unprocessed = word
                while len(unprocessed)>0:
                    head, unprocessed = self.lines._split_for_fitness(unprocessed)
                    yield head
            return
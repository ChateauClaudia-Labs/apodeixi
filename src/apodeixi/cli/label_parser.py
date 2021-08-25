
from apodeixi.util.dictionary_utils                     import DictionaryUtils

class LabelParser():
    '''
    Helper class to the CLI, to parse label commands. Examples of supported formats:

    apo get assertions -l knowledgeBase=production,journey=Modernization

    apo get assertions -l 'kind in (big-rock, milestone)'

    apo get assertions -l 'product notin (opus)'

    '''
    def __init__():
        return
    
    def parse(self, parent_trace, expression):
        '''
        Returns a filter function that acts on dict objects representing manifests and returns a boolean.
        That is, returns a function FUNC such that

            FUNC(parent_trace, manifest_dict)==True 
            
        if and only if all constraints in the expression for the manifest's labels are met.
        '''
        #@TODO For now we only support equality on a single field. All other expressions are not yet implemented

        def FUNC(filter_trace, manifest_dict):
            labels_dict             = DictionaryUtils().get_val(filter_trace, manifest_dict, root_dict_name="Manifest",
                                                            path_list=["metadata", "labels"], valid_types=[dict])
            if self.is_equality(filter_trace, expression):
                label, val = expression.split("=")
                if not label in labels_dict.keys() or labels_dict[label] != val:
                    return False
                else:
                    return True
            elif self.is

    def is_and(self, parent_trace, expression):
        '''
        Checks if expression is like "knowledgeBase=production,journey=Modernization"
        '''
        expression                  = expression.strip()
        tokens                      = expression.split(",")
        tokens                      = [t.strip() for t in tokens if len(t.strip()) > 0]
        if len(tokens) > 0:
            return True
        else:
            return False
    
    def is_clause(self, parent_trace, expression):
        '''
        '''
        if 

    def is_equality(self, parent_trace, expression):
        '''
        Checks if expression is like "journey=Modernization"
        '''
        if self.is_and(expression):
            return False
        expression                  = expression.strip()
        tokens                      = expression.split("=")
        tokens                      = [t.strip() for t in tokens if len(t.strip()) > 0]
        if len(tokens) == 2:
            return True
        else:
            return False

    def is_set(self, parent_trace, expression):
        '''
        Checks if expression is like "(big-rock, milestone)"
        '''
        expression                  = expression.strip()
        if len(expression) < 3:
            return False
        if expression[0] != "(" or expression[-1] != ")":
            return False
        
        return True

    def is_in(self, parent_trace, expression):
        '''
        Checks if expression is like "kind in (big-rock, milestone)"
        '''
        expression                  = expression.strip()
        tokens                      = expression.split(" in ")
        tokens                      = [t.strip() for t in tokens if len(t.strip()) > 0]
        if len(tokens) != 2:
            return False
        else:
            if self.is_set(parent_trace, tokens[2]):
                return True
            else:
                return False

    def is_notin(self, parent_trace, expression):
        '''
        Checks if expression is like "product notin (opus)"
        '''
        expression                  = expression.strip()
        tokens                      = expression.split(" notin ")
        tokens                      = [t.strip() for t in tokens if len(t.strip()) > 0]
        if len(tokens) != 2:
            return False
        else:
            if self.is_set(parent_trace, tokens[2]):
                return True
            else:
                return False
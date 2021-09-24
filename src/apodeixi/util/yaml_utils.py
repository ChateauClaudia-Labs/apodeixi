
import yaml                                 as _yaml
from io                                     import StringIO

from apodeixi.util.a6i_error                import ApodeixiError

class YAML_Utils():
    '''
    Utility class to robustly access YAML functionality, such as loading YAML files.
    Used to encapsulate Apodeixi from some noise that can happen if the yaml library is not invoked with the appropriate
    settings.
    '''
    def __init__(self):
        pass

    def load(self, parent_trace, path):
        '''
        Returns a dictionary, corresponding to the loaded representation of the YAML file in the given `path`
        '''
        try:
            with open(path, 'r', encoding="utf8") as file:
                loaded_dict             = _yaml.load(file, Loader=_yaml.FullLoader)
                return loaded_dict
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Found a problem loading YAML file",
                                 data = {"path":        str(path),
                                        "error":        str(ex)})

    def save(self, parent_trace, data_dict, path):
        '''
        '''
        # As documented in https://nbconvert.readthedocs.io/en/latest/execute_api.html
        #
        # May get an error like this unless we explicity use UTF8 encoding:
        #
        #   File "C:\Alex\CodeImages\technos\anaconda3\envs\ea-journeys-env\lib\encodings\cp1252.py", line 19, in encode
        #   return codecs.charmap_encode(input,self.errors,encoding_table)[0]
        #   UnicodeEncodeError: 'charmap' codec can't encode character '\u2610' in position 61874: character maps to <undefined>
        #
        # Happens in particular when trying to save a string representing a Jupyter notebook's execution, since for the same
        # reason above that string had to be written to a string using UTF8 encoding, so now if we save to a file we must use UTF8
        with open(path, 'w', encoding="utf8") as file:
            _yaml.dump(data_dict, file)

    def dict_to_yaml_string(self, parent_trace, data_dict):
        '''
        Returns a string representation of a YAML content that is equivalent to  the `data_dict`
        '''
        output_stream               = StringIO()
        _yaml.dump(data_dict, output_stream)
        result_yaml                 = output_stream.getvalue()
        return result_yaml

import yaml                                 as _yaml
from io                                     import StringIO
import warnings

from apodeixi.util.a6i_error                import ApodeixiError
from apodeixi.util.warning_utils            import WarningUtils

#YAML_LOADER                         = _yaml.FullLoader
#YAML_DUMPER                         = _yaml.SafeDumper

'''
This cache was added as part of Apodeixi performance improvements made in March 2022. It was found that early adopters encountered
a performance degradation in production, which seemed to become worse as time went by. Initial profiling suggested that the
Apodeixi function `isolation_kb_store.py:_getMatchingManifests` was making a call to load every YAML file in the system
as a way to find if manifests already exist matching a particular manifest handle. Thus, to load a single manifest we
were in effect loading the entire database of manifests. And this was being done multiple times, as many times as there
were manifests to load.
As an initial low-hanging fruit, this cache was introduced so that we only load (and therefore de-serialize) a manifest once.

The cache has paths as keys and dictionaries as values.
'''
_YAML_CACHE = {}

class YAML_Utils():
    '''
    Utility class to robustly access YAML functionality, such as loading YAML files.
    Used to encapsulate Apodeixi from some noise that can happen if the yaml library is not invoked with the appropriate
    settings.
    '''
    def __init__(self):
        pass

    def load(self, parent_trace, path, use_cache=True):
        '''
        Returns a dictionary, corresponding to the loaded representation of the YAML file in the given `path`
        '''
        if use_cache and path in _YAML_CACHE.keys():
            return _YAML_CACHE[path]

        try:
            with open(path, 'r', encoding="utf8") as file:
                # YAML invokes asyncio.base_events.py, that is noisy and issues spurious ResourceWarnings. So catch and suppress
                # such warnings. For other warnings, raise an ApodeixiError
                with warnings.catch_warnings(record=True) as w:
                    WarningUtils().turn_traceback_on(parent_trace, warnings_list=w)

                    loaded_dict             = _yaml.load(file, Loader=_yaml.FullLoader)
                    if use_cache:
                        _YAML_CACHE[path]       = loaded_dict

                    WarningUtils().handle_warnings(parent_trace, warning_list=w)
                    return loaded_dict
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Found a problem loading YAML file",
                                 data = {"path":        str(path),
                                        "error":        str(ex)})

    def save(self, parent_trace, data_dict, path, use_cache=True):
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

            # YAML invokes asyncio.base_events.py, that is noisy and issues spurious ResourceWarnings. So catch and suppress
            # such warnings. For other warnings, raise an ApodeixiError
            with warnings.catch_warnings(record=True) as w:
                WarningUtils().turn_traceback_on(parent_trace, warnings_list=w)

                _yaml.dump(data_dict, file) #, Dumper=YAML_DUMPER)
            
                if use_cache:
                    _YAML_CACHE[path] = data_dict
                WarningUtils().handle_warnings(parent_trace, warning_list=w)           

    def dict_to_yaml_string(self, parent_trace, data_dict):
        '''
        Returns a string representation of a YAML content that is equivalent to  the `data_dict`
        '''
        output_stream               = StringIO()
        _yaml.dump(data_dict, output_stream)
        result_yaml                 = output_stream.getvalue()
        return result_yaml


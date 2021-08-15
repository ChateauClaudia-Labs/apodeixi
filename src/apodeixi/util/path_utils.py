import os                                           as _os
from pathlib                                        import Path
import time                                         as _time

import traceback                                    as _traceback
from io                                             import StringIO

from apodeixi.util.a6i_error                        import ApodeixiError
from apodeixi.util.dictionary_utils                 import DictionaryUtils

class PathUtils():
    '''
    Class of helpers for path manipulation, in as platform-independent way as possible. Spirit is to support the intention
    of the most common inquiries around paths without forcing the user to do string manipulation on paths
    '''
    def __init__(self):
        return

    def is_leaf(self, parent_trace, path):
        '''
        Returns true if 'path` is the name of a file or folder (e.g., "my_file.txt") as opposed to a path
        with at least some parent directories, like "project/config/my_file.txt" would be.
        '''
        if type(path) != str:
            raise ApodeixiError(parent_trace, "The given path should be a string, but is not",
                                            data = {    "type(path)":       str(type(path)),
                                                        "str(path)":        str(path)})

        pair                = _os.path.split(path)
        if len(pair[0]) == 0:
            return True

        return False

    def is_parent(self, parent_trace, parent_dir, path):
        '''
        Returns true if `path` falls under the `parent_dir`, i.e., if there exists a `relative_path` (possibly empty) such
        that

        `parent_dir` + '/' + 'relative_path' 

        refers to the exact same filesystem object as `path`
        '''
        if type(path) != str:
            raise ApodeixiError(parent_trace, "The given path should be a string, but is not",
                                            data = {    "type(path)":       str(type(path)),
                                                        "str(path)":        str(path)})
        if type(parent_dir) != str:
            raise ApodeixiError(parent_trace, "The given parent_dir should be a string, but is not",
                                            data = {    "type(parent_dir)":     str(type(parent_dir)),
                                                        "str(parent_dir)":        str(parent_dir)})

        try:
            if _os.path.commonpath([parent_dir, path]) == _os.path.abspath(parent_dir):
                return True
        except ValueError as ex:
            return False
        
        return False

    def relativize(self, parent_trace, root_dir, full_path):
        '''
        Returns a list with two entries: [relative_path, filename] with the property that

        root_dir + '/' + relative_path + '/' + filename 

        refers to the exact same path as the input `full_path`.

        If `full_path` is a directory then the second element in the returned value (`filename`) is an empty string.

        If this decomposition is not possible, or if `full_path` does not really exist in the file system, it raises
        an ApodeixiError
        '''
        # Check if full_path is real
        if not _os.path.exists(full_path):
            raise ApodeixiError(parent_trace, "The given path does not point to a real file or directory",
                                                data = {'full_path':    str(full_path)})
        
        # Check that full_path lies under the root_dir
        if not self.is_parent(  parent_trace            = parent_trace,
                                parent_dir              = root_dir, 
                                path                    = full_path):
            raise ApodeixiError(parent_trace, "Can't relativize because full_path is not under root_dir",
                                                data = {'root_dir':     str(root_dir),
                                                        'full_path':    str(full_path)})

        relpath                 = _os.path.relpath(full_path, start=root_dir)
        if _os.path.isfile(full_path):
            pair                = _os.path.split(_os.path.relpath(full_path, start=root_dir))
        else:
            pair                = [relpath, '']

        return [pair[0], pair[1]]

    def tokenizePath(self, parent_trace, path):
        '''
        Helper method suggested in  https://stackoverflow.com/questions/3167154/how-to-split-a-dos-path-into-its-components-in-python.
        It tokenizes relative paths to make it easier to construct FilingCoordinates from them
        For example, given a relative path like

                \FY 22\LIQ\MTP

        it returns a list

                ['FY 22', 'LIQ', 'MTP']
        '''
        folders             = []
        SPURIOUS_FOLDERS    = ["\\", "/"] # This might be added in Windows by some _os / split manipulations. If so, ignore it
        LIMIT               = 1000 # Maximum path length to handle. As a precaution to avoid infinte loops
        idx                 = 0

        while idx < LIMIT: # This could have been "while True", but placed a limit out of caution
            path, folder = _os.path.split(path)

            if folder   != "": 
                folders.append(folder)
            elif path   != "":
                folders.append(path)
                break
            idx             += 1

        folders.reverse()
        if len(folders) > 0 and folders[0] in SPURIOUS_FOLDERS:
            folders         = folders[1:]
        return folders

    def create_path_if_needed(self, parent_trace, path):
        '''
        Helper method to create a directory if it does not alreay exist
        '''
        Path(path).mkdir(parents=True, exist_ok=True)

    def get_mask_lambda(self, parent_trace, a6i_config):
        '''
        Returns a mask function to hide the top levels of a path if the path refers to a file in an Apodeixi
        deployment, i.e., the deployment of Apodeixi code or of the knowledge base.

        A mask function takes a string argument and returns a string. 
        It is used in situations (such as in regression testing) when observability should not
        report the paths "as is", but with a mask. 
        
        For example, without a mask function regression tests might output text that displays paths like:
    

                'C:/Users/aleja/Documents/Code/chateauclaudia-labs/apodeixi/test-knowledge-base/envs/big_rocks_posting_ENV/excel-postings'

        By contrast, if the regression tests feeds that path to the "mask lambda" returned by this method, the
        regression thest gets instead a "masked path" that it can use to display in regression output in a way
        that makes the regression output be independent of the physical location for thee Apodeixi deployment
        In our example, that would become:

                '<MASKED>/envs/big_rocks_posting_ENV/excel-postings'
        '''
        KB_ROOT                             = a6i_config.get_KB_RootFolder(parent_trace)
        COLLAB_ROOT                         = a6i_config.get_ExternalCollaborationFolder(parent_trace)
        A6I_DB                              = _os.path.dirname(KB_ROOT)
        def _path_mask(path):
            '''
            '''
            if type(path) != str:
                return path
            elif self.is_parent(parent_trace, parent_dir=KB_ROOT, path=path):
                tokens                                          = path.split(KB_ROOT)
                masked_path                                     = '<KNOWLEDGE BASE ROOT>' + tokens[-1]
                return masked_path
            elif self.is_parent(parent_trace, parent_dir=COLLAB_ROOT, path=path):
                tokens                                          = path.split(COLLAB_ROOT)
                masked_path                                     = '<EXTERNAL COLLABORATION FOLDER>' + tokens[-1]
                return masked_path
            elif self.is_parent(parent_trace, parent_dir=A6I_DB, path=path):
                tokens                                          = path.split(A6I_DB)
                masked_path                                     = '<APODEIXI DATABASE>' + tokens[-1]
                return masked_path
            elif 'apodeixi' in path:
                tokens                                          = path.split('apodeixi')
                masked_path                                     = '<APODEIXI INSTALLATION>/apodeixi' + tokens[-1]
                return masked_path
            else:
                return path

        return _path_mask

class FileMetadata():
    '''
    Helper class to encapsulates properties about a file (notably, its filename) that should be 
    collected when building a FolderHierarchy

    @param filename A string, corresponding to the name of the file (without any parent directories)

    @param file_size An int, corresponding to the number of bytes that the file uses

    @param created_on A float, corresponding to the number of seconds from the start of the epoch
                (in most systems, January 1, 1970 00:00:00 UTC) to the moment the file was created. 
                May be set to None if the datum is not of interest.

    @param last_accessed_on A float, corresponding to the number of seconds from the start of the epoch
                (in most systems, January 1, 1970 00:00:00 UTC) to the moment the file was last accessed.
                May be set to None if the datum is not of interest.

    @param last_modified_on A float, corresponding to the number of seconds from the start of the epoch
                (in most systems, January 1, 1970 00:00:00 UTC) to the moment the file was last modified.
                May be set to None if the datum is not of interest.

    '''
    def __init__(self, filename, file_size, created_on, last_accessed_on, last_modified_on):
        self.filename               = filename
        self.file_size              = file_size
        self.created_on             = created_on
        self.last_accessed_on       = last_accessed_on
        self.last_modified_on       = last_modified_on

    def __str__(self):
        msg     = "\nSize (in bytes):  "   + str(self.file_size)
        if self.created_on != None:
            msg     += "\nCreated on:       "   + _time.asctime(_time.localtime(self.created_on))
        if self.last_modified_on != None:
            msg     += "\nLast modified on: "   + _time.asctime(_time.localtime(self.last_modified_on))
        if self.last_accessed_on != None:
            msg     += "\nLast accessed on: "   + _time.asctime(_time.localtime(self.last_accessed_on))
       
        msg += "\n"
        return msg

class FolderHierarchy():
    '''
    Class used to encapsulate a tree structure of folders, sub-folders and files under a root directory.

    An instance represents a (subset of) all the folders and files under a root directory, built out from
    know the root directory and an (optional) filter for the kind of files that are of interest.

    An instance can also be built from a pre-existing instance, by applying a filter, resulting in a 
    "subtree" of the original FolderHierarchy.

    Folders are represented as strings, and files as FileMetadata objects. 

    This constructor should not be called directly. It is only for internal use within this class.
    To create instances, use the class static build methods
    '''
    def __init__(self, hierarchy_dict):
        self.hierarchy_dict                 = hierarchy_dict

    def build(parent_trace, rootdir, filter=None, include_timestamps=True):
        '''
        Constructs and returns a new FolderHierarchy structure.

        @param rootdir A string, representing the root of the folder structure
        @param filter A function that takes a string as an argument and returns a boolean:

                            filter(object)

        where object is either the name of a file or the full path of a subdirectory in the
        of rootdir (i.e, object = rootdir/<something>)

        As we recurse through the descendent folders beneath `rootdir`, if the filter is not None
        then paths like rootdir/<something> will be included only if filter(rootdir/<something>) = True

        Likewise, a file called myFileName would only be included if filter(myFileName) = True 
        '''
        try:
            
            hierarchy_dict                      = {}
            parent_folder                       = _os.path.split(rootdir)[1]
            path_to_parent                      = _os.path.split(rootdir)[0]
            hierarchy_dict[parent_folder]       = {}
            for currentdir, dirs, files in _os.walk(rootdir):
                
                if filter != None and not filter(currentdir):
                    continue

                for a_file in files:
                    if filter == None or filter(a_file):
                        loop_trace              = parent_trace.doing("Adding file '" + a_file + "'")
                        relative_path           = PathUtils().relativize(loop_trace, path_to_parent, currentdir)
                        branch_tokens           = PathUtils().tokenizePath(loop_trace, relative_path[0] + "/" + a_file)
                        
                        full_path               = currentdir + "/" + a_file
                        if include_timestamps:
                            creation_time           = _os.path.getctime(full_path)
                            access_time             = _os.path.getatime(full_path)
                            modification_time       = _os.path.getmtime(full_path)
                        else:
                            creation_time           = None
                            access_time             = None
                            modification_time       = None
                        file_size               = _os.path.getsize(full_path)
                        file_meta               = FileMetadata(     filename                = a_file, 
                                                                    file_size               = file_size, 
                                                                    created_on              = creation_time, 
                                                                    last_accessed_on        = access_time, 
                                                                    last_modified_on        = modification_time)
                        inner_trace              = loop_trace.doing("Adding value to dict",
                                                            data = {"path_list": str(branch_tokens),
                                                                        "val": str(file_meta)},
                                                            origination = {'signaled_from': __file__})
                        DictionaryUtils().set_val(  parent_trace            = inner_trace, 
                                                    root_dict               = hierarchy_dict, 
                                                    root_dict_name          = parent_folder, 
                                                    path_list               = branch_tokens, 
                                                    val                     = file_meta)

        except ApodeixiError as ex:
            raise ex
        except Exception as ex:
            traceback_stream        = StringIO()
            trace_msg           = ""
            trace_msg           += "\n" + "-"*60 + '\tTechnical Stack Trace\n\n'
            _traceback.print_exc(file = traceback_stream)
            trace_msg           += traceback_stream.getvalue()
            trace_msg           += "\n" + "-"*60
            raise ApodeixiError(parent_trace, "Encountered error while building a FolderHierarchy",
                                                data = {"rootdir": str(rootdir), "exception": str(ex)})
                
        hierarchy                   = FolderHierarchy(hierarchy_dict)
        return hierarchy

    def to_dict(self):
        result_dict                 = {}
        for key in self.hierarchy_dict.keys():
            val = self.hierarchy_dict[key]
            if type(val)== dict:
                sub_hierarchy       = FolderHierarchy(val)
                new_val             = sub_hierarchy.to_dict()
            elif type(val) == list:
                new_val             = [self._elt_to_dict(elt) for elt in val]
            else:
                new_val             = str(val)
            result_dict[key]        = new_val

        return result_dict

    def _elt_to_dict(self, elt):
        '''
        Helper functions to handle elements of a list inside a FolderHierarchy
        '''
        if type(elt) == dict:
            sub_hierarchy       = FolderHierarchy(elt)
            return sub_hierarchy.to_dict()
        else:
            return str(elt)
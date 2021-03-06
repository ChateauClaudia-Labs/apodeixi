import os                                           as _os
import sys                                          as _sys
import shutil                                       as _shutil
from pathlib                                        import Path
import time                                         as _time
import re                                           as _re

import traceback                                    as _traceback
from io                                             import StringIO
from unittest.util import _MAX_LENGTH

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

    def checkPathExists(self, parent_trace, path):
        '''
        Raises an ApodeixiError if the given path does not exist. If it exists, this method does nothing.
        '''
        # Check if full_path is real
        if type(path) != str or not _os.path.exists(path):
            raise ApodeixiError(parent_trace, "The given path does not point to a real file or directory",
                                                data = {'path':    str(path)})

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

    def tokenizePath(self, parent_trace, path, absolute=True):
        '''
        Helper method suggested in  https://stackoverflow.com/questions/3167154/how-to-split-a-dos-path-into-its-components-in-python.
        It tokenizes relative paths to make it easier to construct FilingCoordinates from them
        For example, given a relative path like

                \FY 22\LIQ\MTP

        it returns a list

                ['FY 22', 'LIQ', 'MTP']

        @param absolute A boolean, which is true by default. If True, then the `path` is first expanded to an
                        absolute path, and the linux equivalent is returned. Otherwise, the `path` is treated as a
                        relative path and a linux equivalent relative path is returned.

        '''
        folders             = []
        SPURIOUS_FOLDERS    = ["\\", "/"] # This might be added in Windows by some _os / split manipulations. If so, ignore it
        LIMIT               = 1000 # Maximum path length to handle. As a precaution to avoid infinte loops
        idx                 = 0

        # Added in March, 2022 to support Linux in addition to Windows, especially in situations when the CI/CD pipeline
        # runs tests in a Linux container. In that case, to avoid regression and functional errors we must make sure
        # that `path` is Linux path, i.e., folders are delimted by '/' and not `\`, since otherwise the tokenization
        # will be wrong. For example, tokenizing
        #
        #                  /visions\ideas\problems/corrections
        #
        # would result in 
        #
        #                   		['visions\\ideas\\problems', 'corrections']
        # instead of
        #                           ['visions', 'ideas', 'problems', 'corrections']
        # 
        # unless we did this check
        #
        if _os.name != "nt":
            path = self.to_linux(path, absolute=absolute)

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
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Problem with creating directory",
                                                data = {"path":     str(path),
                                                        "error":    str(ex)})


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

        The mask is separately applied "line-by-line".
        '''
        TEST_DB_ROOT                                                = a6i_config.test_db_dir                                         
        KB_ROOT                                                     = a6i_config.get_KB_RootFolder(parent_trace)
        COLLAB_ROOT                                                 = a6i_config.get_ExternalCollaborationFolder(parent_trace)
        A6I_DB                                                      = _os.path.dirname(KB_ROOT)

        # In case we print the paths for Python modules (e.g., as in stack traces), we want to mask the location of
        # the module so that regression test output does not depend on where Python modules get installed.
        # For that we use this helper function to locate such substrings
        #
        def _match_sys_path(line):
            matches     = [(len(folder.strip()), folder) for folder in _sys.path if len(folder.strip()) > 0 and folder in line]
            if len(matches) > 0:
                max_length      = max([pair[0] for pair in matches])
                best_match      = [pair[1] for pair in matches if pair[0]==max_length][0]
                return best_match
            else:
                return None
                
        def _path_mask(raw_txt):
            '''
            '''
            if type(raw_txt) != str:
                return raw_txt
            lines                                                   = raw_txt.split("\n")
            cleaned_lines                                           = []
            LINE_NB_REGEX                                           = _re.compile(r'line [0-9]+')
            for line in lines:
                linux_line                                          = self.to_linux(line)
                if TEST_DB_ROOT != None and self.is_parent(parent_trace, parent_dir=TEST_DB_ROOT, path=line):
                    tokens                                          = linux_line.split(TEST_DB_ROOT)
                    masked_path                                     = '<TEST DB ROOT>' + tokens[-1]
                    cleaned_lines.append(masked_path)
                elif self.is_parent(parent_trace, parent_dir=KB_ROOT, path=line):
                    tokens                                          = linux_line.split(KB_ROOT)
                    masked_path                                     = '<KNOWLEDGE BASE ROOT>' + tokens[-1]
                    cleaned_lines.append(masked_path)
                elif self.is_parent(parent_trace, parent_dir=COLLAB_ROOT, path=line):
                    linux_line                                      = self.to_linux(line)
                    tokens                                          = linux_line.split(COLLAB_ROOT)
                    masked_path                                     = '<EXTERNAL COLLABORATION FOLDER>' + tokens[-1]
                    cleaned_lines.append(masked_path)
                elif self.is_parent(parent_trace, parent_dir=A6I_DB, path=line):
                    tokens                                          = linux_line.split(A6I_DB)
                    masked_path                                     = '<APODEIXI DATABASE>' + tokens[-1]
                    cleaned_lines.append(masked_path)
                elif 'apodeixi' in line:
                    tokens                                          = line.split('apodeixi')
                    masked_path                                     = '<APODEIXI INSTALLATION>/apodeixi' + tokens[-1]
                    cleaned_lines.append(masked_path)
                else:
                    module_path                                     = _match_sys_path(line)
                    if not module_path is None:
                        '''
                        masked_path                                 = _re.sub(module_path.replace("\\", "/"), 
                                                                                '<PYTHON MODULE>', 
                                                                                line)
                        '''
                        tokens                                      = line.split(module_path)
                        if len(tokens) > 1:
                            prefix                                  = tokens[0]
                        else:
                            prefix                                  = ""
                        masked_path                                 = prefix + '<PYTHON MODULE>' + tokens[-1]

                        # In case we are using a different minor version of Python, in a test run vs when regression test
                        # output was created, don't want line numbers to cause spurious regression test failures
                        masked_path                                 = _re.sub(LINE_NB_REGEX, 'line <HIDDEN>', masked_path)

                        cleaned_lines.append(masked_path)
                    else:
                        cleaned_lines.append(line)



            cleaned_txt                     = "\n".join(cleaned_lines)
            return cleaned_txt

        return _path_mask

    def to_linux(self, path, absolute=True):
        '''
        Takes a path that might be a Windows or Linux path, and returns a linux path

        @param path A string
        @param absolute A boolean, which is true by default. If True, then the `path` is first expanded to an
                        absolute path, and the linux equivalent is returned. Otherwise, the `path` is treated as a
                        relative path and a linux equivalent relative path is returned.
        '''
        if absolute:
            path            = _os.path.abspath(path)
        # The following line does not change the input if we are Linux, but will if we are Windows
        linux_path          = path.replace("\\", "/")
        return linux_path

    def copy_file(self, parent_trace, from_path, to_dir):
        try:
            _shutil.copy2(src = from_path, dst = to_dir)
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Got a problem copying a folder structure",
                                        data = {"source folder":        str(from_path),
                                                "destination folder":   str(to_dir),
                                                "error":                str(ex)})

    def remove_file_if_exists(self, parent_trace, path):
        '''
        Removes the file at the location `path`, and returns an integer status:

        * Returns 0 if the file was found and it was successfully removed
        * Returns -1 if there was not file at that path. For example, if it is a path to a directory
        '''
        try:
            if not _os.path.isfile(path):
                return -1
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Error checking if path provided is a file. Is it really a path?",
                                            data = {"path": str(path), "error": str(ex)})

        try:
            _os.remove(path)
            return 0
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Error attempting to remove file",
                                            data = {"path": str(path), "error": str(ex)})

    def remove_folder_if_exists(self, parent_trace, path):
        '''
        Removes the folder at the location `path`, and returns an integer status:

        * Returns 0 if the folder was found and it was successfully removed
        * Returns -1 if there was not folder at that path. For example, if it is a path to a file
        '''
        try:
            if not _os.path.isdir(path): 
                return -1
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Error checking if path provided is a folder. Is it really a path?",
                                            data = {"path": str(path), "error": str(ex)})
            
        try:
            # shutil.rmtree can behave oddly. It appears that in some computers it might refuse to remove
            # an empty directory ~10% of the time. While it has a flag called 'ignore_errors', setting it 
            # would not help us because we absolutely need to delete the directory - if we can't, we must
            # allow the exception to be propagated.
            # So as a workaround, we implement a limited number of re-tries, to reduce the probability 
            # of the spurious issue
            NUMBER_OF_RETRIES       = 10
            nb_attempts_left        = NUMBER_OF_RETRIES
            while nb_attempts_left > 0:
                try:
                    _shutil.rmtree(path) #, ignore_errors=True)
                except Exception as ex:
                    if "The directory is not empty" in str(ex) or "Access is denied" in str(ex):
                        nb_attempts_left    -= 1
                        continue
                    else:
                        raise ex
                break # If there was no exception, then delete was successful, so don't re-try (that would error out!)

            return 0
        except Exception as ex:
            raise ApodeixiError(parent_trace, "Error attempting to remove folder",
                                            data = {"path": str(path), "error": str(ex)})

class FileMetadata():
    '''
    Helper class to encapsulates properties about a file (notably, its filename) that should be 
    collected when building a FolderHierarchy

    @param filename A string, corresponding to the name of the file (without any parent directories)

    @param file_size An int, corresponding to the number of bytes that the file uses. 
                    GOTCHA: The number of bytes is computed in "Windows" style, not "Linux" style, even
                    if Apodeixi is running under Windows. That means that the number of bytes is computed
                    as if each line ended in "\r\n" (Windows convention) even if the file is a Linux
                    file with lines ending in just "\n". This is done for historical reasons to avoid breaking
                    regression tests, since regression output is created by developers (working in Windows)
                    but sometimes the test harness is run in Linux (e.g., as part of CI/CD pipelines)

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

            if include_timestamps:
                clean_parent_folder             = parent_folder
            else:
                # In this case, mask all consecutive 6-digit substrings, as they are likely to be timestamps.
                # Example:
                #       When the CLI runs, it creates environments with names like '210822.162717_sandbox'
                # (for the 22nd of August of 2021, at 4:27 pm and 17 seconds). The timestamps need to be masked
                # in regression test output so that it bcecomes deterministic.
                clean_parent_folder             = _re.sub(pattern="[0-9]{6}", repl="<MASKED>", string=parent_folder)
            hierarchy_dict[clean_parent_folder] = {}
            for currentdir, dirs, files in _os.walk(rootdir):
                
                if filter != None and not filter(currentdir):
                    continue

                for a_file in files:
                    if filter == None or filter(a_file):
                        loop_trace              = parent_trace.doing("Adding file '" + a_file + "'")
                        relative_path           = PathUtils().relativize(loop_trace, path_to_parent, currentdir)
                        branch_tokens           = PathUtils().tokenizePath(loop_trace, relative_path[0] + "/" + a_file,
                                                                            absolute = False)

                        # If we cleaned timestamps from parent folder, also clean them from the path to the file
                        # we are looking at
                        if len(branch_tokens) > 0 and branch_tokens[0] == parent_folder:
                            branch_tokens[0] = clean_parent_folder
                        
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

                        nb_lines                = FolderHierarchy._count_lines(full_path)

                        # If we are running in Linux and doing regression tests, then 
                        # we must "inflate" the size of the output file because Linux uses
                        # "\n" to end a line, whereas the expected file was created in Windows that adds an extra byte per line, 
                        # since Windows uses "\r\n" to end each line
                        #
                        # GOTCHA: it is possible that a file was not created by the test suite, but "copied" from some
                        #       input area under source control. Example: 
                        #
                        #        test_db/knowledge-base/envs/1501_ENV/kb/manifests/my-corp.production/kb/manifests/line-of-business.1.yaml
                        #
                        # In that case, even when using Linux, such a file would contains the extra "\r" character per line,
                        # since it was created by a developer in Windows, committed to source control, and the Linux test
                        # harness simply copied it.
                        # THEREFORE: we don't "inflate" the size for files that were not created by this test run.
                        #           We can tell that if the file was created more than (say) a minute ago
                        epoch_time              = int(_time.time())
                        if _os.name !="nt" and abs(epoch_time - _os.path.getmtime(full_path)) < 60:
                            file_size += nb_lines

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
                                                    root_dict_name          = clean_parent_folder, 
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
                                                data = {"rootdir": str(rootdir), "exception": str(ex),
                                                        "stack trace":  trace_msg})
                
        hierarchy                   = FolderHierarchy(hierarchy_dict)
        return hierarchy

    def _count_lines(full_path):
        '''
        Internal method used to quickly count number of lines in a file. Taken from one of the samples in 
        https://pynative.com/python-count-number-of-lines-in-file/
        '''
        def _count_generator(reader):
            b = reader(1024 * 1024)
            while b:
                yield b
                b = reader(1024 * 1024)

        with open(full_path, 'rb') as fp:
            c_generator = _count_generator(fp.raw.read)
            # count each \n
            count = sum(buffer.count(b'\n') for buffer in c_generator)
            return count

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
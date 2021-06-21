import os                                           as _os

from apodeixi.util.a6i_error                        import ApodeixiError

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

        pair                    = _os.path.split(_os.path.relpath(full_path, start=root_dir))

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


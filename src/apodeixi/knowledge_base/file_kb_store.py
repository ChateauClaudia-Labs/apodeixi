

from apodeixi.knowledge_base.knowledge_base_util        import PostingLabelHandle, FormRequest
from apodeixi.knowledge_base.filing_coordinates         import TBD_FilingCoordinates

from apodeixi.util.a6i_error                            import ApodeixiError
from apodeixi.util.path_utils                           import PathUtils

from apodeixi.xli.xlimporter                            import ExcelTableReader, PostingLabelXLReadConfig, ManifestXLReadConfig

'''
Abstract class

Represents the implementation of a KnowledgeBaseStore based on the File protocol, i.e., all URLs are paths in the
local file system.

Most KnowledgeBase functionality is implemented in derived classes, but some common methods are implemented in this
class for convenience.
'''
class File_KBStore_Impl():
    def __init__(self):
        return

    def buildPostingHandle(self, parent_trace, excel_posting_path, sheet, excel_range):
        '''
        Returns an PostingLabelHandle for the posting label embedded within the Excel spreadsheet that resides in 
        the path provided.
        '''
        kb_postings_url                     = self.getPostingsURL(parent_trace)
        if PathUtils().is_parent(           parent_trace                = parent_trace,
                                            parent_dir                  = kb_postings_url, 
                                            path                        = excel_posting_path):
            # See Note below in the else clause. This case is rare, even if at first glance it would seem like the
            # "normal" case.

            relative_path, filename         = PathUtils().relativize(   parent_trace    = parent_trace, 
                                                                        root_dir        = kb_postings_url,
                                                                        full_path       = excel_posting_path)

            posting_api                     = self._filename_2_api(parent_trace, filename)
                                   
            my_trace                        = parent_trace.doing("Building the filing coordinates",
                                                                    data = {"relative_path": str(relative_path)})
            filing_coords                   = self._buildFilingCoords(  parent_trace        = my_trace, 
                                                                        posting_api         = posting_api, 
                                                                        relative_path       = relative_path)
        else: # Posting wasn't submitted from the "right" folder, so coordinates will have be inferred later when label 
              # is read.
              # INTERESTING NOTE: This happens rather often if we are
              # in a transaction (normal case) because kb_postings_url is the current environment's URL, which
              # almost certainly is not a parent of excel_posting_path (the kb_postings_url would have tokens like
              # 'store-transation.4' that couldn't possibly be part of the excel_posting_path). 
            filename                        = PathUtils().tokenizePath(parent_trace, excel_posting_path)[-1]
            posting_api                     = self._filename_2_api(parent_trace, filename)

            env_config                      = self.current_environment(parent_trace).config(parent_trace)
            path_mask                       = env_config.path_mask            
            filing_coords                   = TBD_FilingCoordinates(fullpath            = excel_posting_path,
                                                                    posting_api         = posting_api,
                                                                    path_mask           = path_mask)

        # Now build the posting label handle
        posting_handle                  = PostingLabelHandle(       parent_trace        = parent_trace,
                                                                    posting_api         = posting_api,
                                                                    filing_coords       = filing_coords,
                                                                    excel_filename      = filename, 
                                                                    excel_sheet         = sheet, 
                                                                    excel_range         = excel_range)

        return posting_handle

    def getBlindFormRequest(self, parent_trace, relative_path, posting_api, namespace, subnamespace):
        '''
        Returns an FormRequest that can in turn be used to request a form (an Excel spreadsheet)
        that the end-user can use to make a posting for the create or update the manifests 
        in for the posting label embedded within the Excel spreadsheet that resides in 
        the path provided.

        The FormRequest returned is a "blind" form, in the sense that it does not specify the specific
        ManifestHandle objects that will populate the Excel template obtainable by submitting the FormRequest.
        The system will have to do a search within the KnowledgeBase store to find out which manifests, if any,
        already exist for the filing structure and posting API provided.
        If not exist the form will be creating them.
        If on the other hand such manifests already exist, then the Excel template will be generated as an
        update form that is pre-populated with those manifests' contents.

        @param relative_path: A string, representing the path below the end-user's collaboration area root 
                                (the store's clientURL) for which the form is requested. This determines the 
                                filing coordinates for the requested form.
                                Example: "journeys/Dec 2020/FusionOpus/Default"
        @param posting_api: A string, representing a posting API supported by the knowledge base.
                                Example: 'big-rocks.journeys.a6i'
        @param namespace A string, representing a namespace in the KnowledgeBase store's manifests are that
                        delimits the scope for searching for manfiests in scope of this FormRequest.
                        Example: "my-corp.production"
        @param subnamespace An optional string representing a slice of the namespace that further restricts
                        the manifest names to search. If set to None, not subspace is assumed.
                        Example: in the manifest name "modernization.default.dec-2020.fusionopus", the
                                token "modernization" is the subnamespace. The other tokens come from filing coordinates
                                for the posting from whence the manifest arose.
        '''
        my_trace            = parent_trace.doing("Building the filing coordinates",
                                                                data = {"relative_path": str(relative_path)})
        filing_coords       = self._buildFilingCoords(  parent_trace        = my_trace, 
                                                        posting_api         = posting_api, 
                                                        relative_path       = relative_path)

        my_trace            = parent_trace.doing("Building the form request")

        form_request        = FormRequest(  parent_trace            = my_trace, 
                                            posting_api             = posting_api, 
                                            filing_coords           = filing_coords,
                                            scope                   = FormRequest.SearchScope(namespace, subnamespace))


        return form_request

    def loadPostingLabel(self, parent_trace, posting_label_handle):
        '''
        Loads and returns a DataFrame based on the `posting_label_handle` provided
        '''
        excel_range             = posting_label_handle.excel_range

        excel_range             = excel_range.upper()
        path                    = self._getPostingFullPath(parent_trace, posting_label_handle)
        relative_path           = posting_label_handle.getRelativePath(parent_trace)
        sheet                   = posting_label_handle.excel_sheet
        label_xlr_config        = PostingLabelXLReadConfig()

        reader                  = ExcelTableReader( parent_trace        = parent_trace, 
                                                    excel_fullpath      = path, 
                                                    excel_sheet         = sheet,
                                                    excel_range         = excel_range, 
                                                    xlr_config          = label_xlr_config)
        my_trace                = parent_trace.doing("Loading Posting Label data from Excel into a DataFrame",
                                                data = {"relative_path": relative_path, "excel range": excel_range})
        label_df                = reader.read(my_trace)
        return label_df

    def loadPostingData(self, parent_trace, data_handle, config):
        '''
        Loads and returns a DataFrame based on the `posting_data_handle` provided

        @param config PostingConfig
        '''
        path                    = self._getPostingFullPath(parent_trace, data_handle)
        relative_path           = data_handle.getRelativePath(parent_trace)
        sheet                   = data_handle.excel_sheet
        excel_range             = data_handle.excel_range
        r                       = ExcelTableReader( parent_trace        = parent_trace, 
                                                    excel_fullpath      = path, 
                                                    excel_sheet         = sheet,
                                                    excel_range         = excel_range, 
                                                    xlr_config          = config)
        my_trace                = parent_trace.doing("Loading Excel posting data into a DataFrame",
                                                        data = {"relative_path": relative_path, "excel range": excel_range})
        df                      = r.read(my_trace)
        return df

    def _getPostingFullPath(self, parent_trace, posting_handle):
        '''
        It returns a string, corresponding to the full path to the posting referenced by the `posting_handle`.
        '''
        if type(posting_handle.filing_coords) == TBD_FilingCoordinates: # Filing Coords haven't been set yet, so use place holder
            return posting_handle.filing_coords.getFullPath()
        else:
            parsed_tokens               = posting_handle.filing_coords.path_tokens(parent_trace)
            kb_postings_url             = self.getPostingsURL(parent_trace)
            excel_path                  = kb_postings_url  +  '/' + '/'.join(parsed_tokens)
            return excel_path + "/" + posting_handle.excel_filename       

    def _filename_2_api(self, parent_trace, filename):
        '''
        Helper method that can be used by derived classes to infer the posting api from a filename.

        Returns a string: the posting api. Raises an ApodeixiError if none of the store's supported apis matches the filename.
        '''
        posting_api                                 = None
        supported_apis                              = self.supported_apis(parent_trace=parent_trace)
        for api in supported_apis:
            if filename.endswith(api + ".xlsx"):
                posting_api          = api
                break
        if posting_api == None:
            raise ApodeixiError(parent_trace, "Filename is not for an API supported by the Knowledge Base store",
                                            data    = {    'filename':             filename,
                                                            'supported apis':       str(supported_apis)})
        return posting_api

    def _buildFilingCoords(self, parent_trace, posting_api, relative_path):
        '''
        Helper method that concrete derived classes may choose to use as part of implementing `buildPostingHandle`,
        to determine the FilingCoordinates to put into the posting handle.
        '''
        path_tokens                     = PathUtils().tokenizePath( parent_trace    = parent_trace,
                                                                    path   = relative_path) 

        my_trace                        = parent_trace.doing("Looking up filing class for given posting API",
                                                                data = {'posting_api': posting_api})               
        filing_class                    = self.getFilingClass(parent_trace, posting_api)
        if filing_class == None:
            raise ApodeixiError(my_trace, "Can't build filing coordinates from a null filing class")
        my_trace                        = parent_trace.doing("Validating that posting is in the right folder structure "
                                                                + "within the Knowledge Base")
        filing_coords                   = filing_class().build(parent_trace = my_trace, path_tokens = path_tokens)
        if filing_coords == None:
            raise ApodeixiError(my_trace, "Posting is not in the right folder within the Knowledge Base for this kind of API",
                                            data = {'posting relative path tokens':         path_tokens,
                                                    'posting api':                          posting_api,
                                                    'relative path expected by api':        filing_coords.expected_tokens(my_trace)})
        return filing_coords

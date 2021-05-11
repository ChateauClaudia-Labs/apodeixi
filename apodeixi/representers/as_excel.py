import pandas                           as _pd
import xlsxwriter

from apodeixi.util.a6i_error            import ApodeixiError
from .as_dataframe                      import AsDataframe_Representer

class AsExcel_Representer:
    '''
    Class that can represent an Apodeixi manifest as an Excel spreadsheet
    '''
    def __init__(self):
        return

    def yaml_2_xl(self, parent_trace, manifests_folder, manifests_file, contents_path):
        df_rep              = AsDataframe_Representer()
        df, subtree         = df_rep.yaml_to_df(parent_trace, manifests_folder, manifests_file, contents_path)

        self._populate_content(df)

    def _populate_posting_label(self):
    def _populate_content(self, df):
        '''
        Helper method to write the block in Excel that comes from the manifest's content (as opposed to the Posting Label data)
        '''

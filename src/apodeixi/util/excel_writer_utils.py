from apodeixi.util.formatting_utils     import DictionaryFormatter

def nice_ws_info(parent_trace, worksheet_info):
    '''
    Helper method to create a "nice string" that can be outputted in a readable form (for example, in test outputs)

    param worksheet_info An instance of apodeixi.representers.as_excel.XL_WorksheetInfo that should be formatted as a string
    '''
    nice_format                     = ''
    nice_format += "\n======================== Column information =========================="
    nice_format += DictionaryFormatter().dict_2_nice(   parent_trace    = parent_trace,
                                                        a_dict          = worksheet_info.colinfo)

    fmt_dict                        = worksheet_info.format_dict
    for row_nb in fmt_dict.keys():
        row_dict                    = fmt_dict[row_nb]
        for col_nb in row_dict.keys():
            nice_format += "\n\n================ Formats row = " + str(row_nb) + ", col = " + str(col_nb) + " ============"
            cell_fmt_dict           = row_dict[col_nb]
            nice                    = DictionaryFormatter().dict_2_nice(    parent_trace    = parent_trace,
                                                                            a_dict          = cell_fmt_dict)
            nice_format += "\n" + nice
    return nice_format



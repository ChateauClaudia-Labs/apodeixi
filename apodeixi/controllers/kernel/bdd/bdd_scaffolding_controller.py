import yaml as _yaml
from io import StringIO

import apodeixi.xli as xli
from apodeixi.util.ApodeixiError    import *

def applyScaffolding(knowledge_base_dir, relative_path, excel_filename, excel_sheet, ctx_range):

    url                 = knowledge_base_dir + '/excel-postings/' + relative_path + '/' + excel_filename + ':' + excel_sheet


    manifest_file       = excel_filename.replace('xlsx', 'yaml')
    manifests_dir       = knowledge_base_dir + '/manifests/' + relative_path
    _genScaffoldingManifest(url, ctx_range, manifests_dir, manifest_file)

def _genScaffoldingManifest(url, ctx_range, manifests_dir, manifest_file):
    '''
    Helper function, amenable to unit testing, unlike the enveloping controller functions that require a knowledge base
    structure
    '''

    _DOMAIN             = "kernel"
    _PROJECT_TYPE       = "projectType"
    _PROJECT_NAME       = "projectName"
    _DATA_RANGE         = "dataRange"
    _ENVIRONMENT        = 'environment'
    _RECORDED_BY        = 'recordedBy'

    ctx                 = xli.PostingContext( mandatory_fields    = [_PROJECT_TYPE, _PROJECT_NAME, _ENVIRONMENT, _RECORDED_BY,_DATA_RANGE],
                                                    date_fields         = [])

    #url                 = knowledge_base_dir + '/excel-postings/' + relative_path + '/' + excel_filename + ':' + excel_sheet


    ctx.read(url, ctx_range)
    environment         = ctx.ctx[_ENVIRONMENT]
    project_type        = ctx.ctx[_PROJECT_TYPE]
    project_name        = ctx.ctx[_PROJECT_NAME]
    user                = ctx.ctx[_RECORDED_BY]
    excel_range         = ctx.ctx[_DATA_RANGE]

    manifest_dict       = {}

    # =====================

    r           = xli.ExcelTableReader(url        = url,
                                  excel_range = excel_range)
    df          = r.read()
    
    store           = xli.UID_Store()
    tree            = xli.BreakdownTree(uid_store = store, entity_type='Jobs to be done', parent_UID=None)
    interval_jobs          = xli.Interval(None, ['Jobs to be done', 'Stakeholders']) #cols[0:1]
    interval_capabilities  = xli.Interval(None, ['Capabilities']) #cols[2:3]
    interval_features      = xli.Interval(None, ['Feature']) #cols[3:4]
    interval_stories       = xli.Interval(None, ['Story']) #cols[4:]

    rows            = list(df.iterrows())
    intervals       = [interval_jobs, interval_capabilities, interval_features, interval_stories]
    root_trace      = FunctionalTrace(None).doing("Processing DataFrame", data={'tree.entity_type'  : tree.entity_type,
                                                                                'columns'           : list(df.columns)})
    update_policy   = xli.UpdatePolicy(reuse_uids=False, merge=False)
    for idx in range(len(rows)):
        for interval in intervals:
            my_trace        = root_trace.doing(activity="Processing fragment", data={'row': idx, 'interval': interval})
            tree.readDataframeFragment(interval=interval, row=rows[idx], parent_trace=my_trace, update_policy=update_policy)
    tree_dict       = tree.as_dicts()
    

    ###### ========================

    # Namespae would typically be something like 'Development' or 'Production'
    metadata      = {'namespace':   project_type + '.' + environment, 
                     'name':        project_name + '.scaffolding',
                     'labels': {'project': project_name, 'project-type': project_type}}

    manifest_dict['apiVersion']     = _DOMAIN + '.a6i.io/v1dev'
    manifest_dict['kind']           = 'ProjectScaffolding'
    manifest_dict['metadata']       = metadata


    #manifest_dict['scaffolding']   = tree_dict
    manifest_dict['scaffolding']   = {'recorded-by': user , 'jobs-to-be-done': tree_dict}
    
    #_yaml.dump(manifest_dict, _sys.stdout)
    #output = StringIO()
    #_yaml.dump(manifest_dict, output)
    
    with open(manifests_dir + '/' + manifest_file, 'w') as file:
        _yaml.dump(manifest_dict, file)

    return manifest_dict


















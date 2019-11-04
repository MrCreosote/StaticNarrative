import json
import os
import installed_clients.authclient as auth
from installed_clients.WorkspaceClient import Workspace
from installed_clients.authclient import KBaseAuth as _KBaseAuth
import html


def build_report_view_data(config, result):
    """
    Returns a structure like this:
    {
        links: []
        objects: [{
            'upa': '...',
            'name': 'foo',
            'type': '...',
            'description': '...'
        }]
        summary: '',
        report: ''
    }
    """
    if not result or not result[0].get('report_name') or not result[0].get('report_ref'):
        return {}
    report_ref = result[0].get('report_ref')
    ws = Workspace(url=config.narrative_session.ws_url, token=config.narrative_session.token)
    report = ws.get_objects2({'objects': [{'ref': report_ref}]})['data'][0]['data']
    """{'direct_html': None,
     'direct_html_link_index': None,
     'file_links': [],
     'html_links': [],
     'html_window_height': None,
     'objects_created': [{'description': 'Annotated genome', 'ref': '43666/6/1'}],
     'summary_window_height': None,
     'text_message': 'Genome saved to: wjriehl:narrative_1564507007662/some_genome\nNumber of genes predicted: 3895\nNumber of protein coding genes: 3895\nNumber of genes with non-hypothetical function: 2411\nNumber of genes with EC-number: 1413\nNumber of genes with Seed Subsystem Ontology: 1081\nAverage protein length: 864 aa.\n',
     'warnings': []}
    """
    created_objs = []
    if report.get('objects_created'):
        report_objs_created = report['objects_created']
        # make list to look up obj types with get_object_info3
        info_lookup = [{"ref": o["ref"]} for o in report_objs_created]
        infos = ws.get_object_info3({'objects': info_lookup})['infos']
        for idx, info in enumerate(infos):
            created_objs.append({
                'upa': report_objs_created[idx]['ref'],
                'description': report_objs_created[idx].get('description', ''),
                'name': info[1],
                'type': info[2].split('-')[0].split('.')[-1]
            })
    html = {}
    if report.get('direct_html'):
        html['direct'] = report.get('direct_html')

    if report.get('html_links'):
        idx = report.get('direct_html_link_index', 0)
        if idx < 0 or idx >= len(report['html_links']):
            idx = 0
        html['links'] = report['html_links']
        html['paths'] = []
        for idx, link in enumerate(html['links']):
            html['paths'].append(f'/api/v1/{report_ref}/$/{idx}/{link["name"]}')
        html['link_idx'] = idx

    return {
        'objects': created_objs,
        'summary': report.get('text_message', ''),
        'html': html
    }


def get_icon(config, metadata):
    """
    Should return a dict with keys "type" and "icon"
    if "type" = image, then "icon" second should be the src.
    if "type" = class, "icon" should be the full class to use to render the icon - "fa fa-right-arrow", for instance.
    also, if "type" == "class", then the keys "color" and "shape" should also be present.
    """
    meta_icon = metadata.get('attributes', {}).get('icon')
    icon = {
        'type': 'image',
        'icon': None
    }
    icon_type = 'image'
    if metadata.get('type') == 'data':
        icon['type'] = 'class'
        icon.update(get_data_icon(metadata.get('dataCell', {}).get('objectInfo', {}).get('typeName')))
    elif metadata.get('type') == 'output':
        icon['type'] = 'class'
        icon['icon'] = 'fa-arrow-right'
        icon['color'] = 'silver'
        icon['shape'] = 'square'
    elif metadata.get('type') == 'app':
        icon['type'] = 'image'
        icon['icon'] = config.narrative_session.nms_image_url + \
            metadata.get('appCell', {})['app']['spec']['info']['icon']['url']
    else:
        icon['type'] = 'class'
        icon['icon'] = 'fa-question-circle-o'
        icon['shape'] = 'square'
        icon['color'] = 'silver'
    return icon


def get_data_icon(obj_type):
    icon_json = os.path.join("/kb", "module", "data", "icons.json")
    with open(icon_json, 'r') as icon_file:
        icon_mapping = json.load(icon_file)
    icon_info = {
        'icon': icon_mapping['data']['DEFAULT'],
        'color': icon_mapping['colors'][0],
        'shape': 'circle'
    }
    if obj_type in icon_mapping['data']:
        icon_info['icon'] = " ".join(icon_mapping['data'][obj_type])
    if obj_type in icon_mapping['color_mapping']:
        icon_info['color'] = icon_mapping['color_mapping'][obj_type]
    return icon_info


def get_authors(config, wsid):
    ws = Workspace(url=config.narrative_session.ws_url, token=config.narrative_session.token)
    ws_info = ws.get_workspace_info({'id': wsid})
    author_id_list = [ws_info[2]]
    auth = _KBaseAuth(config.narrative_session.auth_url)
    disp_names = auth.get_display_names(config.narrative_session.token, author_id_list)
    author_list = []
    for author in author_id_list:
        author_list.append({
            'id': author,
            'name': html.escape(disp_names.get(author, author)),
            'path': config.narrative_session.profile_page_url + author
        })
    return author_list
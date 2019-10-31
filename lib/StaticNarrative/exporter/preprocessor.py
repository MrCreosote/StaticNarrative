"""
Narrative preprocessor for nbconvert exporting
"""
__author__ = 'Bill Riehl <wjriehl@lbl.gov>'

from nbconvert.preprocessors import Preprocessor
import os
from .processor_util import (
    build_report_view_data,
    get_icon,
    get_authors
)


class NarrativePreprocessor(Preprocessor):
    def __init__(self, config=None, **kw):
        super(NarrativePreprocessor, self).__init__(config=config, **kw)
        # self.c = config
        # # if env == "dev":
        # #     env = "ci"
        # # self.env = env
        self.host = self.config.narrative_session.host  #f'https://{self.env}.kbase.us'
        print(self.host)
        self.fonts_root = os.path.join(os.environ.get('NARRATIVE_DIR', '.'), 'kbase-extension', 'static', 'kbase', 'fonts')
        self.app_style_file = os.path.join(os.environ.get('NARRATIVE_DIR', '.'), 'src', 'biokbase', 'narrative', 'exporter', 'app_style.css')
        self.icon_style_file = os.path.join(os.environ.get('NARRATIVE_DIR', '.'), 'kbase-extension', 'static', 'kbase', 'css', 'kbaseIcons.css')

    def preprocess(self, nb, resources):
        (nb, resources) = super(NarrativePreprocessor, self).preprocess(nb, resources)

        # Get some more stuff to show in the page into resources
        if not 'kbase' in resources:
            resources['kbase'] = {}
        resources['kbase'].update({
            'title': nb['metadata']['name'],
            'host': self.host,
            'creator': nb['metadata']['creator'],
            'narrative_link': f"{self.host}/narrative/{nb['metadata']['wsid']}",
            'authors': get_authors(self.config, nb['metadata']['wsid'])
        })

        if not 'inlining' in resources:
            resources['inlining'] = {}
        if not 'css' in resources['inlining']:
            resources['inlining']['css'] = []
        with open(self.app_style_file, 'r') as css:
            resources['inlining']['css'].append(css.read())
        with open(self.icon_style_file, 'r') as icons:
            icons_file = icons.read()
            icons_file = icons_file.replace('url("../fonts', f'url("{self.fonts_root}')
            resources['inlining']['css'].append(icons_file)

        return nb, resources

    def preprocess_cell(self, cell, resources, index):
        if 'kbase' in cell.metadata:
            kb_meta = cell.metadata.get('kbase')
            kb_info = {
                'type': kb_meta.get('type'),
                'idx': index,
                'attributes': kb_meta.get('attributes', {}),
                'icon': get_icon(self.config, kb_meta)
            }
            if kb_info['type'] == 'app':
                kb_info.update(self._process_app_info(kb_info, kb_meta))
                kb_info['external_link'] = self.host + kb_info['app']['catalog_url']
            elif kb_info['type'] == 'data':
                kb_info['external_link'] = self.host + '/#dataview/' + kb_meta['dataCell']['objectInfo']['ref']
            cell.metadata['kbase'] = kb_info
        else:
            kb_info = {
                'type': 'nonkb'
            }
        if not 'kbase' in resources:
            resources['kbase'] = {}
        if not 'cells' in resources['kbase']:
            resources['kbase']['cells'] = {}
        resources['foo'] = 'bar'
        resources['kbase']['cells'][index] = cell.metadata.get('kbase')
        return cell, resources

    def _process_app_info(self, kb_info: dict, kb_meta: dict) -> dict:
        """
        Extracts the useful bits of the complicated metadata structure so that the Jinja
        templates don't look like spaghetti with stuff like
        'kbase.appCell.app.spec.info......'
        returns a dict with the updated info.
        """
        kb_info['app'] = {
            'title': kb_meta['attributes']['title'],
            'subtitle': kb_meta['attributes']['subtitle'],
            'version': kb_meta['appCell']['app']['version'],
            'id': kb_meta['appCell']['app']['id'],
            'tag': kb_meta['appCell']['app']['tag'],
            'catalog_url': kb_meta['attributes']['info']['url'],
        }
        kb_info['params'] = {
            'input': [],
            'output': [],
            'parameter': []
        }
        param_values = kb_meta['appCell']['params']
        spec_params = kb_meta['appCell']['app']['spec']['parameters']
        for p in spec_params:
            p['value'] = param_values.get(p['id'])
            p_type = p['ui_class']
            kb_info['params'][p_type].append(p)
        kb_info['output'] = {
            "widget": kb_meta['appCell']['exec'].get('outputWidgetInfo', {}),
            "result": kb_meta['appCell']['exec']['jobState'].get('result', []),
            "report": build_report_view_data(
                          self.config,
                          kb_meta['appCell']['exec']['jobState'].get('result', [])
                      )
        }
        kb_info['job'] = {
            'state': kb_meta['appCell']['exec']['jobState']['job_state']
        }
        return kb_info


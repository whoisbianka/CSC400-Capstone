from pathlib import Path
from html.parser import HTMLParser
import unittest
from jinja2 import Environment, FileSystemLoader

ROOT=Path(__file__).resolve().parents[1]
class Inputs(HTMLParser):
    def __init__(self,html):
        super().__init__();self.inputs=[];self.feed(html)
    def handle_starttag(self,tag,attrs):
        if tag=='input':self.inputs.append(dict(attrs))

class StateFilterTemplateTests(unittest.TestCase):
    def render(self,filters):
        env=Environment(loader=FileSystemLoader(ROOT/'degree_path/templates'))
        return Inputs(env.get_template('_state_filter.html').render(filters=filters)).inputs
    def test_saved_multiple_and_single_selections(self):
        for filters, expected in [({'states':['CT','NY']},{'CT','NY'}),({'state':'CA'},{'CA'}),({},set())]:
            inputs=self.render(filters)
            choices=[i for i in inputs if i.get('name')=='state']
            self.assertEqual({i['value'] for i in choices if 'checked' in i},expected)
            self.assertEqual(len(choices),59)
            self.assertEqual(len({i['value'] for i in choices}),59)
            self.assertNotIn('name',next(i for i in inputs if i.get('id')=='state-search'))
            self.assertNotIn('name',next(i for i in inputs if i.get('id')=='state-any'))
    def test_older_saved_code_is_preserved(self):
        inputs=self.render({'states':['ZZ']})
        self.assertTrue(any(i.get('value')=='ZZ' and 'checked' in i for i in inputs))

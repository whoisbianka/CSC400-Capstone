"""Offline search-card contracts; no Gemini calls or database connections."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import unittest
from urllib.parse import urlparse, parse_qs
from flask import Flask
from pydantic import ValidationError
from degree_path.evidence import evidence_list, merge_evidence
from degree_path.chat_schemas import ExploreSearch
from degree_path.chat_search import build_search_metadata, search_card
from degree_path.chat_service import interpret_message
from degree_path.saved_searches import search_url_values

class ChatSearchTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.db.get_chat_major_matches.return_value = [{'cipcode': 260101, 'name': 'Biology'}]
        self.app = Flask(__name__)
        self.app.add_url_rule('/explore', endpoint='web.explore', view_func=lambda: '')

    def test_valid_filters_survive_json_and_build_internal_url(self):
        metadata = build_search_metadata(ExploreSearch(majors=['Biology'], states=['MA','CT'],
            degree_levels=['bachelor'], school_size='medium', net_price_max=0), self.db)
        with self.app.test_request_context():
            card = search_card(json.loads(json.dumps(metadata)))
        query = parse_qs(urlparse(card['url']).query)
        self.assertEqual(query['majors'], ['260101'])
        self.assertEqual(query['state'], ['CT','MA'])
        self.assertEqual(query['degrees'], ['3'])
        self.assertEqual(query['school_size'], ['medium'])
        self.assertEqual(query['net_price_max'], ['0'])
        self.db.get_page_programs.assert_not_called()

    def test_multiple_matching_majors_are_included_and_invalid_states_rejected(self):
        self.db.get_chat_major_matches.return_value = [
            {'cipcode':1,'name':'Marine Biology'}, {'cipcode':2,'name':'General Biology'}]
        metadata = build_search_metadata(ExploreSearch(major_subjects=['Biology']), self.db)
        self.assertEqual(metadata['explore_search']['filters']['majors'], ['1','2'])
        self.db.get_chat_major_matches.return_value = []
        with self.assertRaisesRegex(ValueError, 'No catalog majors'):
            build_search_metadata(ExploreSearch(majors=['Unknown']), self.db)
        with self.assertRaises(ValueError):
            build_search_metadata(ExploreSearch(states=['ZZ']), self.db)
        for bad in ({'school_size':'huge'}, {'net_price_max':-1}, {'degree_levels':['doctorate']}):
            with self.assertRaises(ValidationError): ExploreSearch(**bad)

    def test_no_card_for_ordinary_or_old_messages(self):
        self.assertEqual(build_search_metadata(None, self.db), {})
        self.assertIsNone(search_card({}))
        self.assertIsNone(search_card(None))
        self.db.get_chat_major_matches.assert_not_called()

    def test_gemini_receives_latest_search_and_returns_new_intent(self):
        request = {'majors':['Biology'], 'states':['MA'], 'school_size':'small'}
        metadata = build_search_metadata(ExploreSearch(**request), self.db)
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(text=json.dumps({
            'reply':'Here is your search.', 'keyword_additions':[], 'keyword_removals':[],
            'major_mentions':[], 'search_requested':True, 'explore_search':{**request,'states':['MA','NY']}}))
        turn = interpret_message('Include New York.', [], [], [
            {'role':'assistant','content':'Here is your search.', 'metadata':metadata}],
            client=client, model='test')
        context = json.loads(client.models.generate_content.call_args.kwargs['contents'])
        self.assertEqual(context['latest_search']['states'], ['MA'])
        self.assertEqual(turn.explore_search.states, ['MA','NY'])

    def test_saved_size_restores_and_sql_filters_boundaries(self):
        self.assertEqual(search_url_values('programs', {'school_size':'small'})['school_size'],'small')
        source=(Path(__file__).resolve().parents[1]/'db_functions.py').read_text()
        tree=ast.parse(source)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_program_filters')
        scope={}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'db_functions.py','exec'),scope)
        for value in ('small','medium','large',None): scope['validate_program_filters']({'school_size':value})
        with self.assertRaises(ValueError): scope['validate_program_filters']({'school_size':'huge'})

    def test_guest_and_signed_route_save_and_reload_cards(self):
        from copy import deepcopy
        from flask import Blueprint, request, jsonify, abort, current_app
        from werkzeug.exceptions import HTTPException
        from degree_path.chat_schemas import AdvisorTurn
        from degree_path.chat_service import InvalidAdvisorResponse
        source = (Path(__file__).resolve().parents[1]/'degree_path/routes.py').read_text()
        nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
                 and n.name in ('api_chat', 'apply_guest_chat_turn')]
        for signed_in in (False, True):
            with self.subTest(signed_in=signed_in):
                app = Flask(__name__)
                app.config['TESTING'] = True
                app.add_url_rule('/explore', endpoint='web.explore', view_func=lambda: '')
                web = Blueprint('testchat', __name__)
                database = Mock()
                database.save_chat_turn.return_value = []
                database.save_guest_session.return_value = 2
                guest = {'state': {'messages': [], 'keywords': [], 'recommendations': []}, 'version': 1}
                state = {'messages': [], 'keywords': [], 'recommendations': []}
                database.get_chat_state.return_value = state
                turn = AdvisorTurn(reply='Explore these programs.', keyword_additions=[],
                    keyword_removals=[], major_mentions=[], explore_search=ExploreSearch(states=['MA'], school_size='small'))
                scope = dict(web=web, request=request, jsonify=jsonify, abort=abort,
                    current_app=current_app, HTTPException=HTTPException, InvalidAdvisorResponse=InvalidAdvisorResponse,
                    get_current_user=lambda: {'id':7} if signed_in else None,
                    db_functions=database, get_or_create_guest_session=lambda: ('guest-id', guest),
                    _chat_keyword_catalog=SimpleNamespace(get=lambda fetch: []), interpret_message=Mock(return_value=turn),
                    build_search_metadata=build_search_metadata, search_card=search_card, deepcopy=deepcopy, evidence_list=evidence_list, merge_evidence=merge_evidence)
                exec(compile(ast.Module(body=nodes,type_ignores=[]),'routes.py','exec'),scope)
                app.register_blueprint(web)
                client=app.test_client()
                response=client.post('/api/chat',json={'message':'Find small colleges in Massachusetts'})
                self.assertEqual(response.status_code,200)
                self.assertIn('school_size=small',response.json['search_card']['url'])
                if signed_in:
                    metadata=database.save_chat_turn.call_args.kwargs['metadata']
                    state['messages']=[{'role':'assistant','content':turn.reply,'metadata':metadata}]
                else:
                    guest['state']=database.save_guest_session.call_args.kwargs['state']
                restored=client.get('/api/chat')
                self.assertEqual(restored.status_code,200)
                self.assertEqual(restored.json['messages'][-1]['search_card'],response.json['search_card'])

    def test_math_expands_exact_and_related_majors_and_preserves_state(self):
        self.db.get_chat_major_matches.return_value = [
            {'cipcode':2701,'name':'Mathematics.'}, {'cipcode':2703,'name':'Applied Mathematics.'},
            {'cipcode':2705,'name':'Statistics.'}]
        metadata=build_search_metadata(ExploreSearch(majors=['Mathematics'],states=['CT']),self.db)
        filters=metadata['explore_search']['filters']
        self.assertEqual(filters['majors'],['2701','2703','2705'])
        self.assertEqual(filters['state'],['CT'])
        self.assertEqual(filters['major_filter'],'selected')
        specific=build_search_metadata(ExploreSearch(majors=['Applied Mathematics']),self.db)
        self.assertEqual(specific['explore_search']['filters']['majors'],['2703'])

    def test_broad_search_is_not_truncated_at_autocomplete_limit(self):
        self.db.get_chat_major_matches.return_value=[{'cipcode':i,'name':f'Science {i}'} for i in range(1,31)]
        result=build_search_metadata(ExploreSearch(major_subjects=['Science']),self.db)
        self.assertEqual(len(result['explore_search']['filters']['majors']),30)

    def test_search_filters_without_current_intent_do_not_produce_card(self):
        previous = build_search_metadata(ExploreSearch(states=['CT']),self.db)
        for requested in (False, None):
            payload={'reply':'You are welcome.', 'keyword_additions':[], 'keyword_removals':[],
                     'major_mentions':[], 'explore_search':{'states':['CT']}}
            if requested is not None:
                payload['search_requested']=requested
            client=Mock()
            client.models.generate_content.return_value=SimpleNamespace(text=json.dumps(payload))
            turn=interpret_message('Thanks',[],[],[
                {'role':'assistant','content':'Here is your search.', 'metadata':previous}],client=client,model='test')
            self.assertIsNone(turn.explore_search)
            self.assertEqual(build_search_metadata(turn.explore_search,self.db),{})

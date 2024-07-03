import json
import urllib.request

from collections import namedtuple
from difflib import SequenceMatcher
from typing import Tuple, List

from printer import get_styling

PROFILE = 'python_sandbox'
DECK = 'printer_test'
MODEL_NAME = 'Focus'


def _request(action, **params):
    return {'action': action, 'params': params, 'version': 6}


def invoke(action, **params):
    request_json = json.dumps(_request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765', request_json)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']


def startup():
    result = invoke('getProfiles')
    if PROFILE not in result:
        raise ValueError(f'{PROFILE} not found in getProfiles result')
    result = invoke('loadProfile', name=PROFILE)
    if not result:
        raise ValueError(f'unable to load {PROFILE}')

    return check_for_changes()


def check_for_changes():

    result = invoke('modelNames')
    if MODEL_NAME not in result:
        _create_model()
        return True, None

    changes = {}

    flag, template_changes = requires_template_changes()
    if flag:
        changes['templates'] = template_changes
    if requires_styling_changes():
        changes['css'] = 'Styling changes are required'

    if len(changes) != 0:
        return False, changes
    return True, None


class AnkiJsonEntry:
    def __init__(self, deck, question, answer, tags):
        self.deck = deck
        self.tags = tags
        self.question = question
        self.answer = answer

        self.q_ratio = 0
        self.ans_ratio = 0
        self.status = ''

    def is_valid(self):
        return self.status == 'can_add'

    def set_ratio(self, q_ratio, ans_ratio):
        self.q_ratio = q_ratio
        self.ans_ratio = ans_ratio

    def to_json(self):
        return {
            'deckName': self.deck,
            'modelName': MODEL_NAME,
            'fields': {
                'Question': self.question,
                'Answer': self.answer
            },
            'tags': self.convert_to_nested_tags()
        }

    def calculate_ratio(self):
        q_max, ans_max = 0, 0

        results = find_notes(self.deck, self.tags)
        if len(results) == 1:
            return q_max, ans_max

        results = invoke('notesInfo', notes=results)
        for res in results:
            q = res['fields']['Question']['value']
            matcher = SequenceMatcher(lambda x: x == ' ', self.question, q)
            q_ratio = matcher.ratio()

            ans_b = res['fields']['Answer']['value']
            matcher = SequenceMatcher(lambda x: x == ' ', self.answer, ans_b)
            ans_ratio = matcher.ratio()

            if q_ratio > self.q_ratio:
                q_max = q_ratio
            if ans_ratio > ans_max:
                ans_max = ans_ratio

        return q_max, ans_max

    def parse_can_add_response(self, response):
        if response['canAdd'] is True:
            self.status = 'can_add'
            self.set_ratio(*self.calculate_ratio())
        else:
            self.status = response['error']
            self.set_ratio(0, 0)

    def exceeds_threshold(self, t):
        if self.q_ratio > t or self.ans_ratio > t:
            return True
        return False

    def convert_to_nested_tags(self) -> List[str]:
        anki_tags = []
        for tag in self.tags:
            anki_tags.append(tag.replace('/', '::'))
        return anki_tags


def apply_changes(changes: dict):
    if 'templates' in changes:
        templates = changes['templates']

        for new_template in templates['add']:
            invoke('modelTemplateAdd', modelName=MODEL_NAME, template=new_template)

        if len(templates['update']) > 0:
            modify = {
                'name': MODEL_NAME,
                'templates': { k: v for k, v in templates['update'] }
            }
            invoke('updateModelTemplates', model=modify)
    if 'css' in changes:
        modify = {
            'name': MODEL_NAME,
            'css': get_styling()
        }
        invoke('updateModelStyling', model=modify)


def requires_template_changes():
    templates = _get_templates()

    changes = {
        'add': [],
        'update': []
    }

    result = invoke('modelTemplates', modelName=MODEL_NAME)
    for name in result:
        if name not in templates:
            new_template = {
                'Name': name,
                'Front': templates[name]['Front'],
                'Back': templates[name]['Back']
            }
            changes['add'].append(new_template)
        else:
            if result[name]['Front'] != templates[name]['Front'] or result[name]['Back'] != templates[name]['Back']:
                changes['update'].append((name, templates[name]))

    requires_changes = len(changes['add']) > 0 or len(changes['update']) > 0
    return requires_changes, changes


def requires_styling_changes():
    result = invoke('modelStyling', modelName=MODEL_NAME)
    if result['css'] != get_styling():
        return True
    return False


def match_with_anki(note: AnkiJsonEntry) -> Tuple[float, float]:
    q_max = 0
    ans_max = 0

    results = find_notes(note.deck, note.tags)
    if len(results) == 0:
        return q_max, ans_max

    results = invoke('notesInfo', notes=results)
    for res in results:
        qa = note.question
        qb = res['fields']['Question']['value']
        matcher = SequenceMatcher(lambda x: x == ' ', qa, qb)
        q_ratio = matcher.ratio()

        ans_a = note.answer
        ans_b = res['fields']['Answer']['value']
        matcher = SequenceMatcher(lambda x: x == ' ', ans_a, ans_b)
        ans_ratio = matcher.ratio()

        if q_ratio > q_max:
            q_max = q_ratio
        if ans_ratio > ans_max:
            ans_max = ans_ratio

    return q_max, ans_max


def find_notes(deck, tags):
    if deck not in invoke('deckNames'):
        return []
    if tags not in invoke('getTags'):
        return []

    q = f'deck:{deck} and tag:{tags}'
    return invoke('findNotes', query=q)


def _create_model():
    invoke(
        'createModel',
        modelName=MODEL_NAME,
        inOrderFields=['Question', 'Answer'],
        css=get_styling(),
        isCloze=False,
        cardTemplates=_get_templates(inline=True)
    )


def _get_templates(inline=False):
    templates = {
        'Focus Card 1': {
            'Front': '{{Question}}',
            'Back': '{{Answer}}'
        }
    }
    if inline:
        new_templates = []
        for key in templates:
            new_templates.append({'Name': key, 'Front': templates[key]['Front'], 'Back': templates[key]['Back']})
        templates = new_templates
    return templates

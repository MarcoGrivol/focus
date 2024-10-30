import json
import urllib.request

from difflib import SequenceMatcher
from typing import Tuple, List

# focus imports
import settings

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
    if settings.PROFILE not in result:
        raise ValueError(f'"{settings.PROFILE}" not found in getProfiles result={result}')
    result = invoke('loadProfile', name=settings.PROFILE)
    if not result:
        raise ValueError(f'unable to load {settings.PROFILE}')

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


class AnkiNote:
    def __init__(self, deck: str, question: str, answer: str, tags: List[str]):
        if not isinstance(deck, str):
            raise TypeError('deck must be a string')
        if not isinstance(tags, list):
            raise TypeError('tags must be a list')

        self.deck = deck
        self.tags = tags
        self.question = question
        self.answer = answer

        self.q_ratio = 0
        self.ans_ratio = 0
        self.status = ''
        self.duplicate_id = None

    def is_valid(self):
        return self.status == 'can_add'

    def to_json(self, is_update=False):
        if is_update:
            if self.duplicate_id is None:
                raise ValueError(f'cannot edit note without duplicated_id')
            return {
                'id': self.duplicate_id,
                'fields': {
                    'Question': self.question,
                    'Answer': self.answer,
                }
            }

        else:
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
        q_max, ans_max, dup_id = 0, 0, None

        results = find_notes(self.deck, self.convert_to_nested_tags())
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

            if q_ratio > q_max and ans_ratio > ans_max:
                q_max = q_ratio
                ans_max = ans_ratio
                dup_id = res['noteId']
            elif q_ratio > q_max:
                q_max = q_ratio
            elif ans_ratio > ans_max:
                ans_max = ans_ratio

        self.q_ratio = q_max
        self.ans_ratio = ans_max
        self.duplicate_id = dup_id

    def parse_can_add_response(self, response):
        if response['canAdd'] is True:
            self.status = 'can_add'
        else:
            self.status = response['error']
            self.calculate_ratio()

    def convert_to_nested_tags(self) -> List[str]:
        anki_tags = []
        for tag in self.tags:
            anki_tags.append(tag.replace('/', '::'))
        return anki_tags

    def max_t(self):
        return max(self.q_ratio, self.ans_ratio)

    def min_t(self):
        return min(self.q_ratio, self.ans_ratio)

    def can_edit(self, t):
        if self.duplicate_id is None:
            return False
        if self.max_t() == self.min_t() == 1:
            return False
        if self.max_t() == 1 and self.min_t() != 1:
            return True
        if t <= self.q_ratio < 1 or t <= self.ans_ratio < 1:
            return True
        return False


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
            'css': settings.STYLES.to_string()
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
    if result['css'] != settings.STYLES.to_string():
        return True
    return False


def match_with_anki(note: AnkiNote) -> Tuple[float, float]:
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
    q = f'deck:{deck}'
    for tag in tags:
        q += f' and tag:{tag}'
    return invoke('findNotes', query=q)


def _create_model():
    invoke(
        'createModel',
        modelName=MODEL_NAME,
        inOrderFields=['Question', 'Answer'],
        css=settings.STYLES.to_string(),
        isCloze=False,
        cardTemplates=_get_templates(inline=True)
    )


def _get_templates(inline=False):
    templates = {
        'Focus Card 1': {
            'Front': '{{Question}}',
            'Back': '{{Question}}\n<hr>\n{{Answer}}'
        }
    }
    if inline:
        new_templates = []
        for key in templates:
            new_templates.append({'Name': key, 'Front': templates[key]['Front'], 'Back': templates[key]['Back']})
        templates = new_templates
    return templates

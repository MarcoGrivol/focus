import json
import urllib.request

from collections import namedtuple

PROFILE = 'python_sandbox'
DECK = 'printer_test'
MODEL_NAME = 'Focus'

Style = namedtuple('Style', ['name', 'css'])

CSS_CARD = Style('card', '.card {'
                                ' font-family: arial;'
                                ' font-size: 20px;'
                                ' text-align: left;'
                                ' color: black;'
                                ' background-color: white;'
                            '}'
)
CSS_WIKILINK = Style('wikilink', '.wikilink { color: rgb(0, 85, 255); }')
CSS_HIGHLIGHT = Style('highlight', '.highlight { background-color: rgb(255, 255, 0); }')


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


def _get_styling():
    styling = CSS_CARD.css + '\n'
    styling += CSS_WIKILINK.css + '\n'
    styling += CSS_HIGHLIGHT.css + '\n'
    return styling


def _create_model():
    invoke(
        'createModel',
        modelName=MODEL_NAME,
        inOrderFields=['Question', 'Answer'],
        css=_get_styling(),
        isCloze=False,
        cardTemplates=[
            {
                'Name': 'Focus Card 1',
                'Front': '{{Question}}',
                'Back': '{{Answer}}'
            }
        ]
    )


def startup():
    result = invoke('getProfiles')
    if PROFILE not in result:
        raise ValueError(f'{PROFILE} not found in getProfiles result')
    result = invoke('loadProfile', name=PROFILE)
    if not result:
        raise ValueError(f'unable to load {PROFILE}')

    result = invoke('modelNames')
    if MODEL_NAME not in result:
        _create_model()


def convert_to_note(deck, question, answer, tags):
    if not isinstance(tags, list):
        tags = [tags]

    return {
        'deckName': deck,
        'modelName': MODEL_NAME,
        'fields': {
            'Question': question,
            'Answer': answer
        },
        'tags': tags
    }

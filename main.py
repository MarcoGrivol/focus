import json
import json
import urllib.request

from crawler import vault_crawler
from printer import convert_to_note


def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}


def invoke(action, **params):
    request_json = json.dumps(request(action, **params)).encode('utf-8')
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


def _main():
    vault = 'C:\\mine\\vaults\\projeto_medicina'

    invoke('loadProfile', name='python_sandbox')
    deck_names = invoke('deckNames')

    obsidian_notes = vault_crawler(vault)

    notes = list()
    for obn in obsidian_notes:
        if obn.deck not in deck_names:
            invoke('createDeck', deck=obn.deck)
        notes.append(convert_to_note(obn))

    valid_notes, invalid_notes = list(), list()
    for i, result in enumerate(invoke('canAddNotesWithErrorDetail', notes=notes)):
        if result['canAdd'] is True:
            valid_notes.append(notes[i])
        else:
            invalid_notes.append(notes[i])

    for result in invoke('addNotes', notes=valid_notes):
        print(result)



if __name__ == '__main__':
    _main()

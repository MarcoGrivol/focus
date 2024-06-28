import json
import urllib.request
import os

from datetime import datetime
from os import path

from crawler import vault_crawler
from anki_handler import invoke, startup, convert_to_note


def _test_printer():
    from printer import convert_to_html

    with open('C:\\mine\\vaults\\journey\\Obsidian markdown.md', 'r', encoding='utf-8') as f:
        data = f.read()

    deck = 'printer_deck'
    tag = 'dummy_tag'
    data = convert_to_html(data)

    startup()

    note = convert_to_note(deck, data, 'dummy response', tag)
    note['options'] = {
        'allowDuplicates': True
    }

    invoke('addNote', note=note)


# def _main():
#     now = datetime.now()
#     out_dir = path.join(os.getcwd(), now.strftime('%Y_%m_%d'))
#     vault = 'C:\\mine\\vaults\\projeto_medicina'
#
#     invoke('loadProfile', name='python_sandbox')
#     deck_names = invoke('deckNames')
#
#     obsidian_notes = vault_crawler(vault)
#
#     notes = list()
#     for obn in obsidian_notes:
#         if obn.deck not in deck_names:
#             invoke('createDeck', deck=obn.deck)
#         notes.append(convert_to_note(obn))
#
#     valid_notes, invalid_notes = list(), list()
#     for i, result in enumerate(invoke('canAddNotesWithErrorDetail', notes=notes)):
#         if result['canAdd'] is True:
#             valid_notes.append(notes[i])
#         else:
#             invalid_notes.append({'reason': result, 'note': notes[i]})
#
#     if not path.isdir(out_dir):
#         os.mkdir(out_dir)
#
#     out_data = {
#         'addedCards': invoke('cardsInfo', cards=invoke('addNotes', notes=valid_notes)),
#         'invalidCards': invalid_notes
#     }
#     out_file = path.join(out_dir, f'results_{now.strftime("%H_%M_%S")}.json')
#
#     with open(out_file, 'w', encoding='utf-8') as f:
#         json.dump(out_data, f, indent=4)


if __name__ == '__main__':
    # _main()
    _test_printer()

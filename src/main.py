import json
import urllib.request
import os

from datetime import datetime
from os import path
from typing import List

import display
from crawler import VaultCrawler
from printer import note_to_html
from anki_handler import convert_to_note, invoke, startup


def _main(vault):
    vc = VaultCrawler(vault)
    vc.convert_files()

    _validate_crawler_results(vc)

    notes = []
    for md_note in vc.valid_notes:
        front, back = note_to_html(list(md_note.get_fields()))
        note = convert_to_note(md_note.deck, front, back, md_note.tag)
        notes.append(note)

    result = _validate_generated_noted(notes)


def _validate_crawler_results(vc: VaultCrawler):
    if len(vc.invalid_notes) == 0:
        return

    print(f'Found {len(vc.invalid_notes)} invalid notes:')

    for i, note in enumerate(vc.invalid_notes):
        print(f'\t ({i+1}): {note.filepath}')
        print(f'\t\t reason: {note.get_invalid_reason()}')

    result = input('Would you like to proceed? (y/n)\n')
    if result.lower() != 'y':
        exit(0)


def _validate_generated_noted(notes: List[dict]) -> List[bool | str]:
    result = invoke('canAddNotesWithErrorDetail', notes=notes)

    can_add = []
    contains_invalid = False

    for i, res in enumerate(result):
        if res['canAdd'] is True:
            can_add.append(True)
        else:
            can_add.append(res['error'])
            contains_invalid = True

    if contains_invalid:
        print('\nNot all notes can be added. Options:')
        print('\t 1. Continue with valid notes only')
        print('\t 2. List invalid notes')
        print('\t 3. Exit')
        res = int(input('What would you like to do? (1, 2 or 3)\n'))

        if res == 1:
            pass
        elif res == 2:
            print(f'Listing invalid notes:')
            for i, (res, note) in enumerate(zip(can_add, notes)):
                if res is True:
                    continue
                print(f'\t({i}): note="{notes[i][:64]}"...')
                print(f'\t\t reason: {res}')
            print('\nOptions:')
            print('\t 1. Continue with valid notes only')
            print('\t 2. Exit')
            res = int(input('What would you like to do? (1 or 2)\n'))
            if res == 2:
                exit(0)
        else:
            exit(0)

    return can_add


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

def _test_display(vault):
    crawler = VaultCrawler(vault)
    display.focus(crawler)


if __name__ == '__main__':
    # _main('C:\\mine\\vaults\\projeto_medicina')
    # _test_printer()
    _test_display('C:\\mine\\vaults\\projeto_medicina')

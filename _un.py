import os
import re
import sqlite3
import genanki

from os import path


class Notes:
    def __init__(self, db):
        conn = sqlite3.connect(db)
        c = conn.execute('SELECT id, guid, flds, tags FROM notes ORDER BY id')

        self.notes = list()

        for i, (r_id, r_guid, r_flds, r_tags) in enumerate(c):
            self.notes.append((r_id, r_guid, r_flds, r_tags))


def _main():
    # db = 'C:\\mine\\Journey'
    db = path.join(os.getcwd(), 'collection.sqlite')

    conn = sqlite3.connect(db)

    from prettytable import PrettyTable

    c = conn.execute('select * from notes')
    print('Headers:', [description[0] for description in c.description])

    target_id = 1714051840005
    note = None
    for row in c.execute("SELECT id, guid, flds, tags FROM notes ORDER BY id"):
        if row[0] == target_id:
            note = row

    if note is None:
        exit()

    print('Note:', note)

    print(f'\nFields:')
    fields = note[2].split('\x1f')
    for i, f in enumerate(fields):
        print('\t', i, f)

    fields[0] = fields[0] + ' !MODIFIED SECTION! '

    print(f'\nTags: {note[3]}')

    mod_note = genanki.Note(
        genanki.BASIC_MODEL,
        fields=fields,
        guid=note[1],
        tags=note[3].strip()
    )

    deck = genanki.Deck(2059400110, 'Portugues')
    deck.add_note(mod_note)

    genanki.Package(deck).write_to_file(
        path.join(os.getcwd(), 'test.apkg')
    )



if __name__ == '__main__':
    _main()

import os
import re
import logging

from os import path
from collections import namedtuple
from typing import AnyStr, LiteralString, List, Tuple, Dict

QUESTIONS_HEADING_TOKEN = 'Anki Cards'
ANS_ALIAS_TOKEN = 'ans'
# #[...] [...]ANYTHING[spaces]\n
# Group: (1)=hashtags, (2)=heading text
RE_HEADING = re.compile(r'(#+?) +(.+?) *\n')
# Target: #anki/DECK/TAG[/SUB_TAGS]
# Group: DECK e TAG[/SUB_TAGS], used to determine the Anki deck and Note tags
RE_ANKI_TAG = re.compile(r'(#anki)/(\S+?)/(\S.+)')
# Target: NUMBER. QUESTION TEXT
# Group: returns the text of the question
RE_NOTE_BODY = re.compile(r'(?:^|\n\s*)\d+\. +(.+)')  # re.compile(r'(?<=\n)\s*\d+\. +(.+)')
# Targe: QUESTION .|? [[text[#op]|ans]]
# Groups: (1)=question, (2)=link
RE_NOTE_ENTRY = re.compile(r'(.+?(?:[.?]|$))\s*(?:\[\[(.+\|' + ANS_ALIAS_TOKEN + r')]])*')
# Target: [[ANY TEXT BETWEEN TWO BRACKETS]]
# Group: text in between, may contain the optional #heading link or |link renaming tokens
RE_LINKS = re.compile(r'\[\[(.+?)]]')


ObsidianLink = namedtuple('ObsidianLink', ['path', 'name', 'heading', 'alias'])


def parse_link(link: str) -> ObsidianLink:
    # file[#heading][|rename]
    s = link.split('|')  # file[#heading], [|rename]
    alias = s[1] if len(s) == 2 else ''

    s = s[0].split('#')  # file, [#heading]
    heading = s[1] if len(s) == 2 else ''

    link_path = s[0] + '.md'
    name = path.basename(s[0])

    return ObsidianLink(link_path, name, heading, alias)


def _re_heading(heading):
    return re.compile(r'(#+?) +' + heading + r' *\n')


def _find_heading(data: str, heading: str, mode=None) -> str:
    """
    Find all the text encapsulating a heading, not the heading itself.
    :param data: file contents.
    :param heading: the name of the heading, excluding the '#' and any leading or trailing whitespace.
    :param mode: None exits on first heading, 'forw' reads forwards until end of file, 'curr' reads until higher
    or same level heading.
    """
    if mode not in (None, 'forw', 'curr'):
        raise ValueError(f'Invalid mode: {mode}')

    heads = _re_heading(heading).split(data, maxsplit=1)
    # heads[0] = text before
    # heads[1] = any number of #
    # heads[2] = text after heading
    if len(heads) == 1:
        return ''  # heading is not present in text

    if mode == 'forw':
        text = heads[2]

    else:
        heading_level = len(heads[1])
        text = ''
        for i, s in enumerate(RE_HEADING.split(heads[2])):
            if s == '#' * len(s):  # only hashtags
                if mode is None:
                    break
                elif len(s) <= heading_level:  # mode is 'curr'
                    break
            text += s

    return text.removeprefix(heading).strip('---').strip()


def _navigate(vault: str, link: ObsidianLink, heading_mode=None):
    filepath = path.join(vault, link.path)
    if not path.isfile(filepath):
        return ''

    with open(filepath, 'r', encoding='utf-8') as f:
        data = f.read()

    if link.heading:
        return _find_heading(data, link.heading, heading_mode)

    return data.strip()


class ObsidianNote:
    def __init__(self, questions: List[str], answers: List[str], deck: str, tag: str):
        self.questions = questions
        self.answers = answers
        self.deck = deck
        self.tag = tag

    def __len__(self):
        if self.questions is None:
            return 0
        return len(self.questions)


def vault_crawler(vault: str) -> List[ObsidianNote]:
    notes = list()
    for root, dirs, files in os.walk(vault):
        for f_name in files:

            f_path = path.join(root, f_name)
            if not f_name.endswith('.md'):
                continue

            notes_in_file = _convert_to_note(vault, f_path)

            if notes_in_file is None:
                continue

            for note in notes_in_file:
                if len(note) == 0:
                    continue
                notes.append(note)

    return notes


def _convert_to_note(vault, filepath) -> List[ObsidianNote]:
    from_path = filepath.strip(vault)  # how other files link to filepath

    with open(filepath, 'r', encoding='utf-8') as f:
        data = f.read()

    anki_tag = RE_ANKI_TAG.search(data)
    if anki_tag is None:
        return None

    deck = anki_tag.group(2)
    tag = anki_tag.group(3)

    anki_body = _find_heading(data, QUESTIONS_HEADING_TOKEN)
    notes = list()

    for note in RE_NOTE_BODY.findall(anki_body):
        questions, answers = list(), list()
        for note_fields in RE_NOTE_ENTRY.findall(note):
            q, ans = _parse_note_entry(vault, from_path, data, note_fields)
            if q == '' or ans == '':
                questions = answers = None
                break
            questions.append(q)
            answers.append(ans)
        notes.append(ObsidianNote(questions, answers, deck, tag))

    return notes


def _parse_note_entry(vault, from_path, data, note_entry) -> Tuple[str, str]:
    def _goto():
        if link.path == from_path:
            return _find_heading(data, link.heading, heading_mode)
        return _navigate(vault, link, heading_mode)

    question, answer = note_entry
    heading_mode = None

    if answer:
        link = parse_link(answer)
        if link.heading and link.alias.startswith(f'{ANS_ALIAS_TOKEN}_'):
            heading_mode = link.alias.removeprefix(f'{ANS_ALIAS_TOKEN}_')
        return question, _goto()

    links = RE_LINKS.findall(question)
    if len(links) != 1:
        return '', ''

    link = parse_link(links[0])
    return question, _goto()


def _main():
    db = 'C:\\mine\\vaults\\projeto_medicina'

    vault_notes = vault_crawler(db)

    for i, note in enumerate(vault_notes):
        print(f'{i+1}/{len(vault_notes)}: {note.deck}/{note.tag}')
        if note.questions is None:
            print('\t INVALID NOTE')
            continue

        for j, (q, ans) in enumerate(zip(note.questions, note.answers)):
            print(f'\t {j} Q: {q}')
            print(f'\t {j} A: {ans}')

        print()


if __name__ == '__main__':
    _main()

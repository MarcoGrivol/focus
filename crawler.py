import os
import re

from os import path
from collections import namedtuple
from typing import Tuple, Generator


def _re_heading(heading) -> re.Pattern:
    return re.compile(r'(#+?) +' + heading + r' *\n')


ANS_ALIAS_TOKEN = 'ans'
# #[...] [...]ANYTHING[spaces]\n
# Group: (1)=hashtags, (2)=heading text
RE_HEADING = _re_heading(r'(.+?)')
RE_ANKI_HEADING = _re_heading('Anki Cards')
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


ObsidianLink = namedtuple('ObsidianLink', ['name', 'heading', 'alias'])


class CrawlerError(ValueError):
    def __init__(self, message):
        self.message = message


def parse_link(link: str) -> ObsidianLink:
    # file[#heading][|rename]
    s = link.split('|')  # file[#heading], [|rename]
    alias = s[1] if len(s) == 2 else ''

    s = s[0].split('#')  # file, [#heading]
    heading = s[1] if len(s) == 2 else ''

    name = s[0]

    if name == heading == '':
        raise CrawlerError(f'link does not contain a name AND a heading, got: {link}')

    return ObsidianLink(name, heading, alias)


def _find_heading(data: str, heading: str | re.Pattern, mode='curr') -> str:
    """
    Find all the text encapsulating a heading, not the heading itself.
    :param data: file contents.
    :param heading: the name of the heading, excluding the '#' and any leading or trailing whitespace.
    :param mode: None exits on first heading, 'forw' reads forwards until end of file, 'curr' reads until higher
    or same level heading.
    """
    if mode not in ('curr', 'first', 'forw'):
        raise CrawlerError(f'Invalid mode: {mode}')

    if not isinstance(heading, re.Pattern):
        heading = _re_heading(heading)

    heads = heading.split(data, maxsplit=1)
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
                if mode == 'first':
                    break
                elif len(s) <= heading_level:  # mode is 'curr'
                    break
            text += s

    return text.strip()
    # return text.removeprefix(heading).strip('---').strip()


def _navigate(filepath: str, link: ObsidianLink, heading_mode=None) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = f.read()

    if link.heading:
        return _find_heading(data, link.heading, heading_mode)
    if heading_mode == 'full':
        return data.strip()

    # read until a heading is found (in this case, curr == first)
    new_text = ''
    for i, s in enumerate(RE_HEADING.split(data)):
        if s == '#' * len(s):  # only hashtags
            break
        new_text += s

    data = new_text
    return data.strip()


def _relpath(vault: str, filepath: str):
    relpath = filepath.removeprefix(vault + path.sep)
    if path.sep == '\\':
        relpath = relpath.replace('\\', '/')
    return path.basename(relpath), relpath


def _is_anki_file(text: str) -> Tuple[bool, str]:
    anki_tag = RE_ANKI_TAG.search(text)
    if anki_tag is None:
        return False, 'anki tag is missing or invalid'

    anki_heading = RE_ANKI_HEADING.search(text)
    if anki_heading is None:
        return False, 'anki heading is missing or invalid'

    return True, ''


_VALID_MODES  = ('curr', 'first', 'forw', 'full')
_DEFAULT_MODE = 'curr'


def _parse_mode(link: ObsidianLink) -> str:
    if not link.alias.startswith(ANS_ALIAS_TOKEN + '_'):
        return _DEFAULT_MODE

    mode = link.alias.removeprefix(ANS_ALIAS_TOKEN + '_')
    if mode != '':
        if mode not in _VALID_MODES:
            raise CrawlerError(f'Invalid mode: {mode}')
    else:
        mode = _DEFAULT_MODE

    if link.heading and mode == 'full':
        raise CrawlerError(f'Mode "{mode}" is not allowed when heading is used')

    return mode


class Answer:
    def __init__(self, link: ObsidianLink):
        self._link = link
        self._is_self_ref = link.name == ''
        self._text = ''

    def is_self_ref(self):
        return self._is_self_ref

    def get_link(self):
        return self._link

    def get_text(self):
        return self._text

    def set(self, text):
        if not text:
            raise CrawlerError(f'unable to set answer with empty text')
        if self._text != '':
            raise CrawlerError(f'cannot override answer with {text}')
        self._text = text


class AnkiNote:

    def __init__(self, filepath, deck, tag, note_text):
        self._filepath = filepath
        self._note_text = note_text
        self._deck = deck
        self._tag = tag

        self._is_valid = True
        self._invalid_reason = None

        self._questions = list()
        self._answers = list()

        for question, answer in RE_NOTE_ENTRY.findall(note_text):

            ans_link = None
            if answer:
                ans_link = parse_link(answer)
            else:
                links = RE_LINKS.findall(question)
                if len(links) == 1:
                    ans_link = parse_link(links[0])

            if ans_link is None:
                self._invalid_reason = 'missing or invalid answer link'
                self._is_valid = False
                return
            elif ans_link.name == ans_link.heading == '':
                self._invalid_reason = 'link must contain at least a file name or a heading'
                self._is_valid = False
                return

            self._questions.append(question)
            self._answers.append(Answer(ans_link))

    def is_valid(self) -> bool:
        return self._is_valid

    def set_invalid(self, reason: str):
        self._invalid_reason = reason
        self._is_valid = False

    def get_answers(self) -> Generator[Answer, None, None]:
        for ans in self._answers:
            yield ans

    def set_answer(self, i, text):
        self._answers[i].set(text)


class VaultCrawler:
    def __init__(self, vault: str):

        self._vault = path.normpath(vault)
        self._vault_links = dict()

        self._anki_files = list()
        self._invalid_files = dict()

        for root, subdir, files in os.walk(self._vault):
            for f_name in files:
                f_path = path.join(root, f_name)

                if not f_name.endswith('.md'):
                    continue

                filename, relpath = _relpath(self._vault, f_path)
                filename = filename.removesuffix('.md')
                if filename not in self._vault_links:
                    self._vault_links[filename] = list()
                self._vault_links[filename].append(relpath)

                with open(f_path, 'r', encoding='utf-8') as fp:
                    text = fp.read()

                is_anki, reason = _is_anki_file(text)

                if not is_anki:
                    self._invalid_files[filename] = reason
                else:
                    self._anki_files.append(f_path)

        self._valid_notes = list()
        self._invalid_notes = list()

    def get_anki_files(self):
        return self._anki_files

    def get_invalid_reasons(self):
        return self._invalid_files

    def convert_files(self):
        for filepath in self._anki_files:

            with open(filepath, 'r', encoding='utf-8') as fp:
                text = fp.read()

            anki_tag = RE_ANKI_TAG.search(text)
            deck = anki_tag.group(2)
            tag = anki_tag.group(3)
            cards_text = _find_heading(text, RE_ANKI_HEADING, mode='first')
            if cards_text == '':
                raise ValueError(f'anki heading not found for {filepath}')

            for note_entry in RE_NOTE_BODY.findall(cards_text):

                note = AnkiNote(filepath, deck, tag, note_entry)

                if not note.is_valid():
                    self._invalid_notes.append(note)
                else:
                    try:
                        self._set_answers(note, text)
                        self._valid_notes.append(note)

                    except CrawlerError as ex:
                        note.set_invalid(ex.message)
                        self._invalid_notes.append(note)

    def _set_answers(self, note: AnkiNote, text: str):
        for i, ans in enumerate(note.get_answers()):
            if ans.is_self_ref():
                ans_text = _find_heading(text, ans.get_link().heading, _parse_mode(ans.get_link()))
            else:
                ans_text = self._goto(ans.get_link())

            note.set_answer(i, ans_text)

    def _goto(self, link: ObsidianLink) -> str:
        key = path.basename(link.name)
        relative_paths = self._vault_links[key]

        filepath = None
        if len(relative_paths) == 1:
            filepath = path.join(self._vault, path.normcase(relative_paths[0]))
        else:
            for rp in relative_paths:
                if rp.removesuffix('.md') == link.name:
                    filepath = path.join(self._vault, path.normcase(rp))
                    break

        if filepath is None:
            raise CrawlerError(f'link points to a non-existent file: {link}')

        return _navigate(filepath, link, _parse_mode(link))


def _main_refac():
    db = 'C:\\mine\\vaults\\projeto_medicina'
    vc = VaultCrawler(db)
    vc.convert_files()
    print()


if __name__ == '__main__':
    # _main()
    _main_refac()

import os
from typing import Iterator, Dict, List

from ._utils import *


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


class ObsidianNote:
    def __init__(self, relative_path, name, deck, tags, note_text, main_tag=None):
        self.relative_path = relative_path
        self.name = name
        self.text = note_text
        self.deck = deck
        self.tags = tags
        self.main_tag = main_tag if main_tag else self.tags[0]

        self._is_valid = True
        self._invalid_reason = None

        self.questions = []
        self.answers = []

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

            self.questions.append(question)
            self.answers.append(Answer(ans_link))

    def is_valid(self) -> bool:
        return self._is_valid

    def set_invalid(self, reason: str):
        self._invalid_reason = reason
        self._is_valid = False

    def get_invalid_reason(self) -> str:
        return self._invalid_reason

    def get_fields(self) -> Iterator[Tuple[str, str]]:
        for i in range(len(self.questions)):
            yield self.questions[i], self.answers[i].get_text()


class NoteTree(object):
    def __init__(self, notes: List[ObsidianNote]):
        tree: Dict[str, Dict[str, List[Tuple[int, ObsidianNote]]]] = {}
        for i, note in enumerate(notes):
            d, t = note.deck, note.main_tag
            if d not in tree:
                tree[d] = {}
            if t not in tree[d]:
                tree[d][t] = []
            tree[d][t].append((i, note))
        self._tree = tree

    def __getitem__(self, key) -> Dict[str, List[Tuple[int, ObsidianNote]]]:
        return self._tree[key]

    def __iter__(self):
        return iter(self._tree)


class VaultCrawler:
    def __init__(self, vault: str):

        self.vault = path.normpath(vault)

        # file related
        self._vault_links = {}
        self.anki_files: List[str] = []
        self.invalid_files: Dict[str, str] = {}
        # formatted notes
        self.valid_notes: List[ObsidianNote] = []
        self.invalid_notes: List[ObsidianNote] = []

        self._crawl()

    def reset(self):
        self._crawl()
        self.valid_notes: List[ObsidianNote] = []
        self.invalid_notes: List[ObsidianNote] = []

    def convert_files(self):
        self.valid_notes: List[ObsidianNote] = []
        self.invalid_notes: List[ObsidianNote] = []
        for filepath in self.anki_files:

            with open(filepath, 'r', encoding='utf-8') as fp:
                text = fp.read()

            anki_tags = RE_ANKI_TAG.findall(text)
            deck = anki_tags[0][1]
            tags = [m[0] for m in anki_tags]
            cards_text = find_heading(text, RE_ANKI_HEADING, mode='first')
            if cards_text == '':
                raise ValueError(f'anki heading not found for {filepath}')

            for note_entry in RE_NOTE_BODY.findall(cards_text):

                name, rp = relpath(self.vault, filepath)
                note = ObsidianNote(rp, name, deck, tags, note_entry)

                if not note.is_valid():
                    self.invalid_notes.append(note)
                else:
                    try:
                        self._set_answers(note, text)
                        self.valid_notes.append(note)
                    except CrawlerError as ex:
                        note.set_invalid(ex.message)
                        self.invalid_notes.append(note)

    def build_filetree(self, key=None):
        valid_files = []
        for f in self.anki_files:
            fp = f.removeprefix(self.vault + path.sep)
            if path.sep == '\\':
                fp = fp.replace('\\', '/')
            valid_files.append(fp)

        tree = {
            'valid_files': build_filetree(valid_files),
            'invalid_files': build_filetree(self.invalid_files)
        }

        return deep_sort_filetree(tree, key=key)

    def build_notetree(self) -> Tuple[NoteTree, NoteTree]:
        v_tree = NoteTree(self.valid_notes)
        inv_tree = NoteTree(self.invalid_notes)
        return v_tree, inv_tree

    def _crawl(self):
        self._vault_links = {}
        self.anki_files: List[str] = []
        self.invalid_files: Dict[str, str] = {}

        for root, subdir, files in os.walk(self.vault):
            for f_name in files:
                f_path = path.join(root, f_name)

                if not f_name.endswith('.md'):
                    continue

                filename, rp = relpath(self.vault, f_path)
                filename = filename.removesuffix('.md')
                if filename not in self._vault_links:
                    self._vault_links[filename] = []
                self._vault_links[filename].append(rp)

                with open(f_path, 'r', encoding='utf-8') as fp:
                    text = fp.read()

                is_anki, reason = is_anki_file(text)

                if not is_anki:
                    self.invalid_files[rp] = reason
                else:
                    self.anki_files.append(f_path)

    def _set_answers(self, note: ObsidianNote, text: str):
        for i, ans in enumerate(note.answers):
            if ans.is_self_ref():
                ans_text = find_heading(text, ans.get_link().heading, parse_mode(ans.get_link()))
            else:
                ans_text = self._goto(ans.get_link())

            note.answers[i].set(ans_text)

    def _goto(self, link: ObsidianLink) -> str:
        key = path.basename(link.name)
        relative_paths = self._vault_links[key]

        filepath = None
        if len(relative_paths) == 1:
            filepath = path.join(self.vault, path.normcase(relative_paths[0]))
        else:
            for rp in relative_paths:
                if rp.removesuffix('.md') == link.name:
                    filepath = path.join(self.vault, path.normcase(rp))
                    break

        if filepath is None:
            raise CrawlerError(f'link points to a non-existent file: {link}')

        return navigate(filepath, link, parse_mode(link))

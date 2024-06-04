import os
import re
import logging

from os import path
from collections import namedtuple
from typing import AnyStr, LiteralString, List, Tuple

QUESTIONS_HEADING = 'Anki Questions'
# #[...] [...]ANYTHING[spaces]\n
# Group: (1)=hashtags, (2)=heading text
RE_HEADING = re.compile(r'(#+?) +(.+?) *\n')
# Target: #anki/DECK/TAG[/SUB_TAGS]
# Group: DECK e TAG[/SUB_TAGS], used to determine the Anki deck and Note tags
RE_ANKI_TAG = re.compile(r'(#anki)/(\S+?)/(\S.+)')
# Target: NUMBER. QUESTION TEXT
# Group: returns the text of the question
RE_CARD_BODY = re.compile(r'(?:^|\n\s*)\d+\. +(.+)')  # re.compile(r'(?<=\n)\s*\d+\. +(.+)')
# Targe: QUESTION .|? [[text[#op]|ans]]
# Groups: (1)=question, (2)=link
RE_CARD_ENTRY = re.compile(r'(.+?[.?])\s*(?:\[\[(.+\|ans)]])*')
# Target: [[ANY TEXT BETWEEN TWO BRACKETS]]
# Group: text in between, may contain the optional #heading link or |link renaming tokens
RE_LINKS = re.compile(r'\[\[(.+?)]]')


ObsidianLink = namedtuple('ObsidianLink', ['path', 'name', 'heading', 'alias'])


def re_heading(heading):
    return re.compile(r'(#+?) +' + heading + r' *\n')


def parse_link(link: str) -> ObsidianLink:
    # file[#heading][|rename]
    s = link.split('|')  # file[#heading], [|rename]
    alias = s[1] if len(s) == 2 else ''
    s = s[0].split('#')  # file, [#heading]
    heading = s[1] if len(s) == 2 else ''
    name = s[0]
    return ObsidianLink(f'{s[0]}.md', s[0], heading, alias)


def find_heading(data: str, heading: str, exit_on_first=False) -> str:
    """
    Find all the text encapsulating a heading, not the heading itself.
    :param data: file contents.
    :param heading: the name of the heading, excluding the '#' and any leading or trailing whitespace.
    :param exit_on_first: if True, stops after finding the next heading.
    """
    if re_heading(heading).search(data) is None:
        return ''

    heads = RE_HEADING.split(data)

    target_heading = 0
    text = ''

    for i, s in enumerate(heads):
        if s == '#' * len(s):  # only hashtags
            if heads[i + 1] == heading:
                target_heading = len(s)
            elif target_heading != 0:  # already found the target heading
                if exit_on_first:
                    break
                elif len(s) <= target_heading:  # found a higher level heading, stop
                    break
            continue

        if target_heading == 0:
            continue  # text before heading

        text += s
    return text.removeprefix(heading).strip('---').strip()


def navigate(vault: str, link: ObsidianLink, exit_on_first=False):
    filepath = path.join(vault, link.path)
    if not path.isfile(filepath):
        return ''

    with open(filepath, 'r', encoding='utf-8') as f:
        data = f.read()

    if link.heading:
        return find_heading(data, link.heading, exit_on_first)

    return data.strip()



class ObsidianFile:
    def __init__(self, vault, filepath):
        self.vault = vault
        self.filepath = filepath
        self.name = filepath.removeprefix(vault).removesuffix('.md')

        with open(filepath, 'r', encoding='utf-8') as f:
            self.data = f.read()

        anki_tag = RE_ANKI_TAG.search(self.data)
        if anki_tag is None:
            self.is_anki = False
            self.deck = self.tag = None
            self.cards = []
        else:
            self.is_anki = True
            self.deck = anki_tag.group(1)
            self.tag = anki_tag.group(2)
            self.cards = self._parse()

    def _parse(self) -> List[ Tuple[str, str] ]:
        text = find_heading(self.data, QUESTIONS_HEADING)

        cards = list()

        for card in RE_CARD_BODY.findall(text):
            questions, answers = list(), list()

            for i, card_entry in enumerate(RE_CARD_ENTRY.findall(card)):
                q, ans = self._parse_card_entry(card_entry)
                if q == '' or ans == '':
                    break
                questions.append(q)
                answers.append(ans)

            # if '' in questions or '' in answers:
            #     cards.append(zip())
            # else:
            cards.append(zip(questions, answers))

        return cards

    def _parse_card_entry(self, card_entry) -> Tuple[str, str]:
        question, answer = card_entry

        if answer:
            return question, self._goto(parse_link(answer))

        links = RE_LINKS.findall(question)
        if len(links) != 1:
            return '', ''

        return question, self._goto(parse_link(links[0]))

    def _goto(self, link: ObsidianLink) -> str:
        if link.name == self.name:
            return find_heading(self.data, link.heading)
        return navigate(self.vault, link)


def _main():
    db = 'C:\\mine\\Journey'

    vault_files = list()
    ob_files = list()

    for root, dirs, files in os.walk(db):
        for f_name in files:

            f_path = os.path.join(root, f_name)
            if not f_name.endswith('.md'):
                continue

            vault_files.append(f_path)

            obf = ObsidianFile(db, f_path)
            if obf.is_anki:
                ob_files.append(obf)

    print('ANKI FILES:')
    for i, obf in enumerate(ob_files):
        if len(obf.cards) == 0:
            print(f'{i}: {obf.filepath}\n\t')
        else:
            print(f'{i}: {obf.filepath}:')
            for j, card in enumerate(obf.cards):
                print(f' card {j}')
                for q, ans in card:
                    ans = ans.replace('\n', '\\n')
                    print(f'\t\tQ:   {q}')
                    print(f'\t\tAns: {ans}')


if __name__ == '__main__':
    _main()

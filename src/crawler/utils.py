import re
from collections import namedtuple

from os import path
from typing import Tuple


class CrawlerError(ValueError):
    def __init__(self, message):
        self.message = message


class HeadingNotFoundError(CrawlerError):
    pattern = re.compile(r'<heading>(.*?)\)')

    def __init__(self, heading: str | re.Pattern):
        self.message = f'Heading "{self.format_msg(heading)}" not found'

    def format_msg(self, heading: str | re.Pattern) -> str:
        if isinstance(heading, str):
            return heading

        m = self.pattern.search(heading.pattern)
        if m is None:
            return heading.pattern
        else:
            return m.group(1)


ObsidianLink = namedtuple('ObsidianLink', ['name', 'heading', 'alias'])


VALID_MODES  = ('curr', 'first', 'forw', 'full')
DEFAULT_MODE = 'curr'


def re_heading(heading) -> re.Pattern:
    return re.compile(r'(#+?) +(?P<heading>' + heading + r') *\n')


ANS_ALIAS_TOKEN = 'ans'
# #[...] [...]ANYTHING[spaces]\n
# Group: (1)=hashtags, (2)=heading text
RE_HEADING = re_heading(r'.+?')
RE_ANKI_HEADING = re_heading('Anki Cards')
# Target: #anki/DECK/TAG/SUB_TAGS
# Group: DECK and TAG/SUB_TAGS, used to determine the Anki deck and Note tags
RE_MAIN_ANKI_TAG = re.compile(r'#anki/((?P<deck>\S+?)/\S.+)')
RE_ANKI_TAG = re.compile(r'#anki/(.+?)\s')
# Target: NUMBER. QUESTION TEXT
# Group: returns the text of the question
RE_NOTE_BODY = re.compile(r'(?:^|\n\s*)\d+\. +(.+)')  # re.compile(r'(?<=\n)\s*\d+\. +(.+)')
# Targe: QUESTION .|? [[text[#op]|ans]]
# Groups: (1)=question, (2)=link
RE_NOTE_ENTRY = re.compile(r'(.+?(?:[.?]|$))\s*(?:\[\[(.+\|' + ANS_ALIAS_TOKEN + r'(?:_\w*)?)]])*')
# Target: [[ANY TEXT BETWEEN TWO BRACKETS]]
# Group: text in between, may contain the optional #heading link or |link renaming tokens
RE_LINKS = re.compile(r'\[\[(.+?)]]')


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


def find_heading(data: str, heading: str | re.Pattern, mode='curr') -> str:
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
        heading = re_heading(heading)

    heads = heading.split(data, maxsplit=1)
    # heads[0] = text before
    # heads[1] = any number of #
    # heads[2] = heading text
    # heads[3] = text after
    if len(heads) == 1:
        raise HeadingNotFoundError(heading)

    text = f'{heads[1]} {heads[2]}\n'
    if mode == 'forw':
        text += heads[3]
    else:
        heading_level = len(heads[1])
        heads = RE_HEADING.split(heads[3])
        i = 0
        while i < len(heads):
            s = heads[i]
            if s == '#' * len(s):  # only hashtags
                if mode == 'first':
                    break
                elif len(s) <= heading_level:  # mode is 'curr'
                    break
                s += f' {heads[i + 1]}\n'
                i += 1  # heading text already added (above line), skip next token
            text += s
            i += 1
        # for i, s in enumerate(RE_HEADING.split(heads[3])):
        #     if s == '#' * len(s):  # only hashtags
        #         if mode == 'first':
        #             break
        #         elif len(s) <= heading_level:  # mode is 'curr'
        #             break
        #         s += ' '
        #     text += s

    return text.strip()


def navigate(filepath: str, link: ObsidianLink, heading_mode=None) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = f.read()

    if link.heading:
        return find_heading(data, link.heading, heading_mode)
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


def relpath(vault: str, filepath: str):
    rp = filepath.removeprefix(vault + path.sep)
    if path.sep == '\\':
        rp = rp.replace('\\', '/')
    return path.basename(rp), rp


def is_anki_file(text: str) -> Tuple[bool, str]:
    anki_tag = RE_MAIN_ANKI_TAG.search(text)
    if anki_tag is None:
        return False, 'anki tag is missing or invalid'

    anki_heading = RE_ANKI_HEADING.search(text)
    if anki_heading is None:
        return False, 'anki heading is missing or invalid'

    return True, ''


def parse_mode(link: ObsidianLink) -> str:
    if not link.alias.startswith(ANS_ALIAS_TOKEN + '_'):
        return DEFAULT_MODE

    mode = link.alias.removeprefix(ANS_ALIAS_TOKEN + '_')
    if mode != '':
        if mode not in VALID_MODES:
            raise CrawlerError(f'Invalid mode: {mode}')
    else:
        mode = DEFAULT_MODE

    if link.heading and mode == 'full':
        raise CrawlerError(f'Mode "{mode}" is not allowed when heading is used')

    return mode


def build_filetree(files):
    def _expand_tree(_tree, _parent, _filepath, _text):
        if _parent not in _tree:
            _tree[_parent] = {'root': []}
        if len(_filepath) > 1:
            _tree[_parent] = _expand_tree(_tree[_parent], _filepath[0], _filepath[1:], _text)
        else:
            _tree[_parent]['root'].append((_filepath[0], _text))
        return _tree

    tree = {'root': []}

    if isinstance(files, list):
        it = [(f, 'OK') for f in files]
    elif isinstance(files, dict):
        it = files.items()
    else:
        raise NotImplementedError(f'build_tree does not support type={type(files)}')

    for f, text in it:
        fp = f.split('/')
        if len(fp) == 1:
            tree['root'].append((fp[0], text))
        else:
            tree = _expand_tree(tree, fp[0], fp[1:], text)

    return tree


def deep_sort_filetree(obj, *, key=None, reverse=False):
    if isinstance(obj, dict):
        return {
            k: deep_sort_filetree(v, key=key, reverse=reverse)
            for k, v in sorted(obj.items(), key=key, reverse=reverse)
        }
    if isinstance(obj, list):
        return [
            deep_sort_filetree(v, key=key, reverse=reverse)
            for i, v in sorted(enumerate(obj), key=key, reverse=reverse)
        ]
    return obj

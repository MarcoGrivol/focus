﻿import re
from typing import Tuple, List
from xml.etree import ElementTree as ET
import markdown

from anki_handler import CSS_WIKILINK, CSS_HIGHLIGHT


def note_to_webview(fields: List[Tuple[str, str]]):
    front, back = '', ''
    if len(fields) == 1:
        q, ans = fields[0]
        front = text_to_html(q)
        back = text_to_html(ans)
    else:
        for i, (q, ans) in enumerate(fields):
            front += f'<h1>Q{i}</h1><hr>\n' + text_to_html(q, True)
            back += f'<h1>R{i}</h1><hr>\n' + text_to_html(ans, True)
    root = ET.Element('')
    return front, back


def note_to_html(fields: List[Tuple[str, str]]):
    front, back = '', ''
    if len(fields) == 1:
        q, ans = fields[0]
        front = text_to_html(q)
        back = text_to_html(ans)
    else:
        for i, (q, ans) in enumerate(fields):
            front += f'<h1>Q{i}</h1><hr>\n' + text_to_html(q, True)
            back += f'<h1>R{i}</h1><hr>\n' + text_to_html(ans, True)
    return front, back


def text_to_html(text, lower_headings=False):
    text = _replace_link(text)
    text = _replace_strikethrough(text)
    text = _remove_tags(text)
    if lower_headings:
        text = _remove_hr(text)
        text = _lower_headings(text)
    text = _safe_headings(text)
    text = _safe_lists(text)
    text = _replace_mathjax(text)
    text = _replace_highlight(text)
    return markdown.markdown(text, extensions=['tables', 'sane_lists'])


def _replace_strikethrough(text):
    def repl(m):
        return f'<s>{m.group(1)}</s>'
    return re.sub(r'~~(.*?)~~', repl, text, flags=re.MULTILINE)


def _remove_tags(text):
    return re.sub(r'#\w+([_/\-]\w*)*', '', text)  # remove tags


def _remove_hr(text):
    return re.sub(r'^ {0,3}--- *\n', '', text, flags=re.MULTILINE)


def _lower_headings(text):
    def repl(m):
        return '#' + m.group(1) + m.group(2) + '\n'

    return re.sub(r'^(#+)( +.*?)\n', repl, text, flags=re.MULTILINE)


def _safe_lists(text):
    # add new line before a list block
    list_pattern = re.compile(r'^ *(\*|-|\d+\.) +(.*)')

    new_text = ''

    started = False
    for line in text.split('\n'):
        numbered_list = list_pattern.match(line)
        if numbered_list is not None:
            if not started:
                started = True
                new_text += '\n'
        elif started:
            started = False
            new_text += '\n'

        new_text += line + '\n'

    return new_text


def _safe_headings(text):
    # ensure a new line break is present before and after headings
    heading_pattern = re.compile(r'^(#+? +.+? *\n)', flags=re.MULTILINE)
    prev_pattern = re.compile(r'\n[ \t]*\n$')
    next_pattern = re.compile(r'^[ \t]*(\n+)[ \t]*')

    new_text = ''

    split = heading_pattern.split(text)
    if len(split) < 2:
        return text

    for i in range(1, len(split), 2):

        new_text += split[i - 1]
        if prev_pattern.search(split[i - 1]) is None:
            new_text += '\n'

        new_text += split[i]

        if next_pattern.search(split[i + 1]) is None:
            new_text += '\n'

        if i + 2 >= len(split):
            new_text += split[i + 1]

    return new_text


def _replace_mathjax(text):
    def repl_block(m):
        return f'<anki-mathjax block="true">{m.group(1)}</anki-mathjax>'

    def repl(m):
        return f'<anki-mathjax>{m.group(1)}</anki-mathjax>'

    text = re.sub(r'\$\$(.*?)\$\$', repl_block, text)
    return re.sub(r'\$(.*?)\$', repl, text)


def _replace_highlight(text):
    def repl(m):
        return f'<span class="{CSS_HIGHLIGHT.name}">{m.group(1)}</span>'

    return re.sub(r'==(.*?)==', repl, text)


def _replace_link(text):
    def repl(m):
        link = m.group(1)
        if '|' in link:
            link = link.split('|')[1]
        if '#' in link:
            link = link.split('#')[1]
        return f'<span class="{CSS_WIKILINK.name}">{link}</span>'

    return re.sub(r'\[\[(.*?)]]', repl, text)


def _main():
    from crawler import vault_crawler

    db = 'C:\\mine\\vaults\\projeto_medicina'

    vault_notes = vault_crawler(db)

    for i, note in enumerate(vault_notes):
        print(f'{i + 1}/{len(vault_notes)}: {note.deck}/{note.tag}')
        if note.questions is None:
            print('\t INVALID NOTE')
            continue

        for j, (q, ans) in enumerate(zip(note.questions, note.answers)):
            print(f'\t {j} BEFORE : {ans}')
            print(f'\t {j} AFTER  : {convert_to_html(ans)}')

        print()


if __name__ == '__main__':
    _main()

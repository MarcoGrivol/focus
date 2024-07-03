import re
import markdown
from collections import namedtuple
from typing import Tuple, List

from crawler import AnkiNote

Style = namedtuple('Style', ['name', 'css'])

CSS_CARD = Style('card',
                 '.card {'   
                    ' font-family: arial;'
                    ' font-size: 20px;'
                    ' text-align: left;'
                    ' color: black;'
                    ' background-color: white;'
                 '}'
)
CSS_WIKILINK = Style('wikilink', '.wikilink { color: rgb(0, 85, 255); }')
CSS_HIGHLIGHT = Style('highlight', '.highlight { background-color: rgb(255, 255, 0); }')
CSS_CALLOUT = Style('callout', '.callout { margin-left: auto; margin-right: auto; max-width: 500px; }')
CSS_CALLOUT_HEADER = Style('callout-header',
                            '.callout-header {'
                                'padding: 5px 10px 10px 10px;'
                                'font-weight: 600;'
                                'border-top: 1px solid black;'
                                'border-left: 5px solid;'
                                'border-right: 1px solid black;'
                                'border-top-left-radius: 7px;'
                                'border-top-right-radius: 7px;'
                            '}'
)
CSS_CALLOUT_BODY = Style('callout-body',
                         '.callout-body {'
                            'padding: 1px 10px 1px 10px;'
                            'background-color: #fafafa;'
                            'color: black;'
                            'border-left: 5px solid;'
                            'border-bottom: 1px solid black;'
                            'border-right: 1px solid black;'
                            'border-bottom-left-radius: 7px;'
                            'border-bottom-right-radius: 7px;'
                         '}'
)
CSS_BLOCKQUOTE = Style('blockquote',
                        'blockquote {'
                            'max-width: 75%;'
                            'background-color: #ebebeb;'
                            'padding: 4px;'
                            'border-left: 5px solid #a68cda;'
                            'border-radius: 5px;'
                        '}'
)
CSS_CALLOUT_HEADER_COLORS = {
    'note': 'background: #e6f0fb; border-left-color: #0094fd; color: #086ddd',
    'info': 'background: #e6f0fb; border-left-color: #0094fd; color: #086ddd',
    'warning': 'background: #fdf1e5; border-left-color: #ec7500; color: #ec7500',
    'danger': 'background: #fdeaec; border-left-color: #e93147; color: #e93147'
}
CSS_CALLOUT_BODY_COLORS = {
    'note': 'border-left-color: #0094fd; ',
    'info': 'border-left-color: #0094fd;',
    'warning': 'border-left-color: #ec7500;',
    'danger': 'border-left-color: #e93147;',
}


def get_styling():
    styling = CSS_CARD.css + '\n'
    styling += CSS_WIKILINK.css + '\n'
    styling += CSS_HIGHLIGHT.css + '\n'
    styling += CSS_CALLOUT.css + '\n'
    styling += CSS_CALLOUT_HEADER.css + '\n'
    styling += CSS_CALLOUT_BODY.css + '\n'
    styling += CSS_BLOCKQUOTE.css
    return styling


def notes_webview(notes: List[AnkiNote]) -> str:
    html = '<!DOCTYPE html><html lang="en">\n<head>\n'
    html += '<meta charset="UTF-8">\n'
    html += '<title>Note preview</title>\n'
    html += '<style>' + get_styling() + '</style>\n'
    html += '<script type="text/javascript" id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>\n'
    html += '</head>\n<body>\n'

    for i, note in enumerate(notes):
        html += f'<h1>note={i+1}</h1><hr>'
        front, back = note_to_html(list(note.get_fields()), web=True)
        html += front
        html += back

    html += '</body>\n</html>\n'
    return html


def note_to_html(fields: List[Tuple[str, str]], web=False):
    front, back = '', ''
    if len(fields) == 1:
        q, ans = fields[0]
        front = text_to_html(q, web=web)
        back = text_to_html(ans, web=web)
    else:
        for i, (q, ans) in enumerate(fields):
            front += f'<b>Q{i+1}</b>' + text_to_html(q, True, web)
            back += f'<b>R{i+1}</b>' + text_to_html(ans, True, web)
    return front, back


def text_to_html(text, lower_headings=False, web=False):
    text = _replace_link(text)
    text = _replace_strikethrough(text)
    text = re.sub(r'#\w+([_/\-]\w*)*', '', text)  # remove tags
    text = re.sub(r'^ {0,3}--- *\n', '\n', text, flags=re.MULTILINE)  # remove hr
    if lower_headings:
        text = _lower_headings(text)
    text = _safe_headings(text)
    text = _safe_lists(text)
    text = _replace_highlight(text)
    text = _replace_anki_mathjax(text)
    text = markdown.markdown(text, extensions=['tables', 'sane_lists'])
    text = _replace_callout(text)
    if web:
        text = _replace_mathjax(text)
    return text


def _replace_strikethrough(text):
    def repl(m):
        return f'<s>{m.group(1)}</s>'
    return re.sub(r'~~(.*?)~~', repl, text, flags=re.MULTILINE)


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


def _replace_anki_mathjax(text):
    def repl_block(m):
        return f'<anki-mathjax block="true">{m.group(1)}</anki-mathjax>'

    def repl(m):
        return f'<anki-mathjax>{m.group(1)}</anki-mathjax>'

    text = re.sub(r'\$\$(.*?)\$\$', repl_block, text)
    return re.sub(r'\$(.*?)\$', repl, text)


def _replace_mathjax(text):
    def repl_block(m):
        return f'$${m.group(1)}$$'

    def repl(m):
        return f'\\({m.group(1)}\\)'

    text = re.sub(r'<anki-mathjax block="true">(.*?)</anki-mathjax>', repl_block, text)
    return re.sub(r'<anki-mathjax>(.*?)</anki-mathjax>', repl, text)


def _replace_callout(text):
    def repl(m):
        key = m.group(1) if m.group(1) in CSS_CALLOUT_BODY_COLORS else 'info'

        header_name = CSS_CALLOUT_HEADER.name
        body_name = CSS_CALLOUT_BODY.name

        header_style = CSS_CALLOUT_HEADER_COLORS[key]
        body_style = CSS_CALLOUT_BODY_COLORS[key]

        callout = f'<div class="{CSS_CALLOUT.name}">'
        callout += f'<div class="{header_name}" style="{header_style}">{m.group(2)}</div>'
        callout += f'<div class="{body_name}" style="{body_style}"><p>{m.group(3)}</div>'
        callout += '</div>'
        return callout
    return re.sub(r'<blockquote>\s*<p>\[!(\w+)] *(.*)([\s\S]*)</blockquote>', repl, text, flags=re.MULTILINE)


def _replace_callout1(text, web):
    def repl(m):
        key = m.group(1) if m.group(1) in CSS_CALLOUT_BODY_COLORS else 'info'
        header_style = CSS_CALLOUT_HEADER_COLORS[key]
        body_style = CSS_CALLOUT_BODY_COLORS[key]

        body_text = text_to_html(m.group(3), web)

        callout = f'<div class="{CSS_CALLOUT.name}">'
        callout += f'<div class="{CSS_CALLOUT_HEADER.name}" style="{header_style}">{m.group(2)}</div>'
        callout += f'<div class="{CSS_CALLOUT_BODY.name}" style="{body_style}">{body_text}</div>'
        callout += '</div>'

        return callout

    return re.sub(r'> *\[!(\w+)] +(.*?)\n((?:> *.*\n)+)', repl, text)


def _replace_highlight(text):
    def repl(m):
        return f'<span class="{CSS_HIGHLIGHT.name}">{m.group(1)}</span>'

    return re.sub(r'==(.*?)==', repl, text)


def _replace_link(text):
    def repl(m):
        link = m.group(1)

        if '|' in link:
            link = link.split('|')[1]
        elif '#' in link:
            link = link.split('#')[1]
        else:
            link = link.split('/')[-1]  # name, split on folders

        return f'<span class="{CSS_WIKILINK.name}">{link}</span>'

    return re.sub(r'\[\[(.*?)]]', repl, text)

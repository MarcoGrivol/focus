import re
import webbrowser
import markdown

from html import escape
from os import path
from typing import Tuple, List

# focus imports
import settings
from crawler import ObsidianNote
from anki_handler import AnkiNote


_RE_CALLOUT = re.compile(r'<blockquote>\s*<p>\[!(\w+)] *(.*)([\s\S]*)</p>\s*</blockquote>')
_RE_TAGS = re.compile(r'#\w+([_/\-]\w*)*')
_RE_HR = re.compile(r'^ {0,3}--- *\n', flags=re.MULTILINE)
_RE_STRIKE = re.compile(r'~~(.*?)~~', flags=re.MULTILINE)
_RE_HEADING = re.compile(r'^(#+)( +.*?)\n', flags=re.MULTILINE)
_RE_MATH_BLOCK = re.compile(r'\$\$(.*?)\$\$', flags=re.MULTILINE)
_RE_MATH = re.compile(r'\$(.*?)\$')
_RE_MATH_ANKI_BLOCK = re.compile(r'<anki-mathjax block="true">(.*?)</anki-mathjax>', flags=re.MULTILINE)
_RE_MATH_ANKI = re.compile(r'<anki-mathjax>(.*?)</anki-mathjax>')
_RE_HIGHLIGHT = re.compile(r'==(.*?)==')
_RE_LINK = re.compile(r'\[\[(.*?)]]')
_RE_LISTS = re.compile(r'^ *(\*|-|\d+\.) +(.*)')


def webpreview(notes: List[ObsidianNote]):
    buf = ''
    for i, note in enumerate(notes):
        buf += f'<h1>note={i + 1}</h1><hr>'
        front, back = note_to_html(list(note.get_fields()), web=True)
        buf += front
        buf += f'<hr class="{settings.STYLES.get_class(".field-delimiter")}">\n'
        buf += back

    html_head, html_tail = _webpreview_head_tail()
    buf = html_head + buf + html_tail

    filepath = path.join(settings.OUTPUT_DIR, 'webpreview.html')
    with open(filepath, 'w', encoding='utf-8') as fp:
        fp.write(buf)

    webbrowser.open('file:///' + filepath)


def webpreview_textual(notes: List[AnkiNote]):
    def _format(text: str) -> str:
        return re.sub(
            r'&lt;/(.*?)&gt;',
            lambda m: '&lt;/%s&gt;<br>' % m.group(1),
            text,
            flags=re.MULTILINE
        )
    buf = ''
    for i, note in enumerate(notes):
        buf += f'<h1>note={i + 1} dupID={note.duplicate_id}</h1><hr>'
        buf += _format(escape(note.question))
        buf += f'<hr style="{settings.STYLES[".field-delimiter"]}"/>\n'
        buf += _format(escape(note.answer))

    html_head, html_tail = _webpreview_head_tail()
    buf = html_head + buf + html_tail

    filepath = path.join(settings.OUTPUT_DIR, 'webpreview_textual.html')
    with open(filepath, 'w', encoding='utf-8') as fp:
        fp.write(buf)

    webbrowser.open('file:///' + filepath)


def note_to_html(fields: List[Tuple[str, str]], web=False):
    front, back = '', ''
    if len(fields) == 1:
        q, ans = fields[0]
        front = text_to_html(q, web=web)
        back = text_to_html(ans, web=web)
    else:
        for i, (q, ans) in enumerate(fields):
            front += f'<h1>Q{i+1}</h1>' + text_to_html(q, True, web)
            back += f'<h1>R{i+1}</h1>' + text_to_html(ans, True, web)
    return front, back


def text_to_html(text, lower_headings=False, web=False):
    text = _replace_link(text)
    text = _replace_strikethrough(text)
    text = _RE_TAGS.sub('', text)  # remove tags
    text = _RE_HR.sub('', text)  # remove hr
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


def _webpreview_head_tail() -> Tuple[str, str]:
    html = '<!DOCTYPE html><html lang="en">\n<head>\n'
    html += '<meta charset="UTF-8">\n'
    html += '<title>Note preview</title>\n'
    html += '<style>' + settings.STYLES.to_string() + '</style>\n'
    html += '<script type="text/javascript" id="MathJax-script" '
    html += 'async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js">'
    html += '</script>\n'
    html += '</head>\n<body>\n'

    return html, '</body>\n</html>\n'


def _replace_strikethrough(text):
    def repl(m):
        return f'<s>{m.group(1)}</s>'
    return _RE_STRIKE.sub(repl, text)


def _lower_headings(text):
    def repl(m):
        return '#' + m.group(1) + m.group(2) + '\n'

    return _RE_HEADING.sub(repl, text)


def _safe_lists(text):
    # add new line before a list block
    new_text = ''

    started = False
    for line in text.split('\n'):
        numbered_list = _RE_LISTS.match(line)
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

    text = _RE_MATH_BLOCK.sub(repl_block, text)
    return _RE_MATH.sub(repl, text)


def _replace_mathjax(text):
    def repl_block(m):
        return f'$${m.group(1)}$$'

    def repl(m):
        return f'\\({m.group(1)}\\)'

    text = _RE_MATH_ANKI_BLOCK.sub(repl_block, text)
    return _RE_MATH_ANKI.sub(repl, text)


def _replace_callout(text):
    def repl(m):
        c, ch, cb = settings.STYLES.get_callout(m.group(1))

        buffer = f'<div class="{c}">\n'
        buffer += f'<div class="{ch}">\n {m.group(2)} \n</div>\n'
        buffer += f'<div class="{cb}">\n <p>{m.group(3)}</p>\n</div>\n'
        buffer += '</div>\n'
        return buffer

    return _RE_CALLOUT.sub(repl, text)


def _replace_highlight(text):
    def repl(m):
        return f'<span class="{settings.STYLES.get_class(".highlight")}">{m.group(1)}</span>'

    return _RE_HIGHLIGHT.sub(repl, text)


def _replace_link(text):
    def repl(m):
        link = m.group(1)

        if '|' in link:
            link = link.split('|')[1]
        elif '#' in link:
            link = link.split('#')[1]
        else:
            link = link.split('/')[-1]  # name, split on folders

        return f'<span class="{settings.STYLES.get_class(".wikilink")}">{link}</span>'

    return _RE_LINK.sub(repl, text)

import re
import markdown

from crawler import ObsidianNote


def convert_to_note(obn: ObsidianNote):
    front, back = '', ''
    if len(obn) == 1:
        front = convert_to_html(obn.questions[0])
        back = convert_to_html(obn.answers[0])
    else:
        for i, (q, ans) in enumerate(zip(obn.questions, obn.answers)):
            front += f'<h1>Q{i}</h1><hr>\n' + convert_to_html(q, True)
            back  += f'<h1>R{i}</h1><hr>\n' + convert_to_html(ans, True)

    note = {
        'deckName': obn.deck,
        'modelName': 'Basic',
        'tags': [
            obn.tag
        ],
        'fields': {
            'Front': front,
            'Back': back,
        }
    }

    return note


def convert_to_html(text, lower_headings=False):
    text = _replace_link(text)
    text = _remove_tags(text)
    text = _remove_hr(text)
    if lower_headings:
        text = _lower_headings(text)
    text = _safe_headings(text)
    text = _safe_lists(text)
    text = _replace_mathjax(text)
    text = _replace_highlight(text)
    return markdown.markdown(text)


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
        return f'<span style="background-color: rgb(255, 255, 0);">{m.group(1)}</span>'
    return re.sub(r'==(.*?)==', repl, text)


def _replace_link(text):
    def repl(m):
        link = m.group(1)
        if '|' in link:
            link = link.split('|')[0]
        if '#' in link:
            link = link.split('#')[0]
        return f'<span style="color: rgb(0, 85, 255);">{link}</span>'
    return re.sub(r'\[\[(.*?)]]', repl, text)


def _main():
    from crawler import vault_crawler

    db = 'C:\\mine\\vaults\\projeto_medicina'

    vault_notes = vault_crawler(db)

    for i, note in enumerate(vault_notes):
        print(f'{i+1}/{len(vault_notes)}: {note.deck}/{note.tag}')
        if note.questions is None:
            print('\t INVALID NOTE')
            continue

        for j, (q, ans) in enumerate(zip(note.questions, note.answers)):
            print(f'\t {j} BEFORE : {ans}')
            print(f'\t {j} AFTER  : {convert_to_html(ans)}')

        print()


if __name__ == '__main__':
    _main()

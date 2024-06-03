import os
import re
import logging

from os import path

QUESTIONS_HEADING = 'Anki Questions'

# Target: #anki/DECK/TAG[/SUB_TAGS]
# Group: DECK e TAG[/SUB_TAGS], used to determine the Anki deck and Note tags
RE_ANKI_TAG = re.compile(r'(#anki)/(\S+?)/(\S.+)')
# RE_QUESTIONS_HEAD = re.compile(r'(#)+? +?' + QUESTIONS_HEADING + r' *?\n')
# Target: 1. QUESTION TEXT
# Group: returns the text of the question
RE_QUESTIONS_BODY = re.compile(r'\d+\. (.+)')
# Target: [[ANY TEXT BETWEEN TWO BRACKETS]]
# Group: text in between, may contain the optional #heading link or |link renaming tokens
RE_LINKS = re.compile(r'\[\[(.*?)]]')

# [[link#header|ans]] groups: link, header, ans
# RE_LINKS = re.compile(r'\[\[([a-zA-Z0-9 ]+)#?([a-zA-Z0-9 ]*?)\|?(ans)*?]]')

logger = logging.getLogger(__name__)


# Target: #[#...#] [space...space]HEADING[space..space]\n
# Group: hashtags, used to figure out the heading level
def regex_heading(heading):
    return re.compile(r'(#)+? +?' + heading + r' *?\n')


class ObsidianNote:
    def __init__(self, vault, filepath):
        self.vault = vault
        self.filepath = filepath
        self.link = filepath.removeprefix(vault).removesuffix('.md')

        with open(filepath, 'r', encoding='utf-8') as f:
            self.data = f.read()

        anki_tag = RE_ANKI_TAG.search(self.data)
        if anki_tag is None:
            self.is_anki = False
            self.deck = self.tag = None
            self.fields = []
        else:
            self.is_anki = True
            self.deck = anki_tag.group(1)
            self.tag = anki_tag.group(2)
            self.questions = self._read_questions()
            self.answers = self._read_answers()

    def _read_questions(self):
        questions = RE_QUESTIONS_BODY.findall(
            self._find_heading(QUESTIONS_HEADING)
        )


    def _find_heading(self, heading, exit_on_first=False):
        """
        Find all the text encapsulating a heading.
        :param heading: the name of the heading, excluding the '#' and any leading or trailing whitespace.
        :param exit_on_first: if True, stops after finding the next heading.
        :return: the encapsulated heading text, excluding the heading itself and any '---' or '\n' trailing chars.
        """
        text_before, text = self.data.split(f'# {heading}', maxsplit=1)

        heading_level = 1
        for c in text_before[::-1]:
            if c == '#':
                heading_level += 1
            else:
                break

        heading_text = ''

        for line in text.split('\n'):
            h = re.match(r'(#+?) ', line)
            if h is not None:
                if exit_on_first:
                    break  # first heading found
                elif len(h.group(1)) <= heading_level:
                    break  # found a higher level heading
                # child heading, proceed
            heading_text += line + '\n'

        return heading_text.strip('\n').strip('---')


def load_note(vault, file):
    with open(file, 'r', encoding='utf-8') as reader:
        data = reader.read()

    ob_file = path.basename(file).removesuffix('.md')

    anki_tag = RE_ANKI_FIELDS.search(data)
    deck = anki_tag.group(1)
    tag = anki_tag.group(2)

    q_text = find_heading(data, QUESTIONS_TOKEN, exit_on_first=True)
    q_text = list(filter(lambda x: x is not None and x != '---', q_text.split('\n')))
    q_text = [q.split('. ', maxsplit=1)[1] for q in q_text]

    for i, q in enumerate(q_text):
        print(f'({i}): {q}')

    notes = list()

    for i, q in enumerate(q_text[:1]):
        ans = find_answer(vault, ob_file, data, q)


def find_answer(vault, ob_file, data, question):
    links = RE_LINKS.findall(question)

    if len(links) == 0:
        logger.error('no links found')
        return ''

    if len(links) == 1:
        parsed = parse_link(links[0])
        return read_link(vault, ob_file, data, parsed)

    parsed = [parse_link(x) for x in links]
    ans_link = list(filter(lambda x: x[2] == 'ans', parsed))

    if len(ans_link) == 1:
        return read_link(vault, ob_file, data, ans_link[0])

    logger.error(f'{links} contains incorrect number of "ans" link tags, expected 1 but got {len(ans_link)}')
    return ''


def parse_link(link):
    # file[#heading][|rename]
    s = link.split('|')  # file[#heading], [|rename]
    name = s[1] if len(s) == 2 else ''
    s = s[0].split('#')  # file, [#heading]
    heading = s[1] if len(s) == 2 else ''
    return s[0], heading, name


def read_link(vault, ob_file, data, link, exit_on_first=False):
    file, heading, _ = link

    if file != ob_file:
        with open(path.join(vault, f'{file}.md'), 'r', encoding='utf-8') as reader:
            data = reader.read()

    if heading:
        return find_heading(data, heading, exit_on_first)
    return data


def _main():
    db = 'C:\\mine\\Journey'

    anki_files = list()

    for root, dirs, files in os.walk(db):
        for f_name in files:
            f_path = os.path.join(root, f_name)

            if is_anki(f_path):
                anki_files.append(f_path)

    print('ANKI FILES:')
    for i, f in enumerate(anki_files):
        print(f'\t{i}: {f}')

        load_note(db, f)



if __name__ == '__main__':
    _main()

import os
import re

from difflib import SequenceMatcher
from collections import namedtuple
from pywinauto import Application
from os import path


DB = 'C:\\mine\\Journey'
REGISTRY = path.join(DB, 'q_reg_pending.md')

FileInfo = namedtuple('FileInfo', ['name', 'path'])



def main():
    registry = read_registry()
    if len(registry) == 0:
        print(f'No pending questions in {REGISTRY}')
        exit(os.EX_OK)

    # md_files = db_walk()

    # questions = read_questions()
    # answers = read_answers(questions)

    # app = Application().connect(title_re='.* Obsidian', timeout=1)
    # dlg = app.top_window()
    # print(dlg.children())


def read_registry():
    with open(REGISTRY, 'r') as f:
        links = re.findall(RePat.MD_LINK, f.read())

    pending_files = list()

    for link in links:
        f_path = link.split('|')[0]  # link may contain | (pipe), we are only interested in the preceding text
        f_path = path.join(DB, f'{f_path}.md')
        pending_files.append(f_path)

        with open(f_path, 'f') as f:
            f.readline()

    return pending_files

def search_db(text):
    links = re.findall(r'\[\[(.*?)]]', text)
    if len(links) != 1:
        # multiple links are present, how should we determine the answer?
        return ''

    link = links[0]




def read_answers(questions: list[str]) -> list[str]:
    answers = list()
    for i, q in enumerate(questions):
        if '(R:' in q:
            ans = re.search(r'\(R:(.*?)\)', q).group(1).strip()
        else:
            ans = search_db(q)

        answers.append(ans)

    return answers


def read_questions() -> list[str]:
    with open(REGISTRY, 'r') as f:
        reg = f.read()
    with open()

    questions = list()
    with open(path.join(os.getcwd(), 'questions.txt'), 'r', encoding='utf-8') as reader:
        for line in reader.readlines():
            q = line.strip().strip('\n')
            similarity = SequenceMatcher(None, q, )
            q = line.split(' ', maxsplit=1)[1]
            q = q.replace('\n', '')
            questions.append(q)

    return questions


def db_walk():
    md_files = list()

    for root, dirs, files in os.walk(DB):
        for file in files:

            if not file.endswith('.md'):
                continue

            name = file.strip('.md')
            p = path.join(root, name)

            md_files.append(FileInfo(name, p))

    return md_files


if __name__ == '__main__':
    main()

import os
import re

from os import path


class REGEX:
    MD_LINK = r'\[\[(.*?)]]'
    Q_HUB = r'#hub/(.*)'
    Q_TAG = r'#questions'
    Q_PREFIX = r'# Questões'




class Registry:
    def __init__(self, vault):
        self.vault = vault
        self.pending_links = list()
        self.entries = list()

    def read_pending(self, reg_path):
        with open(reg_path, 'r') as reader:
            links = re.findall(REGEX.MD_LINK, reader.read())

        self.pending_links = list()

        for link in links:
            f_path = link.split('|')[0]
            f_path = path.join(self.vault, f'{f_path}.md')
            self.pending_links.append(f_path)


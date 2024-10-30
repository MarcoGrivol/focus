import re
import os

from pathlib import Path
from os import path
from typing import Iterable, Tuple

_DEFAULTS = path.join(path.dirname(__file__), '_defaults')
_DEFAULT_OUTPUT_DIR = path.join(_DEFAULTS, 'out')
_DEFAULT_STYLES = path.join(_DEFAULTS, 'styles.css')


class Styles:
    _css_pattern = re.compile(
        r'\s*(?P<name>\.?.+?) *{(?P<body>[\s\S]*?)}',
        flags=re.MULTILINE
    )
    _callout_types = ('info', 'note', 'warning', 'error', 'danger')

    def __init__(self, default_styles):
        with open(default_styles, 'r', encoding='utf-8') as fp:
            data = fp.read()

        self._required_styles = {}
        for css in self._css_pattern.finditer(data):
            self._required_styles[css['name']] = css['body'].strip()

        self.css_data = self._required_styles

    def add_user_styles(self, user_styles):
        with open(user_styles, 'r', encoding='utf-8') as fp:
            data = fp.read()

        for css in self._css_pattern.finditer(data):
            if css['name'] not in self.css_data:
                print(f'WARNING: {css["name"]} may not be a valid identifier')
            self.css_data[css['name']] = css['body'].strip()

        self._validate_required_styles(self.css_data)  # just for sanity

    def _validate_required_styles(self, data: Iterable) -> None:
        # unnest all tags
        unique_tags = set()
        for tags in data:
            for t in tags.split(','):
                unique_tags.add(t.strip())

        req = set(self._required_styles)

        if not req.issubset(unique_tags):
            raise ValueError(f'missing styles: {req - unique_tags}')

    def to_string(self) -> str:
        buffer = ''
        for key, value in self.css_data.items():
            buffer += key + ' {\n'
            buffer += value + '\n'
            buffer += '}\n'
        return buffer

    def get_callout(self, callout_type: str) -> Tuple[str, str, str]:
        if callout_type not in self._callout_types:
            raise TypeError(f'invalid callout type: {callout_type}')
        c = 'callout'
        ch = f'{c}-header {c}-header-{callout_type}'
        cb = f'{c}-body {c}-body-{callout_type}'
        return c, ch, cb

    def get_class(self, key: str, variant=None) -> str | Tuple[str, str, str]:
        if variant is not None and '.callout' in key:
            return self.get_callout(variant)
        if key not in self._required_styles:
            raise TypeError(f'invalid style: {key}')
        return key[1:]  # remove the "." prefix

    def __getitem__(self, item):
        if item not in self.css_data:
            raise KeyError(f'invalid style: {item}')
        return self.css_data[item]


VAULT = None
PROFILE = None
OUTPUT_DIR = _DEFAULT_OUTPUT_DIR
STYLES = Styles(_DEFAULT_STYLES)


def update_with_user_settings(filepath) -> None:
    if not path.isfile(filepath):
        raise FileNotFoundError(filepath)

    with open(filepath, 'r', encoding='utf-8') as fp:
        data = fp.read()

    data = re.sub(r'#.*', '', data)

    _update_vault(data)
    _update_profile(data)
    _update_output_dir(data)
    _update_styles(data)


def _update_vault(data: str):
    dirpath = re.search('VAULT=(.*)', data)
    if dirpath is None:
        raise ValueError('"VAULT" must be specified in settings.txt')

    dirpath = Path(dirpath.group(1)).expanduser()
    if not dirpath.is_dir():
        raise NotADirectoryError(dirpath)

    global VAULT
    VAULT = path.normcase(dirpath)


def _update_profile(data):
    profile = re.search('PROFILE=(.*)', data)
    if profile is None:
        raise ValueError('"PROFILE" must be specified in settings.txt')

    global PROFILE
    PROFILE = profile.group(1)


def _update_output_dir(data: str):
    dirpath = re.search('OUTPUT_DIR=(.*)', data)
    if dirpath is None:
        out = _DEFAULT_OUTPUT_DIR
    else:
        out = Path(dirpath.group(1)).expanduser()

    if not out.is_dir():
        os.mkdir(out)

    global OUTPUT_DIR
    OUTPUT_DIR = out


def _update_styles(data: str):
    user_styles = re.search('STYLES=(.*)', data)
    if user_styles is None:
        return

    user_styles = user_styles.group(1)
    if not path.isfile(user_styles):
        raise FileNotFoundError(user_styles)

    STYLES.add_user_styles(user_styles)

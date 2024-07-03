from os import path
from typing import Dict, List

from crawler import NoteTree


def count_leaves(tree: List | NoteTree | Dict[str, List | Dict]) -> int:
    if isinstance(tree, list):
        return len(tree)
    return sum([count_leaves(tree[k]) for k in tree])


def build_filetree_view(treeview, parent_id, tree):
    for k in tree:
        if k == 'root':
            # insert files after directories
            continue
        new_parent_id = treeview.insert(parent_id, 'end', text=k, values=[count_leaves(tree[k]), ''])
        build_filetree_view(treeview, new_parent_id, tree[k])

    if 'root' in tree:
        for f, text in tree['root']:
            treeview.insert(parent_id, 'end', text=f, values=['', text])


def build_notetree_view(treeview, parent_id, tree: NoteTree) -> Dict[str, int]:
    index_map = {}
    for deck in tree:
        values = [count_leaves(tree[deck]), '', '']
        d_id = treeview.insert(parent_id, 'end', text=deck, values=values)

        for tag in tree[deck]:
            values = [count_leaves(tree[deck][tag]), '', '']
            t_id = treeview.insert(d_id, 'end', text=tag, values=values)

            for i, note in tree[deck][tag]:
                if note.is_valid():
                    status_text = 'OK'
                    status_tag = 'valid'
                else:
                    status_text = note.get_invalid_reason()
                    status_tag = 'invalid'

                iid = treeview.insert(
                    t_id,
                    'end',
                    text=note.relative_path,
                    values=['', status_text, note.text[:48] + '...'],
                    tags=['note', status_tag]
                )
                index_map[iid] = i
    return index_map


def open_tree_recursively(tree, event):
    def _open_children(parent):
        tree.item(parent, open=True)
        for child in tree.get_children(parent):
            _open_children(child)

    _open_children(tree.focus())

import os
import time
import webbrowser

from abc import ABC, abstractmethod
from typing import Callable, List
from tkinter import ttk
from tkinter import messagebox

import printer
import anki_handler
from anki_handler import AnkiNote
from crawler import VaultCrawler, ObsidianNote
from .utils import *
from display import messages as mbox

T_RATIO = 0.95


class AppController(ABC):
    @abstractmethod
    def func_continue(self, args):
        raise NotImplementedError

    @abstractmethod
    def func_back(self, args):
        raise NotImplementedError

    @abstractmethod
    def func_cancel(self, args):
        raise NotImplementedError


class AppStep(ABC):
    def __init__(self, parent: AppController, mainframe: ttk.Frame):
        self.parent = parent
        self._mainframe = mainframe

        self._buttons_frame = None
        self._contents_frame = None

    def mainloop(self):
        self._contents_frame = ttk.Frame(self._mainframe)
        self._buttons_frame = ttk.Frame(self._mainframe)

        self.build_contents()
        self.build_buttons()

        self._contents_frame.grid(column=0, row=0, sticky='NEWS')
        self._buttons_frame.grid(column=0, row=1, sticky='WE')

        self._mainframe.columnconfigure(0, weight=1)
        self._mainframe.rowconfigure(0, weight=1)

    @abstractmethod
    def set_input(self, *args):
        raise NotImplementedError

    @abstractmethod
    def build_contents(self):
        raise NotImplementedError

    @abstractmethod
    def build_buttons(self):
        raise NotImplementedError


class FirstStep(AppStep):
    def __init__(self, parent, mainframe: ttk.Frame):
        super().__init__(parent, mainframe)
        self._crawler: VaultCrawler | None = None

    def set_input(self, *args):
        self._crawler = args[0]

    def build_buttons(self):
        root = self._buttons_frame

        b_continue = ttk.Button(root, text='continue', command=self.parent.func_continue)
        b_cancel = ttk.Button(root, text='cancel', command=self.parent.func_cancel)
        b_refresh = ttk.Button(root, text='refresh', command=self.refresh)

        b_refresh.grid(column=0, row=0, sticky='W')
        b_cancel.grid(column=1, row=0)
        b_continue.grid(column=2, row=0)

        root.columnconfigure(0, weight=1)

    def refresh(self):
        for i in self._contents_frame.winfo_children():
            i.destroy()
        self._crawler.reset()
        self.build_contents()

    def build_contents(self):
        root = self._contents_frame

        treeview = ttk.Treeview(root, columns=['counter', 'anki_status'])

        tree = self._crawler.build_filetree()

        vid = treeview.insert('', 'end', text='Valid Anki files', values=[count_leaves(tree['valid_files']), ''])
        iid = treeview.insert('', 'end', text='Invalid Anki files', values=[count_leaves(tree['invalid_files']), ''])
        build_filetree_view(treeview, vid, tree['valid_files'])
        build_filetree_view(treeview, iid, tree['invalid_files'])

        treeview.heading('#0', text='File')
        treeview.heading('counter', text='# of files')
        treeview.heading('anki_status', text='Anki file status')

        treeview.column('counter', anchor='center')
        treeview.column('anki_status', anchor='center')

        treeview.grid(column=0, row=0, sticky='NEWS')

        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)


class SecondStep(AppStep):
    def __init__(self, parent: AppController, mainframe: ttk.Frame):
        super().__init__(parent, mainframe)

        self._crawler: VaultCrawler | None = None
        self._treeview: ttk.Treeview | None = None
        self._index_map: Dict[str, int] = {}

    def set_input(self, *args):
        self._crawler = args[0]

    def build_buttons(self):
        def continue_cmd(): self.execute(self.parent.func_continue)
        def preview_cmd(): self.execute(printer.webpreview)

        b_continue = ttk.Button(self._buttons_frame, text='continue', command=continue_cmd)
        b_cancel = ttk.Button(self._buttons_frame, text='cancel', command=self.parent.func_cancel)
        b_back = ttk.Button(self._buttons_frame, text='back', command=self.parent.func_back)
        b_refresh = ttk.Button(self._buttons_frame, text='refresh', command=self.refresh)
        b_preview = ttk.Button(self._buttons_frame, text='preview', command=preview_cmd)

        b_back.grid(column=0, row=0)
        b_refresh.grid(column=1, row=0, sticky='W')
        b_preview.grid(column=2, row=0, sticky='W')
        b_cancel.grid(column=3, row=0)
        b_continue.grid(column=4, row=0)

        self._buttons_frame.columnconfigure(1, weight=1)
        self._buttons_frame.columnconfigure(2, weight=1)

    def refresh(self) -> None:
        for i in self._contents_frame.winfo_children():
            i.destroy()
        self.build_contents()

    def execute(self, func: Callable):
        iid_list = self._treeview.selection()
        index_list = get_treeview_selection(self._treeview, iid_list, key=lambda x: 'valid' in x, option='tags')

        if len(index_list) == 0:
            mbox.Error.invalid_selection()
            return

        func([
            self._crawler.valid_notes[self._index_map[iid]]
            for iid in index_list
        ])

    def build_contents(self):
        self._treeview = ttk.Treeview(self._contents_frame, columns=['counter', 'status', 'text'])

        self._crawler.convert_files()
        v_tree, inv_tree = self._crawler.build_notetree()

        vid = self._treeview.insert('', 'end', 'valid', text='Valid notes', values=[count_leaves(v_tree), '', ''])
        iid = self._treeview.insert('', 'end', 'invalid', text='Invalid notes', values=[count_leaves(inv_tree), '', ''])
        self._index_map = build_notetree_view(self._treeview, vid, v_tree)
        self._index_map.update(build_notetree_view(self._treeview, iid, inv_tree))

        self._treeview.heading('#0', text='File')
        self._treeview.heading('status', text='Status')
        self._treeview.heading('text', text='Text')
        self._treeview.heading('counter', text='# of notes')

        self._treeview.column('status', anchor='center')
        self._treeview.column('text', anchor='center')
        self._treeview.column('counter', anchor='center')

        self._treeview.grid(column=0, row=0, sticky='NEWS')
        self._contents_frame.columnconfigure(0, weight=1)
        self._contents_frame.rowconfigure(0, weight=1)


class ThirdStep(AppStep):
    def __init__(self, parent: AppController, mainframe: ttk.Frame):
        super().__init__(parent, mainframe)

        self._md_notes: List[ObsidianNote] = []
        self._anki_entries: List[AnkiNote] = []
        self._index_map: Dict[str, int] = {}

        self._treeview: ttk.Treeview | None = None

    def set_input(self, *args):
        if isinstance(args[0][0], ObsidianNote):
            self._md_notes = args[0]

    def build_buttons(self):
        def continue_cmd(): self.execute(self.parent.func_continue)

        b_continue = ttk.Button(self._buttons_frame, text='continue', command=continue_cmd)
        b_cancel = ttk.Button(self._buttons_frame, text='cancel', command=self.parent.func_cancel)
        b_back = ttk.Button(self._buttons_frame, text='back', command=self.parent.func_back)
        b_refresh = ttk.Button(self._buttons_frame, text='refresh', command=self.refresh)

        b_back.grid(column=0, row=0)
        b_refresh.grid(column=1, row=0, sticky='W')
        b_cancel.grid(column=2, row=0)
        b_continue.grid(column=3, row=0)

        self._buttons_frame.columnconfigure(1, weight=1)

    def refresh(self):
        for i in self._contents_frame.winfo_children():
            i.destroy()
        self.build_contents()

    def generate_anki_entries(self):
        self._anki_entries = []
        for md_note in self._md_notes:
            front, back = printer.note_to_html(list(md_note.get_fields()))
            note = AnkiNote(md_note.deck, front, back, md_note.tags)
            self._anki_entries.append(note)

    def execute(self, func):
        iid_list = self._treeview.selection()
        index_list = get_treeview_selection(self._treeview, iid_list, key=lambda x: 'valid' in x, option='tags')

        selected_entries = [self._anki_entries[self._index_map[iid]] for iid in index_list]

        if len(selected_entries) == 0:
            mbox.Error.invalid_selection()
            return

        ratio_warn = len(list(filter(lambda n: n.exceeds_threshold(T_RATIO), selected_entries))) > 0
        if ratio_warn > 0:
            if mbox.Alert.duplicated_notes(ratio_warn, T_RATIO) is not True:
                return

        func(selected_entries)

    def build_contents(self):
        print(f'Started Anki preparation on selected items: step build_contents()')

        self.generate_anki_entries()
        self._index_map = {}

        self._treeview = ttk.Treeview(self._contents_frame, columns=['dt', 'status', 'ratio', 'text'])

        ok_id = self._treeview.insert('', 'end', 'can_add', text='Can add')
        dup_id = self._treeview.insert('', 'end', 'duplicated', text='Duplicated')
        err_id = self._treeview.insert('', 'end', 'error', text='Error')

        notes = [note.to_json() for note in self._anki_entries]
        result = anki_handler.invoke('canAddNotesWithErrorDetail', notes=notes)

        for i, res in enumerate(result):
            print(f'\t ({i + 1})/{len(result)}: {self._md_notes[i].relative_path} response={res}')

            parent, text, values, tags = self.create_treeview(i, res, ok_id, dup_id, err_id)

            iid = self._treeview.insert(parent, 'end', text=text, values=values, tags=tags)
            self._index_map[iid] = i

        self.style_tree()

    def create_treeview(self, i, res, ok_id, dup_id, err_id):
        md_note = self._md_notes[i]
        anki_entry = self._anki_entries[i]

        anki_entry.parse_can_add_response(res)

        tags = []
        if anki_entry.is_valid():
            status = 'OK'
            parent = ok_id

            tags.append('valid')
            if anki_entry.exceeds_threshold(T_RATIO):
                tags.append('ratio_warn')

        else:
            status = anki_entry.status
            if status == 'cannot create note because it is a duplicate':
                parent = dup_id
                anki_entry.set_ratio(*anki_entry.calculate_ratio())
                if anki_entry.exceeds_threshold(T_RATIO):
                    tags.append('ratio_warn')
            else:
                parent = err_id

        text = md_note.relative_path
        values = [
            anki_entry.convert_to_nested_tags(),
            status,
            f'{anki_entry.q_ratio:.2f} {anki_entry.ans_ratio:.2f}',
            md_note.text[:48]
        ]
        return parent, text, values, tags

    def style_tree(self):
        self._treeview.tag_configure('ratio_warn', background='#ffed7d')

        self._treeview.heading('#0', text='File')
        self._treeview.heading('dt', text='deck::tag')
        self._treeview.heading('status', text='Status')
        self._treeview.heading('ratio', text='Ratio')
        self._treeview.heading('text', text='Text')

        self._treeview.column('dt', width=32)
        self._treeview.column('status', width=32)
        self._treeview.column('ratio', width=10, anchor='center')
        self._treeview.column('text', width=48)

        self._treeview.grid(column=0, row=0, sticky='NEWS')
        self._contents_frame.columnconfigure(0, weight=1)
        self._contents_frame.rowconfigure(0, weight=1)


class FourthStep(AppStep):
    def __init__(self, parent: AppController, mainframe: ttk.Frame):
        super().__init__(parent, mainframe)

        self._anki_entries: List[AnkiNote] | None = None
        self.results: List[int | None] = []

    def set_input(self, *args):
        if len(args[0]) < 1:
            raise ValueError('At least one AnkiNote must be present for insertion')
        self._anki_entries = args[0]

    def build_buttons(self):
        def back_cmd(): self.revert(self.parent.func_back)
        def close_cmd(): self.revert(self.parent.func_continue)

        b_back = ttk.Button(self._buttons_frame, text='revert and back', command=back_cmd)
        b_rev_close = ttk.Button(self._buttons_frame, text='revert and close', command=close_cmd)
        b_close = ttk.Button(self._buttons_frame, text='close', command=self.safe_quit)

        b_back.grid(column=0, row=0, sticky='W')
        b_rev_close.grid(column=1, row=0)
        b_close.grid(column=2, row=0)

        self._buttons_frame.columnconfigure(0, weight=1)

    def build_contents(self):
        self.results = anki_handler.invoke('addNotes', notes=[note.to_json() for note in self._anki_entries])

        treeview = ttk.Treeview(self._contents_frame, columns=['deck', 'tags', 'text'])

        for i, res in enumerate(self.results):
            note = self._anki_entries[i].to_json()
            if res is None:
                status = 'ERROR'
            else:
                status = res
            treeview.insert(
                '', 'end', text=status,
                values=[
                    note['deckName'],
                    note['tags'][0],
                    note['fields']['Question'][:32]
                ]
            )

        treeview.heading('#0', text='Result')
        treeview.heading('deck', text='Deck')
        treeview.heading('tags', text='Tags')
        treeview.heading('text', text='Text')

        treeview.grid(column=0, row=0, sticky='NEWS')
        self._contents_frame.columnconfigure(0, weight=1)
        self._contents_frame.rowconfigure(0, weight=1)

    def revert(self, func: Callable):
        notes = list(filter(lambda x: x is not None, self.results))
        anki_handler.invoke('deleteNotes', notes=notes)
        func(self._anki_entries)

    def safe_quit(self):
        if None in self.results:
            if mbox.Alert.add_notes_failed() is not True:
                return
        self.gui_quick_check()
        self.parent.func_continue(None)

    def gui_quick_check(self):
        print(f'Rendering latex equations, please wait...')
        for i, res in enumerate(self.results):
            if res is None:
                continue
            print(f'\t{i+1}/{len(self.results)}: editing {res}')
            anki_handler.invoke('guiEditNote', note=res)
            time.sleep(0.5)

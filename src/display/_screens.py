import os
import time
import webbrowser

from abc import ABC, abstractmethod
from typing import Callable, List
from tkinter import ttk
from tkinter import messagebox

import printer
import anki_handler
from crawler import VaultCrawler, AnkiNote
from ._utils import *

RATIO_THRESHOLD_WARNING = 0.95


class AppStep(ABC):
    def __init__(self, mainframe: ttk.Frame, f_back, f_cancel, f_continue, mbox_window):
        self._mainframe = mainframe

        self._buttons_frame = None
        self._contents_frame = None
        self._mbox_window = mbox_window

        self._continue_func = f_continue
        self._cancel_func = f_cancel
        self._back_func = f_back

    def mainloop(self):
        self._contents_frame = ttk.Frame(self._mainframe)
        self._buttons_frame = ttk.Frame(self._mainframe)

        self.build_contents()
        self.build_buttons()

        self._contents_frame.grid(column=0, row=0, sticky='NEWS')
        self._buttons_frame.grid(column=0, row=1, sticky='WE')

        self._mainframe.columnconfigure(0, weight=1)
        self._mainframe.rowconfigure(0, weight=1)

    def set_continue(self, func: Callable):
        self._continue_func = func

    def set_cancel(self, func: Callable):
        self._cancel_func = func

    def set_back(self, func: Callable):
        self._back_func = func

    def set_messagebox_window(self, window):
        self._mbox_window = window

    @abstractmethod
    def build_contents(self):
        raise NotImplementedError

    @abstractmethod
    def build_buttons(self):
        raise NotImplementedError

    @abstractmethod
    def pass_forward(self):
        raise NotImplementedError

    @abstractmethod
    def receive_message(self, message: object):
        raise NotImplementedError


class FirstStep(AppStep):
    def __init__(self, mainframe: ttk.Frame, f_back, f_cancel, f_continue, mbox_window):
        super().__init__(mainframe, f_back, f_cancel, f_continue, mbox_window)
        self._crawler: VaultCrawler | None = None

    def receive_message(self, message: VaultCrawler):
        self._crawler = message

    def pass_forward(self):
        return self._crawler

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

    def build_buttons(self):
        root = self._buttons_frame

        b_continue = ttk.Button(root, text='continue', command=self._continue_func)
        b_cancel = ttk.Button(root, text='cancel', command=self._cancel_func)
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


class SecondStep(AppStep):
    def __init__(self, mainframe: ttk.Frame, f_back, f_cancel, f_continue, mbox_window):
        super().__init__(mainframe, f_back, f_cancel, f_continue, mbox_window)

        self._crawler: VaultCrawler | None = None
        self.selected_notes: List[int] = []
        self._treeview: ttk.Treeview | None = None
        self._index_map: Dict[str, int] = {}

    def receive_message(self, message: VaultCrawler):
        self._crawler = message

    def pass_forward(self) -> list[AnkiNote]:
        return [self._crawler.valid_notes[i] for i in self.selected_notes]

    def refresh(self) -> None:
        for i in self._contents_frame.winfo_children():
            i.destroy()
        self.build_contents()

    def continue_with_selection(self):
        self.selected_notes = self.selected_items(self._treeview.selection())
        if len(self.selected_notes) == 0:
            messagebox.showerror(
                'Invalid selection',
                'Please select at least one valid note to continue',
                parent=self._mbox_window,
                icon='warning'
            )
            return
        self._continue_func()

    def build_buttons(self):
        b_continue = ttk.Button(self._buttons_frame, text='continue', command=self.continue_with_selection)
        b_cancel = ttk.Button(self._buttons_frame, text='cancel', command=self._cancel_func)
        b_back = ttk.Button(self._buttons_frame, text='back', command=self._back_func)
        b_refresh = ttk.Button(self._buttons_frame, text='refresh', command=self.refresh)
        b_open = ttk.Button(self._buttons_frame, text='open', command=self.open_selection)

        b_back.grid(column=0, row=0)
        b_refresh.grid(column=1, row=0, sticky='W')
        b_open.grid(column=2, row=0, sticky='W')
        b_cancel.grid(column=3, row=0)
        b_continue.grid(column=4, row=0)

        self._buttons_frame.columnconfigure(1, weight=1)
        self._buttons_frame.columnconfigure(2, weight=1)

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

    def selected_items(self, iid_list):
        notes = []
        for iid in iid_list:
            tags = self._treeview.item(iid)['tags']
            if 'note' not in tags:
                notes.extend(self.selected_items(self._treeview.get_children(iid)))
            elif 'valid' in tags:
                idx = self._index_map[iid]
                notes.append(idx)
        return notes

    def open_selection(self):
        notes = self.selected_items(self._treeview.selection())
        notes = [self._crawler.valid_notes[i] for i in notes]
        if len(notes) == 0:
            print('ZERO valid notes selected, nothing to show')
            return

        filepath = path.join(os.getcwd(), 'tmp.html')
        with open(filepath, 'w', encoding='utf-8') as fp:
            buf = printer.notes_webview(notes)
            fp.write(buf)

        webbrowser.open('file:///' + filepath)


class ThirdStep(AppStep):
    def __init__(self, mainframe: ttk.Frame, f_back, f_cancel, f_continue, mbox_window):
        super().__init__(mainframe, f_back, f_cancel, f_continue, mbox_window)
        self.notes: List[AnkiNote] = []
        self.selected_notes: List[int] = []

        self.is_startup_ok, self.changes = anki_handler.startup()

        self.treeview: ttk.Treeview | None = None
        self.anki_entry: List[anki_handler.AnkiJsonEntry] = []
        self.index_map: Dict[str, int] = {}

    def receive_message(self, message: List[AnkiNote]):
        self.notes = message

    def pass_forward(self) -> List[anki_handler.AnkiJsonEntry]:
        return [self.anki_entry[i] for i in self.selected_notes]

    def mainloop(self):
        if not self.is_startup_ok:
            self.changes_warning()
        super().mainloop()

    def build_buttons(self):
        b_continue = ttk.Button(self._buttons_frame, text='continue', command=self.continue_with_selection)
        b_cancel = ttk.Button(self._buttons_frame, text='cancel', command=self._cancel_func)
        b_back = ttk.Button(self._buttons_frame, text='back', command=self._back_func)
        b_refresh = ttk.Button(self._buttons_frame, text='refresh', command=self.refresh)

        b_back.grid(column=0, row=0)
        b_refresh.grid(column=1, row=0, sticky='W')
        b_cancel.grid(column=2, row=0)
        b_continue.grid(column=3, row=0)

        self._buttons_frame.columnconfigure(1, weight=1)

    def continue_with_selection(self):
        def selected_items(_iid_list):
            _notes = []
            for _iid in _iid_list:
                _children = self.treeview.get_children(_iid)
                if len(_children) > 0:
                    _notes.extend(selected_items(_children))
                elif 'note' in self.treeview.item(_iid, option='tags'):
                    _notes.append(self.index_map[_iid])
            return _notes

        self.selected_notes = selected_items(self.treeview.selection())

        ratio_exceed = 0
        valid_count = 0
        for i in self.selected_notes:
            note = self.anki_entry[i]
            if not note.is_valid():
                continue
            if note.q_ratio > RATIO_THRESHOLD_WARNING or note.ans_ratio > RATIO_THRESHOLD_WARNING:
                ratio_exceed += 1
            valid_count += 1

        if valid_count == 0:
            messagebox.showerror(
                'Invalid selection',
                'Please select at least one valid note to continue',
                parent=self._mbox_window,
                icon='warning'
            )
            return
        elif ratio_exceed > 0:
            msg = f'Selection may contain duplicated notes.\n'
            msg += f'\t possible number of duplicated notes: {ratio_exceed}\n'
            msg += f'\t ratio: {RATIO_THRESHOLD_WARNING}'
            response = messagebox.askyesno(
                'Possible duplicates',
                msg,
                parent=self._mbox_window,
                icon='warning'
            )
            if response is not True:
                return

        self._continue_func()

    def build_contents(self):
        print(f'Started third step build_contents()')

        self.generate_anki_entries()
        self.index_map = {}

        self.treeview = ttk.Treeview(self._contents_frame, columns=['dt', 'status', 'ratio', 'text'])

        ok_id = self.treeview.insert('', 'end', 'can_add', text='Can add')
        dup_id = self.treeview.insert('', 'end', 'duplicated', text='Duplicated')
        err_id = self.treeview.insert('', 'end', 'error', text='Error')

        notes = [note.to_json() for note in self.anki_entry]
        result = anki_handler.invoke('canAddNotesWithErrorDetail', notes=notes)

        for i, res in enumerate(result):
            print(f'\t ({i + 1})/{len(result)}: {self.notes[i].relative_path} response={res}')

            parent, text, values = self.create_treeview(i, res, ok_id, dup_id, err_id)

            iid = self.treeview.insert(parent, 'end', text=text, values=values, tags=['note'])
            if self.anki_entry[i].exceeds_threshold(RATIO_THRESHOLD_WARNING):
                self.treeview.item(iid, tags=['ratio_warn', 'note'])

            self.index_map[iid] = i

        self.style_tree()

    def create_treeview(self, i, res, ok_id, dup_id, err_id):
        note = self.anki_entry[i]
        note.parse_can_add_response(res)

        if note.is_valid():
            status = 'OK'
            parent = ok_id
        else:
            status = note.status
            if status == 'cannot create note because it is a duplicate':
                parent = dup_id
            else:
                parent = err_id

        text = self.notes[i].relative_path
        values = [
            note.convert_to_nested_tags(),
            status,
            f'{note.q_ratio:.2f} {note.ans_ratio:.2f}',
            self.notes[i].text[:48]
        ]
        return parent, text, values

    def generate_anki_entries(self):
        self.anki_entry = []
        for md_note in self.notes:
            front, back = printer.note_to_html(list(md_note.get_fields()))
            note = anki_handler.AnkiJsonEntry(md_note.deck, front, back, md_note.tags)
            self.anki_entry.append(note)

    def changes_warning(self):
        message = f'Changes to {anki_handler.MODEL_NAME} are required:\n'
        for i, key in enumerate(self.changes):
            message += f'\n{i + 1}. modify model {key}:\n'
            if isinstance(self.changes[key], str):
                message += '\t' + self.changes[key] + '\n'
            else:
                for subkey in self.changes[key]:
                    message += f'\t{subkey}: {len(self.changes[key][subkey])}\n'

        message += '\nDo you want to apply the changes?'

        response = messagebox.askyesnocancel(
            parent=self._mbox_window,
            message=message,
            title='Modify',
            icon='warning'
        )

        if response is True:
            anki_handler.apply_changes(self.changes)
            changes_applied, _ = anki_handler.check_for_changes()
            if not changes_applied:
                raise ValueError('unable to apply all required changes')
            self.is_startup_ok = True

        elif response is False:
            print('WARNING: continuing with wrong settings')
        else:
            self._cancel_func()

    def refresh(self):
        for i in self._contents_frame.winfo_children():
            i.destroy()
        self.build_contents()

    def style_tree(self):
        self.treeview.tag_configure('ratio_warn', background='#ffed7d')

        self.treeview.heading('#0', text='File')
        self.treeview.heading('dt', text='deck::tag')
        self.treeview.heading('status', text='Status')
        self.treeview.heading('ratio', text='Ratio')
        self.treeview.heading('text', text='Text')

        self.treeview.column('dt', width=32)
        self.treeview.column('status', width=32)
        self.treeview.column('ratio', width=10, anchor='center')
        self.treeview.column('text', width=48)

        self.treeview.grid(column=0, row=0, sticky='NEWS')
        self._contents_frame.columnconfigure(0, weight=1)
        self._contents_frame.rowconfigure(0, weight=1)


class FourthStep(AppStep):
    def __init__(self, mainframe: ttk.Frame, f_back, f_cancel, f_continue, mbox_window):
        super().__init__(mainframe, f_back, f_cancel, f_continue, mbox_window)
        self.notes: List[anki_handler.AnkiJsonEntry] = []
        self.results = []
        self.has_errors = False

    def receive_message(self, message: List[anki_handler.AnkiJsonEntry]):
        self.notes = message

    def pass_forward(self):
        raise NotImplementedError

    def build_buttons(self):
        b_back = ttk.Button(self._buttons_frame, text='back', command=self.revert_and_back)
        b_rev_close = ttk.Button(self._buttons_frame, text='revert and close', command=self.revert_and_close)
        b_close = ttk.Button(self._buttons_frame, text='close', command=self.close)

        b_back.grid(column=0, row=0, sticky='W')
        b_rev_close.grid(column=1, row=0)
        b_close.grid(column=2, row=0)

        self._buttons_frame.columnconfigure(0, weight=1)

    def build_contents(self):
        self.results = anki_handler.invoke('addNotes', notes=[note.to_json() for note in self.notes])

        treeview = ttk.Treeview(self._contents_frame, columns=['deck', 'tags', 'text'])

        for i, res in enumerate(self.results):
            note = self.notes[i].to_json()
            if res is None:
                self.has_errors = True
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

    def revert(self):
        notes = list(filter(lambda x: x is not None, self.results))
        anki_handler.invoke('deleteNotes', notes=notes)

    def revert_and_back(self):
        self.revert()
        self._back_func()

    def revert_and_close(self):
        self.revert()
        self._continue_func()

    def close(self):
        if self.has_errors:
            msg = 'Errors occurred when trying to add notes.\n'
            msg += 'Are you sure you want to leave?\n'
            msg += '\t(Recommended action: [revert and back])'
            response = messagebox.askyesno(
                'Errors detected',
                msg,
                parent=self._mbox_window,
                icon='warning'
            )
            if response is not True:
                return
        self.gui_quick_check()
        self._continue_func()

    def gui_quick_check(self):
        for res in self.results:
            if res is None:
                continue
            anki_handler.invoke('guiEditNote', note=res)
            time.sleep(0.5)


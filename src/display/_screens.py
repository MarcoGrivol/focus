import os
import tkinter
import webbrowser

from abc import ABC, abstractmethod
from typing import Callable
from tkinter import ttk

import printer
from crawler import VaultCrawler, AnkiNote
from ._utils import *


class AppStep(ABC):
    def __init__(self, mainframe: ttk.Frame):
        self.mainframe = mainframe

        self.buttons_frame = ttk.Frame(self.mainframe)
        self.contents_frame = ttk.Frame(self.mainframe)

        self.continue_func = None
        self.cancel_func = None
        self.back_func = None

    def mainloop(self):
        self.build_contents()
        self.build_buttons()

        self.contents_frame.grid(column=0, row=0, sticky='NEWS')
        self.buttons_frame.grid(column=0, row=1, sticky='WE')

        self.mainframe.columnconfigure(0, weight=1)
        self.mainframe.rowconfigure(0, weight=1)

    def set_continue(self, func: Callable):
        self.continue_func = func

    def set_cancel(self, func: Callable):
        self.cancel_func = func

    def set_back(self, func: Callable):
        self.back_func = func

    @abstractmethod
    def build_contents(self):
        pass

    @abstractmethod
    def build_buttons(self):
        pass


class FirstStep(AppStep):
    def __init__(self, mainframe: ttk.Frame, crawler: VaultCrawler):
        super().__init__(mainframe)

        self.crawler = crawler

    def build_contents(self):
        root = self.contents_frame

        treeview = ttk.Treeview(root, columns=['counter', 'anki_status'])

        tree = self.crawler.build_filetree()

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
        root = self.buttons_frame

        b_continue = ttk.Button(root, text='continue', command=self.continue_func)
        b_cancel = ttk.Button(root, text='cancel', command=self.cancel_func)
        b_refresh = ttk.Button(root, text='refresh', command=self.refresh)

        b_refresh.grid(column=0, row=0, sticky='W')
        b_cancel.grid(column=1, row=0)
        b_continue.grid(column=2, row=0)

        root.columnconfigure(0, weight=1)

    def refresh(self):
        for i in self.contents_frame.winfo_children():
            i.destroy()
        self.crawler.reset()
        self.build_contents()


class SecondStep(AppStep):
    def __init__(self, mainframe: ttk.Frame, crawler: VaultCrawler):
        super().__init__(mainframe)

        self.crawler = crawler
        self.treeview = None
        self.selected_note: AnkiNote | None = None

    def build_buttons(self):
        root = self.buttons_frame

        b_continue = ttk.Button(root, text='continue', command=self.continue_func)
        b_cancel = ttk.Button(root, text='cancel', command=self.cancel_func)
        b_back = ttk.Button(root, text='back', command=self.back_func)
        b_refresh = ttk.Button(root, text='refresh', command=self.refresh)
        b_open = ttk.Button(root, text='open', command=self.open_note)

        b_back.grid(     column=0, row=0)
        b_refresh.grid(  column=1, row=0, sticky='W')
        b_open.grid(     column=2, row=0, sticky='W')
        b_cancel.grid(   column=3, row=0)
        b_continue.grid( column=4, row=0)

        root.columnconfigure(1, weight=1)
        root.columnconfigure(2, weight=1)

    def build_contents(self):
        self.treeview = ttk.Treeview(self.contents_frame, columns=['counter', 'status', 'text'])
        self.treeview.tag_bind('note', '<<TreeviewSelect>>', self.note_selected)

        self.crawler.convert_files()
        v_tree, inv_tree = self.crawler.build_notetree()

        vid = self.treeview.insert('', 'end', 'valid', text='Valid notes', values=[count_leaves(v_tree), '', ''])
        iid = self.treeview.insert('', 'end', 'invalid', text='Invalid notes', values=[count_leaves(inv_tree), '', ''])
        build_notetree_view(self.treeview, vid, v_tree)
        build_notetree_view(self.treeview, iid, inv_tree)

        self.treeview.heading('#0', text='File')
        self.treeview.heading('status', text='Status')
        self.treeview.heading('text', text='Text')
        self.treeview.heading('counter', text='# of notes')

        self.treeview.column('status', anchor='center')
        self.treeview.column('text', anchor='center')
        self.treeview.column('counter', anchor='center')

        self.treeview.grid(column=0, row=0, sticky='NEWS')
        self.contents_frame.columnconfigure(0, weight=1)
        self.contents_frame.rowconfigure(0, weight=1)

    def refresh(self) -> None:
        for i in self.contents_frame.winfo_children():
            i.destroy()
        self.build_contents()

    def note_selected(self, event: tkinter.Event) -> None:
        iid = self.treeview.selection()[0]
        tags = self.treeview.item(iid, 'tags')
        index, is_valid = int(tags[1]), int(tags[2])
        if is_valid:
            self.selected_note = self.crawler.valid_notes[index]
        else:
            self.selected_note = self.crawler.invalid_notes[index]

    def open_note(self):
        if self.selected_note is None:
            return
        front, back = printer.note_to_html(list(self.selected_note.get_fields()))

        filepath = path.join(os.getcwd(), 'tmp.html')
        with open(filepath, 'w', encoding='utf-8') as fp:
            fp.write('Front:<br>' + front)
            fp.write('<br>Back:<br>' + back)

        webbrowser.open('file:///' + filepath)




class ThirdStep(AppStep):
    def __init__(self, mainframe: ttk.Frame, crawler: VaultCrawler):
        super().__init__(mainframe)
        self.crawler = crawler

    def build_buttons(self):
        root = self.buttons_frame

        def _open():
            file = 'file:///C:/mine/cs/focus/web/index_linked.html'
            webbrowser.open(file)

        b_open = ttk.Button(root, text='open', command=_open)

        b_open.grid(column=0, row=0)

    def build_contents(self):
        root = self.contents_frame

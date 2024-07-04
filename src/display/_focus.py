from os import path

from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from typing import List

from crawler import VaultCrawler
from ._screens import FirstStep, SecondStep, ThirdStep, FourthStep, AppController
from display import messages as mbox

from anki_handler import MODEL_NAME
import anki_handler





def changes_warning(changes):
    response = mbox.Alert.model_changes_required(changes, MODEL_NAME)
    if response is True:
        anki_handler.apply_changes(changes)
        changes_applied, _ = anki_handler.check_for_changes()
        if not changes_applied:
            raise ValueError('unable to apply all required changes')

    elif response is False:
        print('WARNING: continuing with wrong settings')
    else:
        raise ValueError('unable to apply changes')


class Focus(AppController):
    def __init__(self, root, crawler: VaultCrawler):
        self._root_window = root

        self._mainframe = ttk.Frame(root, padding=(5, 5, 5, 5))
        self._crawler = crawler

        self._step_label = ttk.LabelFrame(self._mainframe, text="Steps")
        self._step_frame = ttk.Frame(self._mainframe)

        self._mainframe.grid(column=0, row=0, sticky='NSEW')
        self._step_label.grid(column=0, row=0, sticky='NEW')
        self._step_frame.grid(column=0, row=1, sticky='NEWS')

        self._mainframe.columnconfigure(0, weight=3)
        self._mainframe.rowconfigure(1, weight=1)

        self._apps = [
            FirstStep(self, self._mainframe),
            SecondStep(self, self._mainframe),
            ThirdStep(self, self._mainframe),
            FourthStep(self, self._mainframe)
        ]
        self._app_index = -1

    def mainloop(self):
        self.func_continue(self._crawler)

    def func_continue(self, args=None):
        if self._app_index == len(self._apps) - 1:
            self._mainframe.quit()
        else:
            self._app_index += 1
            self._execute(args)

    def func_back(self, args=None):
        if self._app_index == 0:
            self._mainframe.quit()
        else:
            self._app_index -= 1
            self._execute(args)

    def func_cancel(self, args=None):
        self._mainframe.quit()

    def _execute(self, args):
        for w in self._step_frame.winfo_children():
            w.destroy()

        i = self._app_index
        step = self._apps[i]
        if isinstance(step, (FirstStep, SecondStep)):
            step.set_input(self._crawler)
        else:
            step.set_input(args)

        step.mainloop()




def focus(crawler: VaultCrawler):

    is_startup_ok, changes = anki_handler.startup()
    if not is_startup_ok:
        changes_warning(changes)

    root = Tk()
    root.columnconfigure(0, weight=1, minsize=900)
    root.rowconfigure(0, weight=1, minsize=600)

    app = Focus(root, crawler)
    app.mainloop()

    root.mainloop()

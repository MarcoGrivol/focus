from os import path

from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from typing import List

from crawler import VaultCrawler
from ._screens import FirstStep, SecondStep, ThirdStep, FourthStep


class Focus:
    def __init__(self, root, crawler: VaultCrawler):
        self.stored_obj = None
        self.mainframe = ttk.Frame(root, padding=(5, 5, 5, 5))
        self.crawler = crawler

        self.step_label = ttk.LabelFrame(self.mainframe, text="Steps")
        self.step_frame = ttk.Frame(self.mainframe)

        self.mainframe.grid(column=0, row=0, sticky='NSEW')
        self.step_label.grid(column=0, row=0, sticky='NEW')
        self.step_frame.grid(column=0, row=1, sticky='NEWS')

        self.mainframe.columnconfigure(0, weight=3)
        self.mainframe.rowconfigure(1, weight=1)

        self.steps = [
            self._first_step,
            self._second_step,
            self._third_step,
            self._fourth_step
        ]
        self.curr_step = -1

    def mainloop(self):
        self.forward()

    def forward(self, stored_obj=None):
        self.stored_obj = stored_obj
        self.curr_step += 1
        self._execute()

    def backwards(self):
        self.stored_obj = None
        self.curr_step -= 1
        self._execute()

    def _execute(self):
        self._clear_step()
        self.steps[self.curr_step]()

    def _clear_step(self):
        for i in self.step_frame.winfo_children():
            i.destroy()

    def _first_step(self):
        label = ttk.Label(self.step_label, text='1. Validate parsed anki files')
        label.grid(column=0, row=0, sticky='NSW')

        step = FirstStep(self.step_frame, self.crawler)
        step.set_continue(self.forward)
        step.set_cancel(self.mainframe.quit)
        step.mainloop()

    def _second_step(self):
        label = ttk.Label(self.step_label, text='2. Convert markdown to html')
        label.grid(column=0, row=1, sticky='NSW')

        step = SecondStep(self.step_frame, self.crawler)
        step.set_continue(self.forward)
        step.set_back(self.backwards)
        step.set_cancel(self.mainframe.quit)
        step.mainloop()

    def _third_step(self):
        label = ttk.Label(self.step_label, text='3. Validate files with Anki')
        label.grid(column=0, row=2, sticky='NSW')

        step = ThirdStep(self.step_frame, self.stored_obj)
        step.set_continue(self.forward)
        step.set_back(self.backwards)
        step.set_cancel(self.mainframe.quit)
        step.mainloop()

    def _fourth_step(self):
        label = ttk.Label(self.step_label, text='4. Anki results')
        label.grid(column=0, row=3, sticky='NSW')

        step = FourthStep(self.step_frame, self.stored_obj)
        step.set_back(self.backwards)
        step.set_cancel(self.mainframe.quit)
        step.mainloop()


def focus(crawler: VaultCrawler):
    root = Tk()
    root.columnconfigure(0, weight=1, minsize=900)
    root.rowconfigure(0, weight=1, minsize=600)

    app = Focus(root, crawler)
    app.mainloop()

    root.mainloop()

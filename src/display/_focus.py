from os import path

from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from typing import List

from crawler import VaultCrawler
from ._screens import FirstStep, SecondStep, ThirdStep, FourthStep, AppStep


class Focus:
    def __init__(self, root, crawler: VaultCrawler):
        self.root_window = root

        self.mainframe = ttk.Frame(root, padding=(5, 5, 5, 5))
        self.crawler = crawler

        self.step_label = ttk.LabelFrame(self.mainframe, text="Steps")
        self.step_frame = ttk.Frame(self.mainframe)

        self.mainframe.grid(column=0, row=0, sticky='NSEW')
        self.step_label.grid(column=0, row=0, sticky='NEW')
        self.step_frame.grid(column=0, row=1, sticky='NEWS')

        self.mainframe.columnconfigure(0, weight=3)
        self.mainframe.rowconfigure(1, weight=1)

        self.step_funcs = [
            self._first_step,
            self._second_step,
            self._third_step,
            self._fourth_step,
        ]
        self.step_objs = [
            FirstStep(self.step_frame, self.backwards, self.mainframe.quit, self.forward, self.root_window),
            SecondStep(self.step_frame, self.backwards, self.mainframe.quit, self.forward, self.root_window),
            ThirdStep(self.step_frame, self.backwards, self.mainframe.quit, self.forward, self.root_window),
            FourthStep(self.step_frame, self.backwards, self.mainframe.quit, self.forward, self.root_window),
        ]
        self.curr_step = -1

    def mainloop(self):
        self.forward()

    def forward(self):
        if self.curr_step == -1:
            message = self.crawler
        else:
            message = self.step_objs[self.curr_step].pass_forward()

        self.curr_step += 1
        self.step_objs[self.curr_step].receive_message(message)
        self._execute()

    def backwards(self):
        self.curr_step -= 1
        self._execute()

    def _execute(self):
        self._clear_step()
        step_obj = self.step_objs[self.curr_step]
        self.step_funcs[self.curr_step](step_obj)

    def _clear_step(self):
        for i in self.step_frame.winfo_children():
            i.destroy()

    def _first_step(self, step: FirstStep):
        label = ttk.Label(self.step_label, text='1. Validate parsed anki files')
        label.grid(column=0, row=0, sticky='NSW')

        step.mainloop()

    def _second_step(self, step: SecondStep):
        label = ttk.Label(self.step_label, text='2. Convert markdown to html')
        label.grid(column=0, row=1, sticky='NSW')

        step.mainloop()

    def _third_step(self, step: ThirdStep):
        label = ttk.Label(self.step_label, text='3. Validate files with Anki')
        label.grid(column=0, row=2, sticky='NSW')

        step.mainloop()

    def _fourth_step(self, step: FourthStep):
        label = ttk.Label(self.step_label, text='4. Anki results')
        label.grid(column=0, row=3, sticky='NSW')

        step.set_continue(self.mainframe.quit)
        step.mainloop()


def focus(crawler: VaultCrawler):
    root = Tk()
    root.columnconfigure(0, weight=1, minsize=900)
    root.rowconfigure(0, weight=1, minsize=600)

    app = Focus(root, crawler)
    app.mainloop()

    root.mainloop()
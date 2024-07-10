from tkinter import messagebox


class Error:
    parent = None

    @classmethod
    def invalid_selection(cls):
        title = 'Invalid selection'
        msg = 'Please select at least one valid item to continue'
        messagebox.showerror(title, msg, parent=cls.parent)


class Alert:
    parent = None

    @classmethod
    def duplicated_notes(cls, dup_count, t_ratio):
        title = 'Duplicated notes detected'

        msg = f'Selection may contain duplicated notes.\n'
        msg += f'\t possible number of duplicated notes: {dup_count}\n'
        msg += f'\t ratio: {t_ratio}\n\n'
        msg += 'Do you wish to proceed?'

        return messagebox.askyesno(title, msg, icon='warning', parent=cls.parent)

    @classmethod
    def add_notes_failed(cls):
        title = 'Errors when adding notes'

        msg = 'Errors occurred when trying to add notes.\n'
        msg += 'Are you sure you want to leave?\n'
        msg += '\t(Recommended action: [revert and back])'

        return messagebox.askyesno(title, msg, icon='warning', parent=cls.parent)

    @classmethod
    def model_changes_required(cls, changes, model_name):
        title = 'Modify Anki model'

        msg = f'Changes to {model_name} are required:\n'

        for i, key in enumerate(changes):
            msg += f'\n{i + 1}. modify model {key}:\n'
            if isinstance(changes[key], str):
                msg += '\t' + changes[key] + '\n'
            else:
                for subkey in changes[key]:
                    msg += f'\t{subkey}: {len(changes[key][subkey])}\n'

        msg += '\nDo you want to apply the changes?'

        return messagebox.askyesnocancel(title=title, message=msg, icon='warning', parent=cls.parent)

# SPDX-License-Identifier: Apache-2.0
"""Optional stdlib Tk window; the same engine also supports terminal prompts."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText


class UIUnavailable(Exception):
    pass


def run(workflow):
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise UIUnavailable(str(error)) from error
    root.title('Surface Duo 2 beta installer')
    root.geometry('760x480')
    tk.Label(root, text='Surface Duo 2 beta', font=('', 20, 'bold')).pack(anchor='w', padx=20, pady=(16, 4))
    tk.Label(root, text='Guided preparation, installation and verification. Keep the phone connected.').pack(anchor='w', padx=20)
    footer = tk.Frame(root)
    footer.pack(side='bottom', fill='x', padx=20, pady=(0, 14))
    log = ScrolledText(root, wrap='word', state='disabled', font=('', 11), height=12)
    log.pack(fill='both', expand=True, padx=20, pady=16)
    requests = queue.Queue()
    busy = [True]

    class UI:
        def call(self, kind, *args):
            reply = queue.Queue()
            requests.put((kind, args, reply))
            value = reply.get()
            if isinstance(value, Exception):
                raise value
            return value

        def log(self, text):
            requests.put(('log', (str(text),), None))

        def confirm(self, text):
            from installer import need
            need(self.call('confirm', text), 'Cancelled. No further steps were taken.')

        step = confirm

        def typed(self, text, word):
            from installer import need
            need(self.call('typed', text + '\n\nType ' + word + ' to confirm.') == word,
                 'Cancelled. No erase/unlock request was sent.')

        def choice(self, text, choices):
            from installer import need
            result = self.call('choice', text, choices)
            need(result is not None, 'Cancelled.')
            return result

        def file(self, text, default=''):
            from pathlib import Path
            from installer import need
            result = self.call('file', text, default)
            need(result, 'Cancelled.')
            return Path(result).expanduser().resolve()

    def choose(text, choices):
        window = tk.Toplevel(root)
        window.title('Choose a step')
        window.transient(root)
        window.grab_set()
        answer = [None]
        tk.Label(window, text=text, wraplength=600, justify='left').pack(padx=20, pady=16)
        for key, label in choices:
            def selected(value=key):
                answer[0] = value
                window.destroy()
            tk.Button(window, text=label, command=selected, anchor='w', padx=14, pady=10).pack(fill='x', padx=20, pady=4)
        tk.Button(window, text='Cancel', command=window.destroy).pack(pady=12)
        root.wait_window(window)
        return answer[0]

    def poll():
        while not requests.empty():
            kind, args, reply = requests.get()
            try:
                if kind == 'log':
                    log.config(state='normal')
                    log.insert('end', args[0] + '\n\n')
                    log.see('end')
                    log.config(state='disabled')
                    continue
                if kind == 'done':
                    busy[0] = False
                    close.config(state='normal')
                    continue
                if kind == 'confirm':
                    value = messagebox.askokcancel('Next step', args[0], parent=root)
                elif kind == 'typed':
                    value = simpledialog.askstring('Data will be erased', args[0], parent=root)
                elif kind == 'choice':
                    value = choose(*args)
                else:
                    text, default = args
                    if 'folder' in text.lower():
                        value = filedialog.askdirectory(title=text, mustexist=False, parent=root)
                    else:
                        value = filedialog.askopenfilename(title=text, parent=root)
                reply.put(value)
            except Exception as error:
                if reply:
                    reply.put(error)
        root.after(100, poll)

    def worker():
        ui = UI()
        try:
            workflow(ui)
        except Exception as error:
            ui.log('Stopped safely: ' + str(error) + '\nSee START-HERE and your local session folder. Do not repeat a flash or choose a wipe to fix an error.')
        finally:
            requests.put(('done', (), None))

    def closing():
        if busy[0]:
            messagebox.showinfo('Installer is active', 'Use Cancel in a step prompt to stop safely. During an installation, keep the window and USB connection open until it finishes.', parent=root)
        else:
            root.destroy()

    close = tk.Button(footer, text='Close', command=closing, state='disabled')
    close.pack(anchor='e')
    root.protocol('WM_DELETE_WINDOW', closing)
    root.after(100, poll)
    root.after(250, lambda: threading.Thread(target=worker, daemon=True).start())
    root.mainloop()

# -*- coding: utf-8 -*-
import tkinter
from .decorators import join_positional_args, wordseps
from argparse import ArgumentParser

class MessageBox(object):

    def __init__(self, msg, b1, b2, choices):

        font = ('Sans', 8)
        root = self.root = tkinter.Tk()
        root.title('Mensaje')
        self.msg = str(msg)
        # remove the outer frame if frame=False
        # default values for the buttons to return
        self.b1_return = True
        self.b2_return = False
        # main frame
        frm_1 = tkinter.Frame(root)
        frm_1.pack(ipadx=2, ipady=2)
        # the message
        message = tkinter.Label(frm_1, text=self.msg, font=font, wraplength=500)
        message.pack(padx=8, pady=8)
        # if entry=True create and set focus
        if choices:
            self.b2_return = None
            self.listbox = tkinter.Listbox(frm_1, selectmode=tkinter.BROWSE, font=font, background='white', width=40)
            self.listbox.bind('<Double-Button>', self.b1_action)
            self.listbox.pack()
            self.listbox.focus_set()
            for i in choices:
                self.listbox.insert(tkinter.END, i)
        # button frame
        frm_2 = tkinter.Frame(frm_1)
        frm_2.pack(padx=4, pady=4)
        # buttons
        btn_1 = tkinter.Button(frm_2, width=8, text=b1, font=font)
        btn_1['command'] = self.b1_action
        btn_1.pack(side='left', padx=3)
        btn_1.bind('<KeyPress-Return>', func=self.b1_action)
        if b2:
            btn_2 = tkinter.Button(frm_2, width=8, text=b2, font=font)
            btn_2['command'] = self.b2_action
            btn_2.pack(side='left', padx=3)
            btn_2.bind('<KeyPress-Return>', func=self.b2_action)
        # roughly center the box on screen
        #root.update_idletasks()
        xp = max(root.winfo_pointerx() - root.winfo_rootx() - 200, 0)
        yp = max(root.winfo_pointery() - root.winfo_rooty() - 100, 0)
        root.geometry('+{0}+{1}'.format(xp, yp))
        # call self.close_mod when the close button is pressed
        root.protocol("WM_DELETE_WINDOW", self.close_mod)

    def b1_action(self, event=None):
        try: x = self.listbox.curselection()
        except AttributeError:
            self.returning = self.b1_return
            self.root.quit()
        else:
            if x:
                self.returning = x
                self.root.quit()

    def b2_action(self, event=None):
        self.returning = self.b2_return
        self.root.quit()

    # remove this function and the call to protocol
    # then the close button will act normally
    def close_mod(self):
        pass

    def to_clip(self, event=None):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.msg)

@join_positional_args(wordseps)
def ynbox(prompt):
    msgbox = MessageBox(prompt, 'Si', 'No', None)
    msgbox.root.mainloop()
    # the function pauses here until the mainloop is quit
    msgbox.root.destroy()
    return msgbox.returning

@join_positional_args(wordseps)
def msgbox(message):
    msgbox = MessageBox(message, 'OK', None, None)
    msgbox.root.mainloop()
    # the function pauses here until the mainloop is quit
    msgbox.root.destroy()

@join_positional_args(wordseps)
def listbox(message, choices):
    msgbox = MessageBox(message, 'Continuar', 'Cancelar', choices)
    msgbox.root.mainloop()
    # the function pauses here until the mainloop is quit
    msgbox.root.destroy()
    if msgbox.returning is None:
        return None
    else:
        return choices[msgbox.returning[0]]

def optionbox():
    parser = ArgumentParser(description='Crea un cuadro de diálogo con una lista de opciones.')
    parser.add_argument('-o', '--option', metavar=('DESCRIPCIÓN', 'COMANDO'), dest='options', action='append', nargs=2, help='Agregar opción a la lista de opciones')
    parser.add_argument('message', metavar='MENSAJE', type=str, help='Mensaje del cuadro de diálogo.')
    arguments = parser.parse_args()
    choice = listbox(arguments.message, choices=[i for i,j in arguments.options])
    if choice is not None:
         print(dict(arguments.options)[choice])


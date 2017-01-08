#!/usr/bin/env python3

# main.py -- uPython Helper main file
#
# Copyright (C)2017 Casten Riepling
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from tkinter import *
import tkinter.scrolledtext as tkst
import sys
from time import sleep
from tkinter.messagebox import showwarning, askquestion
from tkinter.ttk import Treeview
from tkinter import filedialog
import base64
from tkinter import ttk
import threading

# hack for forwards compatibility for serial_device2 on windows
import os

if os.name == 'nt':
    import winreg
    sys.modules['_winreg'] = winreg

# noinspection PyPep8
from serial_device2 import SerialDevice

# noinspection PyPep8Naming
class uPythonHelperUI:
    # ----------------------------------------------------------------------
    # | MainFrame
    # | ---------------------------------------  --------------------------- |
    # | | TermFrame                           |  | File Frame              | |
    # | | ---------------------------------   |  | ----------------------- | |
    # | | | PortFrame                     |   |  | | Transfer Frame      | | |
    # | | ---------------------------------   |  | ----------------------- | |
    # | | ---------------------------------   |  | ----------------------- | |
    # | | | TermView                      |   |  | | FileView            | | |
    # | | ---------------------------------   |  | ----------------------- | |
    # | ---------------------------------------  --------------------------- |
    # ----------------------------------------------------------------------
    def __init__(self):
        self.dev = None
        self.pauseUpdate = True
        self.fileView = None
        self.uploadButton = None
        self.downloadButton = None
        self.deleteButton = None
        self.connectButton = None
        self.portName = None
        self.termArea = None
        self.progress = None
        self.connected = False

        root = Tk()

        mainFrame = Frame(root)
        root.title("uPython Helper")
        mainFrame.pack(padx=10, pady=10)

        # Terminal Side
        termFrame = Frame(mainFrame)
        termFrame.pack(padx=1, pady=1, side=LEFT)

        portFrame = Frame(termFrame)
        portFrame.pack(padx=1, pady=1, side=TOP, fill=X)

        Label(portFrame, text='Port/Device').pack(side=LEFT)

        self.portName = Entry(portFrame)
        self.portName.pack(padx=1, pady=1, side=LEFT)

        #If not Windows, user might try the following:
        # '/dev/ttyUSB0' # Linux
        # '/dev/tty.usbmodem262471' # Mac OS X
        self.portName.insert(0, 'COM3')

        self.connectButton = Button(portFrame, text='Connect', command=self.onConnect)
        self.connectButton.pack(padx=1, pady=1, side=LEFT)

        self.progress = ttk.Progressbar(portFrame, orient="horizontal", length=200, mode="determinate")
        self.progress.pack()

        self.termArea = tkst.ScrolledText(
            master=termFrame,
            wrap=WORD,
            width=100,
            height=30,
            padx=10,
            pady=10,
            takefocus=True,
            background='lightgrey'
        )
        self.termArea.bind('<Key>', self.handleInput)
        self.termArea.bind('<Return>', self.handleInput)
        self.termArea.pack(padx=2, pady=2, side=BOTTOM)

        # File area
        self.fileFrame = Frame(mainFrame)
        self.fileFrame.pack(padx=2, pady=2, side=RIGHT, fill=Y)

        transferFrame = Frame(self.fileFrame)
        transferFrame.pack(padx=1, pady=1, side=TOP, fill=X)

        self.uploadButton = Button(transferFrame, text='Upload File', command=self.uploadFile, state=DISABLED)
        self.uploadButton.pack(padx=1, pady=1, side=LEFT)

        self.downloadButton = Button(transferFrame, text='Download File', command=self.downloadFile, state=DISABLED)
        self.downloadButton.pack(padx=1, pady=1, side=LEFT)

        self.deleteButton = Button(transferFrame, text='Delete File', command=self.deleteFile, state=DISABLED)
        self.deleteButton.pack(padx=1, pady=1, side=LEFT)

        self.fileView = Treeview(self.fileFrame)
        self.fileView["columns"] = "bytes"
        self.fileView.heading("#0", text="filename", anchor=W)
        self.fileView.column("bytes", width=75)
        self.fileView.heading("bytes", text="bytes", anchor=W)
        self.fileView.pack(side=RIGHT, fill=Y)


        termUpdateTimer = None

        def updateDataIfNeeded():
            global termUpdateTimer
            if not self.pauseUpdate:
                if self.dev:
                    if self.dev.in_waiting:
                        resp = self.dev.read_all()
                        self.write(resp)
            termUpdateTimer = threading.Timer(0.5, updateDataIfNeeded)
            termUpdateTimer.start()

        termUpdateTimer = threading.Timer(0.5, updateDataIfNeeded)
        termUpdateTimer.start()

        def on_closing():
            global termUpdateTimer
            root.destroy()
            termUpdateTimer.cancel()

        def make_menu(w):
            global the_menu
            the_menu = Menu(w, tearoff=0)
            the_menu.add_command(label="Copy")
            the_menu.add_command(label="Paste")

        def show_menu(e):
            w = e.widget
            the_menu.entryconfigure("Copy",
                                    command=lambda: w.event_generate("<<Copy>>"))
            the_menu.entryconfigure("Paste",
                                    command=lambda: w.event_generate("<<Paste>>"))
            the_menu.tk.call("tk_popup", the_menu, e.x_root, e.y_root)

        make_menu(root)

        self.termArea.bind("<Button-3><ButtonRelease-3>", show_menu)

        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()

    def remote(self, cmd, ignoreResult=False):
        asc = cmd.encode('ascii', 'ignore')
        self.pauseUpdate = True
        self.dev.write(asc)
        if ignoreResult:
            self.pauseUpdate = False
            return
        sleep(0.5)
        res = self.dev.read_all()
        self.pauseUpdate = False
        return res

    def write(self, txt):
        self.termArea.insert(END, txt)

    def handleInput(self, inputData):
        if self.connected:
            self.remote(inputData.char, ignoreResult=True)
        return "break"

    @staticmethod
    def ascii(uni):
        return uni.encode('ascii', 'ignore')

    def getDirInfo(self):
        self.remote("import os\r\n")
        resp = self.remote("os.listdir()\r\n")
        resp = resp.decode().split("\r\n")[1]
        entries = eval(resp)
        result = []
        for entry in entries:
            resp = self.remote("statinfo = os.stat('{}')\r\nstatinfo\r\n".format(entry))
            resp = resp.decode().split("\r\n")[2]
            statinfo = eval(resp)
            result.append({'name': entry, 'size': statinfo[6]})
        return result

    def uploadFile(self):
        def thrProc():
            filename = filedialog.askopenfile(mode='r')
            if filename is None:
                return
            self.progressStart()
            f = open(filename.name, 'rb')
            bytesRead = f.read()
            b64 = base64.b64encode(bytesRead)
            fn = os.path.split(filename.name)[1]
            self.remote('import ubinascii\r\n')
            self.remote('f = open("{}","w")\r\n'.format(fn))
            b64Len = len(b64)
            chunkSize = 1024
            for i in range(0, b64Len // chunkSize):
                sub = b64[chunkSize * i:(chunkSize * (i + 1))].decode()
                self.remote('s = "{}"\r\n'.format(sub))
                self.remote('s2 = ubinascii.a2b_base64(s)\r\n')
                self.remote('f.write(s2)\r\n', True)
            if b64Len % chunkSize:
                sub = b64[b64Len // chunkSize * chunkSize:b64Len].decode()
                self.remote('s = "{}"\r\n'.format(sub))
                self.remote('s2 = ubinascii.a2b_base64(s)\r\n')
                self.remote('f.write(s2)\r\n', True)
            self.remote('f.close()\r\n', True)
            self.clearFileView()
            self.populateFileView()
            self.progressStop()

        t1 = threading.Thread(target=thrProc)
        t1.start()

    def downloadFile(self):
        def thrProc():
            selected = self.fileView.selection()
            if not selected:
                showwarning("Download", "Please select an item.")
                return
            if len(selected) > 1:
                showwarning("Download", "Please select a single item.")
                return
            sel = self.fileView.item(selected[0])

            filename = filedialog.asksaveasfile(mode='w', initialfile=sel['text'])
            if filename is None:
                return

            self.progressStart()
            fLocal = open(filename.name, 'wb')
            remoteName = sel['text']
            remoteSize = sel['values'][0]
            self.remote('import ubinascii\r\n')
            self.remote('f = open("{}","r")\r\n'.format(remoteName))

            for i in range(0, remoteSize // 1024):
                self.remote("data = f.read(1024)\r\n")
                self.remote('s2 = ubinascii.b2a_base64(data)\r\n')
                resp = self.remote('print(s2)\r\n')
                resp = resp.decode().split("\r\n")[1][2:].split("\\")[0]
                chunkBin = base64.b64decode(resp)
                fLocal.write(chunkBin)

            remainder = remoteSize % 1024
            if remainder:
                self.remote("data = f.read({})\r\n".format(remainder))
                self.remote('s2 = ubinascii.b2a_base64(data)\r\n')
                resp = self.remote('print(s2)\r\n')
                resp = resp.decode().split("\r\n")[1][2:].split("\\")[0]
                tailBin = base64.b64decode(resp)
                fLocal.write(tailBin)
            fLocal.close()
            self.remote('f.close()\r\n')
            self.progressStop()

        t1 = threading.Thread(target=thrProc)
        t1.start()

    def deleteFile(self):
        def thrProc():
            selected = self.fileView.selection()
            if not selected:
                showwarning("Delete", "Please select an item to delete.")
                return
            if len(selected) > 1:
                showwarning("Delete", "Please select a single item.")
                return

            sel = self.fileView.item(selected[0])
            res = askquestion("Delete", 'Are you sure you want to delete "{}"?'.format(sel['text']), icon='warning')
            if res != 'yes':
                return

            self.progressStart()
            self.remote('import os\r\n')
            self.remote('os.remove("{}")\r\n'.format(sel['text']))
            self.fileView.delete(selected[0])
            self.progressStop()

        t1 = threading.Thread(target=thrProc)
        t1.start()

    def populateFileView(self):
        info = self.getDirInfo()
        for item in info:
            values = item['size']
            self.fileView.insert('', 'end', iid=None, text=item['name'], values=values)

    def clearFileView(self):
        self.fileView.delete(*self.fileView.get_children())

    def progressStart(self):
        self.progress["mode"] = "indeterminate"
        self.progress.start(10)

    def progressStop(self):
        self.progress.stop()
        self.progress["mode"] = "determinate"

    def onConnect(self):
        def thrproc():
            if self.connectButton.cget('relief') == 'raised':
                self.progressStart()
                try:
                    port = self.portName.get()
                    self.dev = SerialDevice(port=port)
                except Exception as e:
                    if self.downloadButton:
                        self.downloadButton.config(state=DISABLED)
                        self.uploadButton.config(state=DISABLED)
                        self.deleteButton.config(state=DISABLED)
                    showwarning("Connect", "Problem opening serial.  Details:\n" + str(e))
                    return

                self.dev.baudrate = 115200
                self.connectButton.config(relief=SUNKEN)
                # send ctrl-c to break any potentially running python program
                ctrlc = chr(3)
                self.remote(ctrlc)
                self.populateFileView()
                self.termArea.insert(END, ">>> ")  # write out the initial prompt... purely cosmetic
                self.termArea.config(background='white')
                self.downloadButton.config(state=NORMAL)
                self.uploadButton.config(state=NORMAL)
                self.deleteButton.config(state=NORMAL)
                self.connected = True
            else:
                self.connected = False
                if self.dev is not None:
                    self.dev.close()
                self.dev = None
                self.connectButton.config(relief=RAISED)
                self.downloadButton.config(state=DISABLED)
                self.deleteButton.config(state=DISABLED)
                self.uploadButton.config(state=DISABLED)
                self.clearFileView()
                self.termArea.config(background='lightgrey')

            self.progressStop()

        t1 = threading.Thread(target=thrproc)
        t1.start()

# fire up the UI
ui = uPythonHelperUI()

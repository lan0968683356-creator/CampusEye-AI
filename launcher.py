"""CampusEye AI desktop launcher: a simple window to start and stop the local site."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
import threading
import webbrowser

from werkzeug.serving import make_server

from app import app, monitor

URL = 'http://127.0.0.1:5000'


def main():
    root = tk.Tk()
    root.title('CampusEye AI｜桌面啟動器')
    root.geometry('420x245')
    root.resizable(False, False)
    root.configure(bg='#f5f8ff')

    tk.Label(root, text='CampusEye AI', font=('Segoe UI', 22, 'bold'),
             fg='#315fec', bg='#f5f8ff').pack(pady=(20, 3))
    tk.Label(root, text='校園智慧安全與人流分析系統', font=('Microsoft JhengHei UI', 11),
             fg='#566580', bg='#f5f8ff').pack(pady=(0, 12))

    try:
        server = make_server('127.0.0.1', 5000, app, threaded=True)
    except OSError as exc:
        messagebox.showerror('無法啟動', f'網站埠 5000 可能已被其他程式使用。\n\n請先關閉舊版 CMD 網站，再試一次。\n\n{exc}')
        root.destroy()
        return

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    tk.Label(root, text='● 系統已啟動（僅本機存取）', font=('Microsoft JhengHei UI', 10),
             fg='#159970', bg='#f5f8ff').pack(pady=(0, 9))

    tk.Button(root, text='開啟 CampusEye AI 網站', command=lambda: webbrowser.open(URL),
              font=('Microsoft JhengHei UI', 11, 'bold'), bg='#3869f5', fg='white',
              relief='flat', padx=20, pady=8, cursor='hand2').pack()

    closing = False

    def quit_app():
        nonlocal closing
        if closing:
            return
        closing = True
        monitor.stop()
        server.shutdown()
        root.destroy()

    tk.Button(root, text='結束程式', command=quit_app, font=('Microsoft JhengHei UI', 10),
              bg='#f5f8ff', fg='#566580', relief='flat', pady=7,
              cursor='hand2').pack(pady=(3, 0))
    root.protocol('WM_DELETE_WINDOW', quit_app)
    root.after(700, lambda: webbrowser.open(URL))
    root.mainloop()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-25 19:38:55 krylon>
#
# /data/code/python/hollywoo/gui.py
# created on 24. 06. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the PyKuang network scanner. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
hollywoo.gui

(c) 2025 Benjamin Walkenhorst
"""

from threading import Lock
from typing import Final

import gi  # type: ignore

from hollywoo import common
from hollywoo.database import Database

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")

from gi.repository import \
    Gdk as gdk  # noqa: E402,F401 pylint: disable-msg=C0413,C0411,W0611 # type: ignore
from gi.repository import \
    GLib as glib  # noqa: E402,F401 pylint: disable-msg=C0413,C0411,W0611 # type: ignore
from gi.repository import \
    Gtk as gtk  # noqa: E402,F401 pylint: disable-msg=C0413,C0411,W0611 # type: ignore


class GUI:  # pylint: disable-msg=I1101,E1101
    """A GUI like no other."""

    def __init__(self) -> None:
        self.log = common.get_logger("gui")
        self.lock = Lock()
        self.db = Database()

        root_cols: Final[list[tuple[str, type]]] = [
            ("ID", int),
            ("Path", str),
            ("Last Scan", str),
            ("Remote?", bool),
        ]

        vid_cols: Final[list[tuple[str, type]]] = [  # noqa: F841 pylint: disable-msg=W0612
            ("ID", int),
            ("Path", str),
            ("Title", str),
            ("Resolution", str),
            ("Duration", str),
            ("Tags", str),
            ("People", str),
        ]

        tag_cols: Final[list[tuple[str, type]]] = [  # noqa: F841 pylint: disable-msg=W0612
            ("ID", int),
            ("Name", str),
        ]

        # Create the widgets.

        self.win = gtk.Window()
        self.win.set_title(f"{common.APP_NAME} {common.APP_VERSION}")
        self.mbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)
        self.notebook = gtk.Notebook.new()  # pylint: disable-msg=E1120

        # Create the menu

        self.menubar = gtk.MenuBar()

        self.mb_file_item = gtk.MenuItem.new_with_mnemonic("_File")
        self.mb_edit_item = gtk.MenuItem.new_with_mnemonic("_Edit")
        self.mb_debug_item = gtk.MenuItem.new_with_mnemonic("_Debug")

        self.menu_file = gtk.Menu()
        self.menu_edit = gtk.Menu()

        self.fm_item_add = gtk.MenuItem.new_with_mnemonic("_Add Folder")
        self.fm_item_scan = gtk.MenuItem.new_with_mnemonic("_Scan Folders")
        self.fm_item_quit = gtk.MenuItem.new_with_mnemonic("_Quit")

        # Create the TreeViews and models

        self.root_store = gtk.ListStore(*(c[1] for c in root_cols))
        self.root_view = gtk.TreeView(model=self.root_store)
        self.root_sw = gtk.ScrolledWindow.new(None, None)

        for c in ((i, root_cols[i][0]) for i in range(len(root_cols))):
            col = gtk.TreeViewColumn(c[1],
                                     gtk.CellRendererText(),
                                     text=c[0],
                                     size=12)
            self.root_view.append_column(col)

        self.vid_store = gtk.ListStore(*(c[1] for c in vid_cols))
        self.vid_view = gtk.TreeView(model=self.vid_store)
        self.vid_sw = gtk.ScrolledWindow.new(None, None)

        for c in ((i, vid_cols[i][0]) for i in range(len(vid_cols))):
            col = gtk.TreeViewColumn(c[1],
                                     gtk.CellRendererText(),
                                     text=c[0],
                                     size=12)
            self.vid_view.append_column(col)

        # Assemble the widgets

        self.win.add(self.mbox)

        self.mbox.pack_start(self.menubar,
                             False,
                             True,
                             0)
        self.mbox.pack_start(self.notebook,
                             False,
                             True,
                             0)

        self.root_sw.add(self.root_view)
        self.vid_sw.add(self.vid_view)

        self.notebook.append_page(
            self.root_sw,
            gtk.Label.new("Folders"),
        )

        self.notebook.append_page(
            self.vid_sw,
            gtk.Label.new("Videos"),
        )

        # Register signal handlers

        self.win.connect("destroy", self._quit)

        # And show yourself, you cowardly window!

        self.win.show_all()
        self.win.visible = True

    def run(self):
        """Execute the Gtk event loop."""
        gtk.main()

    def _quit(self, *_ignore):
        self.win.destroy()
        gtk.main_quit()


if __name__ == '__main__':
    w = GUI()
    w.run()


# Local Variables: #
# python-indent: 4 #
# End: #

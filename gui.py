#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-07-03 16:07:09 krylon>
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

import os
import subprocess
from collections import defaultdict
from datetime import datetime
from enum import Enum, auto
from queue import Empty, Queue, ShutDown
from threading import Lock, Thread
from typing import Any, Final, NamedTuple, Optional

import gi  # type: ignore
import krylib

from hollywoo import common
from hollywoo.config import Config
from hollywoo.database import Database
from hollywoo.model import Folder, Person, Tag, Video
from hollywoo.scanner import Scanner

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")

from gi.repository import \
    Gdk as \
    gdk  # noqa: E402,F401 # pylint: disable-msg=C0413,C0411,W0611 # type: ignore
from gi.repository import \
    GLib as \
    glib  # noqa: E402,F401 # pylint: disable-msg=C0413,C0411,W0611 # type: ignore
from gi.repository import \
    Gtk as \
    gtk  # noqa: E402,F401 # pylint: disable-msg=C0413,C0411,W0611 # type: ignore

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
    ("Video ID", int),
    ("Video Title", str),
    ("Video Res", str),
    ("Video Dur", str),
]

person_cols: Final[list[tuple[str, type]]] = [
    ("ID", int),                # 0
    ("Name", str),              # 1
    ("Born", int),              # 2
    ("Role", str),              # 3
    ("Video ID", int),          # 4
    ("Video Title", str),       # 5
    ("Video Res", str),         # 6
    ("Video Dur", str),         # 7
]

roles: Final[list[str]] = ["Actor", "Director"]


class MsgType(Enum):
    """MsgType identifies a type of event the GUI thread might want to know about."""

    NothingBurger = auto()
    ScanComplete = auto()
    ScanError = auto()
    PlayFinished = auto()


class Message(NamedTuple):
    """Message is a tag and a payload to inform the GUI of things happening in other threads."""

    tag: MsgType
    payload: Any


class GUI:  # pylint: disable-msg=I1101,E1101,R0902
    """A GUI like no other."""

    def __init__(self) -> None:
        self.log = common.get_logger("gui")
        self.lock = Lock()
        self.db = Database()
        self.mq: Queue[Message] = Queue()
        self.display_hidden: bool = False
        self.vids: dict[int, Video] = {}

        self.cfg: Config = Config()
        self.display_hidden = self.cfg.get("GUI", "DisplayHidden")

        # Create the widgets.

        self.win = gtk.Window()
        self.win.set_title(f"{common.APP_NAME} {common.APP_VERSION}")
        self.mbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)
        self.notebook = gtk.Notebook.new()  # pylint: disable-msg=E1120

        # Create the menu
        self.__create_menus()

        # Create the TreeViews and models
        self.__create_views()

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
        self.tag_sw.add(self.tag_view)
        self.person_sw.add(self.person_view)

        self.notebook.append_page(
            self.root_sw,
            gtk.Label.new("Folders"))

        self.notebook.append_page(
            self.vid_sw,
            gtk.Label.new("Videos"))

        self.notebook.append_page(
            self.tag_sw,
            gtk.Label.new("Tags"))

        self.notebook.append_page(
            self.person_sw,
            gtk.Label.new("People"))

        # Register signal handlers

        self.win.connect("destroy", self._quit)

        self.fm_item_quit.connect("activate", self._quit)
        self.fm_item_add.connect("activate", self.handle_add_folder)
        self.fm_item_reload.connect("activate", self._reload_data)

        self.em_tag_create.connect("activate", self.handle_create_tag)
        self.em_person_create.connect("activate", self.handle_person_create)
        self.em_show_hidden.connect("activate", self._toggle_show_hidden_cb)

        self.dbg_purge_item.connect("activate", self._purge)
        self.dbg_wstate_item.connect("activate", self._save_window_state)

        self.vid_view.connect("button-press-event",
                              self._handle_vid_view_click)

        glib.timeout_add(500, self.check_queue)
        # TODO I really should listen for changes in size or position, this is
        #      rather crude.
        # self.win.connect("window-state-event", self._save_window_state)
        # glib.timeout_add(15000, self._save_window_state)

        # And show yourself, you cowardly window!

        self.win.show_all()
        self.win.visible = True

        glib.timeout_add(50, self._load_data)
        glib.timeout_add(60, self._load_tags)
        glib.timeout_add(70, self._load_people)
        glib.timeout_add(25, self._restore_window_state)

    def __create_menus(self) -> None:
        self.menubar = gtk.MenuBar()

        self.mb_file_item = gtk.MenuItem.new_with_mnemonic("_File")
        self.mb_edit_item = gtk.MenuItem.new_with_mnemonic("_Edit")
        self.mb_debug_item = gtk.MenuItem.new_with_mnemonic("_Debug")

        self.menu_file = gtk.Menu()
        self.menu_edit = gtk.Menu()
        self.menu_debug = gtk.Menu()

        self.fm_item_add = gtk.MenuItem.new_with_mnemonic("_Add Folder")
        self.fm_item_scan = gtk.MenuItem.new_with_mnemonic("_Scan Folders")
        self.fm_item_reload = gtk.MenuItem.new_with_mnemonic("_Reload all")
        self.fm_item_quit = gtk.MenuItem.new_with_mnemonic("_Quit")

        self.menubar.add(self.mb_file_item)
        self.menubar.add(self.mb_edit_item)
        self.menubar.add(self.mb_debug_item)

        self.mb_file_item.set_submenu(self.menu_file)
        self.menu_file.add(self.fm_item_add)
        self.menu_file.add(self.fm_item_scan)
        self.menu_file.add(self.fm_item_reload)
        self.menu_file.add(self.fm_item_quit)

        self.em_show_hidden = gtk.CheckMenuItem.new_with_mnemonic("Display _Hidden?")
        self.em_show_hidden.set_active(self.display_hidden)
        self.em_tag_create = gtk.MenuItem.new_with_mnemonic("Create _Tag")
        self.em_person_create = gtk.MenuItem.new_with_mnemonic("Create _Person")

        self.mb_edit_item.set_submenu(self.menu_edit)
        self.menu_edit.add(self.em_tag_create)
        self.menu_edit.add(self.em_person_create)
        self.menu_edit.add(self.em_show_hidden)

        self.mb_debug_item.set_submenu(self.menu_debug)
        self.dbg_purge_item = gtk.MenuItem.new_with_mnemonic("_Purge deleted Videos")
        self.dbg_wstate_item = gtk.MenuItem.new_with_mnemonic("Save _window state")
        self.menu_debug.add(self.dbg_purge_item)
        self.menu_debug.add(self.dbg_wstate_item)

    def __create_views(self) -> None:
        self.root_store = gtk.ListStore(*(c[1] for c in root_cols))
        self.root_view = gtk.TreeView(model=self.root_store)
        self.root_sw = gtk.ScrolledWindow.new(None, None)
        self.root_sw.set_vexpand(True)
        self.root_sw.set_hexpand(True)

        for c in ((i, root_cols[i][0]) for i in range(len(root_cols))):
            col = gtk.TreeViewColumn(c[1],
                                     gtk.CellRendererText(),
                                     text=c[0],
                                     editable=False,
                                     size=12)
            col.set_reorderable(True)
            col.set_resizable(True)
            self.root_view.append_column(col)

        self.vid_store = gtk.ListStore(*(c[1] for c in vid_cols))
        self.vid_filter = self.vid_store.filter_new()
        self.vid_filter.set_visible_func(self._vid_visible_fn)
        self.vid_view = gtk.TreeView(model=self.vid_filter)
        self.vid_sw = gtk.ScrolledWindow.new(None, None)
        self.vid_sw.set_vexpand(True)
        self.vid_sw.set_hexpand(True)

        for c in ((i, vid_cols[i][0]) for i in range(len(vid_cols))):
            col = gtk.TreeViewColumn(c[1],
                                     gtk.CellRendererText(),
                                     text=c[0],
                                     editable=False,
                                     size=12)
            col.set_reorderable(True)
            col.set_resizable(True)
            self.vid_view.append_column(col)

        self.tag_store = gtk.TreeStore(*(c[1] for c in tag_cols))
        self.tag_view = gtk.TreeView.new_with_model(self.tag_store)
        self.tag_sw = gtk.ScrolledWindow.new(None, None)
        self.tag_sw.set_vexpand(True)
        self.tag_sw.set_hexpand(True)

        for c in ((i, tag_cols[i][0]) for i in range(len(tag_cols))):
            col = gtk.TreeViewColumn(
                c[1],
                gtk.CellRendererText(),
                text=c[0],
                size=12,
                editable=False,
            )
            col.set_resizable(True)
            self.tag_view.append_column(col)

        self.person_store = gtk.TreeStore(*(c[1] for c in person_cols))
        self.person_view = gtk.TreeView.new_with_model(self.person_store)
        self.person_sw = gtk.ScrolledWindow.new(None, None)
        self.person_sw.set_vexpand(True)
        self.person_sw.set_hexpand(True)

        for c in ((i, person_cols[i][0]) for i in range(len(person_cols))):
            col = gtk.TreeViewColumn(
                c[1],
                gtk.CellRendererText(),
                text=c[0],
                size=12,
                editable=False,
            )
            col.set_resizable(True)
            self.person_view.append_column(col)

    def _restore_window_state(self, *_ignore: Any) -> bool:
        size = self.cfg.get("GUI", "Size")
        pos = self.cfg.get("GUI", "Position")

        self.win.resize(size[0], size[1])
        self.win.move(pos[0], pos[1])

        return False

    def _save_window_state(self, *_ignore: Any) -> bool:
        size = self.win.get_size()
        pos = self.win.get_position()

        self.log.debug("Save Window state: %dx%d @ %d/%d",
                       size[0], size[1],
                       pos[0], pos[1])

        self.cfg.update("GUI", "Size", size)
        self.cfg.update("GUI", "Position", pos)
        return True

    def _display_msg(self, msg: str, modal: bool = True) -> None:
        """Display a message in a dialog."""
        self.log.info(msg)

        dlg = gtk.Dialog(
            parent=self.win,
            title="Attention",
            modal=modal,
        )

        dlg.add_buttons(
            gtk.STOCK_OK,
            gtk.ResponseType.OK,
        )

        area = dlg.get_content_area()
        lbl = gtk.Label(label=msg)
        area.add(lbl)
        dlg.show_all()  # pylint: disable-msg=E1101

        try:
            dlg.run()  # pylint: disable-msg=E1101
        finally:
            dlg.destroy()

    def _reload_data(self, *_ignore) -> None:
        """Clear and re-fill all data stores."""
        self.root_store.clear()
        self.vid_store.clear()
        self.tag_store.clear()
        self.vids.clear()
        self.vid_filter.refilter()

        self._load_data()
        self._load_tags()

    def _load_data(self) -> None:
        folders = self.db.folder_get_all()
        for f in folders:
            glib.timeout_add(100, self.load_folder, f)

        vids = self.db.video_get_all()
        for v in vids:
            self.vids[v.vid] = v

    def _load_tags(self) -> None:
        tags = self.db.tag_get_all()

        for t in tags:
            titer = self.tag_store.append(None)
            self.tag_store.set(titer, (0, 1), (t.tid, t.name))
            vids = self.db.tag_link_get_by_tag(t)

            for v in vids:
                viter = self.tag_store.append(titer)
                self.tag_store.set(viter,
                                   (2, 3, 4, 5),
                                   (v.vid, v.dsp_title, v.res_str, v.dur_str))

    def _load_people(self) -> None:
        people = self.db.person_get_all()

        for p in people:
            piter = self.person_store.append(None)
            self.person_store.set(piter,
                                  (0, 1, 2),
                                  (p.pid,
                                   p.name,
                                   p.born))

            vids = self.db.person_link_get_by_person(p)

            for v in vids:
                viter = self.person_store.append(piter)
                self.person_store.set(viter,
                                      (3, 4, 5, 6, 7),
                                      (v[1],
                                       v[0].vid,
                                       v[0].dsp_title,
                                       v[0].res_str,
                                       v[0].dur_str))

    def _purge(self, _ignore) -> None:
        """Remove any videos from the database that no longer exist in the file system."""
        del_cnt: int = 0
        del_ids: list[int] = []
        with self.db:
            for v_id, vid in self.vids.items():
                if not os.path.isfile(vid.path):
                    self.log.debug("Video %s appears to not exist anymore.",
                                   vid.dsp_title)
                    self.db.video_delete(vid)
                    del_ids.append(v_id)
                    del_cnt += 1
        if del_cnt > 0:
            self.log.debug("Removed %d deleted Videos from database, reloading data stores.""",
                           del_cnt)
            for v in del_ids:
                del self.vids[v]
            self._reload_data()

    def run(self):
        """Execute the Gtk event loop."""
        gtk.main()

    def _quit(self, *_ignore):
        self.win.destroy()
        gtk.main_quit()

    def check_queue(self) -> bool:
        """Get any pending messages from the queue and handle them."""
        status: bool = True
        try:
            while not self.mq.empty():
                msg = self.mq.get_nowait()
                glib.timeout_add(100, self.handle_msg, msg)
        except Empty:
            pass
        except ShutDown:
            status = False
        return status

    def handle_msg(self, msg: Message) -> bool:
        """Process a message about an event we received from another thread."""
        self.log.debug("Handle Message %s", msg.tag)
        try:
            match msg.tag:
                case MsgType.NothingBurger:
                    self.log.debug("NothingBurger? R U kidding me right now?!")
                case MsgType.ScanComplete:
                    assert isinstance(msg.payload, Folder)
                    fldr: Folder = msg.payload
                    self.log.debug("Scan of %s finished.", fldr.path)
                    glib.timeout_add(50, self.load_folder, fldr)
                case MsgType.ScanError:
                    self.log.error("An error occured during a scan: %s",
                                   msg.payload)
                case MsgType.PlayFinished:
                    self.log.debug("Finished playing a Video. Yay!")
        except Exception as err:  # pylint: disable-msg=W0718
            self.log.error("%s while handling message of type %s: %s",
                           err.__class__.__name__,
                           msg.tag,
                           err)

        return False

    def handle_add_folder(self, *_ignore) -> None:
        """Prompt the user for a Folder and add it if needed."""
        self.log.debug("Handle add folder")
        try:
            dlg = gtk.FileChooserDialog(
                title="Pick a folder...",
                parent=self.win,
                action=gtk.FileChooserAction.SELECT_FOLDER)
            dlg.add_buttons(
                gtk.STOCK_CANCEL,
                gtk.ResponseType.CANCEL,
                gtk.STOCK_OPEN,
                gtk.ResponseType.OK)

            res = dlg.run()
            if res != gtk.ResponseType.OK:
                self.log.debug("Response from dialog was %s, I'm out.", res)
                return

            path = dlg.get_filename()
            self.log.info("Add folder %s.", path)
        finally:
            dlg.destroy()

        thr = Thread(target=self.scan_folder,
                     args=(path, ),
                     name=f"Scan {path}",
                     daemon=True)
        thr.start()

    def scan_folder(self, path: str) -> None:
        """scan_folder creates and runs the Scanner on a folder.

        This method is intended to be called in a separate thread.
        """
        self.log.debug("About to scan folder %s", path)
        try:
            scn: Scanner = Scanner(path)
            fldr = scn.scan()
            self.log.debug("Finished scanning %s, informing the UI thread.", path)
            msg = Message(MsgType.ScanComplete, fldr)
            self.mq.put(msg)
        finally:
            self.log.debug("Scanner thread for folder %s is quitting.",
                           path)

    def load_folder(self, fldr: Folder) -> None:
        """Load the videos that scanning the given folder yielded in the GUI."""
        self.log.debug("Loading data from folder %s (%d)", fldr.path, fldr.fid)
        with self.db:
            vids = self.db.video_get_by_folder(fldr)

        riter = self.root_store.append()
        self.root_store.set(
            riter,
            (0, 1, 2, 3),
            (fldr.fid,
             fldr.path,
             fldr.last_scan.strftime(common.TIME_FMT) if fldr.last_scan is not None else "",
             fldr.remote))

        for v in vids:
            viter = self.vid_store.append()
            tags = self.db.tag_link_get_by_vid(v)
            # TODO Load data for tags and linked people
            self.vid_store.set(
                viter,
                tuple(range(len(vid_cols))),
                (v.vid,
                 v.path,
                 v.title,
                 v.res_str,
                 v.dur_str,
                 ", ".join([x.name for x in tags]),
                 ""),
            )

    def _handle_vid_view_click(self, _w, evt: gdk.Event) -> None:
        if evt.button != 3:
            return

        x: Final[float] = evt.x
        y: Final[float] = evt.y

        pinfo = self.vid_view.get_path_at_pos(x, y)
        if pinfo is None:
            return
        path = pinfo[0]
        cpath = self.vid_filter.convert_path_to_child_path(path)
        tree_iter: gtk.TreeIter = self.vid_store.get_iter(cpath)

        v_id: Final[int] = self.vid_store[tree_iter][0]
        vid = self.db.video_get_by_id(v_id)

        if vid is None:
            self.log.debug("No Video was found at click")
            return

        self.log.debug("Clicked on Video %s",
                       vid.dsp_title)

        menu = self._mk_ctx_menu_vid(tree_iter, vid)
        menu.show_all()
        menu.popup_at_pointer(evt)

    def _mk_ctx_menu_vid(self, viter: gtk.TreeIter, vid: Video) \
            -> gtk.Menu:  # pylint: disable-msg=R0914
        tags = self.db.tag_get_all_vid(vid)

        cmenu = gtk.Menu()
        tmenu = gtk.Menu()

        titem = gtk.MenuItem.new_with_mnemonic("_Tags")

        for t in tags:
            litem = gtk.CheckMenuItem.new_with_label(t[0].name)
            litem.set_active(t[1] is not None)
            litem.connect("activate",
                          self.vid_toggle_tag,
                          viter,
                          vid,
                          t)
            tmenu.add(litem)

        # Now we deal with people. I am not a people person (-ish)
        people_item = gtk.MenuItem.new_with_mnemonic("_People")
        people_menu = gtk.Menu()

        people = self.db.person_get_all()
        plinklist = self.db.person_link_get_by_video(vid)
        plinks: defaultdict[int, list[str]] = defaultdict(list)

        for lnk in plinklist:
            plinks[lnk[0].pid].append(lnk[1])

        for p in people:
            rmenu = gtk.Menu()
            ppitem = gtk.MenuItem.new_with_label(p.name)
            ppitem.set_submenu(rmenu)
            people_menu.add(ppitem)

            for r in roles:
                ritem = gtk.CheckMenuItem.new_with_label(r)
                rmenu.add(ritem)
                linked: bool = r in plinks[p.pid]
                if linked:
                    ritem.set_active(True)
                ritem.connect("activate", self.handle_person_link_set, p, vid, r, not linked)

        people_item.set_submenu(people_menu)

        play_item = gtk.MenuItem.new_with_mnemonic("_Play")
        # Register callback!
        play_item.connect("activate", self.vid_play, vid)

        titem.set_submenu(tmenu)

        hide_item = gtk.CheckMenuItem.new_with_mnemonic("_Hide?")
        hide_item.set_active(vid.hidden)
        hide_item.connect("activate", self.vid_hide_cb, vid, viter)

        cmenu.add(gtk.MenuItem.new_with_label(vid.dsp_title))
        cmenu.add(people_item)
        cmenu.add(titem)
        cmenu.add(play_item)
        cmenu.add(hide_item)

        return cmenu

    def vid_toggle_tag(self,
                       _widget,
                       viter: gtk.TreeIter,
                       vid: Video,
                       tag: tuple[Tag, Optional[int]]) -> None:
        """Toggle the link between a Video and a Tag."""
        op: Final[str] = "create" if tag[1] is None else "remove"
        with self.db:
            if tag[1] is None:
                self.db.tag_link_create(tag[0], vid)
            else:
                self.db.tag_link_remove(tag[0], vid)

            tags = self.db.tag_link_get_by_vid(vid)
        tstr: str = ", ".join([x.name for x in tags])
        self.vid_store[viter][5] = tstr

        # Update Tag View

        titer: gtk.TreeIter = self.tag_store.get_iter_first()
        while self.tag_store[titer][0] != tag[0].tid:
            titer = self.tag_store.iter_next(titer)

        # Now we have the Iter for the Tag.
        if op == "create":
            niter = self.tag_store.append(titer)
            self.tag_store.set(niter,
                               (2, 3, 4, 5),
                               (vid.vid,
                                vid.dsp_title,
                                vid.res_str,
                                vid.dur_str))
        else:
            diter: gtk.TreeIter = self.tag_store.iter_children(titer)
            while self.tag_store[diter][2] != vid.vid:
                diter = self.tag_store.iter_next(diter)
            self.tag_store.remove(diter)

    def vid_hide_cb(self, _widget, vid: Video, viter: gtk.TreeIter) -> None:
        """Hide a Video."""
        with self.db:
            self.db.video_set_hidden(vid, True)
            self.vids[vid.vid].hidden = True
            self.vid_filter.refilter()
        # TODO Actually hide Video from TreeView!

    def handle_create_tag(self, _ignore) -> None:
        """Facilitate the creation of a new Tag."""
        self.log.debug("Tag me like you mean it!")

        try:
            dlg = gtk.Dialog(
                title="Create Tag",
                parent=self.win,
                modal=True)
            dlg.add_buttons(
                gtk.STOCK_CANCEL,
                gtk.ResponseType.CANCEL,
                gtk.STOCK_OK,
                gtk.ResponseType.OK)

            grid = gtk.Grid.new()  # pylint: disable-msg=E1120
            lbl = gtk.Label.new("Name: ")
            edit = gtk.Entry.new()  # pylint: disable-msg=E1120

            grid.attach(lbl, 0, 0, 1, 1)
            grid.attach(edit, 1, 0, 1, 1)

            dlg.get_content_area().add(grid)
            dlg.show_all()  # pylint: disable-msg=E1101

            res = dlg.run()
            if res != gtk.ResponseType.OK:
                return

            name = edit.get_text()
            t = Tag(name=name)
            with self.db:
                self.db.tag_add(t)

            titer = self.tag_store.append(None)
            self.tag_store.set(titer, (0, 1), (t.tid, t.name))
        finally:
            self.log.debug("Phewww, that was some tagging, wasn't it?")
            dlg.destroy()

    def _vid_visible_fn(self, model, viter: gtk.TreeIter, _ignore) -> bool:
        if self.display_hidden:
            return True

        try:
            v_id = model[viter][0]
            if v_id not in self.vids:
                return True  # ???

            vid = self.vids[v_id]
            return not vid.hidden
        except TypeError as err:
            self.log.error("%s in _vid_visible_fn: %s\n%s\n\n",
                           err.__class__.__name__,
                           err,
                           krylib.fmt_err(err))
            return True

    def _toggle_show_hidden_cb(self, _widget) -> None:
        self.display_hidden = not self.display_hidden
        self.vid_filter.refilter()
        self.cfg.update("GUI", "DisplayHidden", self.display_hidden)

    def vid_play(self, _ignore, v: Video) -> None:
        """Start playing a Video."""
        self.log.debug("Let's play!")
        thr = Thread(target=self._play_file, args=(v, ), daemon=True)
        thr.start()

    def _play_file(self, v: Video) -> None:
        """Play the Video."""
        self.log.debug("About to play %s", v.dsp_title)
        cmd: list[str] = [
            "mpv",
            "--mute",
            v.path,
        ]

        res = subprocess.run(cmd,
                             check=False,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        msg = Message(MsgType.PlayFinished, res)
        self.mq.put(msg)

    def handle_person_create(self, _ignore) -> None:
        """Prompt for a Person to create."""
        self.log.debug("Create a Person maybe.")
        try:
            dlg = gtk.Dialog(
                title="Create Person",
                parent=self.win,
                modal=True)
            dlg.add_buttons(
                gtk.STOCK_CANCEL,
                gtk.ResponseType.CANCEL,
                gtk.STOCK_OK,
                gtk.ResponseType.OK)

            grid = gtk.Grid.new()  # pylint: disable-msg=E1120
            lbl_name = gtk.Label.new("Name: ")
            edit_name = gtk.Entry.new()  # pylint: disable-msg=E1120
            lbl_born = gtk.Label.new("Born: ")
            edit_born = gtk.SpinButton.new_with_range(1970, datetime.now().year, 1)

            grid.attach(lbl_name, 0, 0, 1, 1)
            grid.attach(edit_name, 1, 0, 1, 1)
            grid.attach(lbl_born, 0, 1, 1, 1)
            grid.attach(edit_born, 1, 1, 1, 1)

            dlg.get_content_area().add(grid)
            dlg.show_all()  # pylint: disable-msg=E1101

            res = dlg.run()
            if res != gtk.ResponseType.OK:
                return

            name: Final[str] = edit_name.get_text()
            born: Final[int] = edit_born.get_value_as_int()

            person: Person = Person(name=name, born=born)

            self.log.debug("Add Person %s, born %d",
                           name,
                           born)

            with self.db:
                self.db.person_add(person)

            piter = self.person_store.append(None)
            self.person_store.set(piter,
                                  (0, 1, 2),
                                  (person.pid,
                                   person.name,
                                   person.born))
        finally:
            self.log.debug("We may or may not have created a Person.")
            dlg.destroy()

    def handle_person_link_set(self, _ignore, p: Person, v: Video, role: str, create: bool) -> None:
        """Create or remove a Person-Video link."""
        with self.db:
            if create:
                self.db.person_link_add(p, v, role)
            else:
                self.db.person_link_remove(p, v, role)

        piter = self.person_store.get_iter_first()
        pid: int = self.person_store[piter][0]

        while pid != p.pid and piter is not None:
            piter = self.person_store.iter_next(piter)
            pid = self.person_store[piter][0]

        if piter is None:
            # This should not happen
            self.log.critical("CANTHAPPEN - Person %s (%d) not found in person_store",
                              p.name,
                              p.pid)
            return

        if create:
            viter = self.person_store.append(piter)
            self.person_store.set(viter,
                                  (3, 4, 5, 6, 7),
                                  (role,
                                   v.vid,
                                   v.dsp_title,
                                   v.res_str,
                                   v.dur_str))
        else:
            viter = self.person_store.iter_nth_child(piter, 0)
            while viter is not None and self.person_store[viter][4] != v.vid:
                viter = self.person_store.iter_next(viter)

            self.person_store.remove(viter)


if __name__ == '__main__':
    w = GUI()
    w.run()


# Local Variables: #
# python-indent: 4 #
# End: #

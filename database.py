#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-30 09:31:29 krylon>
#
# /data/code/python/hollywoo/database.py
# created on 21. 06. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the PyKuang network scanner. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
hollywoo.database

(c) 2025 Benjamin Walkenhorst
"""

import logging
import sqlite3
from datetime import datetime
from enum import IntEnum, auto, unique
from threading import Lock
from typing import Final, Optional, Union

import krylib

from hollywoo import common
from hollywoo.model import Folder, Resolution, Tag, Video


class DBError(common.HollywooError):
    """Base class for database-related exceptions."""


class IntegrityError(DBError):
    """IntegrityError indicates a violation of the database's constraints."""


open_lock: Final[Lock] = Lock()

qinit: Final[tuple[str, ...]] = (
    """
CREATE TABLE folder (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    last_scan INTEGER,
    remote INTEGER NOT NULL DEFAULT 0
) STRICT
    """,
    "CREATE UNIQUE INDEX folder_path_idx ON folder (path)",
    "CREATE INDEX folder_scan_idx ON folder (last_scan)",
    """
CREATE TABLE video (
    id INTEGER PRIMARY KEY,
    folder_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    added INTEGER NOT NULL,
    mtime INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    cksum TEXT,
    xres INTEGER,
    yres INTEGER,
    duration INTEGER,
    hidden INTEGER NOT NULL DEFAULT 0,
    UNIQUE (folder_id, path),
    CHECK ((xres IS NULL) = (yres IS NULL)),
    CHECK (duration IS NULL OR duration > 0),
    FOREIGN KEY (folder_id) REFERENCES folder (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) STRICT
    """,
    "CREATE INDEX vid_folder_idx ON video (folder_id)",
    "CREATE INDEX vid_path_idx ON video (path)",
    "CREATE INDEX vid_res_idx ON video (xres, yres)",
    "CREATE INDEX vid_dur_idx ON video (duration)",
    "CREATE INDEX vid_hidden_idx ON video (hidden <> 0)",
    """
CREATE TABLE program (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL
) STRICT
    """,
    """
CREATE TABLE prog_vid_link (
    id INTEGER PRIMARY KEY,
    vid_id INTEGER NOT NULL,
    prog_id INTEGER NOT NULL,
    UNIQUE (vid_id, prog_id),
    FOREIGN KEY (vid_id) REFERENCES video (id)
      ON UPDATE RESTRICT
      ON DELETE CASCADE,
    FOREIGN KEY (prog_id) REFERENCES program (id)
      ON UPDATE RESTRICT
      ON DELETE CASCADE
) STRICT
    """,
    """
CREATE TABLE tag (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
) STRICT
    """,
    """
CREATE TABLE tag_vid_link (
    id INTEGER PRIMARY KEY,
    tag_id INTEGER NOT NULL,
    vid_id INTEGER NOT NULL,
    UNIQUE (tag_id, vid_id),
    FOREIGN KEY (tag_id) REFERENCES tag (id)
      ON UPDATE RESTRICT
      ON DELETE CASCADE,
    FOREIGN KEY (vid_id) REFERENCES video (id)
      ON UPDATE RESTRICT
      ON DELETE CASCADE
) STRICT
    """,
    "CREATE INDEX tag_link_tag_idx ON tag_vid_link (tag_id)",
    "CREATE INDEX tag_link_vid_idx ON tag_vid_link (vid_id)",
    """
CREATE TABLE person (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    born INTEGER
) STRICT
    """,
    """
CREATE TABLE person_vid_link (
    id INTEGER PRIMARY KEY,
    pid INTEGER NOT NULL,
    vid INTEGER NOT NULL,
    role TEXT NOT NULL,
    UNIQUE (pid, vid, role),
    FOREIGN KEY (pid) REFERENCES person (id)
      ON UPDATE RESTRICT
      ON DELETE CASCADE,
    FOREIGN KEY (vid) REFERENCES video (id)
      ON UPDATE RESTRICT
      ON DELETE CASCADE
) STRICT
    """,
)


@unique
class qid(IntEnum):
    """qid is a symbolic constant representing a database query."""

    FolderAdd = auto()
    FolderUpdateScan = auto()
    FolderSetRemote = auto()
    FolderGetAll = auto()
    FolderGetByID = auto()
    FolderGetByPath = auto()
    VideoAdd = auto()
    VideoSetTitle = auto()
    VideoSetCksum = auto()
    VideoSetMtime = auto()
    VideoGetByID = auto()
    VideoGetByPath = auto()
    VideoGetByFolder = auto()
    VideoGetAll = auto()
    VideoSetResolution = auto()
    VideoSetDuration = auto()
    VideoSetHidden = auto()
    ProgramAdd = auto()
    ProgramSetTitle = auto()
    ProgramAddVideo = auto()
    ProgramGetAll = auto()
    ProgramGetVideos = auto()
    TagCreate = auto()
    TagLinkCreate = auto()
    TagLinkGetByTag = auto()
    TagLinkGetByVid = auto()
    TagLinkRemove = auto()
    TagGetAllVideo = auto()
    TagGetAll = auto()
    PersonAdd = auto()
    PersonUpdateName = auto()
    PersonUpdateBorn = auto()
    LinkPersonAdd = auto()
    LinkPersonGetByPerson = auto()
    LinkPersonGetByVid = auto()


qdb: dict[qid, str] = {
    qid.FolderAdd: """
INSERT INTO folder (path, last_scan, remote) VALUES (?, ?, ?)
    """,
    qid.FolderUpdateScan: """
UPDATE folder
SET last_scan = ?
WHERE id = ?
    """,
    qid.FolderSetRemote: "UPDATE folder SET remote = ? WHERE id = ?",
    qid.FolderGetAll: """
SELECT
    id,
    path,
    last_scan,
    remote
FROM folder
    """,
    qid.FolderGetByID: """
SELECT
    path,
    last_scan,
    remote
FROM folder
WHERE id = ?
    """,
    qid.FolderGetByPath: """
SELECT
    id,
    last_scan,
    remote
FROM folder
WHERE path = ?
    """,
    qid.VideoAdd: """
INSERT INTO video (folder_id, path, added, mtime, xres, yres, duration)
           VALUES (        ?,    ?,     ?,     ?,    ?,    ?,        ?)
""",
    qid.VideoSetTitle: "UPDATE video SET title = ? WHERE id = ?",
    qid.VideoSetCksum: "UPDATE video SET cksum = ? WHERE id = ?",
    qid.VideoSetMtime: "UPDATE video SET mtime = ? WHERE id = ?",
    qid.VideoSetResolution: "UPDATE video SET xres = ?, yres = ? WHERE id = ?",
    qid.VideoSetDuration: "UPDATE video SET duration = ? WHERE id = ?",
    qid.VideoSetHidden: "UPDATE video SET hidden = ? WHERE id = ?",
    qid.VideoGetByID: """
SELECT
    folder_id,
    path,
    added,
    mtime,
    title,
    cksum,
    xres,
    yres,
    duration,
    hidden
FROM video
WHERE id = ?
    """,
    qid.VideoGetByPath: """
SELECT
    id,
    folder_id,
    added,
    mtime,
    title,
    cksum,
    xres,
    yres,
    duration,
    hidden
FROM video
WHERE path = ?
    """,
    qid.VideoGetByFolder: """
SELECT
    id,
    path,
    added,
    mtime,
    title,
    cksum,
    xres,
    yres,
    duration,
    hidden
FROM video
WHERE folder_id = ?
ORDER BY path
    """,
    qid.VideoGetAll: """
SELECT
    id,
    folder_id,
    path,
    added,
    mtime,
    title,
    cksum,
    xres,
    yres,
    duration,
    hidden
FROM video
ORDER BY path
    """,
    qid.ProgramAdd: "INSERT INTO program (title) VALUES (?)",
    qid.ProgramSetTitle: "UPDATE program SET title = ? WHERE id = ?",
    qid.ProgramAddVideo: "INSERT INTO prog_vid_link (prog_id, vid_id) VALUES (?, ?)",
    qid.ProgramGetAll: """
SELECT
    id,
    title
FROM program
    """,
    qid.ProgramGetVideos: """
SELECT
    v.id,
    v.folder_id,
    v.path,
    v.added,
    v.title,
    v.cksum
FROM prog_vid_link p
INNER JOIN video v ON p.vid_id = v.id
WHERE p.prog_id = ?
    """,
    qid.TagCreate: "INSERT INTO tag (name) VALUES (?)",
    qid.TagLinkCreate: "INSERT INTO tag_vid_link (tag_id, vid_id) VALUES (?, ?)",
    qid.TagLinkRemove: "DELETE FROM tag_vid_link WHERE tag_id = ? AND vid_id = ?",
    qid.TagLinkGetByTag: """
SELECT
    v.id,
    v.folder_id,
    v.path,
    v.added,
    v.mtime,
    v.title,
    v.cksum,
    v.xres,
    v.yres,
    v.duration,
    v.hidden
FROM tag_vid_link t
INNER JOIN video v ON t.vid_id = v.id
INNER JOIN folder f ON v.folder_id = f.id
WHERE t.tag_id = ?
ORDER BY f.path, v.path
    """,
    qid.TagLinkGetByVid: """
SELECT
    t.id,
    t.name
FROM tag t
WHERE t.vid_id = ?
    """,
    qid.TagGetAllVideo: """
SELECT
    t.id,
    t.name,
    l.id
FROM tag t
LEFT OUTER JOIN tag_vid_link l ON t.id = l.tag_id AND l.vid_id = ?
ORDER BY t.name
    """,
    qid.TagGetAll: """SELECT id, name FROM tag ORDER BY name""",
    qid.PersonAdd: "INSERT INTO person (name) VALUES (?)",
    qid.PersonUpdateName: "UPDATE person SET name = ? WHERE id = ?",
    qid.PersonUpdateBorn: "UPDATE person SET born = ? WHERE id = ?",
    qid.LinkPersonAdd: "INSERT INTO person_vid_link (pid, vid, role) VALUES (?, ?, ?)",
    qid.LinkPersonGetByPerson: """
SELECT
    vid,
    role
FROM person_vid_link
WHERE pid = ?
    """,
    qid.LinkPersonGetByVid: """
SELECT
    pid,
    role
FROM person_vid_link
WHERE vid = ?
""",
}


class Database:
    """Database is a wrapper for the database connection."""

    __slots__ = [
        "db",
        "log",
        "path",
    ]

    db: sqlite3.Connection
    log: logging.Logger
    path: str

    def __init__(self, path: str = "") -> None:
        if path == "":
            self.path = common.path.db()
        else:
            self.path = path

        self.log = common.get_logger("database")
        self.log.debug("Open database at %s", self.path)

        uri: Final[str] = \
            f"file:{self.path}?_locking=NORMAL&_journal=WAL&_fk=1&recursive_triggers=0"

        with open_lock:
            exist: Final[bool] = krylib.fexist(self.path)
            self.db = sqlite3.connect(
                uri,
                check_same_thread=False,
                uri=True,
                timeout=5.0,
            )

            cur = self.db.cursor()
            cur.execute("PRAGMA foreign_keys = true")
            cur.execute("PRAGMA journal_mode = WAL")
            cur.close()
            # self.db.commit()
            self.db.autocommit = False

            if not exist:
                self.__create_db()

    def __create_db(self) -> None:
        with self.db:
            for q in qinit:
                self.log.debug("Execute SQL: %s", q)
                cur: sqlite3.Cursor = self.db.cursor()
                cur.execute(q)

    def __enter__(self) -> None:
        self.db.__enter__()

    def __exit__(self, ex_type, ex_val, traceback):
        return self.db.__exit__(ex_type, ex_val, traceback)

    def close(self) -> None:
        """Close the underlying database connection explicitly."""
        self.db.close()

    def folder_add(self, f: Folder) -> None:
        """Add a Folder to the database."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.FolderAdd],
                    (f.path,
                     int(f.last_scan.timestamp()) if f.last_scan is not None else None,
                     f.remote))
        fid = cur.lastrowid
        assert fid is not None
        f.fid = fid

    def folder_update_scan(self, f: Folder, s: datetime) -> None:
        """Set a Folder's scan timestamp."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.FolderUpdateScan], (int(s.timestamp()), f.fid))
        f.last_scan = s

    def folder_set_remote(self, f: Folder, remote: bool) -> None:
        """Set a Folder's remote flag."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.FolderSetRemote], (remote, f.fid))
        f.remote = remote

    def folder_get_all(self) -> list[Folder]:
        """Get all Folders from the database."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.FolderGetAll])

        folders: list[Folder] = []

        for row in cur:
            f: Folder = Folder(
                fid=row[0],
                path=row[1],
                last_scan=(datetime.fromtimestamp(row[2]) if row[2] is not None else None),
                remote=row[3],
            )
            folders.append(f)

        return folders

    def folder_get_by_id(self, fid: int) -> Optional[Folder]:
        """Look up a Folder by its ID."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.FolderGetByID], (fid, ))

        row = cur.fetchone()

        if row is None:
            return None

        f: Folder = Folder(
            fid=fid,
            path=row[0],
            last_scan=(None if row[1] is None else datetime.fromtimestamp(row[1])),
            remote=row[2],
        )

        return f

    def folder_get_by_path(self, path: str) -> Optional[Folder]:
        """Look up a Folder by its ID."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.FolderGetByPath], (path, ))

        row = cur.fetchone()

        if row is None:
            return None

        f: Folder = Folder(
            fid=row[0],
            path=path,
            last_scan=(None if row[1] is None else datetime.fromtimestamp(row[1])),
            remote=row[2],
        )

        return f

    def video_add(self, v: Video) -> None:
        """Add a Video to the database."""
        now: Final[datetime] = datetime.now()
        cur = self.db.cursor()
        cur.execute(qdb[qid.VideoAdd],
                    (v.folder_id,
                     v.path,
                     int(now.timestamp()),
                     int(v.mtime.timestamp()),
                     v.resolution.x,
                     v.resolution.y,
                     v.duration))
        v.added = now
        vid = cur.lastrowid
        assert vid is not None
        v.vid = vid

    def video_set_title(self, v: Video, title: str) -> None:
        """Set a Video's title."""
        self.log.debug("Set title of Video %d (%s) => %s",
                       v.vid,
                       v.path,
                       title)
        cur = self.db.cursor()
        cur.execute(qdb[qid.VideoSetTitle],
                    (title, v.vid))
        v.title = title

    def video_set_cksum(self, v: Video, ck: Optional[str]) -> None:
        """Set or clear a Video's Checksum."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.VideoSetCksum],
                    (ck, v.vid))
        v.cksum = ck

    def video_set_mtime(self, v: Video, mtime: datetime) -> None:
        """Update a Videos mtime timestamp."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.VideoSetMtime], (int(mtime.timestamp()), v.vid))
        v.mtime = mtime

    def video_set_hidden(self, v: Video, hidden: bool = True) -> None:
        """Set or clear a Video's hidden flag."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.VideoSetHidden], (hidden, v.vid))
        v.hidden = hidden

    def video_get_by_id(self, vid: int) -> Optional[Video]:
        """Look up a Video by its ID."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.VideoGetByID], (vid, ))
        row = cur.fetchone()
        if row is None:
            return None

        v = Video(
            vid=vid,
            folder_id=row[0],
            path=row[1],
            added=datetime.fromtimestamp(row[2]),
            mtime=datetime.fromtimestamp(row[3]),
            title=row[4],
            cksum=row[5],
            resolution=Resolution(row[6], row[7]),
            duration=row[8],
            hidden=row[9],
        )

        return v

    def video_get_by_path(self, path: str) -> Optional[Video]:
        """Look for a Video by its path."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.VideoGetByPath], (path, ))
        row = cur.fetchone()
        if row is None:
            return None
        v: Video = Video(
            vid=row[0],
            folder_id=row[1],
            path=path,
            added=datetime.fromtimestamp(row[2]),
            mtime=datetime.fromtimestamp(row[3]),
            title=row[4],
            cksum=row[5],
            resolution=Resolution(row[6], row[7]),
            duration=row[8],
            hidden=row[9],
        )
        return v

    def video_get_by_folder(self, f: Union[Folder, str, int]) -> list[Video]:
        """Load all videos that belong to the given folder."""
        fldr: Optional[Folder] = None
        if isinstance(f, Folder):
            fldr = f
        elif isinstance(f, str):
            fldr = self.folder_get_by_path(f)
        elif isinstance(f, int):
            fldr = self.folder_get_by_id(f)
        assert fldr is not None
        self.log.debug("Load videos for Folder %s (%d)...",
                       fldr.path,
                       fldr.fid)

        cur = self.db.cursor()
        cur.execute(qdb[qid.VideoGetByFolder], (fldr.fid, ))
        vids: list[Video] = []

        for row in cur:
            v: Video = Video(
                vid=row[0],
                folder_id=fldr.fid,
                path=row[1],
                added=datetime.fromtimestamp(row[2]),
                mtime=datetime.fromtimestamp(row[3]),
                title=row[4],
                cksum=row[5],
                resolution=Resolution(row[6], row[7]),
                duration=row[8],
                hidden=row[9],
            )
            vids.append(v)

        self.log.debug("Got %d videos for Folder %s",
                       len(vids),
                       fldr.path)

        return vids

    def video_get_all(self) -> list[Video]:
        """Get all videos from the database."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.VideoGetAll])

        vids = []

        for row in cur:
            v = Video(
                vid=row[0],
                folder_id=row[1],
                path=row[2],
                added=datetime.fromtimestamp(row[3]),
                mtime=datetime.fromtimestamp(row[4]),
                title=row[5],
                cksum=row[6],
                resolution=Resolution(row[7], row[8]),
                duration=row[9],
                hidden=row[0],
            )

            vids.append(v)

        return vids

    def tag_add(self, t: Tag) -> None:
        """Add a Tag to the database."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.TagCreate], (t.name, ))
        tid = cur.lastrowid
        assert tid is not None
        self.log.debug("Create new Tag %s, ID is %d", t.name, tid)
        t.tid = tid

    def tag_link_create(self, t: Tag, v: Video) -> None:
        """Attach a Tag to a Video."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.TagLinkCreate],
                    (t.tid, v.vid))
        self.log.debug("Attach Tag %s to Video %s",
                       t.name,
                       v.dsp_title)

    def tag_link_get_by_tag(self, t: Tag) -> list[Video]:
        """Get all Videos that have the given Tag attached."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.TagLinkGetByTag], (t.tid, ))
        vids: list[Video] = []

        for row in cur:
            v = Video(
                vid=row[0],
                folder_id=row[1],
                path=row[2],
                added=datetime.fromtimestamp(row[3]),
                mtime=datetime.fromtimestamp(row[4]),
                title=row[5],
                cksum=row[6],
                resolution=Resolution(row[7], row[8]),
                duration=row[9],
                hidden=row[10],
            )
            vids.append(v)

        return vids

    def tag_link_get_by_vid(self, v: Video) -> list[Tag]:
        """Get all Tags attached to a Video."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.TagLinkGetByVid], (v.vid, ))
        tags: list[Tag] = []

        for row in cur:
            t = Tag(tid=row[0], name=row[1])
            tags.append(t)

        return tags

    # ┌────┬─────────┬────┐
    # │ id │  name   │ id │
    # ├────┼─────────┼────┤
    # │ 3  │ Action  │    │
    # │ 1  │ Doku    │ 2  │
    # │ 4  │ History │    │
    # │ 2  │ SF      │    │
    # └────┴─────────┴────┘
    def tag_get_all_vid(self, v: Video) -> list[tuple[Tag, Optional[int]]]:
        """SELECT a list of all Tags, with the Link ID for that Video, if it is linked."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.TagGetAllVideo], (v.vid, ))
        tags: list[tuple[Tag, Optional[int]]] = []

        for row in cur:
            t = Tag(tid=row[0], name=row[1])
            tags.append((t, row[2]))

        return tags

    def tag_get_all(self) -> list[Tag]:
        """Load all Tags."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.TagGetAll])
        tags: list[Tag] = []

        for row in cur:
            t = Tag(tid=row[0], name=row[1])
            tags.append(t)

        return tags

    def tag_link_remove(self, t: Tag, v: Video) -> None:
        """Detach a Tag from a Video."""
        cur = self.db.cursor()
        cur.execute(qdb[qid.TagLinkRemove], (t.tid, v.vid))
        if cur.rowcount == 0:
            self.log.error("Looks like Tag %s wasn't attaced to Video %s after all",
                           t.name,
                           v.dsp_title)

# Local Variables: #
# python-indent: 4 #
# End: #

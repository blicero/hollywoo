#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-21 20:59:56 krylon>
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

from threading import Lock
from typing import Final

from hollywoo import common


class DBError(common.HollywooError):
    """Base class for database-related exceptions."""


class IntegrityError(DBError):
    """IntegrityError indicates a violation of the database's constraints."""


open_lock: Final[Lock] = Lock()

qinit: Final[tuple[str]] = (
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
    title TEXT NOT NULL DEFAULT '',
    cksum TEXT,
    UNIQUE (folder_id, path),
    FOREIGN KEY (folder_id) REFERENCES folder (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) STRICT
    """,
    "CREATE INDEX vid_folder_idx ON video (folder_id)",
    "CREATE INDEX vid_path_idx ON video (path)",
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
    name TEXT UNIQUE NOT NULL,
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
    """
CREATE TABLE person (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    born: INTEGER
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
    ProgramAdd = auto()
    ProgramSetTitle = auto()
    ProgramAddVideo = auto()
    TagCreate = auto()
    TagLinkCreate = auto()


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
    qid.VideoAdd: "INSERT INTO video (folder_id, path, added) VALUES (?, ?, ?)",
}
    

# Local Variables: #
# python-indent: 4 #
# End: #

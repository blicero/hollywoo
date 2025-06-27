#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-26 17:17:29 krylon>
#
# /data/code/python/hollywoo/scanner.py
# created on 23. 06. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the PyKuang network scanner. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
hollywoo.scanner

(c) 2025 Benjamin Walkenhorst
"""

import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Final, Optional

from pymediainfo import MediaInfo

from hollywoo import common
from hollywoo.database import Database
from hollywoo.model import Folder, Resolution, Video

min_size: Final[int] = 1024 * 1024 * 100  # 100MiB
suffix_pat: Final[re.Pattern] = \
    re.compile(r"[.](avi|mp4|m[4k]v|mpe?g|wmv|m2ts)$", re.I)


class Scanner:
    """Scanner traverses Folders to find Videos."""

    path: str
    db: Database
    log: logging.Logger
    _cache: dict

    def __init__(self, path: str) -> None:
        self.path = path
        self.db = Database()
        self.log = common.get_logger("scanner")
        self._cache = {}

        if not os.path.isdir(path):
            raise ValueError(f"{path} is not a directory")

    def stat(self, path: str) -> os.stat_result:
        """Attempt to get a file's filesystem metadata."""
        if path in self._cache:
            return self._cache[path]

        s = os.stat(path)
        self._cache[path] = s
        return s

    def skip_file(self, f: str) -> bool:
        """Return True if the file f is to be skipped."""
        if suffix_pat.search(f) is None:
            return True

        s = self.stat(f)
        if s.st_size < min_size:
            return True

        return False

    def scan(self) -> Folder:
        """Run the scanner on the given directory tree."""
        self.log.debug("Scan %s", self.path)
        with self.db:
            root = self.db.folder_get_by_path(self.path)
            if root is None:
                root = Folder(
                    path=self.path
                )
                self.db.folder_add(root)
            for dirpath, _folders, files in os.walk(self.path):
                for f in files:
                    full_path = os.path.join(dirpath, f)
                    if self.skip_file(full_path):
                        continue
                    st = self.stat(full_path)
                    mtime = datetime.fromtimestamp(st.st_mtime)

                    vid: Optional[Video] = self.db.video_get_by_path(full_path)
                    if vid is not None:
                        self.log.debug("Video %s is already in database (%d)",
                                       full_path,
                                       vid.vid)
                        if mtime > vid.mtime:
                            self.db.video_set_mtime(vid, mtime)

                    # Attempt to extract metadata
                    meta = self._get_metadata(full_path)
                    if meta["resolution"] is None:
                        self.log.info("Cannot determine resolution of %s",
                                      full_path)
                        meta["resolution"] = Resolution(0, 0)

                    vid = Video(
                        folder_id=root.fid,
                        path=full_path,
                        mtime=mtime,
                        resolution=meta["resolution"],
                        duration=meta["duration"],
                    )

                    self.log.debug("Add Video %s to database", full_path)
                    self.db.video_add(vid)
                    if meta["title"] is not None and len(meta["title"]) > 0:
                        self.log.debug("Set title for %s => %s",
                                       full_path,
                                       meta["title"])
                        self.db.video_set_title(vid, meta["title"])
            self.db.folder_update_scan(root, datetime.now())
        self._cache.clear()
        return root

    def _get_metadata(self, vid: str) -> defaultdict:
        m = MediaInfo.parse(vid)
        info: defaultdict = defaultdict(lambda: None)
        if len(m.video_tracks) == 0 or len(m.general_tracks) == 0:
            return info
        info["resolution"] = Resolution(m.video_tracks[0].width,
                                        m.video_tracks[0].height)
        info["duration"] = m.video_tracks[0].duration
        info["title"] = m.general_tracks[0].title or m.general_tracks[0].movie_name
        info["performer"] = m.general_tracks[0].performer

        return info


# Local Variables: #
# python-indent: 4 #
# End: #

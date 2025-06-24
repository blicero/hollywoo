#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-24 15:01:31 krylon>
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
from typing import Final, Optional

from hollywoo import common
from hollywoo.database import Database
from hollywoo.model import Folder, Video

min_size: Final[int] = 1024 * 1024 * 100  # 100MiB
suffix_pat: Final[re.Pattern] = \
    re.compile(r"[.](avi|mp4|m[4k]v|mpe?g|wmv|m2ts)$", re.I)


class Scanner:
    """Scanner traverses Folders to find Videos."""

    path: str
    db: Database
    log: logging.Logger

    def __init__(self, path: str) -> None:
        self.path = path
        self.db = Database()
        self.log = common.get_logger("scanner")

        if not os.path.isdir(path):
            raise ValueError(f"{path} is not a directory")

    def skip_file(self, f: str) -> bool:
        """Return True if the file f is to be skipped."""
        if suffix_pat.match(f) or not os.path.isfile(f):
            return True

        s = os.stat(f)
        if s.st_size < min_size:
            return True

        return False

    def scan(self) -> None:
        """Run the scanner on the given directory tree."""
        self.log.debug("Scan %s", self.path)
        with self.db:
            root = self.db.folder_get_by_path(self.path)
            if root is None:
                root = Folder(
                    path=self.path
                )
                self.db.folder_add(root)
            for dirpath, folders, files in os.walk(self.path):
                for f in files:
                    full_path = os.path.join(dirpath, f)
                    if self.skip_file(full_path):
                        continue

                    vid: Optional[Video] = self.db.video_get_by_path(full_path)
                    if vid is not None:
                        continue

                    vid = Video(
                        folder_id=root.fid,
                        path=full_path,
                    )

                    self.db.video_add(vid)


# Local Variables: #
# python-indent: 4 #
# End: #

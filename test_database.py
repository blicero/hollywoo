#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-23 19:18:17 krylon>
#
# /data/code/python/hollywoo/test_database.py
# created on 23. 06. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the PyKuang network scanner. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
hollywoo.test_database

(c) 2025 Benjamin Walkenhorst
"""

import os
import sqlite3
import unittest
from datetime import datetime
from typing import Final, Optional

from hollywoo import common
from hollywoo.database import Database
from hollywoo.model import Folder

TEST_DIR: Final[str] = os.path.join(
    "/tmp",
    datetime.now().strftime("hollywoo_test_database_%Y%m%d_%H%M%S"))


class DBTest(unittest.TestCase):
    """Test the database."""

    conn: Optional[Database] = None
    folders: list[Folder] = []

    @classmethod
    def setUpClass(cls) -> None:
        """Prepare the stuff."""
        common.set_basedir(TEST_DIR)

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up the mess."""
        os.system(f'rm -rf "{TEST_DIR}"')

    @classmethod
    def db(cls, db: Optional[Database] = None) -> Database:
        """Set or return the database."""
        if db is not None:
            cls.conn = db
            return db
        if cls.conn is not None:
            return cls.conn

        raise ValueError("No Database connection exists")

    def test_01_db_open(self) -> None:
        """Try opening a database."""
        db: Database = Database(common.path.db())
        self.assertIsNotNone(db)
        self.db(db)

    def test_02_folder_add(self) -> None:
        """Try adding a few folders."""
        test_cases = (
            ("/data/video", False),
            ("/srv01/video", False),
            ("/video", False),
            ("/data/video", True),
        )

        db = self.db()

        with db:
            for c in test_cases:
                try:
                    f = Folder(path=c[0])
                    db.folder_add(f)
                    self.assertGreater(f.fid, 0)
                except sqlite3.Error as err:
                    if not c[1]:
                        msg = f"{err.__class__.__name__} while adding folder {c[0]}: {err}"
                        self.fail(msg)
                else:
                    self.folders.append(f)

    def test_03_folder_get(self) -> None:
        """Test getting folders from the database."""
        db: Database = self.db()
        flist = self.folders

        self.assertEqual(len(flist), 3)

        for f1 in flist:
            f2 = db.folder_get_by_id(f1.fid)
            self.assertIsNotNone(f2)
            self.assertIsInstance(f2, Folder)
            assert f2 is not None
            self.assertEqual(f1.path, f2.path)
            self.assertIsNone(f2.last_scan)
            self.assertEqual(f1.remote, f2.remote)

            f3 = db.folder_get_by_path(f1.path)
            self.assertIsNotNone(f3)
            self.assertIsInstance(f3, Folder)
            assert f3 is not None
            self.assertEqual(f1.fid, f3.fid)
            self.assertIsNone(f3.last_scan)
            self.assertEqual(f1.remote, f3.remote)

        flist = sorted(self.folders, key=lambda x: x.path)

        dlist = db.folder_get_all()
        dlist.sort(key=lambda x: x.path)

        self.assertCountEqual(flist, dlist)

    def test_04_folder_update_scan(self) -> None:
        """Test updating the scan timestamps on Folders."""
        db: Database = self.db()
        flist = self.folders
        now: Final[datetime] = datetime.now()
        self.assertEqual(len(flist), 3)

        with db:
            for f in flist:
                db.folder_update_scan(f, now)

                self.assertIsNotNone(f.last_scan)
                self.assertEqual(f.last_scan, now)

        with db:
            for f1 in flist:
                assert f1.last_scan is not None
                f2 = db.folder_get_by_id(f1.fid)
                assert f2 is not None
                self.assertIsNotNone(f2.last_scan)
                assert f2.last_scan is not None
                self.assertIsInstance(f2.last_scan, datetime)
                self.assertEqual(f2.last_scan,
                                 datetime.fromtimestamp(int(f1.last_scan.timestamp())))


# Local Variables: #
# python-indent: 4 #
# End: #

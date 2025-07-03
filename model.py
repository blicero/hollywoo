#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-07-03 15:37:29 krylon>
#
# /data/code/python/hollywoo/model.py
# created on 21. 06. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the PyKuang network scanner. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
hollywoo.model

(c) 2025 Benjamin Walkenhorst

This module provides the domain-specific data types for use in our application.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple, Optional


class Resolution(NamedTuple):
    """Resolution is the size of a Video in pixels."""

    x: int
    y: int

    def __str__(self) -> str:
        return f"{self.x}x{self.y}"

    def __repr__(self) -> str:
        return f"{self.x}x{self.y}"


@dataclass(slots=True, kw_only=True)
class Folder:
    """Folder is the root of a directory tree that we scan for videos."""

    fid: int = -1
    path: str
    last_scan: Optional[datetime] = None
    remote: bool = False


@dataclass(slots=True, kw_only=True)
class Video:
    """Video is a single video file."""

    vid: int = -1
    folder_id: int
    path: str
    added: datetime = field(default_factory=datetime.now)
    mtime: datetime
    title: Optional[str] = None
    cksum: Optional[str] = None
    resolution: Resolution
    duration: int  # duration in milliseconds
    hidden: bool = False

    @property
    def size(self) -> int:
        """Get the Video's size, in bytes."""
        st = os.stat(self.path)
        return st.st_size

    @property
    def dur_str(self) -> str:
        """Return the duration as a human-readable string."""
        if self.duration is None:
            return "--:--:--"
        hours: int = 0
        minutes: int = 0
        seconds: int = int(self.duration / 1000)

        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def dsp_title(self) -> str:
        """Short title for the video."""
        if self.title is not None and self.title != "":
            return self.title

        return os.path.basename(self.path)

    @property
    def res_str(self) -> str:
        """Return the stringified resolution."""
        return f"{self.resolution.x}x{self.resolution.y}"


@dataclass(slots=True, kw_only=True)
class Program:
    """Program is a movie/film/series that comprises one or more video files."""

    pid: int = -1
    title: str
    files: list[Video] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class Tag:
    """A tag is a small snippet of text that can be affixed to Videos."""

    tid: int = -1
    name: str


@dataclass(slots=True, kw_only=True)
class Person:
    """Person is a ... well, person, that participates in a Video in some capacity.

    This includes acting, but may also be directing, script writing, producing, etc.
    """

    pid: int = -1
    name: str
    born: Optional[int] = None
    urls: dict[str, str] = field(default_factory=dict)


# Local Variables: #
# python-indent: 4 #
# End: #

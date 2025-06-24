#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-24 22:33:30 krylon>
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

import logging
from threading import Lock

import gi  # type: ignore

from hollywoo import common

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")

from gi.repository import \
    Gdk as gdk  # noqa: E402 pylint: disable-msg=C0413,C0411 # type: ignore
from gi.repository import \
    GLib as glib  # noqa: E402 pylint: disable-msg=C0413,C0411 # type: ignore
from gi.repository import \
    Gtk as gtk  # noqa: E402 pylint: disable-msg=C0413,C0411 # type: ignore


class WooI:
    """A GUI like no other."""

    __slots__ = [
        "log",
        "lock",
    ]

    log: logging.Logger
    lock: Lock

    def __init__(self) -> None:
        self.log = common.get_logger("gui")
        self.lock = Lock()
    

# Local Variables: #
# python-indent: 4 #
# End: #

# Big Data Smart Socket
# Copyright (C) 2016 Clemson University
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import importlib
import pkgutil


EXCLUDE_MODULES = ("base",)


def available_mechanisms():
    """
    Names of all available transfer mechanisms.
    """
    all_mechanisms = [name for _, name, _ in pkgutil.iter_modules(__path__) if name not in EXCLUDE_MODULES]
    return [m for m in all_mechanisms if transfer_mechanism_module(m).is_available()]


def default_mechanism(url):
    """
    Name of the default transfer mechanism for a URL.
    This is used if the metadata repository doesn't specify a mechanism.

    Returns
    Tuple of mechanism name and options.
    """
    return ("curl", None)


def transfer_mechanism_module(mechanism_name):
    """
    The Python module for a transfer mechanism.
    """
    try:
        return importlib.import_module(__package__ + "." + mechanism_name)
    except ImportError:
        return None

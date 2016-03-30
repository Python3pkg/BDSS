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

from collections import namedtuple
from tempfile import NamedTemporaryFile

from .transfer_mechanisms import transfer_mechanism_module


class TransferFailedError(Exception):
    pass


TransferSpecBase = namedtuple("TransferSpecBase", "url transfer_mechanism transfer_mechanism_options")


class TransferSpec(TransferSpecBase):

    def run_transfer(self, output_path):
        transfer_module = transfer_mechanism_module(self.transfer_mechanism)
        return transfer_module.transfer_data_file(self.url, output_path, self.transfer_mechanism_options)

    def get_transfer_data(self):
        with NamedTemporaryFile() as temp_f:
            success, _ = self.run_transfer(temp_f.name)
            if not success:
                raise TransferFailedError()
            return temp_f.read()

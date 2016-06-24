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

import unittest
from unittest.mock import ANY, patch

from client.transfer.base import Transfer, TransferFailedError


class TestTransferSpec(unittest.TestCase):

    def setUp(self):
        self.file_url = "http://www.example.com/files/test.txt"
        self.transfer_mechanism = "curl"
        self.transfer_mechanism_options = {}
        self.output_path = "/tmp/test.txt"
        self.file_data = b"hello world"

        self.transfer = Transfer(self.file_url, self.transfer_mechanism, self.transfer_mechanism_options)

    def _write_file_data(self, output_path):
        with open(output_path, "w+b") as f:
            f.write(self.file_data)
        return (True, "")

    def test_get_transfer_data(self):
        with patch.object(self.transfer, "run", side_effect=self._write_file_data) as mock_run_transfer:
            data = self.transfer.get_data()
            mock_run_transfer.assert_called_once_with(ANY)
            self.assertEqual(data, self.file_data)

    def test_raises_if_unable_to_transfer(self):
        """
        Transfer#get_transfer_data should raise a TransferFailedError if run_transfer reported failure.
        """
        with patch.object(self.transfer, "run", return_value=(False, "")):
            self.assertRaises(TransferFailedError, self.transfer.get_data)

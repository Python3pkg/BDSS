import argparse
import hashlib
import os
import sys
import time
import traceback
from collections import namedtuple

import requests

from ..config import metadata_repository_url
from ..transfer_mechanisms import default_mechanism, transfer_mechanism_module

TransferSpec = namedtuple("TransferSpec", "url transfer_mechanism transfer_mechanism_options")


def configure_parser(parser):
    parser.add_argument("urls",
                        help="URLs of data files to download",
                        metavar="data-file-urls",
                        nargs="*")

    parser.add_argument("-m", "--url-manifest",
                        dest="manifest_file",
                        help="Path to file containing a list of URLs of data files to download.",
                        type=argparse.FileType("r"))


def file_md5sum(filename):
    """
    Calculate the MD5 hash of a file.

    Parameters:
    filename - String - The name of the file.
    """
    h = hashlib.md5()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def send_timing_report(success, data_file_url, file_size_bytes, transfer_duration_seconds, file_checksum, mechanism_output):
    """
    Send a timing report to the metadata repository.

    Parameters:
    data_file_url - String - The URL of the data file that was transferred.
    file_size_bytes - Integer - The size of the data file (in bytes).
    transfer_duration_seconds - Float - The time required to download the file (in seconds).
    file_checksum - String - The MD5 checksum of the downloaded file.
    mechanism_output - String - The output of the transfer mechanism used.
    """
    requests.post(metadata_repository_url + "/timing_reports",
                  data={
                      "is_success": success,
                      "url": data_file_url,
                      "file_size_bytes": file_size_bytes,
                      "transfer_duration_seconds": transfer_duration_seconds,
                      "file_checksum": file_checksum,
                      "mechanism_output": mechanism_output
                  })


def transfer_data_file(specs, output_path):
    """
    Transfer a data file.

    Parameters:
    specs - TransferSpec[] - List of TransferSpecs for difference sources for the data file.
    output_path - String - The path to save the downloaded file to.
    """
    print(specs)
    for s in specs:
        transfer_module = transfer_mechanism_module(s.transfer_mechanism)
        start_time = time.time()

        # This assumes transfer_data_file returns an object with a "stdout" member containing the output of
        # the transfer mechanism. Or if it throws an exception, the exception has a "stdout" member.
        # This is true if transfer_data_file returns the result of subprocess.run.
        success = False
        mechanism_output = ""
        try:
            (success, mechanism_output) = transfer_module.transfer_data_file(s.url, output_path, s.transfer_mechanism_options)
        except Exception:
            print("Exception occurred in %s transfer mechanism", s.transfer_mechanism, file=sys.stderr)
            traceback.print_exc()
        finally:
            time_elapsed = time.time() - start_time
            file_size = os.stat(output_path).st_size
            file_checksum = file_md5sum(output_path)
            send_timing_report(success, s.url, file_size, time_elapsed, file_checksum, mechanism_output)
            if success:
                return True

    return False


def handle_action(args, parser):
    if args.manifest_file:
        args.urls = [line.strip() for line in args.manifest_file if line.strip()]

    if not args.urls:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    for url in args.urls:

        output_path = url.partition("?")[0].rpartition("/")[2]
        transfer_specs = None

        if os.path.isfile(output_path):
            print("File at", url, "already exists at", output_path, file=sys.stderr)
            continue

        try:
            response = requests.post("%s/transformed_urls" % metadata_repository_url,
                                     data={"url": url},
                                     headers={"Accept": "application/json"})

            print(response.text)
            response = response.json()

            transfer_specs = [TransferSpec(r["transformed_url"],
                              r["transform_applied"]["to_data_source"]["transfer_mechanism_type"],
                              r["transform_applied"]["to_data_source"]["transfer_mechanism_options"]) for r in response["results"]]

        except Exception:
            traceback.print_exc()

        if not transfer_specs:
            transfer_specs = [TransferSpec(url, *default_mechanism(url))]

        if not transfer_data_file(transfer_specs, output_path):
            print("Failed to download file", file=sys.stderr)

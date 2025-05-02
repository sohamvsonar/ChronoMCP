#!/usr/bin/env python3
import argparse
import subprocess
import re

# Path to your reader binary and config file
READER_BINARY = "/home/ssonar/chronolog/Debug/test_1/build/hdf5_file_reader"
CONFIG_FILE    = "/home/ssonar/chronolog/Debug/conf/grapher_conf_1.json"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run ChronoLog HDF5 reader and print only the 'record' fields."
    )
    parser.add_argument(
        "-C", "--chronicle",
        help="Chronicle name to pass to -C",
        metavar="NAME"
    )
    parser.add_argument(
        "-S", "--story",
        help="Story name to pass to -S",
        metavar="NAME"
    )
    parser.add_argument(
        "-st", "--start_time",
        help="Start timestamp to pass to -st",
        metavar="TS"
    )
    parser.add_argument(
        "-et", "--end_time",
        help="End timestamp to pass to -et",
        default="1746146975184251801",
        metavar="TS"
    )
    return parser.parse_args()

def build_command(args):
    cmd = [
        "stdbuf", "-o0",
        READER_BINARY,
        "-c", CONFIG_FILE
    ]
    if args.chronicle:
        cmd += ["-C", args.chronicle]
    if args.story:
        cmd += ["-S", args.story]
    if args.start_time:
        cmd += ["-st", args.start_time]
    # always include end time (uses default if none provided)
    cmd += ["-et", args.end_time]
    return cmd

def run_and_print_records(cmd):
    # capture stdout
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout

    # extract record="…"
    records = re.findall(r'record="([^"]*)"', output)
    for record in records:
        print(record)

def main():
    args = parse_args()
    cmd = build_command(args)
    run_and_print_records(cmd)

if __name__ == "__main__":
    main()

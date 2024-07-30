import argparse
import os
import os.path
from subprocess import call
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Add directory of cache save files to Conan cache.')
    parser.add_argument("cache_file_directory")
    parser.add_argument('--remove', action='store_true', help="remove files after restoring them in the cache.")

    args = parser.parse_args()
    print(args)

    if not os.path.isdir(args.cache_file_directory):
        print(f"'{args.cache_file_directory}' is not a directory.")
        exit(1)

    exitCode = 0;
    for x in os.listdir(args.cache_file_directory):
        filename = os.path.join(args.cache_file_directory, x)
        if not os.path.isfile(filename):
            continue

        cmd = f'conan cache restore "{filename}"'
        print(f"Running : {cmd}")
        cmdExitCode = call(cmd, shell=True)
        if cmdExitCode != 0:
            print(f"{cmd} => errorCode {cmdExitCode}", file=sys.stderr)
            exitCode = cmdExitCode

        if args.remove:
            print(f"Deleting : {filename}")
            os.remove(filename)
    exit(exitCode)

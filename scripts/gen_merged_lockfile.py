import argparse
import json
import os
import subprocess
import sys
import tempfile

def main():
	parser = argparse.ArgumentParser(
		prog='gen_lockfile',
	    description='Generates lockfiles for all profiles and merges them into a single file.')
	parser.add_argument('out_file')
	parser.add_argument('extra_requires', nargs="*", default=[])


	cmd_line_args = parser.parse_args()

	profiles = [
		'msvc_profile',
		'linux_default',
		'macos_default',
		'macos_arm_default'
	]

	requires = 'natron_installer/conan_build'
	extra_requires = ""
	for x in cmd_line_args.extra_requires:
		extra_requires += f" --requires '{x}'"

	with tempfile.TemporaryDirectory() as tmpdirname:
		lockfiles = []
		for profile in profiles:
			lockfile_name = os.path.join(tmpdirname, f"{profile}-conan.lock")
			cmd = f"conan lock create -pr:a {profile} --build='*' --requires '{requires}' {extra_requires} --update --lockfile-out={lockfile_name}"
			subprocess.check_output(cmd, shell=True)
			lockfiles.append(lockfile_name)


		merged_lockfile_name = os.path.join(tmpdirname, "merged-conan.lock")
		merge_cmd = f"conan lock merge --lockfile-out {merged_lockfile_name}"
		for x in lockfiles:
			merge_cmd += f" --lockfile {x}"
		print("merge_cmd", merge_cmd)
		subprocess.run(args=merge_cmd, shell=True)

		remove_cmd = f"conan lock remove --lockfile {merged_lockfile_name} --lockfile-out {cmd_line_args.out_file}"
		pkgs_to_remove = ["natron_installer", "natron", "openfx-misc"]
		for x in pkgs_to_remove:
			remove_cmd += f" --requires '{x}/*'"
		print("remove_cmd", merge_cmd)
		subprocess.run(args=remove_cmd, shell=True)


if __name__ == '__main__':
    main()
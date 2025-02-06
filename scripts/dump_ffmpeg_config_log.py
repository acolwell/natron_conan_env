import subprocess
import json
import os
import sys
import tempfile

def find_config(base_dir):
	if not os.path.exists(base_dir):
		print(f'Build folder {base_dir} does not exist')

	if not os.path.isdir(base_dir):
		print(f'Build folder {base_dir} does not exist')

	found_log = False
	for root, dirs, files in os.walk(base_dir, topdown=False):
		log_filename = 'config.log'
		if 	log_filename in files:
			found_log = True
			full_path = os.path.join(root, log_filename)
			print(f'\n\nLog file path: "{full_path}"')
			with open(full_path, 'r') as f:
				for line in f:
					sys.stdout.write(line)
		elif os.path.basename(root) == 'ffbuild':
			print(f"Failed to find log in {root}")
			for f in files:
				print(f"\t{f}")

	if not found_log:
		print(f"Failed to find log in {base_dir}")
	return found_log


def main():
	ffmpeg_pkg_info = json.loads(
		subprocess.check_output(
			f'conan list -c -f json "ffmpeg/*#*:*"',
			stderr=subprocess.DEVNULL,
			shell=True))

	if len(ffmpeg_pkg_info.values()) == 0:
		print("conan list command did not return any info.")
		sys.exit(-1)

	print(ffmpeg_pkg_info)
	found_log = False
	for x in ffmpeg_pkg_info.values():
		print(f'ffmpeg_pkf_info item count: {len(x.items())}')
		for (pkg_name_and_version, pkg_map) in x.items():
			print(f"{pkg_name_and_version} item count: {len(pkg_map['revisions'].items())}")
			for (revision_id, revision_map) in pkg_map['revisions'].items():
				print(f"revision {revision_id} package count: {len(revision_map['packages'].keys())}")
				for package_id in revision_map['packages'].keys():
					pkg_ref = f'{pkg_name_and_version}#{revision_id}:{package_id}'
					print(f"package_ref: {pkg_ref}")

					ffmpeg_build_dir_info = json.loads(
						subprocess.check_output(
							f'conan cache path -f json --folder build "{pkg_ref}"',
							stderr=subprocess.DEVNULL,
							shell=True))
					ffmpeg_build_folder = ffmpeg_build_dir_info['cache_path']
					found_log = find_config(ffmpeg_build_folder)

	if not found_log:
		print("Config was not found. Searching conan home:")
		conan_home = subprocess.check_output(
			f'conan config home',
			stderr=subprocess.DEVNULL,
			shell=True).decode('utf-8').strip()
		base_dir = os.path.join(conan_home,"p","b")
		for x in os.listdir(base_dir):
			if x.startswith("ffmp"):
				full_path = os.path.join(base_dir, x)
				if os.path.isdir(full_path):
					print(f"Found candidate path: {full_path}")
					found_log = find_config(full_path)
					if found_log:
						break

if __name__ == '__main__':
    main()
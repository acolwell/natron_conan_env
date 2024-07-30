import glob
import os
import os.path
import subprocess
import sys

from natron_conan_env import export_recipe_entries

def exportRecipes(repo_root_dir, excludes=[]):
	if not os.path.isdir(repo_root_dir):
		print("{} is not a directory.".format(repo_root_dir))
		return 1

	for ri in export_recipe_entries:
		if ri.name in excludes:
			print(f"\nSkipping {ri.name}")
			continue
		print(f"\nExporting {ri.path}")
		subprocess.run(["conan", "export", ".", "--version={}".format(ri.version)],
			cwd=os.path.join(repo_root_dir, ri.path))

	return 0

if __name__ == "__main__":
	if (len(sys.argv) < 2):
		print("Usage: {} <repo_root_dir> [excluded package names]", sys.argv[0])
		exit(1)
	exit(exportRecipes(sys.argv[1], sys.argv[2:]))

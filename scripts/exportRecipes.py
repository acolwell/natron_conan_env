import glob
import os
import os.path
import subprocess
import sys

class RecipeInfo:
	def __init__(self, path, version):
		self.path = path
		self.version = version

def main(argv):
	if (len(argv) < 2):
		print("Usage: {} <repo_root_dir>", argv[0])
		exit(1)

	repo_root_dir = argv[1]
	if not os.path.isdir(repo_root_dir):
		print("{} is not a directory.".format(repo_root_dir))
		exit(1)


	recipe_entries = []
	recipe_entries.append(RecipeInfo("modules/openfx", "1.4.0"))
	recipe_entries.append(RecipeInfo("recipes/openfx-misc/all", "master"))
	recipe_entries.append(RecipeInfo("recipes/openfx-plugin-tools/all", "0.1"))

	for ri in recipe_entries:
		print(ri.path)
		subprocess.run(["conan", "export", ".", "--version={}".format(ri.version)],
			cwd=os.path.join(repo_root_dir, ri.path))

if __name__ == "__main__":
    main(sys.argv[:])
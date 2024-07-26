import os
import os.path
import subprocess
import sys
import platform

from natron_conan_env import RecipeInfo
from exportRecipes import exportRecipes

def main(argv):
	if (len(argv) < 2):
		print("Usage: {} <repo_root_dir>", argv[0])
		exit(1)

	repo_root_dir = argv[1]
	if not os.path.isdir(repo_root_dir):
		print("{} is not a directory.".format(repo_root_dir))
		exit(1)

	profile = None
	output_filename = None
	if platform.system() == "Windows":
		profile = "msvc_profile"
		output_filename = "conan-cache-save_windows-latest.tgz"
	elif platform.system() == "Linux":
		profile = "linux_default"
		output_filename = "conan-cache-save_ubuntu-latest.tgz"
	else:
		print(f"Unexpected platform {platform.system()}")
		exit(1)

	print("Profile:", profile)
	print("OutputFilename:", output_filename)

	recipe_entries = [
		RecipeInfo("recipes/openfx-misc/all", "openfx-misc", "master"),
		RecipeInfo("recipes/natron/all", "natron", "conan_build"),
	]

	print("\nRemoving all packages...")
	subprocess.run(["conan", "remove", "-c", "*"], cwd=repo_root_dir)

	print("\nExporting recipes...")
	exportRecipes(repo_root_dir)

	for ri in recipe_entries:
		print(f"\nBuilding and installing dependencies for {ri.path}")
		subprocess.run(["conan", "create", f"-pr:a={profile}", f"--version={ri.version}", "--build=missing", ".", ],
			cwd=os.path.join(repo_root_dir, ri.path))

		print(f"\nRemoving {ri.name}/{ri.version}")
		subprocess.run(["conan", "remove", "-c", f"{ri.name}/{ri.version}:*"], cwd=repo_root_dir)

	print("\nCleaning cache...")
	subprocess.run(["conan", "cache", "clean", "*"], cwd=repo_root_dir)

	print(f"\nSaving cache to {output_filename}...")
	subprocess.run(["conan", "cache", "save", f"--file={output_filename}", "*:*"])


if __name__ == "__main__":
    main(sys.argv[:])

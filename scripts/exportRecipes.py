import glob
import os
import os.path
import subprocess
import sys

from natron_conan_env import RecipeInfo

def exportRecipes(repo_root_dir):
	if not os.path.isdir(repo_root_dir):
		print("{} is not a directory.".format(repo_root_dir))
		return 1

	qt5_version = "5.15.14"

	recipe_entries = [
		RecipeInfo("modules/openfx", "openfx", "1.4.0"),
		RecipeInfo("recipes/openfx-misc/all", "openfx-misc", "master"),
		RecipeInfo("recipes/openfx-plugin-tools/all", "openfx-plugin-tools", "0.1"),
		RecipeInfo("recipes/natron/all", "natron", "conan_build"),
		RecipeInfo("recipes/clang/all", "clang", "18.1.0"),
		RecipeInfo("recipes/llvm/all", "llvm", "18.1.0"),
		RecipeInfo("modules/conan-center-index/recipes/qt/5.x.x", "qt", qt5_version),
		RecipeInfo("recipes/pyside2/all", "pyside2", qt5_version),
		RecipeInfo("recipes/shiboken2/all", "shiboken2", qt5_version),
	]

	for ri in recipe_entries:
		print(f"\nExporting {ri.path}")
		subprocess.run(["conan", "export", ".", "--version={}".format(ri.version)],
			cwd=os.path.join(repo_root_dir, ri.path))

	return 0

if __name__ == "__main__":
	if (len(sys.argv) < 2):
		print("Usage: {} <repo_root_dir>", sys.argv[0])
		exit(1)
	exit(exportRecipes(sys.argv[1]))

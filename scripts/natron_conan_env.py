class RecipeInfo:
	def __init__(self, path, name, version, extra_options=[]):
		self.path = path
		self.name = name
		self.version = version
		self.extra_options = extra_options


export_recipe_entries = [
		RecipeInfo("modules/conan-center-index/recipes/cairo/all", "cairo", "1.18.0"),
		RecipeInfo("modules/conan-center-index/recipes/cpython/all", "cpython", "3.10.14", extra_options=["cpython/*:shared=True"]),
		RecipeInfo("modules/conan-center-index/recipes/sqlite3/all", "sqlite3", "3.46.0"),
		RecipeInfo("modules/conan-center-index/recipes/tk/all", "tk", "8.6.10"),
		RecipeInfo("modules/conan-center-index/recipes/qt/5.x.x", "qt", "5.15.14", extra_options=["qt/*:shared=True", "qt/*:qttools=False", "qt/*:qttranslations=False", "qt/*:qtdoc=False", "qt/*:essential_modules=False"]),
		RecipeInfo("modules/openfx", "openfx", "1.4.0"),
		RecipeInfo("recipes/clang/all", "clang", "18.1.0"),
		RecipeInfo("recipes/llvm/all", "llvm", "18.1.0"),
		RecipeInfo("recipes/openfx-misc/all", "openfx-misc", "master"),
		RecipeInfo("recipes/openfx-plugin-tools/all", "openfx-plugin-tools", "0.1"),
		RecipeInfo("recipes/natron/all", "natron", "conan_build"),
	]

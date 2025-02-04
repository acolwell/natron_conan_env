import json
import os
import sys

from natron_conan_env import export_recipe_entries

def main(argv):
    recipes_to_build = ["cpython", "qt", "cairo"]

    recipe_map = {}
    for ri in export_recipe_entries:
        recipe_map[ri.name] = ri

    package_info = []
    for recipe_name in recipes_to_build:
        ri = recipe_map[recipe_name]

        pi = {}
        pi["name"] = ri.name
        pi["version"] = ri.version
        pi["path"] = ri.path

        if len(ri.extra_options):
            extra_options = ""
            for x in ri.extra_options:
                extra_options += f' -o "{x}"'
            pi["extra_options"] = extra_options
        package_info.append(pi)
    print(f'package_info={json.dumps(package_info)}')

if __name__ == "__main__":
    main(sys.argv[:])
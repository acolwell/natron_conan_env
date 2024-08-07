from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment
from conan.tools.scm import Git, Version
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy

import os.path
import fnmatch
import re
import shutil

class natronRecipe(ConanFile):
    name = "natron"
    package_type = "application"

    # Optional metadata
    license = "GPL-2.0-only"
    author = "The Natron Developers"
    url = "<Package recipe repository url here, for issues about the package>"
    description = "Natron is a free and open-source node-based compositing application"
    topics = ("<Put some tag here>", "<here>", "<and here>")

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"

    default_options = {
        "cpython/*:shared": True,
        "qt/*:shared": True
    }

    default_build_options = {
        "cpython/*:shared": True,
        "qt/*:shared": True,
    }

    def requirements(self):
        self.requires("expat/2.6.2")
        self.requires("boost/1.84.0")
        self.requires("cairo/1.18.0")
        self.requires("qt/5.15.14")
        self.requires("glog/0.6.0")
        self.requires("ceres-solver/1.14.0")
        self.requires("cpython/3.10.14")

        self.requires("openfx-misc/master")

    def build_requirements(self):
        self.tool_requires("cpython/<host_version>")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        git = Git(self)
        git.fetch_commit(url=self.conan_data["sources"][self.version]["url"], commit=self.conan_data["sources"][self.version]["commit"])
        git.run("submodule update -i --recursive --depth 1")
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.preprocessor_definitions["NATRON_RUN_WITHOUT_PYTHON"] = 1
        tc.cache_variables["BUILD_USER_NAME"] = ""
        tc.cache_variables["NATRON_SYSTEM_LIBS"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _copy_python_module(self, pkg_name, comp_name):
        py_version = Version(self.dependencies["cpython"].ref.version)
        py_dir_name = f"python{py_version.major}.{py_version.minor}"
        dst_dir = os.path.join(self.package_folder, "lib")

        mod = self.dependencies[pkg_name]
        mod_cpp_info = mod.cpp_info.components[comp_name]
        mod_pkg_path = os.path.join(mod.package_folder, mod_cpp_info.libdirs[0])
        python_path = os.path.join(mod_pkg_path, py_dir_name)

        files = []
        files += copy(self, "*.so", mod_pkg_path, dst_dir)
        files += copy(self, "*.so.*", mod_pkg_path, dst_dir)
        files += copy(self, "*.dll", mod_pkg_path, dst_dir)
        files += copy(self, "*.dynlib", mod_pkg_path, dst_dir)
        files += copy(self, "*", python_path, os.path.join(dst_dir, py_dir_name))
        return files

    def fix_rpath(self, directory, rpath, recurse=False):
        base_dir = os.path.join(self.package_folder, directory)
        dirs_left = [(base_dir, rpath)]
        while len(dirs_left):
            (current_dir, current_rpath) = dirs_left.pop(0)
            for filename in os.listdir(current_dir):
                binary_path = os.path.join(current_dir, filename)
                if os.path.isfile(binary_path):
                    if self.settings.os == "Linux":
                        print(f"Updating RPATH for {binary_path}")
                        cmd = f'patchelf --force-rpath --set-rpath "\\$ORIGIN{current_rpath}" {binary_path}'
                        self.run(cmd)
                elif os.path.isdir(binary_path) and recurse:
                    next_rpath = "/.." + current_rpath if len(current_rpath) > 0 else ""
                    dirs_left.append((binary_path, next_rpath))

    def package(self):
        cmake = CMake(self)
        cmake.install()

        files = []

        files += self._copy_python_module("cpython", "embed")

        deps_lib_dir = os.path.join(self.package_folder, "deps_lib")
        if not os.path.exists(deps_lib_dir):
            os.makedirs(deps_lib_dir)

        for dep in self.dependencies.values():
            if not dep.is_build_context and dep.package_folder and len(dep.cpp_info.libdirs):
                src_dir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
                if not os.path.exists(src_dir):
                    continue

                files += copy(self, "*.so", src_dir, deps_lib_dir)
                files += copy(self, "*.so.*", src_dir, deps_lib_dir)
                files += copy(self, "*.dll", src_dir, deps_lib_dir)
                files += copy(self, "*.dynlib", src_dir, deps_lib_dir)
                if dep.ref.name == "qt":
                    # Copy Qt plugins. These need to either be in the "bin" directory
                    # or in "../plugins" relative to the Qt shared libraries.
                    files += copy(self, "*", os.path.join(dep.package_folder, "plugins"),
                        os.path.join(self.package_folder, "bin"))

        print(f"\n\nfiles copied:")
        for x in files:
            print(f"\t{x}")

        dest_plugins_dir = os.path.join(self.package_folder, "Plugins","OFX", "Natron")
        os.makedirs(dest_plugins_dir)
        plugin_src_base = self.dependencies["openfx-misc"].package_folder
        for x in os.listdir(plugin_src_base):
            if re.match("^.*\\.ofx\\.bundle$", x):
                print(f"Copying {x}")
                shutil.copytree(os.path.join(plugin_src_base, x), os.path.join(dest_plugins_dir, x))

        self.fix_rpath("bin", "/../deps_lib", recurse=True)
        self.fix_rpath("deps_lib", "")

    def package_info(self):
        # TODO add finer grain components.
        self.cpp_info.requires = ["qt::qt", "cpython::cpython", "expat::expat", "boost::boost", "cairo::cairo", "glog::glog", "ceres-solver::ceres-solver", "openfx-misc::openfx-misc"]

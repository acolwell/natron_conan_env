from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy
from conan.tools.microsoft import VCVars
from conan.tools.scm import Git, Version

import fnmatch
from io import StringIO
import os.path
import re
import shutil
import subprocess

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

        if self.settings.os == "Windows":
            ms = VCVars(self)
            ms.generate()

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
        python_path = os.path.join(mod.package_folder, "bin", "Lib") if self.settings.os == "Windows" else os.path.join(mod_pkg_path, py_dir_name)

        files = []
        files += copy(self, "*.so", mod_pkg_path, dst_dir)
        files += copy(self, "*.so.*", mod_pkg_path, dst_dir)
        files += copy(self, "*.dll", mod_pkg_path, dst_dir)
        files += copy(self, "*.dylib", mod_pkg_path, dst_dir)
        files += copy(self, "*", python_path, os.path.join(dst_dir, py_dir_name), excludes=("__pycache__", "*.pyc"))
        return files

    def fix_rpath(self, directory, rpath_list, recurse=False):
        base_dir = os.path.join(self.package_folder, directory)
        dirs_left = [(base_dir, rpath_list)]
        while len(dirs_left):
            (current_dir, current_rpath_list) = dirs_left.pop(0)
            for filename in os.listdir(current_dir):
                binary_path = os.path.join(current_dir, filename)
                if os.path.isfile(binary_path):
                    if self.settings.os == "Linux":
                        print(f"Updating RPATH for {binary_path}")
                        for current_rpath in current_rpath_list:
                            origin_path = f"/{current_rpath}" if len(current_rpath) > 0 else ""
                            cmd = f'patchelf --force-rpath --set-rpath "\\$ORIGIN{origin_path}" {binary_path}'
                            self.run(cmd)
                    elif self.settings.os == "Macos" and len(current_rpath) > 0:
                        file_info = subprocess.check_output(["file", "-b", binary_path])
                        if file_info.decode("utf-8").find("Mach-O") == 0:
                            print(f"Updating rpath for {binary_path}")
                            cmd = 'install_name_tool'
                            for current_rpath in current_rpath_list:
                                new_rpath = f"@loader_path/{current_rpath}"
                                cmd += ' -add_rpath "{new_rpath}"'
                            cmd +=  f" {binary_path}"
                            self.run(cmd)

                elif os.path.isdir(binary_path) and recurse:
                    next_rpath_list = []
                    for x in current_rpath_list:
                        next_rpath_list.append(os.path.join("..", x))
                    dirs_left.append((binary_path, next_rpath_list))

    @property
    def _deps_lib_dir(self):
        if self.settings.os == "Windows":
            # All dependencies need to be in the bin dir next to the executables on Windows
            # so that we don't have to update PATH environment variable to find them.
            return os.path.join(self.package_folder, "bin")

        return os.path.join(self.package_folder, "deps_lib")

    @property
    def _qt_base_dir(self):
        if self.settings.os == "Windows":
            return self._deps_lib_dir

        return os.path.join(self._deps_lib_dir, "Qt")

    @property
    def _qt_lib_dir(self):
        if self.settings.os == "Windows":
            # Copy all the Qt libraries into the same directory as the other dependencies.
            return self._deps_lib_dir
        return os.path.join(self._qt_base_dir, "lib")

    @property
    def _qt_plugins_dir(self):
        if self.settings.os == "Windows":
            # Qt plugins need to be installed in the same directory as the
            # executable so that Qt does not try to look for them in bin/../plugins
            return self._deps_lib_dir

        return os.path.join(self._qt_base_dir, "plugins")

    def package(self):
        cmake = CMake(self)
        cmake.install()

        files = []

        files += self._copy_python_module("cpython", "embed")

        if not os.path.exists(self._deps_lib_dir):
            os.makedirs(self._deps_lib_dir)

        for dep in self.dependencies.values():
            if not dep.is_build_context and dep.package_folder and len(dep.cpp_info.libdirs):
                src_dir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0] if self.settings.os != "Windows" else dep.cpp_info.bindirs[0])
                if not os.path.exists(src_dir):
                    continue

                dst_dir = self._deps_lib_dir
                if dep.ref.name == "qt":
                    dst_dir = self._qt_lib_dir
                    # Copy Qt plugins. These need to be in "../plugins" relative to the Qt shared libraries.
                    files += copy(self, "*", os.path.join(dep.package_folder, "plugins"),
                        self._qt_plugins_dir)

                files += copy(self, "*.so", src_dir, dst_dir)
                files += copy(self, "*.so.*", src_dir, dst_dir)
                files += copy(self, "*.dll", src_dir, dst_dir)
                files += copy(self, "*.dylib", src_dir, dst_dir)

        print(f"\n\nfiles copied:")
        for x in files:
            print(f"\t{x}")

        ofx_plugins_base_dir = self.package_folder
        if self.settings.os == "Macos":
            ofx_plugins_base_dir = os.path.join(ofx_plugins_base_dir, "bin", "Natron.app", "Contents")
        dest_plugins_dir = os.path.join(ofx_plugins_base_dir, "Plugins","OFX", "Natron")

        os.makedirs(dest_plugins_dir)
        plugin_src_base = self.dependencies["openfx-misc"].package_folder
        for x in os.listdir(plugin_src_base):
            if re.match("^.*\\.ofx\\.bundle$", x):
                print(f"Copying {x}")
                shutil.copytree(os.path.join(plugin_src_base, x), os.path.join(dest_plugins_dir, x))

        # Fix rpaths so binaries can find their dependencies.
        bin_dir = os.path.join(self.package_folder, "bin")
        rel_deps_lib = os.path.relpath(self._deps_lib_dir, bin_dir)
        rel_qt_lib = os.path.relpath(self._qt_lib_dir, bin_dir)
        paths_for_bin = set()
        if rel_deps_lib != ".":
            paths_for_bin.add(rel_deps_lib)
        if rel_qt_lib != ".":
            paths_for_bin.add(rel_qt_lib)
        if len(paths_for_bin) == 0:
            paths_for_bin.add("")
        self.fix_rpath("bin", list(paths_for_bin), recurse=True)

        if rel_deps_lib != ".":
            # deps_lib is not the bin directory so fix all the rpaths in that directory as well.
            self.fix_rpath(os.path.relpath(self._deps_lib_dir, self.package_folder), [""])

    def package_info(self):
        # TODO add finer grain components.
        self.cpp_info.requires = ["qt::qt", "cpython::cpython", "expat::expat", "boost::boost", "cairo::cairo", "glog::glog", "ceres-solver::ceres-solver", "openfx-misc::openfx-misc"]

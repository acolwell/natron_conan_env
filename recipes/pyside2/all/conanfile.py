from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, check_sha256, download, export_conandata_patches, unzip
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

import shutil
import os
from io import StringIO

class Pyside2Conanfile(ConanFile):
    name = "pyside2"
    description = "Provides LGPL Qt5 bindings for Python and related tools for binding generation"
    license = "spdx:LGPL-3.0-only OR GPL-3.0-or-later"
    homepage = "https://doc.qt.io/qtforpython-5"

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"

    default_options = {
        "cpython/*:shared": True,
        "qt/*:shared": True,
        }

    default_build_options = {
        "cpython/*:shared": True,
        "qt/*:shared": True,
        }


    def build_requirements(self):
        self.tool_requires(f"qt/{self.version}")
        self.tool_requires("cpython/<host_version>")
        self.tool_requires("shiboken2/<host_version>")

    def requirements(self):
        self.requires(f"qt/{self.version}")
        self.requires(f"shiboken2/{self.version}")
        self.requires("cpython/3.10.14")

        self.requires("sqlite3/3.45.2", override=True)
        self.requires("fontconfig/2.15.0", override=True)


    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        zip_name = f"PySide2-{self.version}-src/pyside-setup-opensource-src-{self.version}.zip"
        download(self, self.conan_data["sources"][self.version]["url"] + '/' + zip_name, zip_name)
        check_sha256(self, zip_name, "929168faa5ba70528c025b34a66c9e6066169ac75b08472058d180d9b70b49a5")
        unzip(self, filename=zip_name, strip_root=True)
        os.unlink(zip_name)

        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        ms = VirtualBuildEnv(self)
        ms.generate()
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = False
        tc.variables["DISABLE_DOCSTRINGS"] = True
        tc.variables["QtNetwork_disabled_features"] = "sctp"
        tc.generate()

    # This method is used to build the source code of the recipe using the desired commands.
    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="sources/pyside2")
        cmake.build()

    def _get_lib_name(self, base_name):
        prefix = "" if self.settings.os == "Windows" else "lib"
        python_bin = os.path.join(
            self.dependencies["cpython"].cpp_info.bindirs[0], "python3")
        output = StringIO()
        cmd = f"{python_bin} -c 'import importlib.machinery; print(importlib.machinery.EXTENSION_SUFFIXES[0])'"
        self.run(cmd, output)
        suffix = output.getvalue()
        return f"{prefix}{base_name}{suffix}"

    def package_info(self):
        self.cpp_info.components["libpyside2"].libs = [self._get_lib_name("pyside2")]
        self.cpp_info.components["libpyside2"].libdirs = ["lib"]
        self.cpp_info.components["libpyside2"].includedirs = ["include/PySide2"]
        self.cpp_info.requires = ["qt::qt", "shiboken2::libshiboken2", "cpython::cpython"]

    def package(self):
        cmake = CMake(self)
        cmake.install()

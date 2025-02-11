from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
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
        "qt/*:qttool": False,
        "qt/*:qttranslations": False,
        "qt/*:qtdoc": False,
        "qt/*:essential_modules": False,
        }

    default_build_options = {
        "cpython/*:shared": True,
        "qt/*:shared": True,
        "qt/*:qttool": False,
        "qt/*:qttranslations": False,
        "qt/*:qtdoc": False,
        "qt/*:essential_modules": False,
        }

    def build_requirements(self):
        self.tool_requires("shiboken2/<host_version>")

    def requirements(self):
        self.requires(f"qt/{self.version}")
        self.requires(f"shiboken2/{self.version}")
        self.requires("cpython/3.10.14")


    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        zip_name = f"PySide2-{self.version}-src/pyside-setup-opensource-src-{self.version}.zip"
        download(self, self.conan_data["sources"][self.version]["url"] + '/' + zip_name, zip_name)
        check_sha256(self, zip_name, self.conan_data["sources"][self.version]["sha256"])
        unzip(self, filename=zip_name, strip_root=True)
        os.unlink(zip_name)

        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        vbe = VirtualBuildEnv(self)
        vbe.generate()
        vre = VirtualRunEnv(self)
        vre.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = False
        tc.variables["DISABLE_DOCSTRINGS"] = True
        tc.variables["QtNetwork_disabled_features"] = "sctp"
        tc.generate()

    # This method is used to build the source code of the recipe using the desired commands.
    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_VERBOSE_MAKEFILE":"ON"}, build_script_folder="sources/pyside2")
        cmake.build(cli_args=["-v"])

    def _get_lib_name(self, base_name):
        prefix = "" if self.settings.os == "Windows" else "lib"

        # Suffix examples
        # MacOS : .cpython-310-darwin.dylib
        # Windows: .cp310-win_amd64.pyd
        # Linux: .cpython-310-x86_64-linux-gnu.so
        suffix = None
        if self.settings.os == 'Linux':
            python_version = self.dependencies["cpython"].ref.version
            suffix = f".cpython-{python_version.major}{python_version.minor}-x86_64-linux-gnu.so"
        else:
            python_bin = os.path.join(
            self.dependencies["cpython"].cpp_info.bindirs[0], "python" if self.settings.os == "Windows" else "python3")

            output = StringIO()
            cmd = f'{python_bin} -c "import importlib.machinery; print(importlib.machinery.EXTENSION_SUFFIXES[0])"'
            self.run(cmd, output)
            suffix = output.getvalue().strip()

        if self.settings.os == "Macos" and suffix.endswith(".so"):
            suffix = suffix.replace(".so", ".dylib")
        elif self.settings.os == "Windows" and suffix.endswith(".pyd"):
            suffix = suffix.replace(".pyd", ".lib")

        return f"{prefix}{base_name}{suffix}"

    def package_info(self):
        self.cpp_info.components["libpyside2"].libs = [self._get_lib_name("pyside2")]
        self.cpp_info.components["libpyside2"].libdirs = ["lib"]
        self.cpp_info.components["libpyside2"].includedirs = ["include/PySide2"]
        self.cpp_info.requires = ["qt::qt", "shiboken2::libshiboken2", "cpython::embed"]

    def package(self):
        cmake = CMake(self)
        cmake.install()

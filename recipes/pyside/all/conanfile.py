from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, check_sha256, download, export_conandata_patches, unzip
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

import shutil
import os

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
        self.tool_requires("clang/<host_version>")
        self.tool_requires("cpython/<host_version>")

    def requirements(self):
        self.requires(f"qt/{self.version}")
        self.requires("libxml2/2.12.7")
        self.requires("libxslt/1.1.39")
        self.requires("clang/18.1.0")
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
        env = Environment()
        env.define_path("CLANG_INSTALL_DIR", self.dependencies["clang"].package_folder)
        env.vars(self).save_script("clang_env")

        if self.settings.os == "Linux":
            # On Linux we need to add python's libdirs to the library path so we can find libpython3.12.so.1.0
            env = Environment()
            for libdir in self.dependencies["cpython"].cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
            env.vars(self).save_script("python_env")

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
        cmake.configure()
        cmake.build()

    @property
    def _version_suffix(self):
        v = Version(self.dependencies["cpython"].ref.version)
        prefix = "cp" if is_msvc(self) else "cpython-"
        sufffix = ""
        if is_msvc(self):
            suffix = "win_amd64"
        elif self.settings.os == "Linux":
            suffix = "-x86_64-linux-gnu"
        elif is_apple_os(self):
            suffix = "-darwin"
        #"cpython-310-x86_64-linux-gnu"
        #"cpython-310-darwin"
        #"cp310-win_amd64"
        return f"{prefix}{v.major}{v.minor}{suffix}"

    @property
    def _abi_suffix(self):
        res = ""
        if self.settings.build_type == "Debug":
            res += "d"
        return res

    def _get_lib_name(self, base_name):
        if is_msvc(self):
            if self.settings.build_type == "Debug":
                lib_ext = "_d"
            else:
                lib_ext = ""
        else:
            lib_ext = self._abi_suffix
         #"pyside2.cpython-310-x86_64-linux-gnu"
         #"pyside2.cpython-310-darwin"
         #"pyside2.cp310-win_amd64"
        return f"{base_name}.{self._version_suffix}{lib_ext}"

    def _get_exact_lib_name(self, base_name):
        prefix = "" if self.settings.os == "Windows" else "lib"
        if self.settings.os == "Windows":
            extension = "lib"
        #elif not self.options.shared:
        #    extension = "a"
        elif is_apple_os(self):
            extension = "dylib"
        else:
            extension = "so"
        return f"{prefix}{self._get_lib_name(base_name)}.{extension}"

    def package_info(self):
        self.cpp_info.requires = ["qt::qt", "libxml2::libxml2", "libxslt::libxslt", "cpython::cpython"]

        self.cpp_info.components["libpyside2"].libs = [self._get_exact_lib_name("pyside2")]
        self.cpp_info.components["libpyside2"].libdirs = ["lib"]
        self.cpp_info.components["libpyside2"].includedirs = ["include/PySide2"]

        self.cpp_info.components["libshiboken2"].libs = [self._get_exact_lib_name("shiboken2")]
        self.cpp_info.components["libshiboken2"].libdirs = ["lib"]
        self.cpp_info.components["libshiboken2"].includedirs = ["include/shiboken2"]

        self.cpp_info.components["shiboken2"].bins = ["shiboken2"]
        self.cpp_info.components["shiboken2"].bindirs = ["bin"]
        self.cpp_info.components["shiboken2"].requires = ["clang::clang"]

        if (self.dependencies['clang'].package_folder):
            self.buildenv_info.define_path("CLANG_INSTALL_DIR", self.dependencies["clang"].package_folder)
            self.runenv_info.define_path("CLANG_INSTALL_DIR", self.dependencies["clang"].package_folder)

        if self.settings.os == "Linux":
            # On Linux we need to add clang libdirs to the library path so we can find libclang
            for libdir in self.dependencies["clang"].cpp_info.libdirs:
                self.buildenv_info.append_path("LD_LIBRARY_PATH", libdir)
                self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)

    def package(self):
        cmake = CMake(self)
        cmake.install()

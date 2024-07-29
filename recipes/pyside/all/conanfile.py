from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, check_sha256, download, export_conandata_patches, unzip

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

    def build_requirements(self):
        self.tool_requires("clang/18.1.0")
        self.tool_requires("llvm/18.1.0")
        self.tool_requires("cpython/3.12.2")

    def requirements(self):
        self.requires(f"qt/{self.version}")
        self.requires("libxml2/2.12.5")
        self.requires("libxslt/1.1.39")
        self.requires("clang/18.1.0")
        self.requires("cpython/3.12.2")

        self.requires("sqlite3/3.45.2", override=True)

    # The build_requirements() method is functionally equivalent to the requirements() one,
    # being executed just after it. It's a good place to define tool requirements,
    # dependencies necessary at build time, not at application runtime
    def build_requirements(self):
        # Each call to self.tool_requires() will add the corresponding build requirement
        # Uncommenting this line will add the cmake >=3.15 build dependency to your project
        # self.requires("cmake/[>=3.15]")
        pass

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
        env.append_path("PATH", self.dependencies["qt"].cpp_info.bindirs[0])
        env.vars(self).save_script("clang_env")

        ms = VirtualBuildEnv(self)
        ms.generate()
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = False
        tc.variables["DISABLE_DOCSTRINGS"] = True
        tc.generate()
       
    # This method is used to build the source code of the recipe using the desired commands.
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

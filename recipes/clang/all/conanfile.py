from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, mkdir
from conan.tools.scm import Git

import os

class ClangConanfile(ConanFile):
    name = "clang"
    version="18.1.8"
    description = "LLVM & Clang"
    license = "Apache-2.0"
    homepage = "https://clang.llvm.org/"

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("zlib/1.3.1")

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def source(self):
        git = Git(self)
        git.fetch_commit(url="https://github.com/llvm/llvm-project.git", commit="llvmorg-{}".format(self.version))
        git.run("submodule update --init --recursive --depth 1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        config_vars = {
            "LLVM_INSTALL_UTILS": "ON",
            "LLVM_ENABLE_PROJECTS": "clang;clang-tools-extra",
            "LLVM_TARGETS_TO_BUILD": "host;AArch64;ARM;X86",
            "LLVM_ENABLE_EH": "ON",
            "LLVM_ENABLE_RTTI": "ON" }

        if self.settings.os == "Windows":
            config_vars["LIBUNWIND_ENABLE_SHARED"] = "OFF"
        else:
            config_vars["LLVM_BUILD_LLVM_DYLIB"] = "ON"
            config_vars["LLVM_LINK_LLVM_DYLIB"] = "ON"
            config_vars["LLVM_ENABLE_RUNTIMES"] = "all"

        cmake.configure(variables=config_vars, build_script_folder="llvm")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

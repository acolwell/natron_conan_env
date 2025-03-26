from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, mkdir
from conan.tools.scm import Git

import os

class LLVMConanfile(ConanFile):
    name = "llvm"
    version="18.1.0"
    description = "LLVM"
    license = "<Your project license goes here>"
    homepage = "<Your project homepage goes here>"

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"

    default_options = {
        }

    # The requirements method allows you to define the dependencies of your recipe
    def requirements(self):
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        self.requires("cmake/[>=3.15]")

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
        cmake.configure(variables={"LLVM_INSTALL_UTILS": "ON"}, build_script_folder="llvm")
        cmake.build()

       
    def package(self):
        cmake = CMake(self)
        #cmake.configure(variables={"LLVM_INSTALL_UTILS": "ON"}, build_script_folder="llvm")
        cmake.install()

        src_folder = os.path.join(self.build_folder,"utils", "lit")
        dst_folder = os.path.join(self.package_folder,"utils", "lit")
        mkdir(self, dst_folder)
        copy(self, "*", src_folder, dst_folder)

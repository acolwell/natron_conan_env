from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy
from conan.tools.scm import Git

import os

class ClangConanfile(ConanFile):
    name = "clang"
    version="18.1.0"
    description = "Clang"
    license = "<Your project license goes here>"
    homepage = "<Your project homepage goes here>"

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"

    default_options = {
        }

    def requirements(self):
        self.requires("llvm/{}".format(self.version))

    #def build_requirements(self):
        #self.requires("cmake/[>=3.15]")

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def source(self):
        git = Git(self)
        git.fetch_commit(url="https://github.com/llvm/llvm-project.git", commit="llvmorg-{}".format(self.version))
        git.run("submodule update -i --recursive --depth 1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"LLVM_EXTERNAL_LIT": os.path.join(self.dependencies["llvm"].package_folder,"utils","lit"),
                                   "LLVM_ROOT": self.dependencies["llvm"].package_folder,
                                   "LLVM_INCLUDE_TESTS": "OFF"},
                        build_script_folder="clang")
        cmake.build()

       
    def package(self):
        cmake = CMake(self)
        cmake.install()
from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Git
import os

class seexprRecipe(ConanFile):
    name = "seexpr"
    version = "2.11"

    # Optional metadata
    license = "Apache-2.0"
    author = "Walt Disney Animation Studios"
    url = "https://github.com/wdas/SeExpr"
    description = "SeExpr - An embeddable expression evaluation engine"
    topics = ()

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False]
        }

    default_options = {
        "shared": False,
        "fPIC": True
        }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True, destination=self.source_folder)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        pc = PkgConfigDeps(self)
        pc.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def requirements(self):
        self.requires("zlib/1.3.1")

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "Windows":
            copy(self, "*", src=os.path.join(self.source_folder, "windows7", "SeExpr"), dst=os.path.join(self.source_folder, "src", "SeExpr"))
            copy(self, "*", src=os.path.join(self.source_folder, "windows7", "SeExprEditor"), dst=os.path.join(self.source_folder, "src", "SeExprEditor"))

        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["-v"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "share", "test"))

        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SeExpr")
        self.cpp_info.set_property("pkg_config_name", "seexpr")

        self.cpp_info.libs = ["SeExpr"]

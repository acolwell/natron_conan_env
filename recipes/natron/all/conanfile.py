from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import Environment
from conan.tools.scm import Git
from conan.tools.files import apply_conandata_patches, export_conandata_patches

import os
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
        "qt/*:shared": True,
        "qt/*:qttool": False,
        "qt/*:qttranslations": False,
        "qt/*:qtdoc": False,
        "qt/*:essential_modules": False,
    }

    def build_requirements(self):
        self.tool_requires(f"shiboken2/<host_version>")

    def requirements(self):
        qt_version = "5.15.16"

        self.requires("expat/2.6.2")
        self.requires("boost/1.84.0")
        self.requires("cairo/1.18.0")
        self.requires(f"shiboken2/{qt_version}")
        self.requires(f"qt/{qt_version}")
        self.requires("glog/0.6.0")
        self.requires("ceres-solver/1.14.0")
        self.requires("cpython/3.10.14")

        if self.settings.os == "Linux":
            self.requires("wayland/1.22.0")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        git = Git(self)
        git.fetch_commit(url=self.conan_data["sources"][self.version]["url"], commit=self.conan_data["sources"][self.version]["commit"])
        git.run("submodule update --init --recursive --depth 1")
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):

        if self.settings.os == "Linux":
            # On Linux we need to add python's libdirs to the library path so we can find libpython3.12.so.1.0
            env = Environment()
            for libdir in self.dependencies["cpython"].cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
            env.vars(self).save_script("python_env")

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

    def package(self):
        cmake = CMake(self)
        cmake.install()

        if self.settings.os == "Macos":
            # Move other binaries so they are with the main Natron app binary.
            for x in ["NatronRenderer", "natron-python"]:
                src_path = os.path.join(self.package_folder, "bin", x)
                shutil.move(src_path,
                    os.path.join(self.package_folder, "bin", "Natron.app", "Contents", "MacOS"))

    def package_info(self):
        self.cpp_info.requires = [
            "qt::qt", "cpython::cpython", "expat::expat", "boost::boost", "cairo::cairo",
            "glog::glog", "ceres-solver::ceres-solver", "shiboken2::libshiboken2"]

        if self.settings.os == "Linux":
            self.cpp_info.requires += ["wayland::wayland"]

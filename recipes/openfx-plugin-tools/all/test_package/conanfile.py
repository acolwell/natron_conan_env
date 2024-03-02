import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps


class openfx_plugin_toolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires('openfx/1.4.0')

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["OFX_SUPPORT_SYMBOLS_DIR"] = os.path.join(self.dependencies["openfx"].package_folder, "lib", "symbols").replace("\\", "\\\\")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run("verify_openfx_plugin_loads {}".format(os.path.join("Release","test_plugin.ofx")), env="conanrun")

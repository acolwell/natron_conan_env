import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps


class openFxIoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.test_requires("openfx-plugin-tools/0.1")

    def test(self):
        if can_run(self):
            plugin_names = ["IO"]
            for plugin_name in plugin_names:
                if self.settings.os == "Windows":
                    plugin_arch = "Win64"
                elif self.settings.os == "Macos":
                    plugin_arch = "MacOS"
                elif self.settings.os == "Linux":
                    plugin_arch = "Linux-x86-64"
                pluginPath = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "{}.ofx.bundle".format(plugin_name), "Contents", plugin_arch, "{}.ofx".format(plugin_name))

                self.run("verify_openfx_plugin_loads {}".format(pluginPath), env="conanrun")

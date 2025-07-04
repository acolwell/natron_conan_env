import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from pathlib import PurePath


class shiboken2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        vbe = VirtualBuildEnv(self)
        vbe.generate()
        vre = VirtualRunEnv(self)
        vre.generate()
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["SHIBOKEN2_BIN"] = PurePath(self.conf.get("user.shiboken2:shiboken2")).as_posix()
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(cli_args=[])
        cmake.build(cli_args=["-v"])

    def test(self):
        if can_run(self):
            cmd = "{} --version".format(os.path.join(self.dependencies[self.tested_reference_str].cpp_info.bindirs[0], "shiboken2"))
            self.run(cmd, env="conanrun")

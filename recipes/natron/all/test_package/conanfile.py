import os
from conan import ConanFile
from conan.tools.build import can_run


class natronTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            cmd = "{} -v".format(os.path.join(self.dependencies[self.tested_reference_str].cpp_info.bindirs[0], "NatronRenderer"))
            self.run(cmd, env="conanrun")

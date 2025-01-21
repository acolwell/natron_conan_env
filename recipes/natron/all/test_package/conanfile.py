import os
from conan import ConanFile
from conan.tools.build import can_run


class natronTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package_base = self.dependencies[self.tested_reference_str].package_folder
            dest_bin_dir = os.path.join(package_base, "bin")
            if self.settings.os == "Macos":
                package_base = os.path.join(dest_bin_dir, "Natron.app", "Contents")
                dest_bin_dir = os.path.join(package_base, "MacOS")

            for binary, version_flag in [("NatronRenderer", "-v"), ("Natron", "-v"), ("natron-python", "--version")]:
                binary_path = os.path.join(dest_bin_dir, binary)
                self.run(f"{binary_path} {version_flag}", env="conanrun")

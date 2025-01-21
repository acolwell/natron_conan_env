import os
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.files import download, patch, replace_in_file


class openfx_plugin_toolsRecipe(ConanFile):
    name = "openfx-plugin-tools"
    version = "0.1"
    package_type = "application"

    # Optional metadata
    license = "GPL-2.0-only"
    author = "Aaron Colwell"
    url = "https://github.com/acolwell/natron_conan_env.git"
    description = "Tools for testing OpenFX plugins"
    topics = ("OpenFX")

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"

    requires = "openfx/1.4.0", "expat/2.6.2"

    # Sources are located in the same place as this recipe, copy them to the recipe
    exports_sources = "CMakeLists.txt", "src/*", "patches/*"

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download a version of the openfx Binary HostSupport class and then patch it so that it forces all symbols to be resolved on load.
        # This stricter loading allows us to detect missing dependencies.
        OpenfxBaseURL = "https://raw.githubusercontent.com/AcademySoftwareFoundation/openfx/470a412412c9aa946d35cb54f29a4fe85baec55a/HostSupport/"
        download(self, "{}/src/ofxhBinary.cpp".format(OpenfxBaseURL), os.path.join(self.source_folder, "src/third_party/ofxhBinaryStrict.cpp"),
            sha256="e18a6b56d2051636b3b5deb83ed22b7b80f7fa431c419218387fea277a11eaf7")
        download(self, "{}/include/ofxhBinary.h".format(OpenfxBaseURL), os.path.join(self.source_folder, "src/third_party/ofxhBinaryStrict.h"),
            sha256="b123c2f4a26326201426ee0c597e239de28b722498f22afe03095245b0223d51")
        patch(self, patch_file=os.path.join(self.source_folder, "patches", "strict_binary.patch"))

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    

    

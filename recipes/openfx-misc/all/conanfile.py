import os
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, patch
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class openFxMiscRecipe(ConanFile):
    name = "openfx-misc"

    # Optional metadata
    license = "GPL-2.0-only"
    author = "The Natron Developers"
    url = "https://github.com/NatronGitHub/openfx-misc"
    description = "Miscellaneous OFX / OpenFX / Open Effects plugins"
    topics = ("OpenFX", "Natron")

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*.patch"

    _deps_lib_folder = "deps_libs"

    def source(self):
        git = Git(self)
        git.fetch_commit(url=self.conan_data["sources"][self.version]["url"], commit=self.conan_data["sources"][self.version]["commit"])
        git.run("submodule update -i --recursive --depth 1")

        # Downloading and patching necessary CImg headers.
        CImgBaseURL="https://raw.githubusercontent.com/dtschump/CImg/{}".format(self.conan_data["sources"][self.version]["CImgCommit"])
        download(self, "{}/CImg.h".format(CImgBaseURL), os.path.join(self.source_folder, "CImg", "CImg.h"),
            sha256=self.conan_data["sources"][self.version]["CImg_H_SHA256"])
        download(self, "{}/plugins/inpaint.h".format(CImgBaseURL), os.path.join(self.source_folder, "CImg", "Inpaint", "inpaint.h"),
            sha256=self.conan_data["sources"][self.version]["Inpaint_H_SHA256"])

        patch(self, base_path=os.path.join(self.source_folder, "CImg"), patch_file=os.path.join(self.source_folder, "CImg", "Inpaint", "inpaint.h.patch"))

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

        dst_folder = os.path.join(self.build_folder, self._deps_lib_folder)
        for dep in self.dependencies.values():
            for src_folder in (dep.cpp_info.bindirs + dep.cpp_info.libdirs):
                if not os.path.exists(src_folder):
                    continue

                copy(self, "*.dylib", src_folder, dst_folder)
                copy(self, "*.dll", src_folder, dst_folder)
                copy(self, "*.so.*", src_folder, dst_folder)
                copy(self, "*.so", src_folder, dst_folder)

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        plugin_arch = None
        if self.settings.os == "Windows":
            plugin_arch = "Win64"
        elif self.settings.os == "Macos":
            plugin_arch = "MacOS"
        elif self.settings.os == "Linux":
            plugin_arch = "Linux-x86-64"

        plugin_names = ["Misc", "CImg"]
        for plugin_name in plugin_names:
            src_folder = os.path.join(self.build_folder, self._deps_lib_folder)
            dst_folder = os.path.join(self.package_folder, f"{plugin_name}.ofx.bundle", "Contents", "Libraries")
            copy(self, "*.dylib", src_folder, dst_folder)
            copy(self, "*.dll", src_folder, dst_folder)
            copy(self, "*.so.*", src_folder, dst_folder)
            copy(self, "*.so", src_folder, dst_folder)

    def package_info(self):
        self.cpp_info.libs = ["openfx-misc"]
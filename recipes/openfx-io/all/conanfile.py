from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy
from conan.tools.scm import Git

import os

class openfx_ioRecipe(ConanFile):
    name = "openfx-io"
    version = "master"
    package_type = "library"

    # Optional metadata
    license = "GPL-2.0-only"
    author = "The Natron Developers"
    url = "https://github.com/NatronGitHub/openfx-io"
    description = "A set of Readers/Writers plugins written using the OpenFX standard"
    topics = ("OpenFX", "Natron")

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {
        "shared": True,
        "fPIC": True,
        "opencolorio/*:shared": True,
        "openimageio/*:shared": True,
        "openimageio/*:with_libpng": True,
        "openimageio/*:with_freetype": True,
        "openimageio/*:with_hdf5": True,
        "openimageio/*:with_opencolorio": True,
        "openimageio/*:with_opencv": False,
        "openimageio/*:with_tbb": False,
        "openimageio/*:with_dicom": False,
        "openimageio/*:with_ffmpeg": False,
        "openimageio/*:with_giflib": True,
        "openimageio/*:with_libheif": True,
        "openimageio/*:with_raw": True,
        "openimageio/*:with_openjpeg": True,
        "openimageio/*:with_openvdb": False,
        "openimageio/*:with_ptex": False,
        "openimageio/*:with_libwebp": True,
        "ffmpeg/*:shared": True,
        "ffmpeg/*:with_libfdk_aac": False, # non-free
        "ffmpeg/*:with_programs": False,
        "ffmpeg/*:with_ssl": False, # non-free until deps updated to openssl 3.x.x
        }

    _deps_lib_folder = "deps_libs"

    def requirements(self):
        self.requires("libraw/0.21.2") # OIIO/ReadOIIO
        self.requires("ffmpeg/6.1") # FFmpeg/FFmpegFile
        self.requires("openexr/3.3.2")  # EXR/ReadEXR, EXR/WriteEXR
        self.requires("opencolorio/2.4.1") # OCIO/*.cpp
        self.requires("openimageio/2.5.18.0") # OIIO/*.cpp
        self.requires("libpng/[>=1.6 <2]") # PNG/ReadPNG, PNG/WritePNG
        self.requires("zlib/1.3.1") # PNG/ReadPNG, PNG/WritePNG
        self.requires("seexpr/2.11") # SeExpr/SeExpr


    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        git = Git(self)
        git.fetch_commit(url=self.conan_data["sources"][self.version]["url"], commit=self.conan_data["sources"][self.version]["commit"])
        git.run("submodule update -i --recursive --depth 1")
        apply_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

        if self.settings.os == "Linux":
            self.options["ffmpeg"].with_pulse = False
            self.options["ffmpeg"].with_libalsa = False
            self.options["ffmpeg"].with_vaapi = False
            self.options["ffmpeg"].with_vdpau = False
        elif self.settings.os == "Macos":
            self.options["minizip-ng"].with_libcomp = False # Required for opencolorio


    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

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
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["-v"])

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

        plugin_names = ["IO"]
        shared_libs = []
        for plugin_name in plugin_names:
            src_folder = os.path.join(self.build_folder, self._deps_lib_folder)
            dst_folder = os.path.join(self.package_folder, f"{plugin_name}.ofx.bundle", "Contents", "Libraries")
            copy(self, "*.dylib", src_folder, dst_folder)
            copy(self, "*.dll", src_folder, dst_folder)
            shared_libs += copy(self, "*.so.*", src_folder, dst_folder)
            shared_libs += copy(self, "*.so", src_folder, dst_folder)

        if self.settings.os == "Linux":
            for binary_path in shared_libs:
                self.output.info(f"Fixing rpath for {binary_path}")
                self.run(f'patchelf --force-rpath --set-rpath \'$ORIGIN\' {binary_path}')

    def package_info(self):
        self.cpp_info.libs = ["openfx-io"]


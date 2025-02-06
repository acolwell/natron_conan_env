import os
import shutil
from conan import ConanFile
from conan.tools.files import copy, rm, save
from conan.tools.layout import basic_layout
from conan.tools.microsoft import VCVars
from conan.tools.scm import Git, Version

import os.path
import re
import shutil
import io
import json
import subprocess

class NatronInstallerConanfile(ConanFile):
    name = "natron_installer"
    version = "conan_build"
    description = "Natron Installer"
    license = "GPL-2.0-only"
    homepage = "<Your project homepage goes here>"

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"

    # The requirements method allows you to define the dependencies of your recipe
    def requirements(self):
        self.requires(f"natron/{self.version}")
        self.requires(f"openfx-misc/master")
        self.requires(f"openfx-io/master")

    def source(self):
        # TODO: Create a proper package for Natron OCIO configs.
        git = Git(self, folder="OpenColorIO-Configs")
        git.fetch_commit(url="https://github.com/NatronGitHub/OpenColorIO-Configs.git",
                commit="master")
        git.run("submodule update -i --recursive --depth 1")


    def layout(self):
        basic_layout(self, src_folder="src")

    def generate(self):
        if self.settings.os == "Windows":
            ms = VCVars(self)
            ms.generate()

    # This method is used to build the source code of the recipe using the desired commands.
    def build(self):
        shutil.copytree(
            os.path.join(self.source_folder, "OpenColorIO-Configs"),
            os.path.join(self.build_folder, "OpenColorIO-Configs"))


    def _fix_rpath(self, directory, rpath_list, recurse=False):
        base_dir = os.path.join(self.package_folder, directory)
        dirs_left = [(base_dir, rpath_list)]
        while len(dirs_left):
            (current_dir, current_rpath_list) = dirs_left.pop(0)
            for filename in os.listdir(current_dir):
                binary_path = os.path.join(current_dir, filename)
                if os.path.islink(binary_path):
                    self.output.info(f"Skipping symlink {binary_path}")
                    continue
                elif os.path.isfile(binary_path):
                    if self.settings.os == "Linux":
                        self.output.info(f"Updating RPATH for {binary_path}")
                        new_rpath = ""
                        for current_rpath in current_rpath_list:
                            origin_path = f"/{current_rpath}" if len(current_rpath) > 0 else ""
                            if len(new_rpath) > 0:
                                new_rpath += ":"
                            new_rpath += f"$ORIGIN{origin_path}"
                        cmd = f'patchelf --force-rpath --set-rpath \'{new_rpath}\' {binary_path}'
                        self.run(cmd)
                    elif self.settings.os == "Macos" and len(current_rpath_list) > 0:
                        file_info = subprocess.check_output(["file", "-b", binary_path])
                        if file_info.decode("utf-8").find("Mach-O") == 0:
                            self.output.info(f"Updating rpath for {binary_path}")
                            cmd = 'install_name_tool'
                            for current_rpath in current_rpath_list:
                                new_rpath = f"@loader_path/{current_rpath}"
                                cmd += f' -add_rpath "{new_rpath}"'
                            cmd +=  f" {binary_path}"
                            self.run(cmd)

                elif os.path.isdir(binary_path) and recurse:
                    next_rpath_list = []
                    for x in current_rpath_list:
                        next_rpath_list.append(os.path.join("..", x))
                    dirs_left.append((binary_path, next_rpath_list))

    @property
    def _deps_lib_dir(self):
        if self.settings.os == "Windows":
            # All dependencies need to be in the bin dir next to the executables on Windows
            # so that we don't have to update PATH environment variable to find them.
            return os.path.join(self.package_folder, "bin")
        elif self.settings.os == "Macos":
            return os.path.join(self.package_folder, "Natron.app", "Contents", "Frameworks")

        return os.path.join(self.package_folder, "lib")

    @property
    def _qt_base_dir(self):
        if self.settings.os == "Windows":
            return self._deps_lib_dir

        return os.path.join(self._deps_lib_dir, "Qt")

    @property
    def _qt_lib_dir(self):
        if self.settings.os == "Windows":
            # Copy all the Qt libraries into the same directory as the other dependencies.
            return self._deps_lib_dir
        return os.path.join(self._qt_base_dir, "lib")

    @property
    def _qt_plugins_dir(self):
        if self.settings.os == "Windows":
            # Qt plugins need to be installed in the same directory as the
            # executable so that Qt does not try to look for them in bin/../plugins
            return self._deps_lib_dir

        return os.path.join(self._qt_base_dir, "plugins")

    def _copy_dependencies(self):
        self.output.info("Copying dependencies...")
        files = []
        install_name_rewrites = []

        deps_to_process = []
        deps_already_requested = set()

        # Collect top level dependencies
        for dep in self.dependencies.host.values():
            deps_to_process.append(dep)
            deps_already_requested.add(dep.ref.name)

        while len(deps_to_process) > 0:
            dep = deps_to_process.pop(0)

            # Collect all of the dependencies of the current dependency being handled
            # and add only the ones that have not been requested yet to the processing list.
            for x in dep.dependencies.host.values():
                if x.ref.name not in deps_already_requested:
                    deps_to_process.append(x)
                    deps_already_requested.add(x.ref.name)

            if not dep.package_folder or len(dep.cpp_info.libdirs) == 0:
                continue

            self.output.info(f"\t{dep.ref.name}")

            src_dir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0] if self.settings.os != "Windows" else dep.cpp_info.bindirs[0])
            if not os.path.exists(src_dir):
                continue

            dst_dir = self._deps_lib_dir
            if dep.ref.name == "qt":
                dst_dir = self._qt_lib_dir
                # Copy Qt plugins. These need to be in "../plugins" relative to the Qt shared libraries.
                files += copy(self, "*", os.path.join(dep.package_folder, "plugins"),
                    self._qt_plugins_dir)
            elif dep.ref.name == "cpython":
               (python_files, python_install_name_rewrites) = self._copy_python(dep)
               files += python_files
               install_name_rewrites += python_install_name_rewrites
               continue

            files += copy(self, "*.so", src_dir, dst_dir)
            files += copy(self, "*.so.*", src_dir, dst_dir)
            files += copy(self, "*.dll", src_dir, dst_dir)
            files += copy(self, "*.dylib", src_dir, dst_dir)

        return (files, install_name_rewrites)

    def _copy_natron_binaries(self, dst_dir):
        self.output.info("Copying Natron binaries...")
        files = []

        natron_package_folder = self.dependencies["natron"].package_folder
        src_dir = os.path.join(natron_package_folder, "bin")
        if self.settings.os == "Macos":
            src_dir = os.path.join(src_dir, "Natron.app", "Contents", "MacOS")

        natron_binaries = ["Natron", "NatronRenderer", "natron-python"]

        for src_binary_filename in natron_binaries:
            if self.settings.os == "Windows":
                src_binary_filename += ".exe"

            full_src_binary_path = os.path.join(src_dir, src_binary_filename)
            full_dst_binary_path = os.path.join(dst_dir, src_binary_filename)
            files.append(shutil.copy(full_src_binary_path, full_dst_binary_path))

        return files

    def _files_in_dir(self, dir_to_walk):
        ret = []
        for root, dirs, files in os.walk(dir_to_walk):
                for x in files:
                    ret.append(os.path.join(root, x))
        return ret


    def _copy_plugins(self, plugins_dir):
        self.output.info("Copying Plugins...")
        files = []

        natron_plugins_dir = os.path.join(plugins_dir, "OFX", "Natron")
        plugin_info = {
            "openfx-misc": ["Misc.ofx.bundle", "CImg.ofx.bundle"],
            "openfx-io": ["IO.ofx.bundle"]
        }
        for (dep_name, dir_list) in plugin_info.items():
            src_base_dir = self.dependencies[dep_name].package_folder
            for x in dir_list:
                dir_copied = shutil.copytree(os.path.join(src_base_dir, x),
                    os.path.join(natron_plugins_dir, x))
                files += self._files_in_dir(dir_copied)
        return files

    def _copy_resources(self, resources_dir):
        self.output.info("Copying Resources ...")
        files = []

        dir_copied = shutil.copytree(
            os.path.join(self.build_folder, "OpenColorIO-Configs"),
            os.path.join(resources_dir, "OpenColorIO-Configs"))
        files += self._files_in_dir(dir_copied)

        return files

    def _copy_system_deps(self, dst_dir):
        files = []

        paths_to_copy = []
        if self.settings.os == "Macos":
            if self.settings.arch == "x86_64":
                paths_to_copy = [
                    "/usr/local/opt/gettext/lib/libintl.8.dylib",
                    ]

        for x in paths_to_copy:
            if not os.path.exists(x):
                self.output.error(f"{x} does not exist.")
            elif not os.path.isfile(x):
                self.output.error(f"{x} is not a file.")
            else:
                if os.path.islink(x):
                    canonical_path = os.path.realpath(x, strict=True)
                    self.output.info(f"{x} is a symbolic link to {canonical_path}.")
                    files += copy(self, os.path.basename(canonical_path),
                        os.path.dirname(canonical_path), dst_dir)

                files += copy(self, os.path.basename(x),
                    os.path.dirname(x), dst_dir)

        return files

    def _create_framework_dir(self, base_path, name, version, shared_lib_src, info_plist_str):
        files = []
        install_name_rewrites = []
        framework_dir = os.path.join(base_path, f"{name}.framework")
        versions_dir = os.path.join(framework_dir, "Versions")
        version_dir = os.path.join(versions_dir, version)
        current_version_dir = os.path.join(versions_dir, "Current")
        resources_dir = os.path.join(version_dir, "Resources")

        os.makedirs(resources_dir)
        files += shutil.copy(shared_lib_src, os.path.join(version_dir, name))
        install_name_rewrites.append((f"@rpath/{os.path.basename(shared_lib_src)}", f"@rpath/{name}.framework/{name}"))
        info_plist_path = os.path.join(resources_dir, "Info.plist")
        save(self, info_plist_path, info_plist_str)
        files += info_plist_path

        os.symlink(version, current_version_dir)
        os.symlink(os.path.join("Versions", "Current", "Resources"),
            os.path.join(framework_dir, "Resources"))
        os.symlink(os.path.join("Versions", "Current", name),
            os.path.join(framework_dir, name))

        return (files, install_name_rewrites)

    def _copy_python(self, dep_info):
        files = []
        install_name_rewrites = []

        py_version = Version(dep_info.ref.version)
        py_version_major_minor = f"{py_version.major}.{py_version.minor}"
        py_dir_name = f"python{py_version_major_minor}"

        shared_lib_src_folder = os.path.join(dep_info.package_folder, "lib")
        shared_lib_src = None
        if self.settings.os == "Windows":
            shared_lib_src = os.path.join(dep_info.package_folder, "bin", f"python{py_version.major}{py_version.minor}.dll")
        elif self.settings.os == "Linux":
            shared_lib_src = os.path.join(dep_info.package_folder, "lib", f"lib{py_dir_name}.so.1.0")
        elif self.settings.os == "Macos":
            shared_lib_src = os.path.join(dep_info.package_folder, "lib", f"lib{py_dir_name}.dylib")
        else:
            raise Exception(f"Can't determine python shared library for {self.settings.os}")

        dst_dir = self._deps_lib_dir
        if self.settings.os == "Macos":
            info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist SYSTEM "file://localhost/System/Library/DTDs/PropertyList.dtd">
<plist version="0.9">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>English</string>
    <key>CFBundleExecutable</key>
    <string>Python</string>
    <key>CFBundleGetInfoString</key>
    <string>Python Runtime and Library</string>
    <key>CFBundleIdentifier</key>
    <string>org.python.python</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Python</string>
    <key>CFBundlePackageType</key>
    <string>FMWK</string>
    <key>CFBundleShortVersionString</key>
    <string>{py_version}, (c) 2001-2025 Python Software Foundation.</string>
    <key>CFBundleLongVersionString</key>
    <string>{py_version}, (c) 2001-2025 Python Software Foundation.</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleVersion</key>
    <string>{py_version}</string>
</dict>
</plist>
"""
            (new_files, new_install_name_rewrites) = self._create_framework_dir(self._deps_lib_dir, "Python", py_version_major_minor, shared_lib_src, info_plist)
            files += new_files
            install_name_rewrites += new_install_name_rewrites
        else:
            files.append(shutil.copy(shared_lib_src, os.path.join(dst_dir, os.path.basename(shared_lib_src))))


        python_lib_dir = os.path.join(self.package_folder, "lib")
        if self.settings.os == "Macos":
            python_lib_dir = os.path.join(self._deps_lib_dir, "Python.framework", "Versions", py_version_major_minor, "lib")

        if not os.path.exists(python_lib_dir):
            os.makedirs(python_lib_dir)

        embed_src_dir = os.path.join(dep_info.package_folder, "lib", py_dir_name) if self.settings.os != "Windows" else os.path.join(dep_info.package_folder, "bin", "Lib")
        embed_dst_dir = os.path.join(python_lib_dir, py_dir_name)
        dir_copied = shutil.copytree(embed_src_dir, embed_dst_dir)

        if self.settings.os == "Windows":
            files += copy(self, "*.pyd",
                os.path.join(dep_info.package_folder, "bin", "DLLs"),
                os.path.join(embed_dst_dir, "lib-dynload"))


        # Remove all existing pycache files
        rm(self, "__pycache__", dir_copied, recursive=True)

        files += self._files_in_dir(dir_copied)

        return (files, install_name_rewrites)

    def package(self):
        files = []
        install_name_rewrites = []

        if not os.path.exists(self._deps_lib_dir):
            os.makedirs(self._deps_lib_dir)


        package_base = self.package_folder
        dest_bin_dir = os.path.join(package_base, "bin")

        if self.settings.os == "Macos":
            package_base = os.path.join(package_base, "Natron.app", "Contents")
            dest_bin_dir = os.path.join(package_base, "MacOS")

        dest_plugins_dir = os.path.join(package_base, "Plugins")
        dest_resources_dir = os.path.join(package_base, "Resources")

        for x in [dest_bin_dir, dest_plugins_dir, dest_resources_dir]:
            if not os.path.exists(x):
                os.makedirs(x)

        (deps_files, deps_install_name_rewrites) = self._copy_dependencies()
        files += deps_files
        install_name_rewrites += deps_install_name_rewrites

        files += self._copy_natron_binaries(dest_bin_dir)

        files += self._copy_plugins(dest_plugins_dir)

        files += self._copy_resources(dest_resources_dir)

        files += self._copy_system_deps(self._deps_lib_dir)

        # Fix rpaths so binaries can find their dependencies.
        rel_deps_lib = os.path.relpath(self._deps_lib_dir, dest_bin_dir)
        rel_qt_lib = os.path.relpath(self._qt_lib_dir, dest_bin_dir)
        paths_for_bin = set()
        if rel_deps_lib != ".":
            paths_for_bin.add(rel_deps_lib)
        if rel_qt_lib != ".":
            paths_for_bin.add(rel_qt_lib)
        if len(paths_for_bin) == 0:
            paths_for_bin.add("")

        self._fix_rpath(os.path.relpath(dest_bin_dir, self.package_folder), list(paths_for_bin), recurse=True)

        if rel_deps_lib != ".":
            # deps_lib is not the bin directory so fix all the rpaths in that directory as well.
            self._fix_rpath(os.path.relpath(self._deps_lib_dir, self.package_folder), [""])

        if self.settings.os == "Macos":
            # Create application plist
            app_plist = f"""<?xml version=1.0 encoding=UTF-8?>
<!DOCTYPE plist PUBLIC -//Apple//DTD PLIST 1.0//EN http://www.apple.com/DTDs/PropertyList-1.0.dtd>
<plist version=1.0>
<dict>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSHighResolutionCapable</key>
    <string>True</string>
    <key>CFBundleIconFile</key>
    <string>natronIcon.icns</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{self.version}</string>
    <key>CFBundleVersion</key>
    <string>{self.version}</string>
    <key>CFBundleSignature</key>
    <string>Ntrn</string>
    <key>CFBundleName</key>
    <string>Natron</string>
    <key>CFBundleExecutable</key>
    <string>Natron</string>
    <key>CFBundleIdentifier</key>
    <string>fr.inria.Natron</string>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>ntp</string>
            </array>
            <key>CFBundleTypeMIMETypes</key>
            <array>
                <string>application/vnd.natron.project</string>
            </array>
            <key>CFBundleTypeName</key>
            <string>Natron Project File</string>
            <key>CFBundleTypeRole</key>
            <string>Editor</string>
            <key>LSIsAppleDefaultForType</key>
            <true/>
            <key>CFBundleTypeIconFile</key>
            <string>natronProjectIcon_osx.icns</string>
        </dict>
        <dict>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>nps</string>
            </array>
            <key>CFBundleTypeMIMETypes</key>
            <array>
                <string>application/vnd.natron.nodepresets</string>
            </array>
            <key>CFBundleTypeName</key>
            <string>Natron Node Presets</string>
            <key>CFBundleTypeRole</key>
            <string>Editor</string>
            <key>CFBundleTypeIconFile</key>
            <string>natronProjectIcon_osx.icns</string>
        </dict>
        <dict>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>nl</string>
            </array>
            <key>CFBundleTypeMIMETypes</key>
            <array>
                <string>application/vnd.natron.layout</string>
            </array>
            <key>CFBundleTypeName</key>
            <string>Natron Layout</string>
            <key>CFBundleTypeRole</key>
            <string>Editor</string>
            <key>CFBundleTypeIconFile</key>
            <string>natronProjectIcon_osx.icns</string>
        </dict>
    </array>
</dict>
</plist>"""

            app_plist_filename = os.path.join(package_base, "Info.plist")
            save(self, app_plist_filename, app_plist)
            files += app_plist_filename

            # Apply all install name changes.
            base_cmd = "install_name_tool"
            for (old_name, new_name) in install_name_rewrites:
                base_cmd += f" -change '{old_name}' '{new_name}'"
            for root, dirs, files in os.walk(dest_bin_dir, topdown=False):
                for x in files:
                    self.run(f"{base_cmd} {os.path.join(root, x)}")


        self.output.info(f"\n\nfiles copied:")
        for x in files:
            self.output.info(f"\t{os.path.relpath(x, self.package_folder)}")


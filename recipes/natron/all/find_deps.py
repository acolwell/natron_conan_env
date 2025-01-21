
import argparse
import io
import os.path
import re
import shutil
import subprocess
import sys
import tempfile

import json

def fix_location(platform, location_path):
    if platform == "Msys" and location_path[0] == '/':
        new_location_path = subprocess.run(
            ["cygpath", "-m", location_path],
            capture_output=True).stdout.decode("utf-8").strip()
        return new_location_path

    return location_path

def find_dump_bin():
    program_files_path = os.environ.get("ProgramFiles(x86)")
    vswhere_path = os.path.join(program_files_path, "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if not os.path.exists(vswhere_path) or not os.path.isfile(vswhere_path):
        return None

    proc = subprocess.Popen([vswhere_path], stdout=subprocess.PIPE)
    msvc_regex = re.compile("^installationPath:\s+(.+)$")
    msvs_install_path = None
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.decode("utf-8").strip()

        m = msvc_regex.match(line)
        if m:
            msvs_install_path = m.group(1)
            break

    if msvs_install_path == None:
        return None
    msvc_base_path = os.path.join(msvs_install_path, "VC", "Tools", "MSVC")

    dump_bin_path = None
    for root, dirs, files in os.walk(msvc_base_path, topdown=False):
        if "dumpbin.exe" in files and os.path.basename(root):
            host_dir = os.path.basename(os.path.dirname(root))
            target_dir = os.path.basename(root)
            if host_dir == "Hostx64" and target_dir == "x64":
                dump_bin_path = os.path.join(root,"dumpbin.exe")
                break

    return dump_bin_path

def find_dep_in_search_dirs(dep_name):
    search_dep_location = None
    for x in search_directories:
        candidate_dep_location = os.path.join(x, dep_name)
        if os.path.exists(candidate_dep_location) and os.path.isfile(candidate_dep_location):
            search_dep_location = candidate_dep_location
            break
    return search_dep_location

def is_mac_system_lib(dep_location):
    mac_system_libs = [
            "/usr/lib/libSystem.B.dylib",
            "/usr/lib/libc++.1.dylib",
            "/usr/lib/libobjc.A.dylib",
            "/usr/lib/libiconv.2.dylib",
            "/usr/lib/libresolv.9.dylib",
        ]
    return (dep_location.startswith("/System/Library/Framework") or
            dep_location in mac_system_libs)

def should_follow_dep(platform, dep_name, dep_location):
    if platform == "Windows":
        if (dep_name.startswith("api-ms-win-") or
            dep_name.startswith("ext-ms-win-") or
            dep_location.startswith("C:\\Windows\\system32")):
            return False
    elif platform == "Macos" and is_mac_system_lib(dep_location):
        return False
    elif platform == "Linux":
        linux_system_libs = [
            "/lib/x86_64-linux-gnu/libGL.so.1",
            "/lib/x86_64-linux-gnu/libGLX.so.0",
            "/lib/x86_64-linux-gnu/libGLdispatch.so.0",
            "/lib/x86_64-linux-gnu/libX11.so.6",
            "/lib/x86_64-linux-gnu/libXau.so.6",
            "/lib/x86_64-linux-gnu/libXdmcp.so.6",
            "/lib/x86_64-linux-gnu/libbsd.so.0",
            "/lib/x86_64-linux-gnu/libmd.so.0",
            "/lib/x86_64-linux-gnu/libxcb.so.1",
         ]
        if dep_location in linux_system_libs:
            return False
    return True

def is_valid_lib_path(platform, dep_location):
    if os.path.isfile(dep_location):
        return True

    # MacOS has some library paths that aren't files, but are still valid and handled
    # by the library loader.
    if platform == "Macos" and is_mac_system_lib(dep_location):
        return True

    return False

def get_deps_for_binary(platform, binary_path, search_directories):
    if platform == "Windows":
        ret = set()
        dump_bin_path = find_dump_bin()
        if dump_bin_path == None:
            raise Exception("Failed to find dumpbin")

        proc = subprocess.Popen([dump_bin_path, "/dependents", binary_path], stdout=subprocess.PIPE)
        missing_deps = {}
        windows_search_paths = os.environ.get("PATH").split(";")
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.decode("utf-8").strip()
            if re.match("^[\w_-]+.dll$", line.lower().strip()):
                dep_name = line.strip()

                windows_dep_location = None
                for base_path in windows_search_paths:
                    potential_dep_location = os.path.join(base_path, dep_name)
                    if os.path.exists(potential_dep_location) and os.path.isfile(potential_dep_location):
                        windows_dep_location = potential_dep_location
                        break

                if windows_dep_location == None:
                    missing_deps.setdefault(dep_name, set())
                else:
                    ret.add((dep_name, fix_location(platform, windows_dep_location)))

        return (ret, missing_deps)
    elif platform == "Macos":
        my_name = os.path.basename(binary_path)
        ret = set()

        loader_path = os.path.dirname(binary_path)
        rpaths = []
        cmd_re = re.compile("^cmd\s+(\S+)$")
        path_re = re.compile("^path\s+(\S+)\s+\(.+\)$")
        proc = subprocess.Popen(["otool", "-l", binary_path],stdout=subprocess.PIPE)
        path_is_rpath = False
        for line in proc.stdout:
            line = line.decode("utf-8").strip()
            m = cmd_re.match(line)
            if m:
                path_is_rpath = m.group(1) == "LC_RPATH"
            else:
                m = path_re.match(line)
                if m:
                    rpaths.append(m.group(1))

        #print("RPATHS ", rpaths)
        proc = subprocess.Popen(["otool", "-L", binary_path], stdout=subprocess.PIPE)
        missing_deps = {}

        lib_re = re.compile("^(\S+)\s+\(.+\)$")
        for line in proc.stdout:
            line = line.decode("utf-8").strip()
            m = lib_re.match(line)
            if m:
                macos_dep_location = m.group(1)
                dep_name = os.path.basename(macos_dep_location)

                if dep_name == my_name:
                    continue

                if macos_dep_location.startswith("@rpath"):
                    for rpath in rpaths:
                        if rpath.startswith("@loader_path"):
                            rpath = rpath.replace("@loader_path", loader_path)
                        alt_dep_location = macos_dep_location.replace("@rpath", rpath)

                        alt_dep_location = os.path.normpath(alt_dep_location)

                        if os.path.exists(alt_dep_location) and os.path.isfile(alt_dep_location):
                            macos_dep_location = alt_dep_location
                            break

                if macos_dep_location == None:
                    missing_deps.setdefault(dep_name, set())
                else:
                    ret.add((dep_name, fix_location(platform, macos_dep_location)))

        return (ret, missing_deps)

    my_name = os.path.basename(binary_path)
    proc = subprocess.Popen(['ldd', binary_path], stdout=subprocess.PIPE)

    ret = set()
    missing_deps = {}
    while True:
        line = proc.stdout.readline()
        if not line:
            break

        line = line.decode("utf-8").strip()

        p = re.compile("^([^ ]+) => ([^(]+)( (.*))?$")
        m = p.match(line)
        if m:
            dep_name = m.group(1)
            ldd_dep_location = m.group(2)

            # Skip self
            if dep_name == my_name:
                continue

            if ldd_dep_location == "not found":
                missing_deps.setdefault(dep_name, set())
            else:
                ret.add((dep_name, fix_location(platform, ldd_dep_location)))
        else:
            if ("linux-vdso.so.1" in line or
                "ld-linux-x86-64.so" in line or
                "statically linked" in line):
                continue
            raise Exception(f"Unexpected line in ldd output: {line}")
    return (ret, missing_deps)

def get_all_deps_for_binary(binary_key_name, json_dict):
    if  binary_key_name not in json_dict["binary_deps"]:
        return None

    ret = set()
    deps_list =  json_dict["binary_deps"][binary_key_name].copy()
    while len(deps_list) > 0:
        dep = deps_list.pop()
        if dep not in ret:
            ret.add(dep)
            deps_list += json_dict["binary_deps"][dep]
    return ret

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <target_binary> [search_directories]")
        sys.exit(1)

    parser = argparse.ArgumentParser(
                    prog='find_and_copy_deps',
                    description='Finds all the library dependencies of a executable \
                    or shared library and copies them to a specified directory.')
    parser.add_argument('--json')
    parser.add_argument('--depdirs')
    parser.add_argument('--manifest')
    parser.add_argument('--output_directory')
    parser.add_argument('target_binary')
    parser.add_argument('search_directories', nargs="*", default=[])

    cmd_line_args = parser.parse_args()

    target_binary = cmd_line_args.target_binary
    output_directory = cmd_line_args.output_directory

    search_directories = []
    if cmd_line_args.depdirs:
        if not os.path.isfile(cmd_line_args.depdirs):
            sys.stderr.write(f"{cmd_line_args.depdirs} is not a file.\n")
            sys.exit(1)

        with open(cmd_line_args.depdirs, "rb") as file:
            dep_dirs = json.load(file)
            if not isinstance(dep_dirs, list):
                sys.stderr.write(f"{cmd_line_args.depdirs} does not contain a list.\n")
                sys.exit(1)

            search_directories += dep_dirs

    search_directories += cmd_line_args.search_directories.copy()

    platform = None

    if sys.platform =="win32":
        platform = "Windows"
    elif sys.platform == "msys":
        platform = "Msys"
    elif sys.platform == "linux":
        platform = "Linux"
    elif sys.platform == "darwin":
        platform = "Macos"


    if not os.path.exists(target_binary):
        sys.stderr.write(f"{target_binary} does not exist.\n")
        sys.exit(1)

    if not os.path.isfile(target_binary):
        sys.stderr.write(f"{target_binary} is not a file.\n")
        sys.exit(1)

    if cmd_line_args.output_directory and not os.path.isdir(cmd_line_args.output_directory):
        sys.stderr.write(f"Output directory: '{cmd_line_args.output_directory}' does not exist.\n")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdirname:
        print('created temporary directory', tmpdirname)

        binary_name_to_location_map = {}
        binary_deps = {}

        ldd_filename_path = target_binary
        binary_key_name = os.path.basename(target_binary)
        if platform == "Windows" and target_binary.endswith(".ofx"):
            # Need to make a copy of the plugin and rename it to have a dll extension so ldd
            # works properly.
            new_filename = os.path.splitext(os.path.basename(target_binary))[0] + ".dll"
            ldd_filename_path = os.path.join(tmpdirname,new_filename)
            shutil.copyfile(target_binary, ldd_filename_path)

        binary_deps = {}
        deps_remaining = set()

        binary_name_to_location_map[binary_key_name] = ldd_filename_path
        deps_remaining.add(binary_key_name)

        deps_visited = set()
        missing_deps = {}
        while len(deps_remaining) > 0:
            x = deps_remaining.pop()

            if x in deps_visited:
                continue
            deps_visited.add(x)

            x_location = binary_name_to_location_map[x]

            if not should_follow_dep(platform, x, x_location):
                binary_deps[x] = []
                continue

            print(f"Finding dependencies for {x}")
            search_directories.append(os.path.dirname(x_location))
            (dep_info_list, new_missing_deps) = get_deps_for_binary(platform, x_location, search_directories)
            search_directories.pop()
            deps_for_this_library = set()
            for (dep_name, dep_location) in dep_info_list:
                deps_for_this_library.add(dep_name)

                if dep_name not in binary_name_to_location_map:
                    binary_name_to_location_map[dep_name] = dep_location
                elif not is_valid_lib_path(platform, binary_name_to_location_map[dep_name]):
                    print(f"A: {binary_name_to_location_map[dep_name]} is not a valid lib path")
                elif not is_valid_lib_path(platform, dep_location):
                    print(f"B: {dep_location} is not a file")
                elif os.path.isfile(dep_location) and not os.path.samefile(binary_name_to_location_map[dep_name], dep_location):
                    print(f"{dep_name} appears to have more than one location. \
                     {binary_name_to_location_map[dep_name]} and {dep_location}")
                    #sys.exit(1)

                if dep_name not in deps_visited:
                    deps_remaining.add(dep_name)

            for k, v in new_missing_deps.items():
                dep_set = missing_deps.setdefault(k, set())
                for dep_path in v:
                    dep_set.add(dep_path)

            sorted_deps_list = sorted(deps_for_this_library)
            #for y in deps_list:
            #    print("\t{}".format(y))

            binary_deps[x] = sorted_deps_list

        json_dict = {
            "binary_deps": binary_deps,
            "binary_locations": binary_name_to_location_map,
        }


        full_deps_list = sorted(get_all_deps_for_binary(binary_key_name, json_dict))

        for x in full_deps_list:
            src = binary_name_to_location_map[x]
            print(f"{x} : {src}")

            if cmd_line_args.output_directory:
                shutil.copy(src, cmd_line_args.output_directory)

        if len(missing_deps) > 0:
            print("Missing dependencies:")
            for k, v  in missing_deps.items():
                print(f"\t{k} : {v}")

        if cmd_line_args.json:
            with open(cmd_line_args.json, "w", encoding='UTF-8') as write_file:
                json.dump(json_dict, write_file, sort_keys=True, indent=2)


        if cmd_line_args.manifest:
            # Creates a manifest that can be used with a command like the one below to
            # specify the required DLLs.
            # mt -nologo -manifest IO.ofx.manifest -outputresource:"IO.ofx;2"
            manifest = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            manifest += '<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">\n'
            manifest += f'  <assemblyIdentity name="{ os.path.basename(target_binary)}" version="1.0.0.0" type="win32" processorArchitecture="amd64"/>\n'

            for x in full_deps_list:
                manifest += f'  <file name="{x}"></file>\n'
            manifest += '</assembly>'

            with open(cmd_line_args.manifest, "w", encoding='UTF-8') as write_file:
                write_file.write(manifest)


if __name__ == '__main__':
    main()

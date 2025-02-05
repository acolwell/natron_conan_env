import json
import os
import subprocess
import sys

def get_build_info(profile):
    build_order_cmd = f"conan graph build-order --order-by recipe -f json -pr:a {profile} --build='*' --requires 'natron_installer/conan_build' --update --lockfile-partial"
    #print(build_order_cmd)
    profile_build_order = json.loads(subprocess.check_output(build_order_cmd, stderr=subprocess.DEVNULL, shell=True))

    ret = {}
    for pass_refs in profile_build_order['order']:
        for ref_obj in pass_refs:
            ref = ref_obj['ref']
            pkg = ref[:ref.index("/")]
            build_args = ref_obj["packages"][0][0]["build_args"]
            ret[pkg] = {'ref': ref, "build_args": build_args}
    return ret

def main(argv):
    profiles = [
        'msvc_profile',
        'linux_default',
        'macos_default',
        'macos_arm_default'
    ]

    runs_on_map = {
        'msvc_profile': 'windows-latest',
        'linux_default': 'ubuntu-latest',
        'macos_default': 'macos-13',
        'macos_arm_default': 'macos-14',
    }

    if len(sys.argv) < 2:
        print(f"Usage: {os.path.basename(sys.argv[0])} <package_names ...>")
        sys.exit(-1)

    packages = sys.argv[1:]

    package_info = []
    for profile in profiles:
        build_info = get_build_info(profile)

        for pkg in packages:
            if pkg not in build_info:
                print(f"Build info for '{pkg}' not found!")
                sys.exit(1)

            build_entry = {}
            build_entry["runs_on"] = runs_on_map[profile]
            build_entry["conan_profile"] = profile
            build_entry["name"] = pkg
            build_entry["build_args"] = build_info[pkg]["build_args"]

            package_info.append(build_entry)

    print(f'package_info={json.dumps(package_info)}')

    merge_info = []
    for profile in profiles:
        merge_entry = {}
        merge_entry["conan_profile"] = profile
        merge_entry["runs_on"] = runs_on_map[profile]
        merge_info.append(merge_entry)
    print(f'merge_info={json.dumps(merge_info)}')

if __name__ == "__main__":
    main(sys.argv[:])
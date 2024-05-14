import json
import logging
import os
import re
import subprocess
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO)
"""
need to run `mvn surefire-report:report` at first
"""

format_mode = False


def test_method_name_strip(method_name: str) -> str:
    pat = r"\([\w\s,]+\)\[\d+\]$"
    # if not re.search(pat, method_name):
    #     return method_name
    new_name = re.sub(pat, "", method_name)
    return new_name


def collect_reported_methods(report_dir: str) -> list[str]:
    test_methods = set()
    for file_name in os.listdir(report_dir):
        if file_name.endswith(".xml"):
            file_path = os.path.join(report_dir, file_name)
            tree = ET.parse(file_path)
            root = tree.getroot()
            for testcase in root.iter("testcase"):
                test_class = testcase.get("classname")
                test_method = testcase.get("name")
                assert isinstance(test_method, str)
                test_method = test_method_name_strip(test_method)
                test_methods.add(f"{test_class}#{test_method}")

    return list(test_methods)


# def get_test_mothods_per_module(mod_dir: str):
#     test_report_dir = "target/surefire-reports"
#     test_report_dir = os.path.join(mod_dir, test_report_dir)
#     assert os.path.exists(test_report_dir)
#     test_methods = get_test_methods(test_report_dir)
#     return test_methods
#
#
# def convert_module_dir(mod_name: str):
#     return mod_name.replace(".", "/")


def unique_list(original_list: list) -> list:
    return list(set(original_list))


def get_all_report_dirs() -> list[str]:
    matching_dirs = []
    target_dir = "target/surefire-reports"

    for dirpath, dirnames, filenames in os.walk("."):
        if target_dir in dirpath:
            matching_dirs.append(dirpath)
    return matching_dirs


def persist(test_methods: list[str]):
    filename = "data/test_methods.json"
    dir = os.path.dirname(filename)
    if not os.path.exists(dir):
        os.mkdir(dir)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(test_methods, f, indent=4)


def get_test_methods() -> list[str]:
    if format_mode:
        filename = "data/test_methods.json"
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)

    prepare_maven()
    test_methods: list[str] = []
    for dir in get_all_report_dirs():
        test_methods.extend(collect_reported_methods(dir))
    return test_methods


def main():
    test_methods = get_test_methods()
    test_methods.sort()
    persist(test_methods)
    # print(test_methods)


def run_cmd(cmd: str):
    proc = subprocess.Popen(cmd, shell=True)
    code = proc.wait()
    assert code == 0


# TODO: run papare mvn commands
def prepare_maven():
    run_cmd("mvn surefire-report:report -Drat.skip=true")
    logging.info("run `mvn surefire-report:report` at first")


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Get test methods from surefire-reports"
    )
    parser.add_argument(
        "-f", "--format", action="store_true", help="format the existing unit tests"
    )
    args = parser.parse_args()

    global format_mode
    format_mode = args.format


if __name__ == "__main__":
    parse_args()
    main()

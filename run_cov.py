"""
run each unit test and collect its coverage information
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import colorlog

JACOCO_FILE = "target/site/jacoco/jacoco.xml"
METRIC = "INSTRUCTION"
PKG_PREFIX = "org.apache.shiro"
UT_COV_DIR = "ut_cov_data"
BASE_DIR = os.path.join(sys.path[0], "..")
DATA_DIR = "data"

debug = False
try_mode = False
multi_module_mode = False

sub_projects: list[str] = []
pom_modules: list[str] = []
test_methods: list[str] = []

# Create a logger
logger = colorlog.getLogger()
logger.setLevel(logging.INFO)

# Create a colored formatter
formatter = colorlog.ColoredFormatter(
    "%(log_color)s[%(levelname)s] %(reset)s- %(asctime)s - %(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
)

# Create a StreamHandler with the colored formatter
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)


@dataclass
class CovRes:
    missed: int
    covered: int


@dataclass
class Location:
    package: str
    classes: str
    method: str


@dataclass
class CovRecord:
    loc: Location
    cov: dict[str, CovRes]

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


def prepare_subprojects():
    cmd = 'mvn -q --also-make exec:exec -Dexec.executable="pwd" -Dmaven.clean.failOnError=false'
    filename = "data/report_dir.json"
    root = os.getcwd()
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    # strip the command output
    lines = proc.stdout.split("\n")
    pat = re.compile(r"\[ERROR\]")
    sub_projects = [line for line in lines if not pat.match(line) and len(line) > 0]
    sub_projects = [dir.replace(root, ".") for dir in sub_projects]
    sub_projects.sort()
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(sub_projects, f)


def collect_subprojects() -> list[str]:
    # get from mvn commands
    filename = os.path.join(BASE_DIR, DATA_DIR, "report_dir.json")
    if not os.path.exists(filename):
        prepare_subprojects()
    with open(filename, "r", encoding="utf-8") as f:
        sub_projects = json.load(f)
    assert isinstance(sub_projects, list)
    assert isinstance(sub_projects[0], str)
    return sub_projects


def collect_test_methods() -> list[str]:
    filename = os.path.join(BASE_DIR, DATA_DIR, "test_methods.json")
    with open(filename, "r", encoding="utf-8") as f:
        test_methods = json.load(f)
    assert isinstance(test_methods, list)
    assert isinstance(test_methods[0], str)
    return test_methods


def extract_cov_report(file_path: str) -> list[CovRecord]:
    """
    filter the non-hit method, collect hitted flatten record
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    cov_records = []
    for package in root:
        if package.tag != "package":
            continue
        for classes in package:
            if classes.tag != "class":
                continue
            for method in classes:
                if method.tag != "method":
                    continue
                loc = Location(
                    package.attrib.get("name", ""),
                    classes.attrib.get("name", ""),
                    method.attrib.get("name", ""),
                )
                # construct CovRes
                cov = {}
                for counter in method:
                    assert counter.tag == "counter"
                    metric = counter.attrib.get("type", "")
                    missed = int(counter.attrib.get("missed", "0"))
                    covered = int(counter.attrib.get("covered", "0"))
                    cov[metric] = CovRes(missed, covered)
                cov_rec = CovRecord(loc, cov)
                cov_records.append(cov_rec)
    return cov_records


def calculate_coverage(records: list[CovRecord], metric: str) -> float:
    covered = 0
    missed = 0
    # if debug:
    #     __import__("ipdb").set_trace()
    for rec in records:
        cov_res = rec.cov.get(metric)
        assert isinstance(cov_res, CovRes)
        covered += cov_res.covered
        missed += cov_res.missed
    return (covered) / (covered + missed)


def collect_modules() -> list[str]:
    global multi_module_mode
    file_path = "pom.xml"
    tree = ET.parse(file_path)
    root = tree.getroot()
    namespace = {"maven": "http://maven.apache.org/POM/4.0.0"}
    if debug:
        __import__("ipdb").set_trace()
    mods = root.find("./maven:modules", namespace)
    if mods is None:
        multi_module_mode = False
        return []
    multi_module_mode = True
    pom_modules: list[str] = []
    for mod in mods:
        # assert mod.tag == "module"
        assert mod.text is not None
        pom_modules.append(mod.text)
    return pom_modules


def get_module(full_path: str) -> str:
    global debug, pom_modules, try_mode
    if debug:
        __import__("ipdb").set_trace()
    m = re.search(r"/(\w+)/", full_path)
    assert m is not None
    module = m.group(1)
    if module in pom_modules:
        return module
    else:
        return ""


def get_err_log_name(test_method: str) -> str:
    cmd_err_dir = os.path.join(BASE_DIR, DATA_DIR, "cmd_err")
    if not os.path.exists(cmd_err_dir):
        os.makedirs(cmd_err_dir)
    return os.path.join(cmd_err_dir, test_method + ".log")


def run_ut(test_method: str, full_path: str, sub: bool) -> bool:
    global debug, try_mode
    # if debug:
    #     __import__("ipdb").set_trace()
    # note that the jacoco.skip=false was special extra options for shiro due to its customized project settings
    err_log = get_err_log_name(test_method)

    # construct cmd within different mode
    if sub:
        module = get_module(full_path)
        if len(module) == 0:
            return False
        cmd = f"mvn -pl {module} -am clean test jacoco:report -Drat.skip=true -Dsurefire.failIfNoSpecifiedTests=false -Djacoco.skip=false -Dtest={test_method}"
    else:
        cmd = f"mvn clean test jacoco:report -Drat.skip=true -Dsurefire.failIfNoSpecifiedTests=false -Djacoco.skip=false -Dtest={test_method}"

    logger.info(f"command: {cmd}")

    if debug or try_mode:
        proc = subprocess.run(cmd.split(), text=True, capture_output=True)
    else:
        proc = subprocess.run(cmd.split(), text=True, capture_output=True)
    ret = proc.returncode
    if debug:
        debug_log = os.path.join(DATA_DIR, "run_ut.log")
        with open(debug_log, "w", encoding="utf-8") as f:
            f.write(proc.stdout)
            f.write(proc.stderr)
        logger.error(f"refer to log file {debug_log}")
    if ret != 0:
        with open(err_log, "w", encoding="utf-8") as f:
            f.write(proc.stdout + proc.stderr)
        logger.error(f"maven command failed: {cmd}")
        logger.error(f"refer to log file {err_log}")
        return False
    return True


def extract_method_name(method_name: str) -> Location:
    pat = r"^([\w.]+)\.(\w+)#(\w+)$"
    m = re.fullmatch(pat, method_name)
    assert m is not None
    return Location(m.group(1), m.group(2), m.group(3))


def is_project(dir: str) -> None:
    assert os.path.exists(os.path.join(dir, JACOCO_FILE))


def package_name2dir(package: str) -> str:
    return package.replace(".", "/")


def get_full_path(loc: Location) -> str:
    package_dir = loc.package.replace(".", "/")
    filename = loc.classes + ".java"

    for dirpath, dirs, filenames in os.walk("."):
        if not dirpath.endswith(package_dir):
            continue
        if not filename in filenames:
            continue
        return os.path.join(dirpath, filename)

    assert False


def check_valid_report_dir(report_dir: str, loc: Location) -> bool:
    file_path = os.path.join(report_dir, JACOCO_FILE)
    if not os.path.exists(file_path):
        return False

    package_dir = loc.package.replace(".", "/")

    tree = ET.parse(file_path)
    root = tree.getroot()

    # if debug:
    #     __import__("ipdb").set_trace()

    flag = False
    for package in root:
        if package.tag != "package":
            continue
        if not package.attrib.get("name", "") == package_dir:
            continue
        flag = True
        if debug:
            logging.info("Find corresponding package in the jacoco report")
        break
    return flag


def search_for_report_path(loc: Location, full_path: str) -> str:
    """
    sub_project was defined by maven
    part of package name(prefix removed) does not always mapped to the sub project directory path
    solution: walk and find the full path of the test file, and then get sub project dir must be the prefix of it.
    candidates longest match
    required: contains jacoco report
    """
    global debug, sub_projects
    # if debug:
    #     __import__("ipdb").set_trace()
    report_dir = ""
    for dir in sub_projects:
        if not full_path.startswith(dir):
            continue
        if not check_valid_report_dir(dir, loc):
            continue
        if len(dir) > len(report_dir):
            report_dir = dir

    if len(report_dir) != 0:
        return os.path.join(report_dir, JACOCO_FILE)
    else:
        return ""


def get_report(test_method: str, sub: bool) -> str:
    """
    get report xml  for corresponding UT, xml file resides in the corresponding subproject dir plus fixed target sub structure
    UT(method name) -> package -> sub project,
    sub project constitutes part of sub project
    """
    global sub_projects
    loc = extract_method_name(test_method)
    full_path = get_full_path(loc)
    flag = run_ut(test_method, full_path, sub)
    if not flag:
        return ""
    report_path = search_for_report_path(loc, full_path)
    return report_path


def persist_cov_data(test_method: str, cov_records: list[CovRecord]):
    if not os.path.exists(UT_COV_DIR):
        os.mkdir(UT_COV_DIR)
    file_path = os.path.join(UT_COV_DIR, test_method + ".json")
    if debug:
        __import__("ipdb").set_trace()
    json_str = "["
    for ind, cov_rec in enumerate(cov_records):
        if ind > 0:
            json_str += ",\n"
        json_str += cov_rec.toJSON()
    json_str += "\n]"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json_str)


def run_and_collect_cov(test_method: str) -> bool:
    """
    run and then collect data(path needed)
    returns whether succeed
    """
    global sub_projects, multi_module_mode
    if multi_module_mode:
        report_path = get_report(test_method, True)
        if len(report_path) == 0:
            report_path = get_report(test_method, False)
            if len(report_path) == 0:
                return False
    else:
        report_path = get_report(test_method, False)
        if len(report_path) == 0:
            return False

    cov_records = extract_cov_report(report_path)
    logger.info(f"cov_record sample: {cov_records[0]}")
    rate = calculate_coverage(cov_records, METRIC)
    logger.info(f"{METRIC} coverage rate: {rate:.2f}")
    persist_cov_data(test_method, cov_records)
    return True


def prepare_dir(dir: str):
    if not os.path.exists(dir):
        os.mkdir(dir)


def prepare_dirs():
    prepare_dir(os.path.join(BASE_DIR, DATA_DIR))


def main():
    global debug, try_mode, sub_projects, test_methods, pom_modules
    prepare_dirs()
    test_methods = collect_test_methods()
    sub_projects = collect_subprojects()
    pom_modules = collect_modules()

    if debug:
        __import__("ipdb").set_trace()

    if try_mode:
        test_method = (
            "org.apache.shiro.web.env.EnvironmentLoaderServiceTest#singleServiceTest"
        )
        flag = run_and_collect_cov(
            test_method,
        )
        if not flag:
            logging.error("failed to collect testing UT")
        else:
            logging.info("test running succeeded")
    else:
        succ = 0
        for ind, test_method in enumerate(test_methods):
            logger.info(f"running testmethod {ind+1}: {test_method}")
            flag = run_and_collect_cov(
                test_method,
            )
            if not flag:
                logger.warning(f"running {ind+1} failed")
            else:
                succ += 1
                logger.info(f"running {ind + 1} succeeded, succeeded: {succ}/{ind+1}")
            print()
            if debug:
                break
        logger.info(f"success totally: {succ}/{len(test_methods)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="run maven UT-coverage command and collect coverage informartion each"
    )
    parser.add_argument("-d", "--debug", help="debug mode", action="store_true")
    parser.add_argument(
        "-t", "--try", help="try sample execution", action="store_true", dest="try_mode"
    )
    args = parser.parse_args()

    debug = args.debug
    try_mode = args.try_mode
    main()

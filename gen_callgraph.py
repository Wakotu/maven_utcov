# substitute the gen_callgraph bash script
import os
import subprocess
import xml.etree.ElementTree as ET

from config import BASE_DIR, CALL_LOG, LOG_DIR, TARGET_DIR
from utils import prepare_dir


def run_single_cmd(cmd: str) -> bool:
    return subprocess.run(cmd, shell=True).returncode == 0


def collect_compiled_jars() -> list[str]:
    res = []
    pat = "-tests.jar"
    for root, dirs, files in os.walk("."):
        if os.path.basename(root) == "target":
            for file in files:
                if file.endswith(pat):
                    # add in pair
                    res.append(os.path.join(root, file))
                    source_jar_name = file.replace(pat, ".jar")
                    source_jar_path = os.path.join(root, source_jar_name)
                    if os.path.exists(source_jar_path):
                        res.append(source_jar_path)
    return res


def single_generation(jar_name: str) -> str | None:
    dest_log = jar_name + ".log"
    flag = run_single_cmd(
        f"java -jar scripts/utils/javacg-0.1-SNAPSHOT-static.jar {jar_name} >{dest_log}"
    )
    if flag:
        return dest_log
    else:  # if failed, return None
        return None


def concatenate(log_list: list[str]):
    log_list_str = " ".join(log_list)
    run_single_cmd(f"cat {log_list_str} >{CALL_LOG}")


def run_generation() -> bool:
    compiled_jars = collect_compiled_jars()
    if len(compiled_jars) == 0:
        run_single_cmd("mvn package -Drat.skip=true -Dmaven.test.failure.ignore=true")
        compiled_jars = collect_compiled_jars()

    log_list = []
    for jar in compiled_jars:
        dest_log = single_generation(jar)
        if dest_log is None:
            continue
        log_list.append(dest_log)

    if len(log_list) == 0:
        return False
    concatenate(log_list)
    return True


def find_project_property_element(
    root: ET.Element, tag_name: str, namespace: str
) -> ET.Element:
    res = root.find(f"{namespace}{tag_name}")
    if res is not None:
        return res
    parent = root.find(f"{namespace}parent")
    assert parent is not None, "failed to find parent Element in pom.xml"
    res = parent.find(f"{namespace}{tag_name}")
    assert res is not None, f"failed to find Element {tag_name} in pom.xml"
    return res


def extract_artifact_id() -> str:
    pom_path = os.path.join("pom.xml")
    assert os.path.exists(pom_path), f"not a maven project"
    tree = ET.parse(pom_path)
    root = tree.getroot()

    # Define the namespace
    namespace = "{http://maven.apache.org/POM/4.0.0}"

    artifact_id = find_project_property_element(root, "artifactId", namespace).text
    # group_id = find_project_property_element(root, "groupId", namespace).text
    version = find_project_property_element(root, "version", namespace).text
    return f"{artifact_id}-{version}"


def prepare_dirs():
    prepare_dir(LOG_DIR)
    prepare_dir(TARGET_DIR)


def main() -> bool:
    prepare_dirs()
    return run_generation()


if __name__ == "__main__":
    main()

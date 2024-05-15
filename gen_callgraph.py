# substitute the gen_callgraph bash script
import os
import subprocess
import xml.etree.ElementTree as ET


def run_single_cmd(cmd: str):
    assert (
        subprocess.run(cmd, shell=True).returncode == 0
    ), f"faile to run command: {cmd}"


def run_script(artifact_id: str):
    __import__("ipdb").set_trace()
    test_jar_name = f"target/{artifact_id}-tests.jar"
    jar_name = f"target/{artifact_id}.jar"
    if not os.path.exists(test_jar_name) or not os.path.exists(jar_name):
        run_single_cmd("mvn package -Drat.skip=true")
    run_single_cmd(
        f"java -jar scripts/utils/javacg-0.1-SNAPSHOT-static.jar {test_jar_name} >logs/test_call.log"
    )
    run_single_cmd(
        f"java -jar scripts/utils/javacg-0.1-SNAPSHOT-static.jar {jar_name} >logs/source_call.log"
    )
    run_single_cmd(
        "cat logs/test_call.log logs/source_call.log >logs/test_source_call.log"
    )


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

    tree = ET.parse("pom.xml")
    root = tree.getroot()

    # Define the namespace
    namespace = "{http://maven.apache.org/POM/4.0.0}"

    artifact_id = find_project_property_element(root, "artifactId", namespace).text
    # group_id = find_project_property_element(root, "groupId", namespace).text
    version = find_project_property_element(root, "version", namespace).text
    return f"{artifact_id}-{version}"


if __name__ == "__main__":
    artifact_id = extract_artifact_id()
    run_script(artifact_id)

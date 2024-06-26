# test call extraction
import argparse
import json
import os
import pickle
import re
from dataclasses import dataclass

from config import BASE_DIR, CALL_ENTRY_JSON, CALL_ENTRY_PICKLE, CALL_LOG, LOG_DIR

# TODO: automatically extract package project_prefix

package_project_prefix = ""


@dataclass
class Method:
    class_name: str
    func_name: str
    arg_types: list[str]

    def __str__(self) -> str:
        return f"{self.class_name}:{self.func_name}({','.join(self.arg_types)})"

    def __repr__(self) -> str:
        return f"{self.func_name}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Record:
    caller: Method
    callee: Method
    call_type: str


@dataclass
class CallEnry:
    callee: Method
    level: int


test_method_call_mapping: dict[Method, list[Method]] = {}

method_pat = re.compile(r"([\w[\]$.]+):([\w<>$]+)\(([\w.[\]$,]*)\)")

debug_mode = False
try_mode = False


def extract_method(sub_record: str) -> tuple[Method, int]:
    m = method_pat.match(sub_record)
    assert m is not None, f"failed to extract string {sub_record}"
    class_name = m.group(1)
    func_name = m.group(2)
    arg_types = m.group(3).split(",")
    return Method(class_name, func_name, arg_types), m.end()


def extract_method_record(record: str) -> Record | None:
    if not record.startswith("M:"):
        return None
    caller, length = extract_method(record[2:])
    call_type = record[2 + length + 2]
    callee, _ = extract_method(record[2 + length + 4 :])
    return Record(caller, callee, call_type)


def collect_unit_test_method(
    test_method_call_mapping: dict[Method, list[Method]]
) -> list[Method]:
    log_name = "unit_tests.json"
    log_file = os.path.join(LOG_DIR, log_name)
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            methods = json.load(f)
            assert isinstance(methods, list)
            assert isinstance(methods[0], str)
            return [extract_method(m)[0] for m in methods]

    unit_test_methods = []
    for method in test_method_call_mapping.keys():
        if method.class_name.endswith("Test") and method.func_name.startswith("test"):
            unit_test_methods.append(method)
    # persist
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump([str(m) for m in unit_test_methods], f, indent=4)
    return unit_test_methods


def construct_method_call_mapping(call_log: str) -> dict[Method, list[Method]]:
    """
    method call mapping: a method -> all the methods it calls
    test and normal call construction shares the same logic, difference lies in:
    - call log file
    - result name(no need to worry about in local scope)
    """
    method_call_mapping = {}
    with open(call_log, "r", encoding="utf-8") as f:
        for line in f:
            record = extract_method_record(line)
            if record is None:
                continue
            if record.caller not in method_call_mapping:
                method_call_mapping[record.caller] = set()

            method_call_mapping[record.caller].add(record.callee)
    for key, val in method_call_mapping.items():
        method_call_mapping[key] = list(val)
    return method_call_mapping


def traverse_ut_call_tree(
    root: Method,
    test_method_call_mapping: dict[Method, list[Method]],
    depth: int,
    entries: list[CallEnry],
):
    if root not in test_method_call_mapping:
        return
    for callee in test_method_call_mapping[root]:

        # judge if callee in entreis
        flag = False
        for entry in entries:
            if callee == entry.callee:
                flag = True
                break
        if flag:
            continue
        if not callee.class_name.startswith(package_project_prefix):
            continue
        entries.append(CallEnry(callee, depth))
        traverse_ut_call_tree(callee, test_method_call_mapping, depth + 1, entries)


def construct_ut_call_tree(
    ut: Method,
    method_call_mapping: dict[Method, list[Method]],
    call_entries: dict[Method, list[CallEnry]],
):
    call_entries[ut] = []
    traverse_ut_call_tree(ut, method_call_mapping, 1, call_entries[ut])


def call_entries_pretty_persist(call_entries: dict[Method, list[CallEnry]]):
    json_obj = {}
    filename = CALL_ENTRY_JSON
    for key, val in call_entries.items():
        json_obj[str(key)] = [
            {"callee": str(entry.callee), "level": entry.level} for entry in val
        ]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(json_obj, f, indent=4)


def construct_call_entry_mapping(
    method_call_mapping: dict[Method, list[Method]], unit_test_methods: list[Method]
) -> dict[Method, list[CallEnry]]:
    log_name = CALL_ENTRY_PICKLE
    log_file = os.path.join(LOG_DIR, log_name)
    if os.path.exists(log_file):
        with open(log_file, "rb") as f:
            return pickle.load(f)

    call_entries = {}
    for ut in unit_test_methods:
        construct_ut_call_tree(ut, method_call_mapping, call_entries)
    with open(log_file, "wb") as f:
        pickle.dump(call_entries, f)

    call_entries_pretty_persist(call_entries)
    return call_entries


def longest_common_prefix(strs: list[str]):
    """
    Find the longest common prefix string amongst an array of strings.

    Parameters:
    strs (list of str): The list of strings.

    Returns:
    str: The longest common prefix.
    """
    if not strs:
        return ""

    # Start with the first string in the list as the prefix
    prefix = strs[0]

    for string in strs[1:]:
        # Compare the prefix with each string and update the prefix
        while string[: len(prefix)] != prefix and prefix != "":
            prefix = prefix[: len(prefix) - 1]

    return prefix


def extract_project_prefix(uts: list[Method]) -> str:
    """
    get the longest common prefix
    """
    return longest_common_prefix([ut.class_name for ut in uts])


def get_call_chains():
    method_call_mapping = construct_method_call_mapping(CALL_LOG)
    unit_tests = collect_unit_test_method(method_call_mapping)
    global package_project_prefix
    package_project_prefix = extract_project_prefix(unit_tests)
    call_entries = construct_call_entry_mapping(method_call_mapping, unit_tests)


def parse_args():
    global debug_mode, try_mode
    parser = argparse.ArgumentParser(description="Extract call graph from log")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "-t", "--try", action="store_true", help="try demo", dest="try_mode"
    )
    args = parser.parse_args()
    debug_mode = args.debug
    try_mode = args.try_mode


def main():
    get_call_chains()


if __name__ == "__main__":
    main()

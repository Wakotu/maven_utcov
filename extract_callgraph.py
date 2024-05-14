# test call extraction
import argparse
import json
import os
import pickle
import re
import sys
from dataclasses import dataclass


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


BASE_DIR = os.path.join(sys.path[0], "..")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CALL_LOG = os.path.join(LOG_DIR, "test_source_call.log")

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
                method_call_mapping[record.caller] = []
            method_call_mapping[record.caller].append(record.callee)

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
        entries.append(CallEnry(callee, depth))
        traverse_ut_call_tree(callee, test_method_call_mapping, depth + 1, entries)


def construct_ut_call_tree(
    ut: Method,
    tm_call_mapping: dict[Method, list[Method]],
    call_entries: dict[Method, list[CallEnry]],
):
    call_entries[ut] = []
    traverse_ut_call_tree(ut, tm_call_mapping, 1, call_entries[ut])


def call_entries_pretty_persist(call_entries: dict[Method, list[CallEnry]]):
    json_obj = {}
    filename = os.path.join(LOG_DIR, "call_entries.json")
    for key, val in call_entries.items():
        json_obj[str(key)] = [
            {"callee": str(entry.callee), "level": entry.level} for entry in val
        ]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(json_obj, f, indent=4)


def construct_call_entry_mapping(
    tm_call_mapping: dict[Method, list[Method]], unit_test_methods: list[Method]
) -> dict[Method, list[CallEnry]]:
    log_name = "call_entries.pickle"
    log_file = os.path.join(LOG_DIR, log_name)
    if os.path.exists(log_file):
        with open(log_file, "rb") as f:
            return pickle.load(f)

    call_entries = {}
    for ut in unit_test_methods:
        construct_ut_call_tree(ut, tm_call_mapping, call_entries)
    with open(log_file, "wb") as f:
        pickle.dump(call_entries, f)

    call_entries_pretty_persist(call_entries)
    return call_entries


def get_call_chains():
    tm_call_mapping = construct_method_call_mapping(CALL_LOG)
    unit_tests = collect_unit_test_method(tm_call_mapping)
    call_entries = construct_call_entry_mapping(tm_call_mapping, unit_tests)


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


if __name__ == "__main__":
    parse_args()
    get_call_chains()

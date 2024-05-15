import os
import sys

# PROJECT_PREFIX = "org.apache.commons.lang3"
BASE_DIR = os.path.join(sys.path[0], "..")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CALL_LOG = os.path.join(LOG_DIR, "test_source_call.log")
CALL_ENTRY_PICKLE = os.path.join(LOG_DIR, "call_entries.pickle")
CALL_ENTRY_JSON = os.path.join(LOG_DIR, "call_entries.json")

TARGET_DIR = os.path.join(BASE_DIR, "target")

DATA_DIR = os.path.join(BASE_DIR, "data")
TEST_METHODS_FILE = os.path.join(DATA_DIR, "test_methods.json")

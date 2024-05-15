import os
import sys

PROJECT_PREFIX = "org.apache.commons.lang3"
BASE_DIR = os.path.join(sys.path[0], "..")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CALL_LOG = os.path.join(LOG_DIR, "test_source_call.log")
TARGET_DIR = os.path.join(BASE_DIR, "target")

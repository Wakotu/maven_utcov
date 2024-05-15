import json
import os
import re
import subprocess

cmd = 'mvn -q --also-make exec:exec -Dexec.executable="pwd" -Dmaven.clean.failOnError=false'
filename = "data/report_dir.json"
root = os.getcwd()
proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
# strip the command output
lines = proc.stdout.split("\n")
pat = re.compile(r"\[ERROR\]")
sub_projects = [line for line in lines if not pat.match(line) and len(line) > 0]
sub_projects = [dir.replace(root, ".") for dir in sub_projects if len(dir) > len(root)]
sub_projects.sort()
with open(filename, "w", encoding="utf-8") as f:
    json.dump(sub_projects, f, indent=4)

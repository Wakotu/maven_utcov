#!/usr/bin/env bash

mvn package -Drat.skip=true

java -jar utils/javacg-0.1-SNAPSHOT-static.jar target/commons-lang3-3.15.0-SNAPSHOT-tests.jar >logs/test_call.log
java -jar utils/javacg-0.1-SNAPSHOT-static.jar target/commons-lang3-3.15.0-SNAPSHOT.jar >logs/source_call.log

cat logs/test_call.log logs/source_call.log >logs/test_source_call.log

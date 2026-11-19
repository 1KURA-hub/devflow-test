#!/bin/bash
# 用法: run.sh <scenario> <threads> <duration_s> <tag>
set -e
export JAVA_HOME="$HOME/tools/jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$HOME/tools/apache-jmeter-5.6.3/bin:$PATH"
SC=$1; TH=$2; DUR=$3; TAG=$4
mkdir -p /tmp/perf/results
python3 /tmp/perf/gen_jmx.py "$SC" "$TH" "$DUR" > "/tmp/perf/${SC}_${TAG}.jmx"
rm -f "/tmp/perf/results/${SC}_${TAG}.jtl"
jmeter -n -t "/tmp/perf/${SC}_${TAG}.jmx" \
       -l "/tmp/perf/results/${SC}_${TAG}.jtl" \
       -j "/tmp/perf/results/${SC}_${TAG}.log" > /dev/null 2>&1
python3 /tmp/perf/stats.py "/tmp/perf/results/${SC}_${TAG}.jtl" | sed "s/^/${SC} ${TH}线程 | /"

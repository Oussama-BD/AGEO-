#!/bin/bash
set -eu
export HADOOP_CONF_DIR=/config
if [ "$1" = namenode ]; then
  mkdir -p /data/name
  if [ ! -f /data/name/current/VERSION ]; then hdfs namenode -format -nonInteractive; fi
  exec hdfs namenode
fi
mkdir -p /data/data
exec hdfs datanode

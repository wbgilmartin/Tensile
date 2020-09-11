#!/bin/bash


SCRIPT_DIR=`pwd`
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

if [ "$#" -ge 6 ]
then
    SOLUTION_TAG=$1
    TENSILE_ROOT=$2
    CONFIG_YAML=$3
    SOURCE_DIR=$4
    RESULTS_DIR=$5
    SIZES_FILE=$6
else
    echo "need more vars"
fi;

GENERATE_BENCHMARKS=$TENSILE_ROOT/Tensile/bin/GenerateBenchmarks
WORKING_DIR=$ROOT_DIR/$SOLUTION_TAG

if [ "$#" -ge 7 ]
then
    CLIENT_ROOT=$7
else
    CLIENT_ROOT=$WORKING_DIR/client
fi;

mkdir -p $RESULTS_DIR
mkdir -p $CLIENT_ROOT

$GENERATE_BENCHMARKS $WORKING_DIR $CONFIG_YAML $SOURCE_DIR $RESULTS_DIR $SIZES_FILE $CLIENT_ROOT


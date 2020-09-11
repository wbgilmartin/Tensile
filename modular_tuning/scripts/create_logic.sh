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
    LOGIC_DIR=$6
else
    echo "need more vars"
fi;

GENERATE_LOGIC=$TENSILE_ROOT/Tensile/bin/GenerateLogic
WORKING_DIR=$ROOT_DIR/$SOLUTION_TAG

mkdir -p $LOGIC_DIR

$GENERATE_LOGIC $WORKING_DIR $CONFIG_YAML $SOURCE_DIR $RESULTS_DIR $LOGIC_DIR




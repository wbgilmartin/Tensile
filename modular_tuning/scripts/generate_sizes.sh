#!/bin/bash


if [ "$#" -ge 2 ]
then
    EXACT_FILE=$1
    TEST_FILE=$2
else
    echo "need more vars"
fi;


EXACT_ROOT=$(dirname "$EXACT_FILE")
TEST_ROOT=$(dirname "$TEST_FILE")

mkdir -p $EXACT_ROOT
mkdir -p $TEST_ROOT


GENERATE_SCRIPT=size_factory.py

python3 $GENERATE_SCRIPT $EXACT_FILE $TEST_FILE


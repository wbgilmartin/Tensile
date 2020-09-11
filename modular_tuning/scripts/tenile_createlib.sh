#!/bin/bash


SCRIPT_DIR=`pwd`
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

if [ "$#" -ge 3 ]
then
    TENSILE_ROOT=$1
    LOGIC_PATH=$2
    BUILD_PATH=$3
else
    echo "need more vars"
fi;


TENSILE_CREATE_LIB=$TENSILE_ROOT/Tensile/bin/TensileCreateLibrary

mkdir -p $BUILD_PATH

$TENSILE_CREATE_LIB --merge-files --no-legacy-components --no-short-file-names --no-library-print-debug --new-client-only --architecture=all --code-object-version=V3 --cxx-compiler=hipcc --library-format=yaml $LOGIC_PATH $BUILD_PATH HIP



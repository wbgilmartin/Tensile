#!/bin/bash

ROCBLAS_BENCH=/home/billg/amd/wbgilmartin/tasks/tile_aware_metric/rocblas/rocBLAS-for-tile-aware-metric_10-merge-parts/build/debug/clients/staging/rocblas-bench

#LIBPATH=/home/billg/amd/wbgilmartin/tasks/tile_aware_metric/tensile/tensile_tam_parts_11/t0/lib/library
#TESTPATH=/home/billg/amd/wbgilmartin/tasks/tile_aware_metric/tensile/tensile_tam_parts_11/t0/test

if [ "$#" -ge 3 ]
then
    LIB_PATH=$1
    TEST_PATH=$2
    TEST_YAML=$3
else
    echo "need more vars"
fi;



mkdir -p $TEST_PATH/new
mkdir -p $TEST_PATH/old

BENCH_NAME=bench.out

NEW_FILE=$TEST_PATH/new/$BENCH_NAME
OLD_FILE=$TEST_PATH/old/$BENCH_NAME

$ROCBLAS_BENCH --yaml $TEST_YAML > $OLD_FILE
ROCBLAS_TENSILE_LIBPATH=$LIB_PATH  $ROCBLAS_BENCH --yaml $TEST_YAML > $NEW_FILE

sed -i -e 's/4transA/transA/g' $NEW_FILE
sed -i -e 's/4transA/transA/g' $OLD_FILE



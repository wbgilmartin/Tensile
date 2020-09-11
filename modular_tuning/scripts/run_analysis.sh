#!/bin/bash



if [ "$#" -ge 4 ]
then
    WORKING_PATH=$1
    WORK_ROOT=$2
    TEST_ROOT=$3
    ANALYZE_ROOT=$4
else
    echo "need more vars"
fi;


RESULTS_PATH_NAME=results
#WORKING_PATH=/home/billg/amd/wbgilmartin/tasks/tile_aware_metric/tensile/tensile_tam_parts_11
RESULTS_ROOT=$TEST_ROOT
OLDROOT=${RESULTS_ROOT}/old
NEWROOT=${RESULTS_ROOT}/new
OLDPATH=${OLDROOT}
NEWPATH=${NEWROOT}

RESULTS_LOCAL=$WORK_ROOT/testing_results
RESULTS_REFERENCE=${RESULTS_LOCAL}/OLD
RESULTS_NEW=${RESULTS_LOCAL}/NEW

mkdir -p ${RESULTS_REFERENCE}
mkdir -p ${RESULTS_NEW}

cp -r ${OLDPATH}/* ${RESULTS_REFERENCE}
cp -r ${NEWPATH}/* ${RESULTS_NEW}

#ANALYZE_ROOT=$WORKING_PATH/analysis
ANALYZE_RESULTS_PATH=${ANALYZE_ROOT}

#mkdir ${ANALYZE_ROOT}
mkdir -p ${ANALYZE_RESULTS_PATH}


ANALYSIS_SCRIPT=$WORKING_PATH/tuning/scripts/analyze-results.sh
$ANALYSIS_SCRIPT  -o ${ANALYZE_RESULTS_PATH} -s 2 -f 1372 -r ${RESULTS_REFERENCE}  -b ${RESULTS_NEW} 


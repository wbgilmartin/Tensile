
import os
import sys
import argparse
import shutil
import subprocess
from copy import deepcopy, copy

from . import ClientExecutable
from . import TensileCreateClientLibrary
from . import Common
from . import BenchmarkProblems
from . import ClientWriter
from . import LibraryLogic
from . import YAMLIO
from . import SolutionLibrary
from . import Utils

from .BenchmarkStructs import BenchmarkProcess
from .ClientWriter import runClient, writeClientParameters, writeClientConfig
from .Common import ClientExecutionLock, assignGlobalParameters, globalParameters, defaultSolution, defaultBenchmarkCommonParameters, \
  HR, pushWorkingPath, popWorkingPath, print1, print2, printExit, printWarning, ensurePath, startTime, ProgressBar, hasParam
from .KernelWriterAssembly import KernelWriterAssembly
from .KernelWriterSource import KernelWriterSource
from .SolutionStructs import Solution, ProblemType, ProblemSizes
from .SolutionWriter import SolutionWriter
from .TensileCreateLibrary import writeSolutionsAndKernels, writeCMake
from .SolutionLibrary import MasterSolutionLibrary
from .Contractions import ProblemType as ContractionsProblemType
from .TensileCreateClientLibrary import assigenParameters, generateSolutions, WriteClientLibraryFromSolutions, \
    CreateBenchmarkClientPrametersForSizes, runNewClient




def GenerateSolutions(userArgs):
    
    assignGlobalParameters({"PrintWinnersOnly": 1})

    problemTypeConfig = {"Batched": True, "DataType": "s", "OperationType": "GEMM", "TransposeA": False, "TransposeB": False,
    "UseBeta": True}

    #problemType = ProblemType(problemTypeConfig)
    #print (problemType)

    #BenchmarkCommonParameters:
    benchmarkCommonParameters = [{"LoopTail": [True]}, {"KernelLanguage": ["Assembly"]}, \
        {"EdgeType": ["ShiftPtr"]}, {"GlobalSplitU": [1] } ]

    #ForkParameters:
    forkParameters = [ \
    {"PrefetchGlobalRead": [False, True]}, \
    {"WorkGroupMapping": [1, 8]}, \
    {"DepthU": [8, 16, 32]}, \
    {"LdsPadA": [0, -1]}, \
    {"PrefetchLocalRead": [False, True]}, \
    {"LdsPadB": [0, -1]}, \
    {"VectorWidth": [-1]}, \
    {"GlobalReadVectorWidth": [-1, 1]}, \
    {"FractionalLoad": [1]}]
    #, \
    #{"ThreadTile": [[4, 4], [8, 8]]}, \
    #{"WorkGroup": [[16, 16, 1]]}
    #]


    #ttSides = [1,2,3,4,5,6]
    #ttSides = [4,8]
    ttSides = [8]
    tt = []
    for i in ttSides:
      for j in ttSides:
        tt.append([i, j])

    #wgSides = [8,16]
    #wg = []
    #for i in wgSides:
    #  for j in wgSides:
    #      wg.append([i,j,1])
    wg = [[16,16,1]]
    forkParameters.append({"ThreadTile": tt})
    forkParameters.append({"WorkGroup": wg})
    #validWorkGroups = []
    #for numThreads in range(64, 1025, 64):
    #  for nsg in [ 1, 2, 4, 8, 16, 32, 64, 96, 128, 256 ]:
    #    for sg0 in range(1, numThreads//nsg+1):
    #      sg1 = numThreads//nsg//sg0
    #      if sg0*sg1*nsg == numThreads:
    #          workGroup = [sg0, sg1, nsg]
    #          validWorkGroups.append(workGroup)


    #validThreadTileSides = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16] + list(range(20, 256, 4))
    #validThreadTiles = []
    #for i in validThreadTileSides:
    #  for j in validThreadTileSides:
    #    validThreadTiles.append([i, j])

    globalSourcePath = "/home/billg/amd/wbgilmartin/tasks/tensile_library_step/Tensile-library_step/Tensile/Source"
    effectiveWorkingPath = "/home/billg/amd/wbgilmartin/tasks/tensile_library_step/tensile_tuning_4/tune0/testLibrary"
    ensurePath(effectiveWorkingPath)

    sourcePath = ensurePath(os.path.join(effectiveWorkingPath, "source"))
    solutionsPath = ensurePath(os.path.join(effectiveWorkingPath, "solutions"))
    libraryPath = ensurePath(os.path.join(sourcePath, "library"))
    dataPath = ensurePath(os.path.join(effectiveWorkingPath, "data"))
    configFilePath = ensurePath(os.path.join(effectiveWorkingPath, "configs"))
    scriptPath = ensurePath(os.path.join(effectiveWorkingPath, "script"))
    clientBuildDir = ensurePath(os.path.join(effectiveWorkingPath, "client"))
    resultsPath = ensurePath(os.path.join(effectiveWorkingPath, "results"))

    dataFilePath = os.path.join(dataPath, "benchmark.csv")
    configFile = os.path.join(configFilePath, "ClientParameters.ini")
    solutionsFilePath = os.path.join(solutionsPath, "solutions.yaml")

    ClientExecutable.getClientExecutable(clientBuildDir)

    problemSizeGroupConfigs = [{"BenchmarkCommonParameters": benchmarkCommonParameters, "ForkParameters": forkParameters}]
    hardcodedParametersSets, initialSolutionParameters = assigenParameters(problemTypeConfig, problemSizeGroupConfigs)

    solutionsList = generateSolutions (problemTypeConfig, hardcodedParametersSets, initialSolutionParameters)

    WriteClientLibraryFromSolutions(solutionsList, globalSourcePath, sourcePath)

    problemTypeDict = solutionsList[0]["ProblemType"].state

    sizes = [
        {"Exact": [784, 512, 1, 128]}, \
        {"Exact": [784, 128, 1, 512]}, \
        {"Exact": [196, 1024, 64, 256]}, \
        {"Exact": [196, 256, 64, 1024]}
    ]

    problemSizes = ProblemSizes(problemTypeDict, sizes)
    YAMLIO.writeSolutions(solutionsFilePath, problemSizes, [solutionsList])

    CreateBenchmarkClientPrametersForSizes(libraryPath, problemSizes, dataFilePath, configFile)

    returncode = runNewClient(scriptPath, configFile, clientBuildDir)
    print2(returncode)

    problemTypeObj = ProblemType(problemTypeConfig)
    problemTypeName = str(problemTypeObj)

    resultsDataFile = os.path.join(resultsPath, problemTypeName + ".csv")
    resultsSolutionsFile = os.path.join(resultsPath, problemTypeName + ".yaml")

    shutil.copyfile(dataFilePath, resultsDataFile)
    shutil.copyfile(solutionsFilePath, resultsSolutionsFile)

    globalParameters["BenchmarkDataPath"] = "results"
    globalParameters["LibraryLogicPath"] = "logic"
    globalParameters["WorkingPath"] = effectiveWorkingPath

    libraryLogic = { \
        "ArchitectureName": "gfx906", \
        "DeviceNames": ["Device 66a0", "Device 66a1", "Device 66a7", "Vega 20"], \
        "ScheduleName": "vega20" \
    }

    LibraryLogic.main(libraryLogic)

    print ("done")
    #print (returncode)
    
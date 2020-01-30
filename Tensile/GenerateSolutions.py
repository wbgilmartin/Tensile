
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

    problemSizeGroupConfigs = [{"BenchmarkCommonParameters": benchmarkCommonParameters, "ForkParameters": forkParameters}]
    #hardcodedParametersSets, initialSolutionParameters = assigenParameters(problemTypeConfig, problemSizeGroupConfigs)

    #print (hardcodedParametersSets)
    #print (initialSolutionParameters)
    #solutionsList = generateSolutions (problemTypeConfig, hardcodedParametersSets, initialSolutionParameters)

    #solutionsList = generateSolutions (problemTypeConfig, hardcodedParametersSets, initialSolutionParameters)

    effectiveWorkingPath = "/home/billg/amd/wbgilmartin/tasks/tensile_library_step/tensile_tuning_3/tune0/testLibrary"

    sourcePath = os.path.join(effectiveWorkingPath, "source")
    #ensurePath(sourcePath)
    globalSourcePath = "/home/billg/amd/wbgilmartin/tasks/tensile_library_step/Tensile-leadsize2/Tensile/Source"
    #WriteClientLibraryFromSolutions(solutionsList, globalSourcePath, sourcePath)

    solutionsPath = ensurePath(os.path.join(effectiveWorkingPath, "solutions"))
    solutionsFilePath = os.path.join(solutionsPath, "solutions.yaml")

    #problemTypeObject = ProblemType(problemTypeConfig)
    #problemSizes = ProblemSizes(problemTypeObject, None)
    #YAMLIO.writeSolutions(solutionsFilePath, problemSizes, [solutionsList])

    #print (solutionsList)

    #problemTypeDict = metaData["ProblemType"]
    #problemTypeDict = solutionsList[0]["ProblemType"].state
    #problemType = ContractionsProblemType.FromOriginalState(problemTypeDict)

    #sizeFile = YAMLIO.readConfig(sizeFilePath)
    #problemSizes = ProblemSizes(problemTypeDict, sizeFile)
    sizes = [
        {"Exact": [784, 512, 1, 128]}, \
        {"Exact": [784, 128, 1, 512]}, \
        {"Exact": [196, 1024, 64, 256]}, \
        {"Exact": [196, 256, 64, 1024]}
    ]

    #problemSizes = ProblemSizes(problemTypeDict, sizes)
    #YAMLIO.writeSolutions(solutionsFilePath, problemSizes, [solutionsList])
    #print (problemType)
    #print (problemSizes)
    libraryPath = ensurePath(os.path.join(sourcePath, "library"))
    dataPath = ensurePath(os.path.join(effectiveWorkingPath, "data"))
    dataFilePath = os.path.join(dataPath, "benchmark.csv")
    configFilePath = ensurePath(os.path.join(effectiveWorkingPath, "configs"))
    configFile = os.path.join(configFilePath, "ClientParameters.ini")
    #CreateBenchmarkClientPrametersForSizes(libraryPath, problemSizes, dataFilePath, configFile)

    clientBuildDir = ensurePath(os.path.join(effectiveWorkingPath, "client"))
    #ClientExecutable.getClientExecutable(clientBuildDir)

    scriptPath = os.path.join(effectiveWorkingPath, "script")
    ensurePath(scriptPath)
    #returncode = runNewClient(scriptPath, configFile, clientBuildDir)

    problemTypeObj = ProblemType(problemTypeConfig)
    problemTypeName = str(problemTypeObj)

    resultsPath = os.path.join(effectiveWorkingPath, "results")
    ensurePath(resultsPath)
    resultsDataFile = os.path.join(resultsPath, problemTypeName + ".csv")
    resultsSolutionsFile = os.path.join(resultsPath, problemTypeName + ".yaml")

    #shutil.copyfile(dataFilePath, resultsDataFile)
    #shutil.copyfile(solutionsFilePath, resultsSolutionsFile)
   
    #os.path.join(globalParameters["WorkingPath"], \
    #globalParameters["LibraryLogicPath"])
    libraryLogicPath = os.path.join(effectiveWorkingPath, "logic")
    #libraryLogicFiles = []
    #globalParameters["LibraryLogicPath"])
    #if "LibraryLogic" in config:
    #  if os.path.exists(resultsPath):
    #    libraryLogicFiles = os.listdir(resultsPath)
    #  else:
    #    libraryLogicFiles = []
      #if len(libraryLogicFiles) < 1 or globalParameters["ForceRedoLibraryLogic"]:
      #  if config["LibraryLogic"] != None:
      #    libraryLogicConfig = config["LibraryLogic"]
      #  else:
      #    libraryLogicConfig = {}
      #  LibraryLogic.main( libraryLogicConfig )
      #  print1("")
      #else:
      #  print1("# LibraryLogic already done.")
      #print1("")
    #print2("# LibraryLogic config: %s" % config)
    #print2("# DefaultAnalysisParameters: " % defaultAnalysisParameters)
    #benchmarkDataPath = os.path.join(globalParameters["WorkingPath"], \
    #globalParameters["BenchmarkDataPath"])
    #pushWorkingPath(globalParameters["LibraryLogicPath"])
    #globalParameters["BenchmarkDataPath"] = resultsPath
    globalParameters["BenchmarkDataPath"] = "results"
    #globalParameters["LibraryLogicPath"] = libraryLogicPath
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
    

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
from .ClientWriter import runClient, writeClientParameters #, writeClientConfigNew
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


def buildSolution(problemTypeConfig, benchmarkCommonParameters, forkParameters, globalSourcePath, effectiveWorkingPath):

  infoFile = os.path.join(effectiveWorkingPath, "solution.info")
  problemSizeGroupConfigs = [{"BenchmarkCommonParameters": benchmarkCommonParameters, "ForkParameters": forkParameters}]

  f = open(infoFile, "w")
  hardcodedParametersSets, initialSolutionParameters = assigenParameters(problemTypeConfig, problemSizeGroupConfigs)
  f.write("Total solutions: %u\n" % len(hardcodedParametersSets))

  solutionsList = generateSolutions (problemTypeConfig, hardcodedParametersSets, initialSolutionParameters)
  f.write("Valid solutions: %u\n" % len(solutionsList))
  f.close()

  if len(solutionsList) > 0: 

    sourcePath = ensurePath(os.path.join(effectiveWorkingPath, "source"))
    WriteClientLibraryFromSolutions(solutionsList, globalSourcePath, sourcePath)

    solutionsPath = ensurePath(os.path.join(effectiveWorkingPath, "solutions"))
    solutionsFilePath = os.path.join(solutionsPath, "solutions.yaml")
    problemTypeDict = solutionsList[0]["ProblemType"].state
    problemSizes = ProblemSizes(problemTypeDict, None)
    YAMLIO.writeSolutions(solutionsFilePath, problemSizes, [solutionsList])

  return solutionsList 

def getProblemTypeConfigs():
  problemTypeConfigs = [ 
    {"Batched": True, "DataType": "s", "OperationType": "GEMM", "TransposeA": False, "TransposeB": False, "UseBeta": True}, \
    {"Batched": True, "DataType": "s", "OperationType": "GEMM", "TransposeA": False, "TransposeB": True, "UseBeta": True}, \
    {"Batched": True, "DataType": "s", "OperationType": "GEMM", "TransposeA": True, "TransposeB": False, "UseBeta": True} 
  ]
  return problemTypeConfigs

def generateConfigs():
  problemTypeConfigs = getProblemTypeConfigs()

  benchmarkCommonParameters = [{"LoopTail": [True]}, {"KernelLanguage": ["Assembly"]}, \
        {"EdgeType": ["ShiftPtr"]}, {"GlobalSplitU": [1] } ]

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

  configsList = []
  for problemTypeConfig in problemTypeConfigs:

    #ttSides = [([2,4,8], [2,4,8]),([3,5,7], [2,4,8])]
    ttSides = [([4], [4,8]), ([5], [4,8])]
    #ttSides = [8]
    ttList = []
    for ttIndexSet in ttSides:
      tt = []
      for i in ttIndexSet[0]:
        for j in ttIndexSet[1]:
          tt.append([i, j])
      ttList.append(tt)

    wgSides = [([8,16],[8]), ([8,16],[16])]
    lsu = [1,2]
    wgList = []
    for wgIndexSet in wgSides:
      wg = []
      for i in wgIndexSet[0]:
        for j in wgIndexSet[1]:
          for l in lsu:
            wg.append([i,j,l])
      wgList.append(wg)
    #wg = [[16,16,1]]

    
    for tt in ttList:
      for wg in wgList:
        fp = deepcopy(forkParameters)
        fp.append({"ThreadTile": tt})
        fp.append({"WorkGroup": wg})
        configsList.append((problemTypeConfig, benchmarkCommonParameters, fp))
  
  return configsList

def generateAllSolutions(globalSourcePath, effectiveWorkingPath):
  configs = generateConfigs()
  #print ("count %u" % len(configs))
  configCount = 0
  for config in configs:
    problemTypeConfig, benchmarkCommonParameters, forkParameters = config
    problemTypeObj = ProblemType(problemTypeConfig)
    problemTypeName = str(problemTypeObj)
    currentPathName = "%u" % configCount 
    solutionWorkingPath = ensurePath(os.path.join(effectiveWorkingPath, problemTypeName, currentPathName))
    startFile = os.path.join(solutionWorkingPath, "time.start")
    stopFile = os.path.join(solutionWorkingPath, "time.stop")

    os.mknod(startFile)
    buildSolution(problemTypeConfig, benchmarkCommonParameters, forkParameters, globalSourcePath, solutionWorkingPath)
    os.mknod(stopFile)

    configCount += 1

def getProblemTypeName(problemTypeConfig):
  problemTypeObj = ProblemType(problemTypeConfig)
  problemTypeName = str(problemTypeObj)

  return problemTypeName

#def runSizesForAllSolutions(effectiveWorkingPath, clientBuildDir):

#  problemTypeConfigs = getProblemTypeConfigs()[0]
#  problemTypeObj = ProblemType(problemTypeConfigs)
#  problemTypeName = str(problemTypeObj)

#  print (problemTypeName)

def getSizeMapper():
  sizeMap = {
    "Cijk_Ailk_Bjlk_SB": [
      #{"Exact": [784, 512, 1, 128]}, 
      #{"Exact": [784, 128, 1, 512]}, 
      #{"Exact": [196, 1024, 64, 256]}, 
      {"Exact": [196, 256, 64, 1024]}
    ],
    "Cijk_Ailk_Bljk_SB": [
      #{"Exact": [784, 512, 1, 128]}, \
      #{"Exact": [784, 128, 1, 512]}, \
      #{"Exact": [196, 1024, 64, 256]}, \
      {"Exact": [196, 256, 64, 1024]}
    ],
    "Cijk_Alik_Bljk_SB": [
      #{"Exact": [784, 512, 1, 128]}, \
      #{"Exact": [784, 128, 1, 512]}, \
      #{"Exact": [196, 1024, 64, 256]}, \
      {"Exact": [196, 256, 64, 1024]}
    ]}

  return sizeMap

#def runSizesForAllSolutions(effectiveWorkingPath, clientBuildDir):

#  problemTypeConfigs = getProblemTypeConfigs()[0]
#  problemTypeObj = ProblemType(problemTypeConfigs)
#  problemTypeName = str(problemTypeObj)

#  print (problemTypeName)
#  sizeMap = getSizeMapper()

#  for key in sizeMap:
#    print (key)
#   value = sizeMap[key]
#    print (value)

def runSizesForAllSolutions(effectiveWorkingPath, clientBuildDir, outputPath):

  #sizes = [
  #  {"Exact": [784, 512, 1, 128]}, \
  #  {"Exact": [784, 128, 1, 512]}, \
  #  {"Exact": [196, 1024, 64, 256]}, \
  #  {"Exact": [196, 256, 64, 1024]}
  #]

  sizeMap = getSizeMapper()

  for sizeKey in sizeMap:
    
    currentWorkingPath = os.path.join(effectiveWorkingPath, sizeKey)
    currentResultsPath = ensurePath(os.path.join(outputPath, sizeKey))
    thePaths = [f for f in os.scandir(currentWorkingPath) if f.is_dir() and f.name != "client"]
    for pathObj in thePaths:
      #print (type(path))
      #print (path)
      path = pathObj.path
      localPathName = pathObj.name
      localOutputPath = ensurePath(os.path.join(currentResultsPath, localPathName))
      libraryPath = os.path.join(path, 'source', 'library' )
      sizes = sizeMap[sizeKey]
      if os.path.isdir(libraryPath):
        #print (libPath)
        metadataFilepath = os.path.join(libraryPath, "metadata.yaml")
        metadataFile = YAMLIO.readConfig(metadataFilepath)
        #print (metadataFile["ProblemType"])
        problemTypeDict = metadataFile["ProblemType"]
        #problemTypeObj = ProblemType(problemTypeDict)
        #problemTypeName = str(problemTypeObj)
        problemSizes = ProblemSizes(problemTypeDict, sizes)
        #print (True)
        dataPath = ensurePath(os.path.join(localOutputPath, "data"))
        configFilePath = ensurePath(os.path.join(localOutputPath, "configs"))
        dataFilePath = os.path.join(dataPath, "benchmark.csv")
        configFile = os.path.join(configFilePath, "ClientParameters.ini")
        scriptPath = ensurePath(os.path.join(localOutputPath, "script"))

        CreateBenchmarkClientPrametersForSizes(libraryPath, problemSizes, dataFilePath, configFile)
        #returncode = runNewClient(scriptPath, configFile, clientBuildDir)
        runNewClient(scriptPath, configFile, clientBuildDir)

def GenerateSolutions(userArgs):
    
    assignGlobalParameters({"PrintWinnersOnly": 1})

    #problemTypeConfig = {"Batched": True, "DataType": "s", "OperationType": "GEMM", "TransposeA": False, "TransposeB": False,
    #"UseBeta": True}

    #problemType = ProblemType(problemTypeConfig)
    #print (problemType)

    #BenchmarkCommonParameters:
    #benchmarkCommonParameters = [{"LoopTail": [True]}, {"KernelLanguage": ["Assembly"]}, \
    #    {"EdgeType": ["ShiftPtr"]}, {"GlobalSplitU": [1] } ]

    #ForkParameters:
    #forkParameters = [ \
    #{"PrefetchGlobalRead": [False, True]}, \
    #{"WorkGroupMapping": [1, 8]}, \
    #{"DepthU": [8, 16, 32]}, \
    #{"LdsPadA": [0, -1]}, \
    #{"PrefetchLocalRead": [False, True]}, \
    #{"LdsPadB": [0, -1]}, \
    #{"VectorWidth": [-1]}, \
    #{"GlobalReadVectorWidth": [-1, 1]}, \
    #{"FractionalLoad": [1]}]
    #, \
    #{"ThreadTile": [[4, 4], [8, 8]]}, \
    #{"WorkGroup": [[16, 16, 1]]}
    #]


    #ttSides = [1,2,3,4,5,6]
    #ttSides = [2,4,8]
    #ttSides = [8]
    #tt = []
    #for i in ttSides:
    #  for j in ttSides:
    #    tt.append([i, j])

    #wgSides = [8,16]
    #wg = []
    #for i in wgSides:
    #  for j in wgSides:
    #      wg.append([i,j,1])
    #wg = [[16,16,1]]
    #forkParameters.append({"ThreadTile": tt})
    #forkParameters.append({"WorkGroup": wg})
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

    globalSourcePath = "/home/billg/amd/wbgilmartin/tasks/tensile_library_step/Tensile-library-step2/Tensile/Source"
    effectiveWorkingPath = "/home/billg/amd/wbgilmartin/tasks/tensile_library_step/tensile_tuning_5/tune0/testLibrary"
    ensurePath(effectiveWorkingPath)

    #sourcePath = ensurePath(os.path.join(effectiveWorkingPath, "source"))
    #solutionsPath = ensurePath(os.path.join(effectiveWorkingPath, "solutions"))
    #libraryPath = ensurePath(os.path.join(sourcePath, "library"))
    #dataPath = ensurePath(os.path.join(effectiveWorkingPath, "data"))
    #configFilePath = ensurePath(os.path.join(effectiveWorkingPath, "configs"))
    #scriptPath = ensurePath(os.path.join(effectiveWorkingPath, "script"))
    clientBuildDir = ensurePath(os.path.join(effectiveWorkingPath, "client"))
    #resultsPath = ensurePath(os.path.join(effectiveWorkingPath, "results"))

    #dataFilePath = os.path.join(dataPath, "benchmark.csv")
    #configFile = os.path.join(configFilePath, "ClientParameters.ini")
    #solutionsFilePath = os.path.join(solutionsPath, "solutions.yaml")

    ClientExecutable.getClientExecutable(clientBuildDir)

    #configs = generateConfigs()
    #print ("count %u" % len(configs))
    #configCount = 0
    #for config in configs:
    #  problemTypeConfig, benchmarkCommonParameters, forkParameters = config
    #  currentPathName = "%u" % configCount 
      #solutionWorkingPath = ensurePath(os.path.join(effectiveWorkingPath, currentPathName))
      #buildSolution(problemTypeConfig, benchmarkCommonParameters, forkParameters, globalSourcePath, solutionWorkingPath)
    #  configCount += 1
  
    #### use this @@@@@
    generateAllSolutions(globalSourcePath, effectiveWorkingPath)
    
    
    
    #problemSizeGroupConfigs = [{"BenchmarkCommonParameters": benchmarkCommonParameters, "ForkParameters": forkParameters}]
    #hardcodedParametersSets, initialSolutionParameters = assigenParameters(problemTypeConfig, problemSizeGroupConfigs)

    #print ("number of possable solutions: %u" % len(hardcodedParametersSets))
    #solutionsList = generateSolutions (problemTypeConfig, hardcodedParametersSets, initialSolutionParameters)

    #print ("actual number of solutions: %u" % len(solutionsList))

    #WriteClientLibraryFromSolutions(solutionsList, globalSourcePath, sourcePath)

    #problemTypeDict = solutionsList[0]["ProblemType"].state

    #sizes = [
    #    {"Exact": [784, 512, 1, 128]}, \
    #    {"Exact": [784, 128, 1, 512]}, \
    #    {"Exact": [196, 1024, 64, 256]}, \
    #    {"Exact": [196, 256, 64, 1024]}
    #]

    ###### use this $$$ 
    #thePaths = [f.path for f in os.scandir(effectiveWorkingPath) if f.is_dir()]
    #for currentWorkingPath in thePaths:
    outputPath = "/home/billg/amd/wbgilmartin/tasks/tensile_library_step/tensile_tuning_5/tune0/testLibrary/results"
    runSizesForAllSolutions(effectiveWorkingPath, clientBuildDir, outputPath)

    #problemSizes = ProblemSizes(problemTypeDict, sizes)
    #problemSizes = ProblemSizes(problemTypeDict, None)
    #YAMLIO.writeSolutions(solutionsFilePath, problemSizes, [solutionsList])

    #thePaths = os.walk(effectiveWorkingPath)
    #thePaths = [x for x in os.listdir(effectiveWorkingPath)]
    #thePaths = [f.path for f in os.scandir(effectiveWorkingPath) if f.is_dir() and f.name != "client"]
    #for path in thePaths:
      #print (type(path))
      #print (path)
    #  libraryPath = os.path.join(path, 'source', 'library' )
    #  if os.path.isdir(libraryPath):
        #print (libPath)
    #    metadataFilepath = os.path.join(libraryPath, "metadata.yaml")
    #    metadataFile = YAMLIO.readConfig(metadataFilepath)
        #print (metadataFile["ProblemType"])
    #    problemTypeDict = metadataFile["ProblemType"]
    #    problemSizes = ProblemSizes(problemTypeDict, sizes)

        #print (True)
    #    dataPath = ensurePath(os.path.join(path, "data"))
    #    configFilePath = ensurePath(os.path.join(path, "configs"))
    #    dataFilePath = os.path.join(dataPath, "benchmark.csv")
    #    configFile = os.path.join(configFilePath, "ClientParameters.ini")
    #    scriptPath = ensurePath(os.path.join(path, "script"))

    #    CreateBenchmarkClientPrametersForSizes(libraryPath, problemSizes, dataFilePath, configFile)
        #returncode = runNewClient(scriptPath, configFile, clientBuildDir)
    #    runNewClient(scriptPath, configFile, clientBuildDir)
    #CreateBenchmarkClientPrametersForSizes(libraryPath, problemSizes, dataFilePath, configFile)

    #returncode = runNewClient(scriptPath, configFile, clientBuildDir)
    #print2(returncode)

    #problemTypeObj = ProblemType(problemTypeConfig)
    #problemTypeName = str(problemTypeObj)

    #resultsDataFile = os.path.join(resultsPath, problemTypeName + ".csv")
    #resultsSolutionsFile = os.path.join(resultsPath, problemTypeName + ".yaml")

    #shutil.copyfile(dataFilePath, resultsDataFile)
    #shutil.copyfile(solutionsFilePath, resultsSolutionsFile)

    #globalParameters["BenchmarkDataPath"] = "results"
    #globalParameters["LibraryLogicPath"] = "logic"
    #globalParameters["WorkingPath"] = effectiveWorkingPath

    #libraryLogic = { \
    #    "ArchitectureName": "gfx906", \
    #    "DeviceNames": ["Device 66a0", "Device 66a1", "Device 66a7", "Vega 20"], \
    #    "ScheduleName": "vega20" \
    #}

    #LibraryLogic.main(libraryLogic)

    print ("done")
    #print (returncode)
    
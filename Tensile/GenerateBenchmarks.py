
import os
import csv
import sys
import argparse
import shutil
import subprocess
from copy import deepcopy, copy
import yaml

parentdir = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
sys.path.append(parentdir)

from . import ClientExecutable
from . import Common
from . import BenchmarkProblems
from . import ClientWriter
from . import LibraryLogic
from . import LibraryIO
from . import SolutionLibrary
from . import Utils

from .BenchmarkStructs import BenchmarkProcess, assignParameters, fillMissingParametersWithDefaults, getSingleValues, \
  constructForkPermutations, forkHardcodedParameters
from .BenchmarkProblems import generateForkedSolutions
from .ClientWriter import CreateBenchmarkClientParametersForSizes, runClient, runNewClient, writeClientParameters 
from .Common import ClientExecutionLock, assignGlobalParameters, globalParameters, defaultSolution, defaultBenchmarkCommonParameters, restoreDefaultGlobalParameters, \
  HR, setWorkingPath, pushWorkingPath, popWorkingPath, print1, print2, printExit, printWarning, ensurePath, startTime, ProgressBar, hasParam
from .KernelWriterAssembly import KernelWriterAssembly
from .KernelWriterSource import KernelWriterSource
from .SolutionStructs import Solution, ProblemType, ProblemSizes
from .SolutionWriter import SolutionWriter
from .TensileCreateLibrary import  WriteClientLibraryFromSolutions, writeSolutionsAndKernels, writeCMake
from .SolutionLibrary import MasterSolutionLibrary
from .Contractions import ProblemType as ContractionsProblemType

from .SolutionGenerator import generateSolutionsFromConfigs, createSolutions, assembleParameters, generateSolutionSet
from .BenchmarkGenerator import runBenchmarksForSizes
from .LogicGenerator import generateLogic

def myReadConfig( filename ):
  try:
    stream = open(filename, "r")
  except IOError:
    printExit("Cannot open file: %s" % filename )
  config = yaml.load(stream) #, yaml.SafeLoader)
  stream.close()
  return config




def getProblemTypeConfigs():

  #problemTypeConfigs = [ 
  #  {"Batched": True, "DataType": "s", "OperationType": "GEMM", "TransposeA": False, "TransposeB": False, "UseBeta": True}
  #]

  problemTypeConfigs = [ 
    {"Batched": True, "DataType": "s", "OperationType": "GEMM", "TransposeA": False, "TransposeB": False, "UseBeta": True, \
       "TileAwareSelection": True, "SelectionModel": "TileAwareMetricSelection"}
  ]

  return problemTypeConfigs

def generateConfigs():
  problemTypeConfigs = getProblemTypeConfigs()

  benchmarkCommonParameters = [{"LoopTail": [True]}, {"KernelLanguage": ["Assembly"]}, \
        {"EdgeType": ["ShiftPtr"]}, {"GlobalSplitU": [1]}, {"VectorWidth": [-1]}, {"FractionalLoad": [1]}, \
        {"PrefetchGlobalRead": [True]}]

  forkParameters = [ ] 


  configsList = []
  for problemTypeConfig in problemTypeConfigs:

    ttSides = [([4, 8], [4, 8])]
    ttList = []
    for ttIndexSet in ttSides:
      tt = []
      for i in ttIndexSet[0]:
        for j in ttIndexSet[1]:
          tt.append([i, j])
      ttList.append(tt)

    wgSides = [([16],[8, 16])]
    lsu = [1]
    wgList = []
    for wgIndexSet in wgSides:
      wg = []
      for i in wgIndexSet[0]:
        for j in wgIndexSet[1]:
          for l in lsu:
            wg.append([i,j,l])
      wgList.append(wg)
    
    for tt in ttList:
      for wg in wgList:
        fp = deepcopy(forkParameters)
        fp.append({"ThreadTile": tt})
        fp.append({"WorkGroup": wg})
        configsList.append((problemTypeConfig, benchmarkCommonParameters, fp))
  
  return configsList

def generateAllSolutions(effectiveWorkingPath):
  configs = generateConfigs()

  configCount = 0
  for config in configs:
    problemTypeConfig, benchmarkCommonParameters, forkParameters = config
    problemTypeObj = ProblemType(problemTypeConfig)
    problemTypeName = str(problemTypeObj)
    currentPathName = "%u" % configCount 
    solutionWorkingPath = ensurePath(os.path.join(effectiveWorkingPath, problemTypeName, currentPathName))
    createSolutions(problemTypeConfig, benchmarkCommonParameters, forkParameters, solutionWorkingPath)

    configCount += 1
  
#def generateSolutionsFromConfigs(effectiveWorkingPath, problemTypeConfig, benchmarkCommonParameters, forkParameters, tag):
#  problemTypeObj = ProblemType(problemTypeConfig)
#  problemTypeName = str(problemTypeObj)
#  #currentPathName = "%u" % configCount 
#  solutionWorkingPath = ensurePath(os.path.join(effectiveWorkingPath, problemTypeName, tag))
#  createSolutions(problemTypeConfig, benchmarkCommonParameters, forkParameters, solutionWorkingPath)

def getProblemTypeName(problemTypeConfig):
  problemTypeObj = ProblemType(problemTypeConfig)
  problemTypeName = str(problemTypeObj)

  return problemTypeName


def getSizeMapper():
  sizeMap = {
    "Cijk_Ailk_Bjlk_SB": [
      {"Exact": [196, 256, 64, 1024]}
    ],
    "Cijk_Ailk_Bljk_SB": [
      {"Exact": [196, 256, 64, 1024]}
    ],
    "Cijk_Alik_Bljk_SB": [
      {"Exact": [196, 256, 64, 1024]}
    ]}

  return sizeMap




def runSizesForAllSolutions(effectiveWorkingPath, clientBuildDir, outputPath):
  sizeMap = getSizeMapper()

  for sizeKey in sizeMap:
    
    currentWorkingPath = os.path.join(effectiveWorkingPath, sizeKey)
    #currentWorkingPath = effectiveWorkingPath
    if os.path.isdir(currentWorkingPath):
      currentResultsPath = ensurePath(os.path.join(outputPath, sizeKey))
      thePaths = [f for f in os.scandir(currentWorkingPath) if f.is_dir() and f.name != "client"]
      for pathObj in thePaths:
        path = pathObj.path
        localPathName = pathObj.name
        localOutputPath = ensurePath(os.path.join(currentResultsPath, localPathName))
        libraryPath = os.path.join(path, 'source')
        sizes = sizeMap[sizeKey]
        if os.path.isdir(libraryPath):
          runBenchmarksForSizes(libraryPath, localOutputPath, clientBuildDir, sizes)


def GenerateBenchmarks(userArgs):
  
  effectiveWorkingPath = userArgs[0]
  configFile = userArgs[1]
  sourcePath = userArgs[2]
  resultsPath = userArgs[3]
  sizeDefs = userArgs[4]

  if len(userArgs) > 5:
    clientBuildDir = userArgs[5]
  else:
    clientBuildDir = os.path.join(effectiveWorkingPath, "client")

  ensurePath(effectiveWorkingPath)
  config = LibraryIO.readConfig(configFile)

  #restoreDefaultGlobalParameters()

  #globalParameters["ConfigPath"] = configFile

  # assign global parameters
  if "GlobalParameters" in config:
    assignGlobalParameters( config["GlobalParameters"] )
  else:
    assignGlobalParameters({})
   
  #clientBuildDir = ensurePath(os.path.join(effectiveWorkingPath, "client"))
  ClientExecutable.getClientExecutable(clientBuildDir)

  macroTileDefs = config["MacroTileDefs"]

######## loop sizes
  size_set_a = LibraryIO.readConfig(sizeDefs)

  if True:

    #size_set_a = [{"Exact": [196, 256, 64, 1024]}]
    #solutionsRoot = os.path.join(effectiveWorkingPath, "solutions")

    #for mt in macroTileDefs:
      
    #  subPath = "{}_{}".format(mt[0], mt[1])
    #  subfolterPath = os.path.join(solutionsRoot, subPath)
    #  sourcePath = ensurePath(os.path.join(subfolterPath, "source"))
    
    #resultsRoot = os.path.join(effectiveWorkingPath, "results")
    #sizeSetName = "set_a"
    #resultsPath = os.path.join(resultsRoot, sizeSetName, subPath)
      
    print ("running benchmarks")
    runBenchmarksForSizes(sourcePath, resultsPath, clientBuildDir, size_set_a)

    #exit(0)

  print ("done")

    
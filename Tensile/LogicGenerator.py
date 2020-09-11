

import os
import csv
import sys
import argparse
import shutil
import subprocess
from copy import deepcopy, copy
import yaml


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
from .Common import ClientExecutionLock, assignGlobalParameters, globalParameters, defaultSolution, defaultBenchmarkCommonParameters, \
  HR, setWorkingPath, pushWorkingPath, popWorkingPath, print1, print2, printExit, printWarning, ensurePath, startTime, ProgressBar, hasParam
from .KernelWriterAssembly import KernelWriterAssembly
from .KernelWriterSource import KernelWriterSource
from .SolutionStructs import Solution, ProblemType, ProblemSizes
from .SolutionWriter import SolutionWriter
from .TensileCreateLibrary import  WriteClientLibraryFromSolutions, writeSolutionsAndKernels, writeCMake
from .SolutionLibrary import MasterSolutionLibrary
from .Contractions import ProblemType as ContractionsProblemType


def extractProblemsSizes(results_file, numSolutions):
    dataFile = None
    try:
      dataFile = open(results_file, "r")
    except IOError:
      printExit("Can't open \"%s\" to get data" % results_file )
    results_csv = csv.reader(dataFile)

    problemSizes = []
    problemSizeStartIdx = 1
    totalSizeIdx = 1
    rowIdx = 0
    for row in results_csv:
      rowIdx+=1
      if rowIdx == 1:
        # get the length of each row, and derive the first column of the solution instead of using wrong "solutionStartIdx = totalSizeIdx + 1"
        rowLength = len(row)
        solutionStartIdx = rowLength - numSolutions
        totalSizeIdx = solutionStartIdx - 1
        continue
      else:
        problemSize = []
        for i in range(problemSizeStartIdx, totalSizeIdx):
          problemSize.append(int(row[i]))
        problemSizes.append({"Exact": problemSize})

    return problemSizes

def provisionResultsFile(resultsFile, targetPath, provisionName, targeExt):

  targetFileName = "%s.%s" % (os.path.join(targetPath, provisionName),targeExt)
  if resultsFile:
    shutil.copyfile(resultsFile, targetFileName)
  else:
    open(targetFileName, 'a').close()

def provisionStaging(exactData, granularityData, solutions, provisionName, targetPath):

  provisionResultsFile(exactData, targetPath, provisionName, "csv")
  provisionResultsFile(granularityData, targetPath, provisionName, "gsp")

  problemSizes = []
  numSolutions = len(solutions) - 2
  if exactData:
    problemSizes = extractProblemsSizes(exactData, numSolutions)
  if granularityData:
    problemSizes0 = extractProblemsSizes(granularityData, numSolutions)
    problemSizes = problemSizes + problemSizes0

  solutions[1]["ProblemSizes"] = problemSizes

  staging_yaml = "%s.%s" % (os.path.join(targetPath, provisionName), "yaml")
  LibraryIO.YAMLWriter().write(staging_yaml, solutions)


#def provisionLogic():
#  provisionStaging(None, results_file, solutions_yaml, "Cijk_Ailk_Bljk_SB_00", staging_path)

def launchLogic(workingPath, libraryLogicSpec, logicPath, dataPath):
  ######
    ##############################################################################
    # Library Logic
    ##############################################################################
    config = {}
    
    config["LibraryLogic"] = libraryLogicSpec
    globalParameters["WorkingPath"] = workingPath
    globalParameters["LibraryLogicPath"] = logicPath
    globalParameters["BenchmarkDataPath"] = dataPath
    #benchmarkDataPath = os.path.join(globalParameters["WorkingPath"], \
    #  globalParameters["BenchmarkDataPath"])#

    libraryLogicDataPath = os.path.join(globalParameters["WorkingPath"], \
      globalParameters["LibraryLogicPath"])
    if "LibraryLogic" in config:
      if os.path.exists(libraryLogicDataPath):
        libraryLogicFiles = os.listdir(libraryLogicDataPath)
      else:
        libraryLogicFiles = []
      if len(libraryLogicFiles) < 1 or globalParameters["ForceRedoLibraryLogic"]:
        if config["LibraryLogic"] != None:
          libraryLogicConfig = config["LibraryLogic"]
        else:
          libraryLogicConfig = {}
        LibraryLogic.main( libraryLogicConfig )
        print1("")
      else:
        print1("# LibraryLogic already done.")
      print1("")


def generateLogic(workingPath, libraryLogicSpec, solutions_path, results_path): #, logicPath, dataPath):
  #solutions_path = os.path.join(effectiveWorkingPath, "solutions/64_64/solutions")
  #results_path = os.path.join(effectiveWorkingPath, "results/set_a/64_64/data")

  staging_path = ensurePath(os.path.join(workingPath, "staging"))

  solutions_file = os.path.join(solutions_path, 'solutions.yaml')
  solutions_yaml = LibraryIO.readConfig(solutions_file)
  
  results_file = os.path.join(results_path, 'benchmark.csv')

  provisionStaging(None, results_file, solutions_yaml, "Cijk_Ailk_Bljk_SB_00", staging_path)

  libraryLogicSpec = { "ArchitectureName": "gfx906", \
      "DeviceNames": ["Device 66a0", "Device 66a1", "Device 66a7"], \
      "ScheduleName": "vega20" }

  logicPath = "logic"
  dataPath = "staging"
  #launchLogic(staging_path, libraryLogicSpec, logicPath, dataPath)
  launchLogic(workingPath, libraryLogicSpec, logicPath, dataPath)
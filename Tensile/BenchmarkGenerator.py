
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

#from .BenchmarkStructs import BenchmarkProcess, assignParameters, fillMissingParametersWithDefaults, getSingleValues, \
#  constructForkPermutations, forkHardcodedParameters
from .BenchmarkProblems import generateForkedSolutions
from .BenchmarkStructs import assignParameters, fillMissingParametersWithDefaults, getSingleValues, \
    constructForkPermutations, forkHardcodedParameters
from .ClientWriter import CreateBenchmarkClientParametersForSizes, runClient, runNewClient, writeClientParameters 
from .Common import ClientExecutionLock, assignGlobalParameters, globalParameters, defaultSolution, defaultBenchmarkCommonParameters, \
  HR, setWorkingPath, pushWorkingPath, popWorkingPath, print1, print2, printExit, printWarning, ensurePath, startTime, ProgressBar, hasParam
from .KernelWriterAssembly import KernelWriterAssembly
from .KernelWriterSource import KernelWriterSource
from .SolutionStructs import Solution, ProblemType, ProblemSizes
from .SolutionWriter import SolutionWriter

def runBenchmarksForSizes(libraryPath, outputPath, clientBuildDir, sizes):
  metadataFilepath = os.path.join(libraryPath, "library", "metadata.yaml")
  metadataFile = LibraryIO.readConfig(metadataFilepath)
  problemTypeDict = metadataFile["ProblemType"]
  problemSizes = ProblemSizes(problemTypeDict, sizes)
  dataPath = ensurePath(os.path.join(outputPath, "data"))
  configFilePath = ensurePath(os.path.join(outputPath, "configs"))
  dataFilePath = os.path.join(dataPath, "benchmark.csv")
  configFile = os.path.join(configFilePath, "ClientParameters.ini")
  scriptPath = ensurePath(os.path.join(outputPath, "script"))
  CreateBenchmarkClientParametersForSizes(libraryPath, problemSizes, dataFilePath, configFile)
  runNewClient(scriptPath, configFile, clientBuildDir)



def runSizesForSolutionsDirect(sizes, effectiveWorkingPath, clientBuildDir, outputPath):
  #sizeMap = getSizeMapper()
  #sizes = sizeMap["Cijk_Ailk_Bljk_SB"]
  runBenchmarksForSizes(effectiveWorkingPath, outputPath, clientBuildDir, sizes)
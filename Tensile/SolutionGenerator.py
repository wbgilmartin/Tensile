


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
#from .TensileCreateLibrary import  WriteClientLibraryFromSolutions, writeSolutionsAndKernels, writeCMake

from .TensileCreateLibrary import  WriteClientLibraryFromSolutions #, writeSolutionsAndKernels, writeCMake
#from .SolutionLibrary import MasterSolutionLibrary
#from .Contractions import ProblemType as ContractionsProblemType


def createSolutions(problemTypeConfig, benchmarkCommonParameters, forkParameters, effectiveWorkingPath):
  setWorkingPath (effectiveWorkingPath)
  infoFile = os.path.join(effectiveWorkingPath, "solution.info")

  f = open(infoFile, "w")
  problemTypeObj, hardcodedParametersSets, initialSolutionParameters = assignParameters(problemTypeConfig, benchmarkCommonParameters, forkParameters)
  f.write("Total solutions: %u\n" % len(hardcodedParametersSets))

  solutionsList = generateForkedSolutions (problemTypeObj, hardcodedParametersSets, initialSolutionParameters)
  f.write("Valid solutions: %u\n" % len(solutionsList))
  f.close()

  if len(solutionsList) > 0: 

    sourcePath = ensurePath(os.path.join(effectiveWorkingPath, "source"))
    WriteClientLibraryFromSolutions(solutionsList, sourcePath)

    solutionsPath = ensurePath(os.path.join(effectiveWorkingPath, "solutions"))
    solutionsFilePath = os.path.join(solutionsPath, "solutions.yaml")
    LibraryIO.writeSolutions(solutionsFilePath, None, [solutionsList])
  
  popWorkingPath()

  return solutionsList 


def generateSolutionsFromConfigs(solutionWorkingPath, problemTypeConfig, benchmarkCommonParameters, forkParameters):
  #problemTypeObj = ProblemType(problemTypeConfig)
  #problemTypeName = str(problemTypeObj)
  #currentPathName = "%u" % configCount 
  #solutionWorkingPath = ensurePath(os.path.join(effectiveWorkingPath, problemTypeName, tag))
  createSolutions(problemTypeConfig, benchmarkCommonParameters, forkParameters, solutionWorkingPath)

#solutionsList = generateForkedSolutions (problemTypeObj, fullParamsList, initialSolutionParameters)

def assembleParameters(problemTypeConfig, configBenchmarkCommonParameters, configForkParameters):

  #problemTypeObj = ProblemType(problemTypeConfig)
  initialSolutionParameters = { "ProblemType": problemTypeConfig }
  initialSolutionParameters.update(defaultSolution)

  hardcodedParameters = []
  benchmarkCommonParameters = fillMissingParametersWithDefaults([configBenchmarkCommonParameters, configForkParameters], defaultBenchmarkCommonParameters)
  if configBenchmarkCommonParameters != None:
    for paramDict in configBenchmarkCommonParameters:
      benchmarkCommonParameters.append(deepcopy(paramDict))

  singleValues = getSingleValues([benchmarkCommonParameters, configForkParameters])
  for paramName in singleValues:
    paramValue = singleValues[paramName]
    initialSolutionParameters[paramName] = paramValue
    
  forkPermutations = constructForkPermutations(configForkParameters)
  if len(forkPermutations) > 0:
    hardcodedParameters = forkHardcodedParameters([initialSolutionParameters], forkPermutations)
  
  return (hardcodedParameters, initialSolutionParameters)


def generateSolutionSet(problemTypeConfig, benchmarkCommonParameters, forkParameters, mt_defs, solutionsPath, sourcePath):
    hardcodedParameters, initialSolutionParameters = assembleParameters(deepcopy(problemTypeConfig), \
      deepcopy(benchmarkCommonParameters), deepcopy(forkParameters))

    fullParamsList = []

    for hcp in hardcodedParameters:
      for mt in mt_defs:
        wg = mt[0]
        tt = mt[1]
        hcp0 = deepcopy(hcp)
        hcp0["ThreadTile"] = tt
        hcp0["WorkGroup"] = wg
        fullParamsList.append(hcp0)

    print("place holder 2")

    problemTypeObj = ProblemType(problemTypeConfig)
    solutionsList = generateForkedSolutions (problemTypeObj, fullParamsList, [initialSolutionParameters])

    solutions = []
    for s in solutionsList:
      if len(s) > 0:
        s[0]._state["ProblemType"] = deepcopy(problemTypeObj)
        solutions.append(s[0])

    #sourcePath = ensurePath(os.path.join(effectiveWorkingPath, "source_64_64"))
    WriteClientLibraryFromSolutions(solutions, sourcePath)

    #solutionsPath = ensurePath(os.path.join(effectiveWorkingPath, "solutions_64_64"))
    solutionsFilePath = os.path.join(solutionsPath, "solutions.yaml")
    #solutionsList = generateForkedSolutions (problemTypeObj, fullParamsList, initialSolutionParameters)
    LibraryIO.writeSolutions(solutionsFilePath, None, [solutions])

    solutionsMetadataFile = os.path.join(solutionsPath, "solutions_metadat.yaml")
    solutions_metadat = {}
    solutions_metadat["NumSolutions"] = len(solutions)

    LibraryIO.YAMLWriter().write(solutionsMetadataFile, solutions_metadat)

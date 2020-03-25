
#if __name__ == "__main__":
#    print("This file can no longer be run as a script.  Run 'Tensile/bin/Tensile' instead.")
#    exit(1)

import os
import sys
import argparse
import shutil
import subprocess
from copy import deepcopy, copy

from . import ClientExecutable
from . import Common

from . import BenchmarkProblems
from . import ClientWriter
from . import LibraryLogic
from . import YAMLIO
from . import SolutionLibrary
from . import Utils

from .BenchmarkStructs import BenchmarkProcess
from .ClientWriter import runClient, writeClientParameters, writeClientConfigNew
from .Common import ClientExecutionLock, assignGlobalParameters, globalParameters, defaultSolution, defaultBenchmarkCommonParameters, \
  HR, pushWorkingPath, popWorkingPath, print1, print2, printExit, printWarning, ensurePath, startTime, ProgressBar, hasParam
from .KernelWriterAssembly import KernelWriterAssembly
from .KernelWriterSource import KernelWriterSource
from .SolutionStructs import Solution, ProblemType, ProblemSizes
from .SolutionWriter import SolutionWriter
from .TensileCreateLibrary import writeSolutionsAndKernels, writeCMake
from .SolutionLibrary import MasterSolutionLibrary
from .Contractions import ProblemType as ContractionsProblemType

def writeNewClientRunScript(scriptPath, clientParametersPath, clientExePath = None): #, forBenchmark):
  # create run.bat or run.sh which builds and runs
  runScriptName = os.path.join(scriptPath, \
    "run.%s" % ("bat" if os.name == "nt" else "sh") )
  runScriptFile = open(runScriptName, "w")

  if os.name != "nt":
    runScriptFile.write("#!/bin/bash\n\n")

  #if forBenchmark:
  newClientExe = ClientExecutable.getClientExecutable(clientExePath)
  configFile = clientParametersPath
  runScriptFile.write("{} --config-file={}\n".format(newClientExe, configFile))
  runScriptFile.write("ERR1=$?\n\n")

  runScriptFile.write("""
ERR=0
if [[ $ERR1 -ne 0 ]]
then
    echo one
    ERR=$ERR1
fi
""")
  if os.name != "nt":
    runScriptFile.write("exit $ERR\n")
  runScriptFile.close()
  if os.name != "nt":
    os.chmod(runScriptName, 0o777)
  return runScriptName


def runNewClient(scriptPath, clientParametersPath, clientBuildDir=None):
  
  # write runScript
  runScriptName = writeNewClientRunScript(scriptPath, clientParametersPath, clientBuildDir)

  with ClientExecutionLock():
    process = subprocess.Popen(runScriptName, cwd=scriptPath)
    process.communicate()

  if process.returncode:
    printWarning("ClientWriter Benchmark Process exited with code %u" % process.returncode)
  return process.returncode

################################################################################
# Write Benchmark Files
################################################################################
def writeBenchmarkClientFiles(libraryWorkingPath, tensileSourcePath, solutions, cxxCompiler, mergeFiles=False):

  filesToCopy = [
        "CMakeLists.txt",
        "TensileTypes.h",
        "tensile_bfloat16.h",
        "KernelHeader.h",
        ]

  for f in filesToCopy:
      shutil.copy(os.path.join(tensileSourcePath, f),libraryWorkingPath)

  if not mergeFiles:
    ensurePath(os.path.join(libraryWorkingPath, "Solutions"))
    ensurePath(os.path.join(libraryWorkingPath, "Kernels"))

  ##############################################################################
  # Min Naming
  ##############################################################################
  kernels = []
  kernelsBetaOnly = []
  for solution in solutions:
    solutionKernels = solution.getKernels()
    for kernel in solutionKernels:
      if kernel not in kernels:
        kernels.append(kernel)
    solutionKernelsBetaOnly = solution.getKernelsBetaOnly()
    for kernel in solutionKernelsBetaOnly:
      if kernel not in kernelsBetaOnly:
        kernelsBetaOnly.append(kernel)

  solutionSerialNaming = Solution.getSerialNaming(solutions)
  kernelSerialNaming = Solution.getSerialNaming(kernels)
  solutionMinNaming = Solution.getMinNaming(solutions)
  kernelMinNaming = Solution.getMinNaming(kernels)
  solutionWriter = SolutionWriter( \
      solutionMinNaming, solutionSerialNaming, \
      kernelMinNaming, kernelSerialNaming)
  kernelWriterSource = KernelWriterSource( \
      kernelMinNaming, kernelSerialNaming)
  kernelWriterAssembly = KernelWriterAssembly( \
      kernelMinNaming, kernelSerialNaming)

  # write solution, kernels and CMake
  problemType = solutions[0]["ProblemType"]
  codeObjectFiles = writeSolutionsAndKernels( \
    libraryWorkingPath, cxxCompiler, [problemType], solutions, kernels, kernelsBetaOnly, \
    solutionWriter, kernelWriterSource, kernelWriterAssembly, errorTolerant=True )
  newLibraryDir = ensurePath(os.path.join(libraryWorkingPath, 'library'))
  newLibraryFile = os.path.join(newLibraryDir, "TensileLibrary.yaml")
  newLibrary = SolutionLibrary.MasterSolutionLibrary.BenchmarkingLibrary(solutions)
  newLibrary.applyNaming(kernelMinNaming)
  YAMLIO.write(newLibraryFile, Utils.state(newLibrary))

  return (codeObjectFiles, newLibrary)

def getValidSolutionsForStep(benchmarkStep, benchmarkProblemType):

  numHardcoded = len(benchmarkStep.hardcodedParameters)

  ############################################################################
  # Enumerate Benchmark Permutations
  ############################################################################
  solutions = []
  totalBenchmarkPermutations = 1

  for benchmarkParamName in benchmarkStep.benchmarkParameters:
    print (benchmarkParamName)
    totalBenchmarkPermutations *= len(benchmarkStep.benchmarkParameters[benchmarkParamName])
  maxPossibleSolutions = totalBenchmarkPermutations*numHardcoded
  print1("# MaxPossibleSolutions: %u = %u (hardcoded) * %u (benchmark)" % \
      (maxPossibleSolutions, numHardcoded, totalBenchmarkPermutations))

  benchmarkPermutations = []
  for i in range(0, totalBenchmarkPermutations):
    permutation = {}
    pIdx = i
    for benchmarkParamName in benchmarkStep.benchmarkParameters:
      benchmarkParamValues = deepcopy( \
          benchmarkStep.benchmarkParameters[benchmarkParamName])
      valueIdx = pIdx % len(benchmarkParamValues)
      permutation[benchmarkParamName] = benchmarkParamValues[valueIdx]
      pIdx /= len(benchmarkParamValues)
    benchmarkPermutations.append(permutation)

  ############################################################################
  # Enumerate Solutions = Hardcoded * Benchmark
  ############################################################################
  print1("# Enumerating Solutions")
  if globalParameters["PrintLevel"] >= 1:
    progressBar = ProgressBar(maxPossibleSolutions)
  solutionSet = set() # avoid duplicates for nlca=-1, 1
  for hardcodedIdx in range(0, numHardcoded):
    solutions.append([])
    hardcodedParamDict = benchmarkStep.hardcodedParameters[hardcodedIdx]
    for benchmarkPermutation in benchmarkPermutations:
      solution = {"ProblemType": deepcopy(benchmarkProblemType.state)}
      solution.update(benchmarkPermutation)
      solution.update(hardcodedParamDict)

      # append default parameters where necessary
      for initialSolutionParameterName in benchmarkStep.initialSolutionParameters:
        if initialSolutionParameterName not in solution:
          solution[initialSolutionParameterName] = \
              benchmarkStep.initialSolutionParameters[initialSolutionParameterName]
      # TODO check if solution matches problem size for exact tile kernels
      solutionObject = Solution(solution)
      if solutionObject["Valid"]:
        if solutionObject not in solutionSet:
          solutionSet.add(solutionObject)
          solutions[hardcodedIdx].append(solutionObject)
      else:
        if globalParameters["PrintSolutionRejectionReason"]:
          print1("rejecting solution %s" % str(solutionObject))
      if globalParameters["PrintLevel"] >= 1:
        progressBar.increment()

  # remove hardcoded that don't have any valid benchmarks
  removeHardcoded = []
  for hardcodedIdx in range(0, numHardcoded):
    if len(solutions[hardcodedIdx]) == 0:
      hardcodedParamDict = benchmarkStep.hardcodedParameters[hardcodedIdx]
      removeHardcoded.append(hardcodedParamDict)

  for hardcodedParam in removeHardcoded:
    benchmarkStep.hardcodedParameters.remove(hardcodedParam)
  solutionList = list (solutionSet)

  return solutionList


def WriteClientLibraryFromSolutions(solutionList, tensileSourcePath, libraryWorkingPath):

  firstSolution = deepcopy(solutionList[0])
  problemType = firstSolution["ProblemType"].state
  problemType["DataType"] = problemType["DataType"].value
  problemType["DestDataType"] = problemType["DestDataType"].value
  problemType["ComputeDataType"] = problemType["ComputeDataType"].value
 
  effectiveWorkingPath = os.path.join(libraryWorkingPath, "library") 
  ensurePath(effectiveWorkingPath)
  mataDataFilePath = os.path.join(effectiveWorkingPath, 'metadata.yaml')

  metaData = {"ProblemType":problemType}
  YAMLIO.write(mataDataFilePath, metaData)
  codeObjectFiles, newLibrary = writeBenchmarkClientFiles(libraryWorkingPath, tensileSourcePath, solutionList, globalParameters["CxxCompiler"],mergeFiles=True)

  return (codeObjectFiles, newLibrary)


def WriteClientLibraryFromSolutionFilePath(libraryWorkingPath, tensileSourcePath, solutionsFilePath):

  fileSolutions = YAMLIO.readSolutions(solutionsFilePath)
  solutions = fileSolutions[1]
  WriteClientLibraryFromSolutions(solutions, tensileSourcePath, libraryWorkingPath)


def runProblemSizeGroup(problemSizeGroupIdx, problemSizeGroupConfig, problemTypeConfig, libraryWorkingPath, tensileSourcePath):

  benchmarkTestFails = 0
  problemTypeObj = ProblemType(problemTypeConfig)
  globalParameters["EnableHalf"] = problemTypeObj["DataType"].isHalf()
  benchmarkProcess = BenchmarkProcess( problemTypeConfig, problemSizeGroupConfig )

  totalBenchmarkSteps = len(benchmarkProcess)

  for benchmarkStepIdx in range(0, totalBenchmarkSteps):
    benchmarkStep = benchmarkProcess[benchmarkStepIdx]

    solutionList = getValidSolutionsForStep(benchmarkStep, benchmarkProcess.problemType)

    shortName = benchmarkStep.abbreviation()
    problemTypeName = str(benchmarkProcess.problemType)
    problemSizeGroupName = "%s_%02u" % (problemTypeName, problemSizeGroupIdx)

    problemSizeGroupNamePath = os.path.join(libraryWorkingPath, problemSizeGroupName)
    ensurePath (problemSizeGroupNamePath)

    shortNamePath = os.path.join(problemSizeGroupNamePath, shortName)
    ensurePath(shortNamePath)

    solutionsPath = os.path.join(shortNamePath, "solutions")
    ensurePath(solutionsPath)
    solutionFilePath = os.path.join(solutionsPath,"solutions.yaml")
    ps = ProblemSizes(benchmarkProcess.problemType, None)
    YAMLIO.writeSolutions(solutionFilePath, ps, [solutionList])

    sourcePath = os.path.join(shortNamePath, "source")
    ensurePath(sourcePath)

    dataPath = os.path.join(shortNamePath, "data")
    ensurePath(dataPath)
    codeObjectFiles, newLibrary = WriteClientLibraryFromSolutions(solutionList, tensileSourcePath, sourcePath)

    resutlsFilePath = os.path.join(dataPath, shortName+"-new.csv")
    scriptPath = os.path.join(shortNamePath,"script")
    ensurePath(scriptPath)
    configFile = os.path.join(scriptPath, '../source/ClientParameters.ini')
    newSolution = next(iter(newLibrary.solutions.values()))
    writeClientConfigNew(True, benchmarkStep.problemSizes, newSolution.problemType, codeObjectFiles, resutlsFilePath, configFile)

    returncode = runNewClient(scriptPath, configFile)

    if returncode:
      benchmarkTestFails += 1
      printWarning("BenchmarkProblems: Benchmark Process exited with code %u" % returncode)

  return benchmarkTestFails


def RunBenchmarkProblem(benchmarkProblemTypeConfig, libraryWorkingPath, tensileSourcePath):

  benchmarkTestFails = 0
  problemTypeConfig = benchmarkProblemTypeConfig[0]
  if len(benchmarkProblemTypeConfig) < 2:
    problemSizeGroupConfigs = [{}]
  else:
    problemSizeGroupConfigs = benchmarkProblemTypeConfig[1:]

  for problemSizeGroupIdx, problemSizeGroupConfig in enumerate(problemSizeGroupConfigs):
    numFailes = runProblemSizeGroup(problemSizeGroupIdx, problemSizeGroupConfig, problemTypeConfig, libraryWorkingPath, tensileSourcePath)
    benchmarkTestFails += numFailes
  
  return benchmarkTestFails

def RunBenchmarkProblems(benchmarkProblemConfigs, libraryWorkingPath, tensileSourcePath):

  for benchmarkProblemTypeConfig in benchmarkProblemConfigs:
    RunBenchmarkProblem(benchmarkProblemTypeConfig, libraryWorkingPath, tensileSourcePath)

def CreateBenchmarkClientPrametersForSizes(libraryPath, problemSizes, dataFilePath, configFile):

  libraryFiles = [os.path.join(libraryPath, f) for f in os.listdir(libraryPath)] 
  codeObjectFiles = [f for f in libraryFiles if f.endswith("co")] 
  
  metaDataFilePath = os.path.join(libraryPath, "metadata.yaml")
  metaData = YAMLIO.readConfig(metaDataFilePath)
  problemTypeDict = metaData["ProblemType"]
  problemType = ContractionsProblemType.FromOriginalState(problemTypeDict)
  
  #sizeFile = YAMLIO.readConfig(sizeFilePath)
  #problemSizes = ProblemSizes(problemTypeDict, sizeFile)

  writeClientConfigNew(True, problemSizes, problemType, codeObjectFiles, dataFilePath, configFile)

def CreateBenchmarkClientPrameters(libraryPath, sizeFilePath, dataFilePath, configFile):

  libraryFiles = [os.path.join(libraryPath, f) for f in os.listdir(libraryPath)] 
  codeObjectFiles = [f for f in libraryFiles if f.endswith("co")] 
  
  metaDataFilePath = os.path.join(libraryPath, "metadata.yaml")
  metaData = YAMLIO.readConfig(metaDataFilePath)
  problemTypeDict = metaData["ProblemType"]
  problemType = ContractionsProblemType.FromOriginalState(problemTypeDict)
  
  sizeFile = YAMLIO.readConfig(sizeFilePath)
  problemSizes = ProblemSizes(problemTypeDict, sizeFile)

  writeClientConfigNew(True, problemSizes, problemType, codeObjectFiles, dataFilePath, configFile)

def forkHardcodedParameters( hardcodedParameters, update ):
  updatedHardcodedParameters = []
  for oldPermutation in hardcodedParameters:
    for newPermutation in update:
      permutation = {}
      permutation.update(oldPermutation)
      permutation.update(newPermutation)
      updatedHardcodedParameters.append(permutation)
  return updatedHardcodedParameters

def assigenParameters(problemTypeConfig, problemSizeGroupConfigs):

  hardcodedParametersSets = [{}]

  problemTypeObj = ProblemType(problemTypeConfig)
  globalParameters["EnableHalf"] = problemTypeObj["DataType"].isHalf()
  initialSolutionParameters = { "ProblemType": problemTypeConfig }
  initialSolutionParameters.update(defaultSolution)

  for problemSizeGroupConfig in problemSizeGroupConfigs:

    configBenchmarkCommonParameters = deepcopy(problemSizeGroupConfig["BenchmarkCommonParameters"])
    configForkParameters = deepcopy(problemSizeGroupConfig["ForkParameters"])

    benchmarkCommonParameters = []
    for paramDict in defaultBenchmarkCommonParameters:
      for paramName in paramDict:
        if not hasParam( paramName, [ configBenchmarkCommonParameters, configForkParameters ]) \
            or paramName == "ProblemSizes":
          benchmarkCommonParameters.append(paramDict)
    if configBenchmarkCommonParameters != None:
      for paramDict in configBenchmarkCommonParameters:
        benchmarkCommonParameters.append(paramDict)

    for stepList in [benchmarkCommonParameters, configForkParameters]:
      for paramDict in copy(stepList):
        for paramName in copy(paramDict):
          paramValues = paramDict[paramName]
          if paramValues == None:
            printExit("You must specify value for parameters \"%s\"" % paramName )
          if len(paramValues) < 2 and paramName != "ProblemSizes":
            paramDict.pop(paramName)
            hardcodedParametersSets[0][paramName] = paramValues[0]
            initialSolutionParameters[paramName] = paramValues[0]
            if len(paramDict) == 0:
              stepList.remove(paramDict)

    totalPermutations = 1
    for param in configForkParameters:
      for name in param: # only 1
        values = param[name]
        totalPermutations *= len(values)
    forkPermutations = []
    for i in range(0, totalPermutations):
      forkPermutations.append({})
      pIdx = i
      for param in configForkParameters:
        for name in param:
          values = param[name]
          valueIdx = pIdx % len(values)
          forkPermutations[i][name] = values[valueIdx]
          pIdx //= len(values)
    if len(forkPermutations) > 0:
      hardcodedParameters = forkHardcodedParameters(hardcodedParametersSets, forkPermutations)

  return (hardcodedParameters, initialSolutionParameters)


def generateSolutions (problemTypeConfig, hardcodedParameters, initialSolutionParameters):
  numHardcoded = len(hardcodedParameters)

  problemType = ProblemType(problemTypeConfig)
  ############################################################################
  # Enumerate Benchmark Permutations
  ############################################################################
  solutions = []

  ############################################################################
  # Enumerate Solutions = Hardcoded * Benchmark
  ############################################################################
  print1("# Enumerating Solutions")
  solutionSet = set() 
  for hardcodedIdx in range(0, numHardcoded):
    solutions.append([])
    hardcodedParamDict = hardcodedParameters[hardcodedIdx]
    
    solution = {"ProblemType": deepcopy(problemType.state)}
    solution.update(hardcodedParamDict)

    # append default parameters where necessary
    for initialSolutionParameterName in initialSolutionParameters:
      if initialSolutionParameterName not in solution:
        solution[initialSolutionParameterName] = \
            initialSolutionParameters[initialSolutionParameterName]
    # TODO check if solution matches problem size for exact tile kernels
    solutionObject = Solution(solution)
    if solutionObject["Valid"]:
      if solutionObject not in solutionSet:
        solutionSet.add(solutionObject)
        solutions[hardcodedIdx].append(solutionObject)
    else:
      if globalParameters["PrintSolutionRejectionReason"]:
        print1("rejecting solution %s" % str(solutionObject))
    #if globalParameters["PrintLevel"] >= 1:
    #  progressBar.increment()

  # remove hardcoded that don't have any valid benchmarks
  removeHardcoded = []
  for hardcodedIdx in range(0, numHardcoded):
    if len(solutions[hardcodedIdx]) == 0:
      hardcodedParamDict = hardcodedParameters[hardcodedIdx]
      removeHardcoded.append(hardcodedParamDict)

  for hardcodedParam in removeHardcoded:
    hardcodedParameters.remove(hardcodedParam)
  solutionList = list (solutionSet)

  return solutionList


def TensileCreateClientLibrary(userArgs):
  # 1st half of splash
  print1("")
  print1(HR)
  print1("#")

  # setup argument parser
  argParser = argparse.ArgumentParser()
  argParser.add_argument("config_file", \
    help="benchmark config.yaml file")
  argParser.add_argument("output_path", \
    help="path where to conduct benchmark")
  argParser.add_argument("--client-build-path", default=None)

  args = argParser.parse_args(userArgs)
  configPath = os.path.realpath( args.config_file)

  # read config
  config = YAMLIO.readConfig( configPath )
  globalParameters["ConfigPath"] = configPath
  
  # assign global parameters
  if "GlobalParameters" in config:
    assignGlobalParameters( config["GlobalParameters"] )
  else:
    assignGlobalParameters({})

  globalParameters["OutputPath"] = ensurePath(os.path.abspath(args.output_path))
  globalParameters["WorkingPath"] = globalParameters["OutputPath"]
  if args.client_build_path:
    globalParameters["ClientBuildPath"] = args.client_build_path

  effectiveWorkingPath = "/home/billg/amd/wbgilmartin/tasks/tensile_library_step/tensile_tuning_2/tune1/testLibrary"

  globalSourcePath = globalParameters["SourcePath"]
  
  builddir = os.path.join(effectiveWorkingPath, globalParameters["ClientBuildPath"])
  ClientExecutable.getClientExecutable(builddir)
  benchmarkProblemConfigs = config["BenchmarkProblems"]

  #RunBenchmarkProblems(benchmarkProblemConfigs, effectiveWorkingPath, globalSourcePath)

  
  problemSizeGroupIdx = 0
  shortName = "Final_00"
  for benchmarkProblemTypeConfig in benchmarkProblemConfigs:

    problemTypeConfig = benchmarkProblemTypeConfig[0]

    problemSizeGroupConfigs = [{}]
    if len(benchmarkProblemTypeConfig) > 1:
      problemSizeGroupConfigs = benchmarkProblemTypeConfig[1:]
    hardcodedParametersSets, initialSolutionParameters = assigenParameters(problemTypeConfig, problemSizeGroupConfigs)

    problemTypeObj = ProblemType(problemTypeConfig)
    problemTypeName = str(problemTypeObj)
    problemSizeGroupName = "%s_%02u" % (problemTypeName, problemSizeGroupIdx)

    problemSizeGroupNamePath = os.path.join(effectiveWorkingPath, problemSizeGroupName)
    ensurePath (problemSizeGroupNamePath)

    shortNamePath = os.path.join(problemSizeGroupNamePath, shortName)
    ensurePath(shortNamePath)

    solutionsList = generateSolutions (problemTypeConfig, hardcodedParametersSets, initialSolutionParameters)

    solutionPath = os.path.join(shortNamePath, "solutions")
    ensurePath (solutionPath)
    solutionsFilePath = os.path.join(solutionPath, "solutions.yaml")


    ps = ProblemSizes(problemTypeObj, None)
    YAMLIO.writeSolutions(solutionsFilePath, ps, [solutionsList])

    sourcePath = os.path.join(shortNamePath, "source")
    ensurePath(sourcePath)
    WriteClientLibraryFromSolutions(solutionsList, globalSourcePath, sourcePath)

    libraryPath = os.path.join(sourcePath, "library")
    sizePath = "/home/billg/amd/wbgilmartin/tasks/tensile_library_step/tensile_tuning_2/tune0/testLibrary/sizes"
    sizeFilePath = os.path.join(sizePath, "sizes.yaml")

    outputPath = os.path.join(shortNamePath, "results")
    ensurePath(outputPath)
    dataPath = os.path.join(shortNamePath, "data")
    ensurePath(dataPath)
    resutlsFilePath = os.path.join(dataPath, "benchmark.csv")
    configFile = os.path.join(outputPath, "ClientParameters.ini")
    CreateBenchmarkClientPrameters(libraryPath, sizeFilePath, resutlsFilePath, configFile)
    scriptPath = os.path.join(shortNamePath, "script")
    ensurePath(scriptPath)
    returncode = runNewClient(scriptPath, configFile)

    print (returncode)



################################################################################
# Main
################################################################################
#if __name__ == "__main__":
#    TensileCreateClientLibrary(sys.argv[1:])


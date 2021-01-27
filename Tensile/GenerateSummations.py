

import yaml
import os

import pandas as pd
import numpy as np
import math
import yaml
import scipy
import subprocess
import itertools
import glob

from shutil import copyfile
from copy import deepcopy

from . import LibraryIO

from . import TensileCreateLibrary
from . import ClientWriter
from .Common import assignGlobalParameters, restoreDefaultGlobalParameters, ensurePath, globalParameters, \
    gfxName, gfxArch, pushWorkingPath, popWorkingPath
from .SolutionStructs import ProblemSizes, Solution


def getArchitecture(isaName):
    archid = gfxName(isaName)
    return TensileCreateLibrary.getArchitectureName(archid)

def isValidArch(archName, currentArch):
    arch = gfxArch(archName)
    return currentArch == arch

def createLibraryForBenchmark(logicPath, libraryPath, currentPath):
    args = ["/home/billg/amd/wbgilmartin/tasks/tile_aware_metric/dockerdx2/Tensile-tile-aware-metric-integration/Tensile/bin/TensileCreateLibrary", \
        "--merge-files", "--no-legacy-components", \
        "--new-client-only", "--no-short-file-names", "--no-library-print-debug", "--architecture=all", \
        "--code-object-version=V3", "--cxx-compiler=hipcc", "--library-format=yaml", \
        logicPath, libraryPath, "HIP"]

   #print (args)
    try:
        subprocess.run(args, check=True, cwd=currentPath)
    except (subprocess.CalledProcessError, OSError) as e:
        print("ClientWriter Benchmark Process exited with error: {}".format(e))
    except:
        print ("no good")


def GenerateSummations(userArgs):

    inputLogicPath = userArgs[0]
    outputPath = userArgs[1]
    #libPath = ensurePath(os.path.join(outputPath, "lib"))
    #finalPath = ensurePath(os.path.join(outputPath, "final"))

    #restoreDefaultGlobalParameters()
    assignGlobalParameters({})

    #supportedISAs = globalParameters["SupportedISA"]    
    currentISA = globalParameters["CurrentISA"]
    currentArchitecture = getArchitecture(currentISA)

    globPath = os.path.join(inputLogicPath, "{}*".format(currentArchitecture))
    logicFileNames = glob.glob(globPath)

    for logicFileName in logicFileNames:

        logicFileBaseName = os.path.basename(logicFileName)
        logicFileStem, ext = os.path.splitext(logicFileBaseName)
        if (ext != ".yaml"):
            continue

        currentPath = ensurePath(os.path.join(outputPath, logicFileStem))

        libPath = ensurePath(os.path.join(currentPath, "lib"))
        finalPath = ensurePath(os.path.join(currentPath, "final"))
        localLogicPath = ensurePath(os.path.join(currentPath, "logic"))
        localLogicFilePath = os.path.join(localLogicPath, logicFileBaseName)
        
        logic = LibraryIO.readLibraryLogicForSchedule(logicFileName)

        (scheduleName, deviceNames, problemType, solutionsForSchedule, \
           indexOrder, exactLogic, rangeLogic, _, architectureName) = logic

        naming = Solution.getMinNaming(solutionsForSchedule)

        for s in solutionsForSchedule:
            s_state = s._state
            name = Solution.getNameMin(s_state, naming)
            s_state["SolutionNameMin"] = name          
            isa = s_state["ISA"]
            s_state["ISA"] = list(isa) 

        exactLogic0 = {}
        for e in exactLogic:
            exactLogic0[tuple(e[0])] = e[1]

        logicTuple = (problemType, solutionsForSchedule, indexOrder, exactLogic0, rangeLogic)
        LibraryIO.configWriter("yaml").writeLibraryLogicForSchedule(localLogicPath, \
            scheduleName, architectureName, \
            deviceNames, logicTuple)

        createLibraryForBenchmark(localLogicPath, libPath, currentPath)

        logic1 = LibraryIO.readLibraryLogicForSchedule(localLogicFilePath)

        (scheduleName1, deviceNames1, problemType1, solutionsForSchedule1, \
           indexOrder1, exactLogic1, rangeLogic1, _, architectureName1) = logic1

        exactList = []

        solutionSummationSizes = [32,64,96,128,256,512,1024,2048,4096,8192,16384]

        for K in solutionSummationSizes:
            e = {"Exact" : [8192, 4096, 1, K]}
            exactList.append(e)

        libraryPath = libPath
        clientBuildDir = os.path.join(outputPath, "client")
        problemTypeObj1 = problemType1.state   

        problemSizes = ProblemSizes(problemTypeObj1, exactList)
        dataPath = ensurePath(os.path.join(outputPath, logicFileStem, "data"))
        configFilePath = ensurePath(os.path.join(outputPath, logicFileStem, "configs"))
        dataFilePath = os.path.join(dataPath, "benchmark.csv")
        configFile = os.path.join(configFilePath, "ClientParameters.ini")
        scriptPath = ensurePath(os.path.join(outputPath, logicFileStem, "script"))
        ClientWriter.CreateBenchmarkClientParametersForSizesP(libraryPath, problemSizes, dataFilePath, configFile, problemTypeObj1)
        ClientWriter.runNewClient(scriptPath, configFile, clientBuildDir)


        tensileLibraryFile = os.path.join(libPath, "library", "TensileLibrary.yaml")

        stream = open(tensileLibraryFile, "r")
        tensileLibrary = yaml.load(stream, yaml.SafeLoader)
        stream.close()

        libSolutions = tensileLibrary["solutions"]

        mapper={}
        for s in libSolutions:
            key=s["name"]
            value=s["info"]["SolutionNameMin"]
            mapper[key]=value

        data_df=pd.read_csv(dataFilePath)
        working_data = data_df.rename(str.strip,axis='columns').rename(columns=mapper)

        index_keys = working_data.SizeL.unique()
        solutionsDF = working_data.filter(like='Cij')
        perf_max = solutionsDF.max().max().item()
    
        for s in solutionsForSchedule1:
            s_state = s._state
            solution_name = s_state["SolutionNameMin"]
            perf_raw = working_data[solution_name] 
            perf = (1000*index_keys) / perf_raw
            model = np.polyfit(x=index_keys, y=perf, deg=1)
            slope = model[0].item()
            intercept = model[1].item()
            #perf_max = perf_raw.max().item()
            linearModel = {"slope": slope, "intercept": intercept, "max": perf_max}
        
            s["LinearModel"] = deepcopy(linearModel)

            isa = s_state["ISA"]
            s_state["ISA"] = list(isa)

        exactLogic1 = {}
        for e in exactLogic:
            exactLogic1[tuple(e[0])] = e[1]

        logicTuple1 = (problemType1, solutionsForSchedule1, indexOrder1, exactLogic1, rangeLogic1)
        LibraryIO.configWriter("yaml").writeLibraryLogicForSchedule(finalPath, \
            scheduleName1, architectureName1, \
            deviceNames1, logicTuple1)

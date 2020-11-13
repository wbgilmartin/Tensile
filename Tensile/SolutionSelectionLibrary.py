################################################################################
# Copyright 2016-2020 Advanced Micro Devices, Inc. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell cop-
# ies of the Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IM-
# PLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNE-
# CTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
################################################################################

import sys

from .Common import printExit
from .CSVReader import readCSV
from .SolutionStructs import Solution

import csv

def getSummationKeys(header):
  keys=[]
  for i in range(7, len(header)):
    keystr = header[i].split("=")[1].strip()
    key = int(keystr)
    keys.append(key)
  return keys

def makeKey(row):
  key=row[3]
  for i in range(4, 7):
    key += "_%s" % row[i].strip()
  return key

def getSolutionBaseKey (solution):

  macroTile0 = solution["MacroTile0"]
  macroTile1 = solution["MacroTile1"]
  globalSplitU = solution["GlobalSplitU"]
  localSplitU = solution["WorkGroup"][2]

  key = "%s_%s_%s_%s" % (macroTile0, macroTile1, localSplitU, globalSplitU)

  return key

def updateIfGT(theDictionary, theKey, theValue):
  if not theKey in theDictionary:
    theDictionary[theKey] = theValue
  else:
    theOldValue = theDictionary[theKey]
    if theValue > theOldValue:
      theDictionary[theKey] = theValue


def updateValidSolutions(validSolutions, analyzerSolutions, solutionMinNaming):
  solutionsStartIndex = len(analyzerSolutions)
  validSelectionSolutionsIncluded = []
  validSelectionSolutionsRemainder = []
  selectionSolutionsIds = set([])
  for validSelectionSolution in validSolutions:
    (validSolution, validSolutionInfo) = validSelectionSolution
    if validSolution in analyzerSolutions:
      validExactSolutionIndex = analyzerSolutions.index(validSolution)
      selectionSolutionsIds.add(validExactSolutionIndex)
      validExactSolution = analyzerSolutions[validExactSolutionIndex]
      validSelectionSolutionsIncluded.append((validExactSolution, validSolutionInfo))
    else:
      validSelectionSolutionsRemainder.append(validSelectionSolution)

  selectionSolutions = []
  for i in range(0 ,len(validSelectionSolutionsIncluded)):
    validSelectionSolution = validSelectionSolutionsIncluded[i]
    (validSolution, validSolutionInfo) = validSelectionSolution
    validSolution["Ideals"] = validSolutionInfo
    analyzerSolutions.append(validSolution)

  solutionsStartIndex = len(analyzerSolutions)

  for i in range(0, len(validSelectionSolutionsRemainder)):
    validSelectionSolution = validSelectionSolutionsRemainder[i]
    (validSolution, validSolutionInfo) = validSelectionSolution
    selectionSolutionIndex = solutionsStartIndex + i
    selectionSolutionsIds.add(selectionSolutionIndex)
    validSolution["SolutionNameMin"] = Solution.getNameMin(validSolution, solutionMinNaming)
    validSolution["Ideals"] = validSolutionInfo
    selectionSolutions.append(validSolution)

  selectionSolutionsIdsList = list(selectionSolutionsIds)

  return selectionSolutionsIdsList


def analyzeSolutionSelectionOldClient( problemType, problemSizeGroups):

  dataFileNameList = []
  performanceMap = {}
  solutionsHash = {}

  for problemSizeGroup in problemSizeGroups:
    dataFileName = problemSizeGroup[3]
    dataFileNameList.append(dataFileName)
    solutionsFileName = problemSizeGroup[2]

    # solutions are already read and kept in problemSizeGroups, no need to call LibraryIO.readSolutions(solutionsFileName) again
    solutions = problemSizeGroup[4]
    if len(solutions) == 0:
      printExit("%s doesn't contains any solutions." % (solutionsFileName) )

    csvData = readCSV(dataFileName)

    rowIdx = 0
    summationKeys = None

    for row in csvData:
      if rowIdx == 0:
        print(rowIdx)
        summationKeys = getSummationKeys(row)
      else:
        if len(row) > 1:
          solution = solutions[rowIdx - 1]
          keyBase = makeKey(row)
          idx=7
          perfData = {}
          for summationKey in summationKeys:
            key = "%s_%s" % (keyBase,summationKey)
            value = float(row[idx])
            perfData[summationKey] = value
            idx+=1

            if not solution in solutionsHash:
              dataMap = {}
              solutionsHash[solution] = dataMap

            updateIfGT(solutionsHash[solution], summationKey, value)

            if not key in performanceMap:
              performanceMap[key] = (solution, value)
            else:
              _,valueOld = performanceMap[key]
              if value > valueOld:
                performanceMap[key] = (solution, value)
      rowIdx+=1

  validSolutions = []
  validSolutionSet = set([])

  for key in performanceMap:
    solution, _ = performanceMap[key]
    validSolutionSet.add(solution)

  for validSolution in validSolutionSet:
    dataMap = solutionsHash[validSolution]
    validSolutions.append((validSolution,dataMap))
  return validSolutions

def analyzeSolutionSelection(problemType, selectionFileNameList, numSolutionsPerGroup, solutionGroupMap, solutionsList):

  performanceMap = {}
  solutionsHash = {}

  totalIndices = problemType["TotalIndices"]
  summationIndex = totalIndices
  numIndices = totalIndices + problemType["NumIndicesLD"]
  problemSizeStartIdx = 1
  totalSizeIdx = problemSizeStartIdx + numIndices
  solutionStartIdx = totalSizeIdx + 1
  for fileIdx in range(0, len(selectionFileNameList)):
    solutions = solutionsList[fileIdx]
    selectionFileName = selectionFileNameList[fileIdx]
    numSolutions = numSolutionsPerGroup[fileIdx]
    rowLength = solutionStartIdx + numSolutions
    solutionBaseKeys = []

    for solution in solutions:
      baseKey = getSolutionBaseKey(solution)
      solutionBaseKeys.append(baseKey)

    selectionfFile = open(selectionFileName, "r")
    csvFile = csv.reader(selectionfFile)

    firstRow = 0
    for row in csvFile:
      if firstRow == 0:
        firstRow += 1
      else:
        sumationId = row[summationIndex].strip()

        solutionIndex = 0
        for i in range(solutionStartIdx, rowLength):
          baseKey = solutionBaseKeys[solutionIndex]
          key = "%s_%s" % (baseKey, sumationId)
          solution = solutions[solutionIndex]
          solutionIndex += 1
          value = float(row[i])
          if not solution in solutionsHash:
            dataMap = {}
            solutionsHash[solution] = dataMap

          updateIfGT(solutionsHash[solution], sumationId, value)
          if not key in performanceMap:
            performanceMap[key] = (solution, value)
          else:
            _,valueOld = performanceMap[key]
            if value > valueOld:
              performanceMap[key] = (solution, value)


  validSolutions = []
  validSolutionSet = set([])

  for key in performanceMap:
    solution, _ = performanceMap[key]
    validSolutionSet.add(solution)

  for validSolution in validSolutionSet:
    dataMap = solutionsHash[validSolution]
    validSolutions.append((validSolution,dataMap))

  return validSolutions

def analyzeSolutionSelectionForMetric(problemType, selectionFileNameList, numSolutionsPerGroup, solutionGroupMap, solutionsList):

  performanceMap = {}
  solutionsHash = {}

  totalIndices = problemType["TotalIndices"]
  summationIndex = totalIndices
  numIndices = totalIndices + problemType["NumIndicesLD"]
  problemSizeStartIdx = 1
  totalSizeIdx = problemSizeStartIdx + numIndices
  solutionStartIdx = totalSizeIdx + 1
  validSolutions = []
  for fileIdx in range(0, len(selectionFileNameList)):
    solutions = solutionsList[fileIdx]
    selectionFileName = selectionFileNameList[fileIdx]
    numSolutions = numSolutionsPerGroup[fileIdx]
    rowLength = solutionStartIdx + numSolutions
    solutionBaseKeys = []

    for solution in solutions:
      #baseKey = getSolutionBaseKey(solution)
      macroTile0 = solution["MacroTile0"]
      macroTile1 = solution["MacroTile1"]
      globalSplitU = solution["GlobalSplitU"]
      wg0 = solution["WorkGroup"][0]
      wg1 = solution["WorkGroup"][1]
      localSplitU = solution["WorkGroup"][2]
      depthU = solution["DepthU"]
      #baseKey = "%s_%s_%s_%s_%s_%s_%s" % (macroTile0, macroTile1, wg0, wg1, localSplitU, globalSplitU, depthU)
      baseKey = "%s_%s_%s_%s" % (macroTile0, macroTile1, wg0, wg1)

      solutionBaseKeys.append(baseKey)

    selectionfFile = open(selectionFileName, "r")
    csvFile = csv.reader(selectionfFile)

    firstRow = 0
    #keySizeMap = {}
    #bestSolutionMap = {}
    for row in csvFile:
      if firstRow == 0:
        firstRow += 1
      else:
        sumationId = row[summationIndex].strip()
        size = row[1:5]
        sizeId = (int(size[0].strip()),int(size[1].strip()),int(size[2].strip()),int(size[3].strip()))
        sizeKey = "%s_%s_%s_%s" % (sizeId[0], sizeId[1], sizeId[2], sizeId[3])
        #keySizeMap[key] = sizeId
        solutionIndex = 0
        #bestSolution = None
        #bestValue = sys.float_info.max
        #bestSize = None
        #bestKey = None
        #bestParams = None
        for i in range(solutionStartIdx, rowLength):
          #baseKey = solutionBaseKeys[solutionIndex]
          baseKey = solutionBaseKeys[solutionIndex]
          #key = "%s_%s" % (baseKey, sumationId)
          problemKey = "%s_%s" % (baseKey, sizeKey)

          #print ("The problem key is: %s" % problemKey)
          #keySizeMap[key] = sizeId
          solution = solutions[solutionIndex]

          #macroTile0 = solution["MacroTile0"]
          #macroTile1 = solution["MacroTile1"]
          #globalSplitU = solution["GlobalSplitU"]
          #localSplitU = solution["WorkGroup"][2]


          solutionIndex += 1
          value = float(row[i])
          if not solution in solutionsHash:
            dataMap = {}
            solutionsHash[solution] = dataMap
          #  bestKey = problemKey
          #  bestSize = sizeId
          #if bestValue > value:
          #  bestSolution = solution
          #  bestValue = value
          #  bestKey = problemKey
          #  bestSize = sizeId

          solutionsHash[solution][sumationId] = value

          #if value < bestValue:
          #  bestSolution = solution
          #  bestValue = value
          #  bestSize = bestSize
          #  bestKey = problemKey
          #updateIfGT(solutionsHash[solution], sumationId, value)
          #updateIfGT(solutionsHash[solution], sizeId, value)
          #if not key in performanceMap:
          if not problemKey in performanceMap:
            performanceMap[problemKey] = (solution, value, sizeId)
            print ("in compute loop: %s" % problemKey)
          else:
            _,valueOld,_ = performanceMap[problemKey]
            if value > valueOld:
              performanceMap[problemKey] = (solution, value, sizeId)
              print ("in compute loop: %s" % problemKey)
        #performanceMap[key] = (bestSolution, bestValue)
        #validSolutions.append((bestSolution, solutionsHash[bestSolution], sizeId))
        #bestSolutionMap[bestKey] = (bestSize, bestSolution, bestValue)
          #if not problemKey in bestSolutionMap:
          #  bestSolutionMap[problemKey] = (solution, value )

  #validSolutions = []
  #validSolutionSet = set([])

  for key in performanceMap:

    print ("int Construction loop: %s" % key)
  #for key in bestSolutionMap:
    #validSolution, _ = performanceMap[key]
    validSolution, _, validSize = performanceMap[key]
    #validSize, validSolution, _ = bestSolutionMap[key]
    dataMap = solutionsHash[validSolution]
    #validSize = keySizeMap[key]
    macroTile0 = validSolution["MacroTile0"]
    macroTile1 = validSolution["MacroTile1"]
    globalSplitU = validSolution["GlobalSplitU"]
    localSplitU = validSolution["WorkGroup"][2]
    validRep = (validSize[0],validSize[1], validSize[2], validSize[3], macroTile0, macroTile1, globalSplitU, localSplitU)
    #validParams = (macroTile0, macroTile1, globalSplitU, localSplitU)
    #validSolutions.append((validSolution, dataMap, validSize, validParams))
    validSolutions.append((validSolution, dataMap, validRep))
  #  #validSolutionSet.add(solution)

  #for validSolution in validSolutionSet:
  #  dataMap = solutionsHash[validSolution]
  #  validSolutions.append((validSolution,dataMap))

  return validSolutions


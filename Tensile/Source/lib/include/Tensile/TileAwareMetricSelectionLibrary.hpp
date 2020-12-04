/*******************************************************************************
 *
 * MIT License
 *
 * Copyright 2019-2020 Advanced Micro Devices, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 *******************************************************************************/

#pragma once

#include <set>
#include <vector>

#include <Tensile/Debug.hpp>
#include <Tensile/Properties.hpp>
#include <Tensile/Utils.hpp>

#include <Tensile/PropertyMatching.hpp>

namespace Tensile
{
    /**
 * \ingroup SolutionLibrary
 */
    struct TileAwareMetricSolutionTableEntry
    {
        std::vector<size_t> key;
        int                 value;
    };

    //template <typename MySolution>
    struct TileAwareMetricModelTableEntry
    {
        //std::vector<size_t>         key;
        //std::shared_ptr<MySolution> solution;
        int                         solution_id;
        //std::vector<double>         problem;
        std::vector<size_t>         problem;
    };

    /**
 * \ingroup SolutionLibrary
 *
 * Compares the tile sizes of each kernel, the dimensions of the problem,
 * and the number of compute units on the target GPU to select a kernel
 * that fits the best on the GPU with the lowest amount of waste
 * ("granularity loss").
 */
    template <typename MyProblem, typename MySolution = typename MyProblem::Solution>
    struct TileAwareMetricSelectionLibrary : public SolutionLibrary<MyProblem, MySolution>
    {
        //std::map<int, std::shared_ptr<MySolution>>              solutions;
        std::map<int, std::shared_ptr<MySolution>>                solutions;
        std::map<std::vector<size_t>, int>                        exactMap;
        std::vector<TileAwareMetricModelTableEntry>               modelProblems;
        //std::vector<TileAwareMetricModelTableEntry>               modelProblems;
        //std::map<std::vector<size_t>, int>                        modelProblems;

        static std::string Type()
        {
            return "TileAwareMetricSelection";
        }
        virtual std::string type() const override
        {
            return Type();
        }
        virtual std::string description() const override
        {
            std::string rv = this->type();

            return rv;
        }

        virtual std::shared_ptr<MySolution> findBestSolution(MyProblem const& problem,
                                                             Hardware const& hardware,
                                                             double* fitness = nullptr) const override
        {
            const bool debug = Debug::Instance().printPropertyEvaluation();

            std::vector<size_t> key;
            size_t              M = problem.freeSizeA(0);
            key.push_back(M);
            size_t N = problem.freeSizeB(0);
            key.push_back(N);
            size_t NumBatches = problem.batchSize(0);
            key.push_back(NumBatches);
            size_t K = problem.boundSize(0);
            key.push_back(K);

            auto exactMatch = exactMap.find(key);
            if(exactMatch != this->exactMap.end())
            {
                int index = exactMatch->second;

                auto rv = solutions.at(index);

                if(debug)
                {
                    std::cout << "Exact match: " << rv->description();
                    rv->problemPredicate->debugEval(problem, std::cout);
                    std::cout << std::endl;
                    rv->hardwarePredicate->debugEval(hardware, std::cout);
                    std::cout << std::endl;
                }

                if((*rv->problemPredicate)(problem) && (*rv->hardwarePredicate)(hardware))
                {
                    return rv;
                }
                else if(debug)
                {
                    std::cout << "Predicate failure" << std::endl;
                }
            }

            double                      bestDistance = std::numeric_limits<double>::max();
            std::shared_ptr<MySolution> bestSolution;

            ContractionSolution::TAMetricProblemScore bestppReference;
            ContractionSolution::TAMetricProblemScore bestpp;

            //auto it = modelProblems.begin();


            //std::map<std::vector<size_t>, int>::iterator it;

            //while(it != modelProblems.end())

            for (auto it = exactMap.begin(); it != exactMap.end(); ++it)
            {
                std::vector<size_t> model_size = it->first;
                //int solution_index = it->second;

                //size_t model_M         = (size_t)it->problem[0];
                //size_t model_N         = (size_t)it->problem[1];
                //size_t model_batchSize = (size_t)it->problem[2];
                //size_t model_K         = (size_t)it->problem[3];

                size_t model_M         = model_size[0];
                size_t model_N         = model_size[1];
                size_t model_batchSize = model_size[2];
                size_t model_K         = model_size[3];

                //std::cout << "this is a test print me." << std::endl;
                //size_t solution_id = it->solution_id;
                size_t solution_id = it->second;

                auto slnIter = solutions.find(solution_id);
                if(slnIter == solutions.end())
                {
                     //iot::setError(io, concatenate("Invalid solution index: ", index));
                     std::cout << "invalid solution index" << std::endl;
                }
                else
                {
                    auto solution = slnIter->second;
                    //lib.solutions.insert(std::make_pair(index, solution));
                //}

                  //double slope = solution->linearModel["slope"];

                  //std::cout << "The slope is " << slope << std::endl;

                  ContractionSolution::TAMetricProblemScore ppReference
                      = solution->computeProblemScore(
                          hardware, model_M, model_N, model_K, model_batchSize, 0, 0, 0, 0);

                  //if(debug) {
                  //   std::cout << "granulatity for reference: " << ppReference << std::endl;
                  //}

                  ContractionSolution::TAMetricProblemScore pp
                      = solution->computeProblemScore(hardware, M, N, K, NumBatches, 0, 0, 0, 0);
                  //if(debug) {
                  //   std::cout << "granulatity for problem: " << pp << std::endl;
                  //}

                  it++;

                  double metric = 0.0; //std::numeric_limits<double>::max();
  
                  double tile0GranularityDim = abs(log(ppReference.tile0Granularity) - log(pp.tile0Granularity));
                  metric = tile0GranularityDim; 

                  double tile1GranularityDim = abs(log(ppReference.tile1Granularity) - log(pp.tile1Granularity));
                  metric += tile1GranularityDim;

                  double natCuGranularityDim = abs(log(ppReference.natCuGranularity) - log(pp.natCuGranularity));
                  metric += natCuGranularityDim;

                  double suCuGranularityDim = abs(log(ppReference.suCuGranularity) - log(pp.suCuGranularity));
                  metric += suCuGranularityDim;

                  double suWaveGranularityDim = abs(log(ppReference.suWaveGranularity) - log(pp.suWaveGranularity));
                  metric += suWaveGranularityDim;

                  double natTilesPerCuDim = abs(log(ppReference.natTilesPerCu) - log(pp.natTilesPerCu));
                  metric += natTilesPerCuDim;

                  double suTilesPerCuDim = abs(log(ppReference.suTilesPerCu) - log(pp.suTilesPerCu));
                  metric += suTilesPerCuDim;

                  double summationPerformanceDim = abs(ppReference.summationPerformance - pp.summationPerformance);
                  metric += summationPerformanceDim;
                  if(metric < bestDistance)
                  {
                      bestDistance = metric;
                      bestSolution = solution;
                      bestppReference = ppReference;
                      bestpp = pp;
                  }
                }
            }

            /*double tile0GranularityDim = abs(log(ppReference.tile0Granularity) - log(pp.tile0Granularity));
                  if(debug) {
                      std::cout << " tile0GranularityDim=" << tile0GranularityDim << std::endl;
                  }
                  metric = abs(tile0GranularityDim; 
                  double tile1GranularityDim = abs(log(ppReference.tile1Granularity) - log(pp.tile1Granularity));
                  if(debug) {
                      std::cout << " tile1GranularityDim=" << tile0GranularityDim << std::endl;
                  }
                  metric += abs(tile1GranularityDim;
                  double natCuGranularityDim = abs(log(ppReference.natCuGranularity) - log(pp.natCuGranularity));
                  if(debug) {
                      std::cout << " natCuGranularityDim=" << tile0GranularityDim << std::endl;
                  }
                  metric += abs(natCuGranularityDim;
                  double suCuGranularityDim = abs(log(ppReference.suCuGranularity) - log(pp.suCuGranularity));
                  if(debug) {
                      std::cout << " suCuGranularityDim=" << tile0GranularityDim << std::endl;
                  }
                  metric += abs(suCuGranularityDim;
                  double suWaveGranularityDim = abs(log(ppReference.suWaveGranularity) - log(pp.suWaveGranularity));
                  if(debug) {
                      std::cout << " suWaveGranularityDim=" << tile0GranularityDim << std::endl;
                  }
                  metric += abs(suWaveGranularityDim;
                  double natTilesPerCuDim = abs(log(ppReference.natTilesPerCu) - log(pp.natTilesPerCu));
                  if(debug) {
                      std::cout << " natTilesPerCuDim=" << tile0GranularityDim << std::endl;
                  }
                  metric += natTilesPerCuDim;
                  double suTilesPerCuDim = abs(log(ppReference.suTilesPerCu) - log(pp.suTilesPerCu));
                  if(debug) {
                      std::cout << " suTilesPerCuDim=" << tile0GranularityDim << std::endl;
                  }
                  metric += suTilesPerCuDim;
                  double summationPerformanceDim = abs(ppReference.summationPerformance - pp.summationPerformance);
                  if(debug) {
                      std::cout << " summationPerformanceDim=" << tile0GranularityDim << std::endl;
                  }
                  metric += summationPerformanceDim;
                  if(debug) {
                      std::cout << " summationPerformanceDim=" << tile0GranularityDim << std::endl;
                  }*/

            if (debug) {
                if(debug) {
                      std::cout << " best distance=" << bestDistance << std::endl;
                  }
            }
            if(debug) {
                     std::cout << "granulatity best reference: " << bestppReference << std::endl;
                     std::cout << "granularity best solution:" << bestpp << std::endl;
            }
            return bestSolution;
        }

        virtual SolutionSet<MySolution> findAllSolutions(MyProblem const& problem,
                                                         Hardware const&  hardware) const override
        {
            bool debug = Debug::Instance().printPropertyEvaluation();

            SolutionSet<MySolution> rv;

            for(auto const& row : solutions)
            {
                if(debug)
                {
                    std::cout << row.second->description() << ": ";
                }

                if((*row.second->problemPredicate)(problem)
                   && (*row.second->hardwarePredicate)(hardware))
                {
                    rv.insert(row.second);

                    if(debug)
                        std::cout << " Works";
                }
                else if(debug)
                {
                    if(debug)
                        std::cout << " Predicate failed";
                }

                if(debug)
                {
                    row.second->problemPredicate->debugEval(problem, std::cout);
                    std::cout << std::endl;
                    row.second->hardwarePredicate->debugEval(hardware, std::cout);
                    std::cout << std::endl;
                }
            }

            return rv;
        }
    };
} // namespace Tensile



import os
import sys
import random as rn




#f = open("demofile2.txt", "a")
#f.write("Now the file has more content!")
#f.close()


#f = open("demofile3.txt", "w")
#f.write("Woops! I have deleted the content!")
#f.close()


#File_object.writelines(L) for L = [str1, str2, str3] 
#"RegisterPool::remove(%u,%u) pool[%u](%s)
lineFormat = "- { rocblas_function: \"rocblas_sgemm\", transA: 'N', transB: 'N', M: %s, N: %s, K: %s, lda: %s, ldb: %s, ldc: %s, cold_iters: 2, iters: 10 }\n"
#exactFormat = "      - Exact: [%s, %s, %s, %s]\n"
exactFormat = " - Exact: [%s, %s, %s, %s]\n"



def formatSizeDef(m, n, k):
    line = lineFormat % (m, n, k, m, k, m)
    return line

def formatExactDef(m, n, b, k):
    line = exactFormat % (m, n, b, k)
    return line

def GenerateSizes(args):

    nexact = 20
    ntest = 200

    exactSizeFile = args[0]
    testSizeFile = args[1]
#size_list = [[1024, 1264, 1, 345],
#            [1025, 1064, 1, 148],
#            [2450, 512, 1, 1023],
#            [2345, 2222, 1, 345]]

    rangeM = [2048, 2096]
    rangeN = [2048, 2096]
    rangeK = [128, 512]
    #kvalues = [32, 64, 128, 256, 512, 1024, 2048, 4096]
    exact_size_lines = []
    i = 0
    b = 1
    while i < nexact:
        m = rn.randint(rangeM[0], rangeM[1])
        n = rn.randint(rangeN[0], rangeN[1])
        k = rn.randint(rangeK[0], rangeK[1])
        line = formatExactDef(m, n, b, k)
        exact_size_lines.append(line)
        #for k in kvalues:
        #    line = formatExactDef(m, n, b, k)
        #    exact_size_lines.append(line)
        i = i + 1

    f = open(exactSizeFile, "w")
    f.writelines(exact_size_lines)
    f.close()

    test_size_lines = []    
    i = 0
    while i < ntest:
        m = rn.randint(rangeM[0], rangeM[1])
        n = rn.randint(rangeN[0], rangeN[1])
        k = rn.randint(rangeK[0], rangeK[1])
        line = formatSizeDef(m, n, k)
        test_size_lines.append(line)
        #for k in kvalues:
        #    line = formatSizeDef(m, n, k)
        #    test_size_lines.append(line)
            
        i = i + 1

    f = open(testSizeFile, "w")
    f.writelines(test_size_lines)
    f.close()
#size_list = []

#bSize = 1

#for i in range(64, 128, 1):
#    size = [1024, 2048, bSize, i] 
#
#    size_list.append(size)

#  sizeDefFile = "/home/billg/amd/wbgilmartin/tasks/tile_aware_metric/tensile/tensile_tam_parts_9m/scripts/sizes_run.yaml"
#  sizeDefTestFile = "/home/billg/amd/wbgilmartin/tasks/tile_aware_metric/tensile/tensile_tam_parts_9m/scripts/sizes_test.yaml"

#lines = []
#for size in size_list:
#    m = size[0]
#    n = size[1]
#    b = size[2]
#    k = size[3]
#    #line = formatSizeDef(m, n, k)
#    line = formatExactDef(m, n, b, k)
#    lines.append(line)

#f = open(sizeDefFile, "w")
#f.writelines(lines)
#f.close()

#lines = []
#for size in size_list:
#    m = size[0]
#    n = size[1]
#    b = size[2]
#    k = size[3]
#    line = formatSizeDef(m, n, k)
#    lines.append(line)

#f = open(sizeDefTestFile, "w")
#f.writelines(lines)
#f.close()

 
if __name__ == "__main__":
    GenerateSizes(sys.argv[1:])
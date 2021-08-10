import math
import random
import numpy as np
import pandas as pd
import pymongo
import config

conn = pymongo.MongoClient(config.MONGO_ADDR)
db = conn[config.MONGO_AUTH]

def simple(s, lb, ub, d):
    ns_tmp = s
    for i in range(0, d):
        ns_tmp[i] = abs(ns_tmp[i])
        # if ns_tmp[i] < lb:
        #     ns_tmp[i] = lb
        # if ns_tmp[i] > ub:
        #     ns_tmp[i] = ub
    return ns_tmp

def levy(d):
    lamda = 1.5
    sigma = (math.gamma(1 + lamda) * math.sin(math.pi * lamda / 2) / (
    math.gamma((1 + lamda) / 2) * lamda * (2 ** ((lamda - 1) / 2)))) ** (1 / lamda)
    # sigma = 0.6965745025576968
    u = np.random.randn(1, d) * sigma
    v = np.random.randn(1, d)
    step = u / abs(v) ** (1 / lamda)
    return 0.01 * step

def findMin(initialFungUji):
    for x in range(1, len(initialFungUji)):
        tmp = initialFungUji[0]
        minArr = initialFungUji[0]

        if np.all([initialFungUji[x][0] < tmp[0], initialFungUji[x][1] < tmp[1]]):
            minArr = initialFungUji[x]
            tmp = initialFungUji[x]
    return initialFungUji.index(minArr), minArr

def fungUji(constant):
    a = constant[0]
    b = constant[1]
    c = constant[2]
    d = constant[3]
    total_mre_tdev = 0
    total_mre_effort = 0
    count = 0
    MMRE_TDEV = 0
    MMRE_EFFORT= 0
    tdev_list = []
    effort_list = []

    datasets = db["datasets"].find({'name': 'nasa93'})
    for dataset in datasets:
        EM = dataset["EM"]
        LOC = dataset["loc"]
        A_TD = dataset["A_TD"]
        AE = dataset["AE"]
        PM = a * (LOC**b) * EM
        TD = c * (PM**d)
        mre_tdev = (abs(A_TD-TD / A_TD))*100
        mre_effort = (abs(AE-PM / AE))*100
        tdev_list.append(mre_tdev)
        effort_list.append(mre_effort)
        total_mre_tdev += mre_tdev
        total_mre_effort += mre_effort
        count += 1
    MMRE_TDEV = total_mre_tdev / count
    MMRE_EFFORT = total_mre_effort / count
    
    pd_data = {"MRE_TDEV": tdev_list, "MRE_EFFORT": effort_list}
    df = pd.DataFrame(pd_data)
    
    return [MMRE_TDEV, MMRE_EFFORT]

# ==========================================BAT ALGO====================================================
#Sol = Posisi kelelawar
#S = Posisi kelelawar sementara
def algoKelelawar(n, d, limit):
#     n => population of bats
#     A => loudness
#     r = pulse rate
    A = 3
    r = 4
    
    Qmin = 0 # lowest frequency
    Qmax = 2 # highest frequency
    
    #Loop parameter
    limit = 10 #loop limit
    N_iter = 0     #number of iterations
    
    #d = search space dimension
    
    #initial array of values
    Q = np.zeros(n) #frequency each bat
    v = np.zeros((n, d)) #the speed of each bat in each dimension
    
    #assignment of initial values in bat populations (solution)
#     Sol = np.zeros((n, d))
    Sol = np.random.randint(5, size=(n, d))
    S = np.zeros((n, d))
    Fitness = []
    
    #initial best solution
    initialFungUji = []
    for i in range(len(Sol)):
        initialFungUji.append(fungUji(Sol[i, :]))
        Fitness.append(fungUji(Sol[i, :]))
        
#     fmin = min(initialFungUji)
#     fminIndex = initialFungUji.index(fmin)
#     best = Sol[fminIndex, :]
    fminIndex, fmin = findMin(initialFungUji)
    best = Sol[fminIndex, :]
    
    #The application of bat algorithm
    while N_iter < limit:
        
        #loops imposed all bats
        for i in range(n):
            beta = np.random.rand()
            Q[i] = Qmin + (Qmax-Qmin) * beta
            v[i, :] = v[i, :] + (Sol[i, :] - best) * Q[i] #*
            S[i, :] = Sol[i, :] + v[i, :]
            
             #pulse rate effect
            alpha = 0.01
            if np.random.rand() > r:
                S[i, :] = best + alpha * np.random.randn(1, d)
        
            S[i,] = simple(S[i,], 0.001, 3.0, 4)
            Fnew = fungUji(S[i, ])
        
            if Fnew[0] <= Fitness[i][0] and Fnew[1] <= Fitness[i][1] and np.random.rand() < A:
                Sol[i, :] = S[i, :].copy()
                Fitness[i] = Fnew.copy()
            
            
            #update the smallest / best test function value
            if Fnew[0] < fmin[0] and Fnew[0] < fmin[0]:
                best = S[i, :].copy()
                fmin = Fnew.copy()
        N_iter = N_iter + 1
    print(best)
    print(fmin)
    return best, fmin

# ==================================FPA ALGO=============================================================
#n => number of population
#d => number of dimension
#p => probability switch p (0->1)
def fpaAlgorithm(n, d, N_iter):
    #     Sol = np.zeros((n, d))
    Sol = np.random.randint(1,5, size=(n, d))
    S = np.zeros((n, d),dtype=float)
#     Fitness = np.full(n,99.99)
    Fitness = []
    
    #initial best solution
    initialFungUji = []
    for i in range(len(Sol)):
        initialFungUji.append(fungUji(Sol[i, :]))
        Fitness.append(fungUji(Sol[i, :]))
        
#     fmin = min(initialFungUji)
#     fminIndex = initialFungUji.index(fmin)
    fminIndex, fmin = findMin(initialFungUji)
    best = Sol[fminIndex, :]

    #S = Sol.copy()
    
    for t in range(0, N_iter):
        for i in range(0, n):
            p=0.8-0.7*t/N_iter
            if np.random.random() < p:
                L = levy(d)
                S[i, :] = Sol[i, :] + L * (Sol[i, :] - best)
            else:
                epsilon = np.random.random_sample()
                #jk -> Find random flowers in the neighbourhood
                jk = np.random.permutation(n)
                S[i, :] = S[i, :] + epsilon * (Sol[jk[0], :] - Sol[jk[1], :])
            S[i,] = simple(S[i,], 0.001, 3.0, 4)
            Fnew = fungUji(S[i, :])
            
            if Fnew[0] <= Fitness[i][0] and Fnew[1] <= Fitness[i][1]:
                Sol[i, :] = S[i, :].copy()
                Fitness[i] = Fnew.copy()

            if Fnew[0] < fmin[0] and Fnew[1] < fmin[1]:
                best = S[i, :].copy()
                fmin = Fnew.copy()
    print(best)
    print(fmin)
    return best, fmin

# ==============================================HYBRID ALGO ====================================
#Sol = Posisi kelelawar
#S = Posisi kelelawar sementara
#A dan r masih konstan
def baFpa(n, d, limit):
#     n => population of bats
#     A => loudness
#     r = pulse rate
    A = 3
    r = 4
    
    Qmin = 0 # lowest frequency
    Qmax = 2 # highest frequency
    
    fmin_FPA = 0.0
    fmin_BAT = 0.0
    
    #Loop parameter
    limit = 20 #loop limit
    N_iter = 0     #number of iterations
    
    #d => search space dimension
    
    #initial array of values
    Q = np.zeros(n) #frequency each bat
    v = np.zeros((n, d)) #the speed of each bat in each dimension
    
    #assignment of initial values in bat populations (solution)
#     Sol = np.random.randint(1, 5, size=(n, d))
#     S = np.random.randint(1, 5, size=(n, d))
    Sol = np.random.uniform(1, 5, size=(n,d))
    S = np.random.uniform(1, 5, size=(n,d))
    Fitness = []
#     Fitness = np.full(n, (99999.999999))
    
    #initial best solution
    initialFungUji = []
    for i in range(len(Sol)):
        initialFungUji.append(fungUji(Sol[i, :]))
        Fitness.append(fungUji(Sol[i, :]))
        
#     fmin = min(initialFungUji)
#     fminIndex = initialFungUji.index(fmin)
#     best = Sol[fminIndex, :]
    fminIndex, fmin = findMin(initialFungUji)
    best = Sol[fminIndex, :]
    
    #The application of bat algorithm
    while N_iter < limit:
        
        #loops imposed all bats
        for i in range(n):
            beta = np.random.rand()
            Q[i] = Qmin + (Qmax-Qmin) * beta
            v[i, :] = v[i, :] + (Sol[i, :] - best) * Q[i] #*
            S[i, :] = Sol[i, :] + v[i, :]
            
             #pulse rate effect
            alpha = 0.01
            if np.random.rand() > r:
                S[i, :] = best + alpha * np.random.randn(1, d)
        
            S[i,] = simple(S[i,], 2.0, 2.0, 4)
            Fnew = fungUji(S[i, :])
            
            #Flying randomly
#             v[i, :] = v[i, :] + (Sol[i, :] - best) * Q[i] #*
#             S[i, :] = Sol[i, :] + v[i, :]
        
            if Fnew[0] <= Fitness[i][0] and Fnew[1] <= Fitness[i][1] and np.random.rand() < A:
                Sol[i, :] = S[i, :]
                Fitness[i] = Fnew
                
                #increase r[i] reduce A[i]
                #A[i] = alpha * A[i]
                #r[i] = r[i] * (1- math.exp(-1*gamma * N_iter)
                
            #=======================FPA ALGORITHM===================================
            S_FPA = Sol.copy()
            Sol_FPA = Sol.copy()
            Fnew_FPA = Fnew.copy()
            Fitness_FPA = Fitness.copy()
    
            for t in range(0, N_iter):
                for i in range(0, n):
                    p=0.8-0.7*t/N_iter
                    if np.random.random() < p:
                        L = levy(d)
                        S_FPA[i,] = Sol_FPA[i,] + L * (Sol_FPA[i,] - best)
                    else:
                        epsilon = np.random.random_sample()
                        #jk -> Find random flowers in the neighbourhood
                        jk = np.random.permutation(n)
                        S_FPA[i,] = S_FPA[i,] + epsilon * (Sol_FPA[jk[0],] - Sol_FPA[jk[1],])

                    S_FPA[i,] = simple(S_FPA[i,], 2.0, 2.0, 4)
            
                    Fnew_FPA = fungUji(S[i, :])
                    if Fnew_FPA[0] <= Fitness_FPA[i][0] and Fnew_FPA[1] <= Fitness_FPA[i][1]:
                        Sol_FPA[i, :] = S_FPA[i, :]
                        Fitness_FPA[i] = Fnew_FPA
            #=======================END FPA ALGORITHM===============================
            #=======================Start Find Best Position==============================
#             fmin_FPA = np.amin(Fitness_FPA)
#             fminFPAIndex = np.where(Fitness_FPA == np.amin(Fitness_FPA))
#             fmin_BAT = np.amin(Fitness)
#             fminBATIndex = np.where(Fitness == np.amin(Fitness))
            
            fminFPAIndex, fmin_FPA = findMin(Fitness_FPA)
            fminBATIndex, fmin_BAT = findMin(Fitness)
            
#             print("FPA: ",fmin_FPA, "Param: ", S_FPA[fminFPAIndex[0][0], :])
#             print("BAT: ", fmin_BAT, "Param : ", S[fminBATIndex[0][0], :])
            #update the smallest / best test function value
            if fmin_FPA[0] < fmin[0] and fmin_FPA[1] < fmin[1]:
                best = S_FPA[fminFPAIndex, :].copy()
                fmin = fmin_FPA.copy()
            if fmin_BAT[0] <= fmin[0] and fmin_BAT[1] <= fmin[1]:
                best = S[fminBATIndex, :].copy()
                fmin = fmin_BAT.copy()
#             print(best)
#             print(fmin)
            #=======================End Find Best Position==============================
#         print(best)
#         print(fmin)
        N_iter = N_iter + 1
    print(best)
    print(fmin)
    return best, fmin

# fungUji([2.94, 0.91, 3.67, 0.28])
# bat = algoKelelawar(4, 4, 10)
# fpa = fpaAlgorithm(4, 4, 10)
# hybrid = baFpa(4, 4, 10)
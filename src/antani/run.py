import os, sys, gzip, random, csv, json, datetime, re
import numpy as np
import pandas as pd
import scipy as sp
import matplotlib.pyplot as plt
sys.path.append(os.environ['LAV_DIR']+'/src/')
baseDir = os.environ['LAV_DIR']
import antani.etl as etl
import geomadi.graph_viz as g_v
import mallink.path_opt as p_o
import mallink.monte_carlo as m_c
import mallink.monte_markov as m_m
import mallink.rein_learn as r_l

import importlib

id_zone = "berlin"
version = "optEn"
conf = {"reset":True
        ,"cost_route":70.35,"cost_stop":.1,"max_n":50,"temp":.5,"link":5,"phantom":4,"cluster":False
        ,"moveProb":{"move":1,"distance":1,"markov":4,"extrude":3,"flat":1}
        ,"net_layer":[128,128],"load_model":"","init_chain":True}

# jobN = "job_s"+str(592)+"_v"+str(9)+"_sol"
# solJ = json.load(open(baseDir + "raw/opt/"+jobN+".json"))
# importlib.reload(etl)
# spotL, pathL = etl.routificFrame(solJ)
solJ = json.load(open(baseDir + "src/ui/antani_viz/data/sol_blank.json"))
spotL, pathL = etl.dict2frame(solJ)

jobN = "job_winter"
solD = json.load(open(baseDir+"raw/opt/"+jobN+".json","r"))
spotL, pathL, options = etl.inputRoutific(solD)

opsL = pd.DataFrame({"action":['collect','potential']})
pairL = pd.read_csv(baseDir+"gis/graph/"+"spot2spot.csv.gz",compression="gzip")
if conf['reset']:
    spotL['agent'] = 0
import importlib
importlib.reload(p_o)
importlib.reload(m_c)
importlib.reload(m_m)
importlib.reload(r_l)
importlib.reload(g_v)
conf['phantom'] = 0
mc = m_m.MonteMarkov(spotL,pathL=pathL,opsL=opsL,conf=conf)
mc.loop()
n_iter = 2001
for i in range(1,n_iter):
    status = mc.loop()
    if i%100 == 0:
        j = "%03d" % (i//100)
        spotL, pathL = mc.getPath()
        n = int(spotL.loc[spotL['agent']>0,'occupancy'].sum())
        print("energy %.2f stops %d" % (mc.En,n))
        print("saving pic " + j)
        fig, ax = plt.subplots(1,1)
        mc.plotState(ax)
        plt.tight_layout(pad=0.05,h_pad=0.05,w_pad=None,rect=None)
        plt.savefig(baseDir+"fig/route/"+'opt_'+j+'.png',figsize=(8,4),dpi=100)
        plt.close()
        if mc.completion > .99: break
        # route.to_csv(baseDir + "raw/opt/route.csv",index=False)

fig, ax = plt.subplots(1,3)
mc.plotHistory(ax[0])
mc.plotAcceptance(ax[1])
ax[1].set_title("acceptance rate")
mc.plotStrategy(ax[2])
ax[2].set_title("strategy")
plt.savefig(baseDir+"fig/route/"+'nrg.png',figsize=(12,6),dpi=100)
plt.close()
print('writing %s ' %(jobN+"_"+version))
spotL, pathL = mc.getPath()
#spotL, pathL = mc.spotL, mc.pathL
spotL.to_csv(baseDir + "raw/opt/sol_"+jobN+"_"+version+".csv",index=False)
summ = mc.printSummary()
summ['conf'] = conf
json.dump(summ,open(baseDir+"raw/opt/sol_"+jobN+"_"+version+".json","w"))
spotL.replace(float('nan'),'',inplace=True)
pathL.replace(float('nan'),'',inplace=True)
solD = {"spot":spotL.to_dict(orient="index"),"path":pathL.to_dict(orient="index")}
json.dump(solD,open(baseDir + "src/ui/antani_viz/data/sol_"+"latest.json","w"),indent=2)

if False:
    print('--------------------convert-routific--------------------------')
    jobN = "job_routific"
    jobN = "job_routific_small"
    for jobN in ["job_routific","job_routific_small"]:
        conf['phantom'] = 0
        conf['init_chain'] = False
        solJ = json.load(open(baseDir + "raw/opt/"+jobN+".json"))
        importlib.reload(etl)
        spotL, pathL = etl.routificFrame(solJ)
        mc = p_o.pathOpt(spotL,pathL=pathL,opsL=opsL,conf=conf)
        spotL = mc.spotL
        pathL = mc.pathL
        spotL.replace(float('nan'),'',inplace=True)
        solD = {"spot":spotL.to_dict(orient="index"),"path":pathL.to_dict(orient="index")}
        fName = re.sub("job_","sol_",jobN)
        json.dump(solD,open(baseDir + "src/ui/antani_viz/data/"+fName+".json","w"),indent=2)
    
if False:
    print('--------------------convert-files--------------------------')
    projDir = baseDir + "src/ui/antani_viz/data/"
    fL = os.listdir(projDir)
    fL = [x for x in fL if bool(re.search(".json",x))]
    importlib.reload(p_o)
    for f in fL:
        sol = json.load(open(projDir + f))
        spotL, pathL = etl.dict2frame(sol)
        mc = p_o.pathOpt(spotL,pathL=pathL,opsL=opsL,conf=conf)
        spotL, pathL = mc.getPath()
        spotL.replace(float('nan'),'',inplace=True)
        pathL.replace(float('nan'),'',inplace=True)
        solD = {"spot":spotL.to_dict(orient="index"),"path":pathL.to_dict(orient="index")}
        json.dump(solD,open(projDir+f,"w"),indent=2)

if False:
    route = mc.simplifyRoute(route)
    En = mc.calcEnergy(route)
    route1 = simplifyRoute(route,agentP)
    route2, En = tryMove(route,agentP,En,temp,conf)
    ax0 = g_v.graphRoute(route)
    ax0 = g_v.graphRoute(route1)
    plt.show()

if False:
    print('--------------------------test-etl------------------------')
    solR = json.load(open(baseDir + "src/antani/conf/job_routific_sol.json"))
    json.dump(solR,open(baseDir + "tmp.json","w"),indent=2)
    solJ = json.load(open(baseDir + "raw/opt/"+"job_winter"+".json"))
    importlib.reload(etl)
    spotL, pathL, options = etl.inputRoutific(solJ)
    spotL = spotL.head(10)
    spotL['agent'] = 1
    solR1 = etl.frameRoutific(spotL,pathL,solR.copy())
    json.dump(solR1,open(baseDir + "tmp.json","w"))

    print('--------------------------test-etl------------------------')
    importlib.reload(etl)
    solR = json.load(open(baseDir + "src/antani/conf/job_routific_sol.json"))
    solD = json.load(open(baseDir + "prod/antani/antani_viz/data/sol_latest.json"))
    spotL, pathL = etl.dict2frame(solD)
    pathL['x_end'] = 0
    pathL['y_end'] = 0
    pathL['id'] = pathL['agent']
    solR = etl.frameRoutific(spotL,pathL,solR)
    json.dump(solR,open(baseDir + "tmp.json","w"))
    
    importlib.reload(etl)
    sol = etl.to_json(solR)
    with open(baseDir + "tmp.json", 'w') as f:
        print(sol, file=f)
    

    
print('-----------------te-se-qe-te-ve-be-te-ne------------------------')


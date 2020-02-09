"""
path_opt:
Path optimization library
"""
import numpy as np
import pandas as pd
import scipy as sp
import matplotlib.pyplot as plt
import geomadi.graph_viz as g_v
import geomadi.lib_graph as l_g
from sklearn.cluster import KMeans
from scipy.cluster.hierarchy import fcluster
from scipy.cluster.hierarchy import dendrogram, linkage

def updatePath(spotL,pathL):
    agentG = spotL.groupby("agent").sum()
    agentA = spotL.groupby("agent").agg(np.mean)
    agentL = spotL.groupby("agent").agg(len)
    idx = agentG.index
    idxn = [x for x in idx if not x in pathL.index]
    pathL1 = pathL.tail(len(idxn))
    pathL1.index = idxn
    pathL1['agent'] = idxn
    pathL = pd.concat([pathL,pathL1])
    pathL['load'] = 0
    pathL.loc[idx,'distance'] = agentG['distance']
    pathL.loc[idx,'load'] = agentL['occupancy']
    pathL.loc[idx,'potential'] = agentG['potential']
    pathL.loc[idx,'duration'] = agentG['duration']
    pathL.loc[idx,"x"] = agentA['x']
    pathL.loc[idx,"y"] = agentA['y']
    pathL['completion'] = pathL['load']/pathL['capacity']
    pathL.replace(float('inf'),0.,inplace=True)
    pathL.replace(float('nan'),0.,inplace=True)
    spotL['agent'] = spotL['agent'].astype(int)
    pathL['agent'] = pathL['agent'].astype(int)
    return pathL

class pathOpt:
    """optimization of paths"""
    def __init__(self,spotL,pathL=None,opsL=None,pairL=None,conf=None):
        """initialize quantities"""
        if spotL.shape[0] == 0:
            print("---------------no-spot------------------")
            return False
        if pathL.shape[0] == 0:
            print("---------------no-path------------------")
            return False        
        if conf == None:
            conf = {"cost_route":70.35,"cost_stop":.1,"max_n":50,"temp":.5,"link":5,'phantom':4,'cluster':True
        ,"moveProb":{"move":1,"distance":1,"markov":4,"extrude":3,"flat":1}}
        self.conf = conf
        if not isinstance(opsL,pd.DataFrame):
            opsL = pd.DataFrame({"action":['collect','potential']})
        self.colorL = ['black','blue','red','green','brown','orange','purple','magenta','olive','maroon','steelblue','midnightblue','darkslategrey','crimson','teal','darkolivegreen']
        self.colorL = ["#B4aaaaf0","#8b122870","#6CAF3070","#F8B19570","#F6728070","#C06C8470","#6C5B7B70","#355C7D70","#99B89870","#2A363B70","#67E68E70","#9F53B570","#3E671470","#7FA8A370","#6F849470","#38577770","#5C527A70","#E8175D30","#47474730","#36363630","#A7226E30","#EC204930","#F26B3830","#F7DB4F30","#2F959930","#E1F5C430","#EDE57430","#F9D42330","#FC913A30","#FF4E5030","#E5FCC230","#9DE0AD30","#45ADA830","#54798030","#594F4F30","#FE436530","#FC9D9A30","#F9CDAD30","#C8C8A930","#83AF9B30"]
        self.checkInit(spotL.copy(),pathL.copy())
        self.phantom = 0
        self.completion = 0.
        self.opsL = opsL['action']
        self.loadRouted(pairL)
        self.calcDistance()
        self.updatePath()
        self.insertPhantom(n=conf['phantom'])
        if conf['cluster']: self.startPos()

    def checkInit(self,spotL,pathL):
        """check columns in initial data frame"""
        print('-------------check-init---------------')
        if not isinstance(pathL,pd.DataFrame):
            pathL = spotL.groupby("agent").sum().reset_index()
            pathL.index = pathL['agent']
        l1 = [x for x in ['duration','load','distance','agent','y','x','active','potential','occupancy','geohash'] if x not in spotL.columns]
        l2 = [x for x in ['agent','id','capacity','load','warehouse','x_start','y_start','x_end','y_end','lenght','distance','score','phantom','energy','t_start','t_end'] if not x in pathL.columns]
        if len(l1) != 0: print("replacing columns",l1)
        if len(l2) != 0: print("replacing columns",l2)
        for l in l1: spotL[l] = 0
        for l in l2: pathL[l] = 0
        pathL.loc[:,"color"] = self.colorL[:pathL.shape[0]]
        pathL.loc[:,"phantom"] = False
        spotL.index = spotL['geohash']
        spotL.index.names = ['index']
        spotL.replace(float('nan'),0.,inplace=True)
        if len(set(spotL.index)) != spotL.shape[0]:
            print("duplicated geohash entries")
            tL = ['occupancy','priority','distance','potential','load']
            occL = spotL[['geohash'] + tL].groupby('geohash').agg(sum)
            spotL = spotL.groupby('geohash').first().reset_index()
            spotL.index = spotL['geohash']
            #spotL = spotL.loc[~spotL.index.duplicated(keep='first')]
            for t in tL:
                spotL[t] = occL[t]
        spotL['agent'] = spotL['agent'].astype(int)
        pathL['agent'] = pathL['agent'].astype(int)
        self.spotL = spotL
        self.pathL = pathL
        
    def updateSys(self,route):
        """update system from accepted solution"""
        self.spotL = route
        self.updatePath()

    def updatePath(self):
        """update path frame from spot frame"""
        self.pathL = updatePath(self.spotL,self.pathL)
        pathv = self.pathL.loc[self.pathL['agent']>0]
        pathv = pathv.loc[~pathv['phantom']]
        self.completion = np.mean(pathv['completion'])
        
    def addScore(self):
        """add score value"""
        self.pathL['score'] = 0.
        pathL = self.pathL[self.pathL['agent'] > 0]
        wp = pathL['potential']/pathL['potential'].max()
        wl = 1.5 - pathL['distance']/pathL['distance'].max()
        wc = pathL['load']/pathL['capacity']
        wc = wc/wc.max()        
        pathL.loc[:,'score'] = wp*wl*wc
        self.pathL.loc[pathL.index,"score"] = pathL['score']
        
    def insertPhantom(self,n=0):
        """insert phantom agents"""
        if n == 0: return False
        pathS = self.pathL.tail(n).copy()
        nv = max(self.pathL['agent'])
        l = list(range(nv+1,nv+n+1))
        pathS.index = l
        pathS.loc[:,'agent'] = l
        pathS['phantom'] = True
        self.pathL = pd.concat([self.pathL,pathS])
        self.updatePath()
        self.pathL.loc[:,"color"] = self.colorL[:self.pathL.shape[0]]
        self.phantom = self.phantom + n
        self.agentL = list(self.pathL.index)
        print("inserting %d paths" % (n))
        print(l)
        return True

    def removePhantom(self,n=1):
        """remove phantom agent"""
        if self.phantom <= 0: return False
        pathv = self.pathL[pathL['agent'] > 0]
        enL = pathv['energy']
        enL = enL.sort_values()
        idx = enL[:n]
        for v in idx:
            self.pathL.drop(v,inplace=True)
            self.spotL.loc[self.spotL['agent']==v,'agent'] = 0
        self.phantom = self.phantom - n
        self.agentL = list(self.pathL.index)
        return True

    def swapPath(self,vp,vn):
        """remove phantom agent"""
        pathP = self.pathL.loc[vp]
        pathN = self.pathL.loc[vn]
        tmpP = pathP.copy()
        tmpN = pathN.copy()
        pathP.loc[:] = tmpN.values
        pathN.loc[:] = tmpP.values
        for i in ['agent','id','color']:
            pathP[i] = tmpP[i]
            pathN[i] = tmpN[i]
        self.pathL.loc[vn,:] = pathP.values
        self.pathL.loc[vp,:] = pathN.values
        self.spotL.loc[self.spotL['agent']==vp,"agent"] = vn
        self.spotL.loc[self.spotL['agent']==vn,"agent"] = vp
        print("phantom swap %d->%d" % (vp,vn))
        self.agentL = list(self.pathL.index)
        return True

    def swapPhantom(self):
        """look whether is convenient to swap a path"""
        if self.phantom <= 0: return False
        pathv = self.pathL[self.pathL['agent'] > 0]
        idx = pathv['phantom']
        pathP = pathv.loc[idx]
        pathN = pathv.loc[~idx]
        vp = np.random.choice(pathP.index)
        vn = np.random.choice(pathN.index)
        pathP = self.pathL.loc[vp]
        pathN = self.pathL.loc[vn]
        if pathP['energy'] < pathN['energy']: return False
        return swapPath(vp,vn)

    def getPath(self):
        """return path list without phantoms"""
        pathL = self.pathL.loc[~self.pathL['phantom']]
        # self.addScore()
        # self.pathL = self.pathL.sort_values('score')
        spotL = self.spotL.copy()
        # pathL = self.pathL.tail(-self.phantom)
        agentL = list(pathL.index)
        setL = [not x in agentL for x in spotL['agent']]
        spotL.loc[setL,"agent"] = 0
        return spotL, pathL

    def checkAllowed(self,v,p,s):
        """check if the move is allowed"""
        if self.isLog: print('%d) check allowed' % self.step)
        if v == 0 : return True
        o1 = self.pathL.loc[v,'load']
        o2 = self.pathL.loc[v,'capacity']
        o3 = self.spotL.loc[p,'occupancy']
        if o1 + o3 > o2: return False
        return True

    def calcDistance(self):
        """lookup distances and update data frames"""
        for v,g in self.spotL.groupby("agent"):
            if v == 0: continue
            idx = list(g.index)
            for j1,j2 in zip(idx[:-1],idx[1:]):
                self.spotL.loc[j1,'distance'] = self.distM.loc[j1,j2]
            self.spotL.loc[idx[-1],'distance'] = self.distM.loc[idx[0],idx[-1]]
        agentG = self.spotL.groupby("agent").agg(sum).reset_index()
        agentG.index = agentG['agent']
        return agentG

    def probNorm(self,p):
        """return a correct normalized probability"""
        p[p!=p] = 0.
        p = p.abs()
        p = p.replace(float('inf'),0.)
        p = p.replace(float('nan'),0.)
        if p.sum() > 0.: p = p/p.sum()
        else: p.loc[:] = 1./len(p)
        return p
        
    def probPath(self):
        """weight for favoring incomplete paths"""
        agentL = self.pathL[self.pathL['agent']>0]
        pv = agentL['load']/agentL['capacity']
        pv = 1.5 - pv
        return self.probNorm(pv)

    def simplifyRoute(self,route1,isPlot=False,isSingle=True):
        """sort route considering the shortest distance"""
        if sum(route1['agent']>0) == 0: route1
        distM = self.distM
        route = route1.copy()
        route.sort_values("agent",inplace=True)
        routeL = []
        route.loc[:,"distance"] = 0.
        for v,g in route.groupby("agent"):
            if v == 0:
                routeL.append(g)
                continue
            if not v in self.pathL['agent']:
                g['agent'] = 0
                routeL.append(g)
                continue
            agent = self.pathL.loc[v]
            pos = g[['x','y']]
            distM1 = distM.loc[g.index,g.index]
            tree = sp.spatial.KDTree(pos.values)
            nearest_dist, nearest_ind = tree.query(pos.values,k=2)
            l1, j = tree.query(agent[['x_start','y_start']])
            j = pos.iloc[j].name
            idx = sorted(list(g.index))
            distL = [0]
            id_sort = [j]
            for i in range(pos.shape[0]-1):
                idx = [x for x in idx if x != j]
                j1 = distM1.loc[j,idx].idxmin()
                distL.append(distM1.loc[j,j1])
                j = j1
                id_sort.append(j)
            l2 = distM1.loc[id_sort[0],id_sort[-1]]
            distL[0] = l2
            g.loc[id_sort,"distance"] = distL
            routeL.append(g.loc[id_sort,:])
            route = pd.concat(routeL)
        if isPlot:
            g_v.graphRoute(route)
            #plt.imshow(distM)
            plt.show()
        return route

    def startPos(self,isPlot=False,complete=False):
        """propose a start pos for each path"""
        print("clustering and adding a random agent")
        colL = ['x','y']#,'potential']
        pos = self.spotL[colL]
        n_clust = self.pathL.shape[0]
        min_clust = max(3.,np.mean(self.pathL['capacity']))
        n_clust = int(self.spotL.shape[0]/min_clust)
        route = self.spotL.copy()
        aid = self.pathL.index
        kmeans = KMeans(n_clusters=n_clust+3).fit(pos)
        clusters = kmeans.predict(pos)
        clusters = [x+1 for x in clusters]
        c1, c2 = np.unique(clusters,return_counts=True)
        cD = pd.DataFrame({"cluster":c1,"count":c2})
        cD['cluster2'] = cD['cluster']
        cD.loc[cD['count'] < 10,'cluster2'] = 0
        cD1 = cD.groupby('cluster2').agg(sum).reset_index()
        cD1['cluster3'] = cD1.index
        cD = cD.merge(cD1,on="cluster2",how="left",suffixes=["","_y"])
        cD.loc[~cD['cluster3'].isin(aid),'cluster3'] = 0
        route['cluster'] = clusters
        route = route.merge(cD[['cluster','cluster3']],on="cluster",how="left")
        if complete:
            self.spotL['agent'] = route['cluster3'].values
        else:
            agentG = route.groupby('cluster3').agg(np.mean).reset_index()
            tree = sp.spatial.KDTree(pos.values)
            nearest_dist, nearest_ind = tree.query(pos.values,k=2)
            l1, cL = tree.query(agentG[colL])
            cL = self.spotL.index[cL]
            agentG['spot'] = cL
            for i,g in agentG.iterrows():
                self.spotL.loc[g['spot'],'agent'] = i
        if isPlot:
            cent = kmeans.cluster_centers_
            plt.scatter(route['x'],route['y'],color="blue")
            plt.scatter(route.loc[cL,'x'],route.loc[cL,'y'],color='red')
            # plt.scatter(route.loc[cL1,'x'],route.loc[cL1,'y'],color='purple')
            plt.scatter(cent[:,0],cent[:,1],color='purple')            
            plt.show()

    def loadRouted(self,pairL):
        """load a routed pair relationship between spots"""
        if not isinstance(pairL,pd.DataFrame):
            pos = self.spotL[['x','y']].sort_index()
            self.distM = pd.DataFrame(sp.spatial.distance_matrix(pos.values,pos.values),index=pos.index,columns=pos.index)
        else: 
            odm = pairL.pivot_table(index="geohash_o",columns="geohash_d",values="length",aggfunc=np.sum)
            odw = pairL.pivot_table(index="geohash_o",columns="geohash_d",values="weight",aggfunc=np.sum)
            odm.replace(float('nan'),10000.,inplace=True)
            odw.replace(float('nan'),0.,inplace=True)
            self.distM = odm
            self.markovC = odw
        
    def plotOccupancy(self,ax=None):
        """plot occupanvy on agent level"""
        agentv = self.pathL[self.pathL['agent']>0]
        agentv.loc[:,'width'] = .5
        if ax == None: fig, ax = plt.subplots(1,1)
        colors = agentv['color']
        x = range(agentv.shape[0])
        y = agentv['load']/agentv['capacity']
        ax.bar(x,y,width=.5,color=colors)
        return ax


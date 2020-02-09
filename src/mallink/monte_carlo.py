"""
monte_carlo:
Monte Carlo library for paths optimization
"""
import numpy as np
import pandas as pd
import scipy as sp
import matplotlib.pyplot as plt
import geomadi.graph_viz as g_v
import geomadi.lib_graph as l_g
from mallink.path_opt import pathOpt
import time

class MonteCarlo(pathOpt):
    """Monte Carlo for path optimization"""
    def __init__(self,spotL,pathL=None,opsL=None,pairL=None,conf=None):
        """initialize quantities"""
        pathOpt.__init__(self,spotL,pathL,opsL,pairL,conf)
        l = conf['moveProb']
        l = [l[k] for k in l.keys()]
        self.moveP = [x/sum(l) for x in l]
        self.moveS = list(conf['moveProb'].keys())
        self.opsL = opsL['action']
        self.stateL = spotL.index
        self.agentL = pathL.index
        self.actionL = opsL['action']
        actionD = {}
        for i,x in zip(opsL.index,opsL['action']): actionD[x] = i
        self.actionD = actionD
        self.isLog = False
        self.step = 0
        self.moveN = 0
        self.timeL = []
        self.moveL = []
        self.perfL = []
        self.conf = conf
        self.chemPot = 0.
        self.En, self.cost, self.revenue = 0, 0, 0
        self.En = self.calcEnergy(spotL)
        self.start = time.time()

    def calcEnergy(self,route):
        """calculate the route energy"""
        if self.isLog: print('%d) calc energy' % self.step)
        route1 = route[route['agent'] > 0]
        if route1.shape[0] == 0: return 0.0
        length = sum(route1['distance'])
        stop = route1[route1['agent']>0].shape[0]
        cost = length*self.conf['cost_route'] + stop*self.conf['cost_stop']
        self.pathL['energy'] = self.pathL['distance']*self.conf['cost_route'] + self.pathL['load']*self.conf['cost_stop']
        pathv = self.pathL[self.pathL['agent'] > 0]
        pathv = pathv.loc[~pathv['phantom']]
        self.chemPot = np.mean(pathv['energy'])
        revenue = route1['potential'].sum()
        #revenue = route1.apply(lambda x: x[x['ops']]*x['occupancy'],axis=1).sum()
        energy = - revenue + cost
        self.cost, self.revenue = cost, revenue
        if self.step > 0:
            self.timeL.append({"step":self.step,"length":length,"stop":stop,"revenue":revenue,"energy":energy,"cost":cost,"current":self.En})
        return energy

    def isMetropolis(self,dEn,weight=1.):
        """metropolis criterium"""
        if -dEn < 1: return True
        temp = self.conf['temp']
        if weight*np.exp(-dEn/temp) < np.random.uniform(0,1): return True
        return False

    def tryChange(self,m=None):
        """perform a move and try to accept it"""
        if m == None:
            m = np.random.choice(self.moveS,p=self.moveP)
        if   m == "move": move = self.tryMove()
        elif m == "distance": move = self.tryDistance()
        else: move = self.tryMove()
        if self.isLog: print('%d) try change, move %d' % (self.step,m))
        for v,p,s in zip(move['agent'],move['state'],move['action']):
            if not self.checkAllowed(v,p,s):
                return False, move
        return True, move

    def move(self,move):
        """actuate a move"""
        route1 = self.spotL.copy()
        p, v, s = move['state'], move['agent'], move['action']
        for i,j in enumerate(p):
            route1.loc[j,'agent'] = v[i]
            route1.loc[j,'ops'] = s[i]
        route1 = self.simplifyRoute(route1)
        return route1

    def checkEnergy(self,route,move):
        """check energy"""
        if self.isLog: print('%d) check energy' % self.step)
        En1 = self.calcEnergy(route)
        dEn = (self.En - En1)
        string = "%.2f %.2f %.2f %d                " % (self.En,dEn,self.completion,self.phantom)
        print(string,end="\r",flush=True)
        return En1

    def loop(self,m=None):
        """a single iteration for loop"""
        start = time.time()
        self.step += 1
        status, move = self.tryChange(m)
        move_time = time.time() - start
        if not status: return False
        route1 = self.move(move)
        En1 = self.checkEnergy(route1,move)
        nrg_time = time.time() - start
        self.updateHistory(move)
        dEn = (self.En - En1)
        if not self.isMetropolis(dEn,weight=move['weight']): return False
        self.En = En1
        self.updateSys(route1)
        self.moveN += 1
        end_time = time.time() - start
        self.moveL.append([self.step,end_time,move['move'],self.En,self.cost,self.revenue,self.completion])
        self.perfL.append([move_time,nrg_time,end_time])
        self.grandCanonical()
        return True

    def updateHistory(self,move):
        """update learning history"""
        return False
    
    def grandCanonical(self):
        """insert or remove paths in case of local minima"""
        #if (self.step % 10) != 0: return False
        nph = self.phantom
        self.swapPhantom()
        moveRate = 1. - self.moveN/max(self.step,1)
        rand = 0.3*np.random.uniform(0.,moveRate)
        probRem = 2./(nph+(1.5+rand))
        probIns = (nph+(.4+rand) )/2.
        #if self.completion > probRem: self.removePhantom()
        #if self.completion > probIns: self.insertPhantom()
        return True
    
    def tryMove(self):
        """try a move favoring uncomplete"""
        pv = self.probPath()
        ps = self.probNorm(self.spotL['occupancy'])
        v1 = np.random.choice(pv.index,p=pv)
        p1 = np.random.choice(ps.index,p=ps)
        s1 = np.random.choice(self.opsL)
        weight = 1. # - ps[s1] - pv[v2]
        return {"weight":weight,"agent":[v1],"state":[p1],"action":[s1],"move":"uniform"}

    def tryRemove(self):
        """try a move favoring uncomplete"""
        route1 = self.spotL[spotL['agent']>0]
        pv = self.probPath()
        ps = self.probNorm(route1['occupancy'])
        v1 = 0
        p1 = np.random.choice(ps.index,p=ps)
        s1 = np.random.choice(self.opsL)
        weight = 1. # - ps[s1] - pv[v2]
        return {"weight":weight,"agent":[v1],"state":[p1],"action":[s1],"move":"uniform"}

    def tryDistance(self):
        """try a move favouring reducing distances"""
        pv = self.probNorm(self.pathL['distance'])
        v1 = np.random.choice(pv.index,p=pv)
        routev = self.spotL[self.spotL['agent'] == v1]
        if routev.shape[0] == 0:
            ps = self.probNorm(self.spotL['occupancy'])
            p1 = np.random.choice(ps.index,p=ps)
            routev = self.spotL.loc[p1:p1]
        ps = self.probNorm(routev['distance'])
        p1 = np.random.choice(ps.index,p=ps)
        s1 = np.random.choice(self.opsL)
        weight = 1. # - pv[v1] - ps[s1]
        return {"weight":weight,"agent":[v1],"state":[p1],"action":[s1],"move":"dist"}

    def plotHistory(self,ax=None):
        """plot energy distribution over time"""
        timeL = pd.DataFrame(self.timeL)
        if len(timeL) == 0: return ax
        if ax == None: fig, ax = plt.subplots(1,1)
        ax.set_title("energy distribution")
        ax.plot(timeL['revenue'],label="revenue")
        ax.plot(-timeL['energy'],label="energy")
        ax.plot(timeL['cost'],label="cost")
        ax.plot(-timeL['current'],label="chosen")
        #ax.legend()
        return ax

    def printSummary(self):
        """print summary of the simulation"""
        summ = {"step":self.step}
        summ['total_time'] = time.time() - self.start
        summ['acceptance'] = len(self.timeL)/self.step
        summ['time_move']  = summ['total_time']/self.step
        summ['completion'] = self.completion
        summ['move_col'] = ['step','time','move','energy','cost','revenue','completion']
        summ['move'] = self.moveL
        summ['performance'] = self.perfL
        return summ

    def plotStrategy(self,ax=None):
        """plot strategy distribution"""
        moveL = self.moveL
        if len(moveL) == 0: return ax
        stepL = [x[2] for x in moveL]
        if ax == None: fig, ax = plt.subplots(1,1)
        l, x = np.unique(stepL,return_counts=True)
        ax.pie(x,labels=l)
        return ax

    def plotAcceptance(self,ax=None):
        """plot acceptance graph"""
        moveL = [x[0] for x in self.moveL]
        if len(moveL) == 0: return ax
        l = 100.*np.arange(0,len(moveL),1)/moveL
        l = l[l == l]
        if ax == None: fig, ax = plt.subplots(1,1)
        ax.plot(l)
        return ax

    def plotState(self,ax=None):
        """plot graph and kpi plots"""
        route = self.spotL
        n = int(route.loc[route['agent']>0,'occupancy'].sum())
        if ax == None: fig, ax = plt.subplots(1,1)
        g_v.graphRoute(route,ax=ax)
        axins1 = ax.inset_axes([0.07, 0.75, 0.1, 0.2])
        self.plotHistory(axins1)
        axins2 = ax.inset_axes([0.07, 0.05, 0.1, 0.1])
        self.plotAcceptance(axins2)
        axins3 = ax.inset_axes([0.10, 0.15, 0.1, 0.1])
        self.plotStrategy(axins3)
        axins4 = ax.inset_axes([0.85, 0.05, 0.1, 0.1])
        self.plotOccupancy(axins4)
        l_g.insetStyle(axins1)
        l_g.insetStyle(axins2)
        l_g.insetStyle(axins3)
        l_g.insetStyle(axins4)
        xe, ye = ax.get_xlim(), ax.get_ylim()
        xd, yd = xe[1]-xe[0], ye[1]-ye[0]
        dt2 = (time.time() - self.start)/self.step
        nv = len(self.pathL) - 1
        string = "%.2f %% %.0f en %d agent %.2f s" % (self.completion,-self.En,nv,dt2)
        ax.text(xe[0]+.32*xd,ye[0]+.0*yd,string)
        #axins2.set_axis_off()
        # plt.show()
        return ax
    

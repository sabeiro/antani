import json
import numpy as np
import pandas as pd
import geomadi.geo_octree as g_o
import mallink.path_opt as p_o
import re

gO = g_o.h3tree()
conf = {"reset":False
        ,"cost_route":70.35,"cost_stop":.1,"max_n":50,"temp":.5,"link":5,"phantom":0,"cluster":False
        ,"moveProb":{"move":1,"distance":1,"markov":4,"extrude":3,"flat":1}
        ,"net_layer":[128,128],"load_model":"","init_chain":True}

def frame2dict(spotL,pathL):
   """convert data frames into a single dict"""
   solD = {"spot":spotL.to_dict(orient="index"),"path":pathL.to_dict(orient="index")}
   return solD

def dict2frame(solD):
   """convert the dicts to data frames"""
   if not bool(solD):
      raise Exception('empty dictionary')
      return pd.DataFrame(), pd.DataFrame()
   if not list(solD) == ['spot','path']:
      raise Exception("'spot','path' not present")
      return pd.DataFrame(), pd.DataFrame()
   spotL = pd.DataFrame.from_dict(solD['spot'],orient='index')
   pathL = pd.DataFrame.from_dict(solD['path'],orient='index')
   pathL.index = [int(x) for x in pathL.index]
   spotL.index.name = 'index'
   pathL.index.name = 'index'
   return spotL, pathL

def routificFrame(solJ):
   pathL = pd.DataFrame.from_dict(solJ['input']['fleet'],orient='index')
   pathL['id'] = pathL.index
   pathL = pd.concat([pathL.head(1),pathL])
   pathL['agent'] = range(pathL.shape[0])
   pathL.index = pathL['agent']
   spotL = pd.DataFrame.from_dict(solJ['input']['network'],orient='index')
   visit = pd.DataFrame.from_dict(solJ['input']['visits'],orient='index')
   visit1 = visit['location'].apply(pd.Series)
   del visit['location']
   visit = pd.concat([visit,visit1],axis=1)
   unserved = pd.DataFrame.from_dict(solJ['output']['unserved'],orient='index',columns=["collect"])
   unserved['collect'] = False
   spotL = spotL.merge(visit,how="outer",left_index=True,right_index=True,suffixes=["","_y"])
   spotL = spotL.merge(unserved,how="outer",left_index=True,right_index=True,suffixes=["","_y"])
   spotL.drop(columns=['lat_y','lng_y','name_y'],inplace=True)
   spotL.rename(columns={"lat":"y","lng":"x","load":"occupancy"},inplace=True)
   solL = []
   for k in list(solJ['output']['solution'].keys()):
      solF = pd.DataFrame(solJ['output']['solution'][k])
      agent = pathL.loc[pathL['id']==k,"agent"].values[-1]
      solF['agent'] = agent
      solF['sequence'] = range(solF.shape[0])
      solL.append(solF)
      solF = pd.concat(solL).reset_index()
      solF.drop(columns=["index"],inplace=True)
      spotL = spotL.merge(solF,how="outer",left_index=True,right_on="location_id")
      spotL.loc[spotL['agent'] != spotL['agent'],'agent'] = 0
      spotL['agent'] = [int(x) for x in spotL['agent']]
      spotL = spotL.sort_values(["agent","sequence"])
      spotL['potential'] = spotL['priority']*.01
      spotL['potential'] = 1. + spotL['potential']/spotL['potential'].max()
      spotL['potential'] = spotL['potential'].replace(float('nan'),1.)
      spotL.loc[:,"geohash"] = spotL.apply(lambda x: gO.encode(x['x'],x['y'],precision=11),axis=1)
      # spotL.replace(float('nan'),0,inplace=True)
      # spotL = spotL.groupby('geohash').head(1)
   spotL.index = spotL['geohash']
   spotL['ops'] = ''
   pathL = p_o.updatePath(spotL,pathL)
   idp = set(list(pathL['start-location']) + list(pathL['end-location']))
   pathS = spotL.loc[spotL['name'].isin(idp),["name","x","y"]].drop_duplicates()
   pathL = pathL.merge(pathS,left_on="start-location",right_on="name",suffixes=["","_start"],how="left")
   pathL = pathL.merge(pathS,left_on="end-location",right_on="name",suffixes=["","_end"],how="left")
   pathL.drop(columns={"name","name_end"},inplace=True)
   return spotL, pathL

def frameRoutific(spotL,pathL,solR):
   """convert from dataframe to routific"""
   polylines = pathL.to_dict(orient="index")
   unserved = spotL[spotL['agent']==0].to_dict(orient="index")
   solution = {}
   for i,g in pathL.groupby('agent'):
      if i == 0: continue
      spot = spotL.loc[spotL['agent']==i]
      spot = spot.head(g['capacity'].values[0])
      spotS = spot.head(1).copy()
      spotE = spot.tail(1).copy()
      if 'start_location' in g.columns:
         spotS['name'] = g['start_location'].iloc[0]['id']
      else:
         spotS["name"] = g.apply(lambda x: gO.encode(x['x_start'],x['y_start'],precision=11),axis=1).values[0]
      if 'end_location' in g.columns:
         spotE['name'] = g['end_location'].iloc[0]['id']
      else:
         spotE["name"] = g.apply(lambda x: gO.encode(x['x_end'],x['y_end'],precision=11),axis=1).values[0]
      spot = pd.concat([spotS,spot,spotE])
      spot['arrival_time'] = 0
      spot['finish_time']  = 0
      spot['location_name'] = spot['name']
      spot['location_id'] = spot['name']
      spot.index.name = "index"
      spot = spot.reset_index()
      sol = spot.to_dict(orient="index")
      id_agent = g['id'].values[0]
      solution[id_agent] = sol
   solR['output']['unserved'] = unserved
   solR['output']['solution'] = solution
   return solR

def inputRoutific(solD):
   """convert the dicts to data frames"""
   if not bool(solD):
      raise Exception('empty dictionary')
      return pd.DataFrame(), pd.DataFrame(), {}
   if not list(solD) == ['visits','fleet','options']:
      print(list(solD))
      raise Exception("fields 'visits','fleet','options' not present")
      return pd.DataFrame(), pd.DataFrame(), {}
   spotL = pd.DataFrame.from_dict(solD['visits'],orient='index')
   pathL = pd.DataFrame.from_dict(solD['fleet'],orient='index')
   pathL['id'] = pathL.index
   pathL = pd.concat([pathL.head(1),pathL])
   pathL['agent'] = range(pathL.shape[0])
   pathL['distance'] = 0
   pathL.index = pathL['agent'] 
   pathL['x_start'] = pathL['start_location'].apply(lambda x: x['lng'])
   pathL['x_end'] = pathL['end_location'].apply(lambda x: x['lat'])
   pathL['y_start'] = pathL['start_location'].apply(lambda x: x['lng'])
   pathL['y_end'] = pathL['end_location'].apply(lambda x: x['lat'])
   spotL1 = spotL['location'].apply(pd.Series)
   del spotL['location']
   spotL = pd.concat([spotL,spotL1],axis=1)
   spotL.rename(columns={"lat":"y","lng":"x","load":"occupancy"},inplace=True)
   spotL['potential'] = spotL['priority']*.01
   spotL['potential'] = 1. + spotL['potential']/spotL['potential'].max()
   spotL['potential'] = spotL['potential'].replace(float('nan'),1.)
   spotL.loc[:,"geohash"] = spotL.apply(lambda x: gO.encode(x['x'],x['y'],precision=11),axis=1)
   spotL.index = spotL['geohash']
   spotL['ops'] = ''
   spotL['agent'] = 0
   spotL['distance'] = 0
   pathL = p_o.updatePath(spotL,pathL)
   pO = p_o.pathOpt(spotL,pathL=pathL,conf=conf)
   spotL, pathL = pO.getPath()
   return spotL, pathL, solD['options']

def to_json(sol):
   str1 = str(sol)
   str1 = re.sub("'",'"',str1)
   str1 = re.sub("False",'false',str1)
   str1 = re.sub("True",'true',str1)
   str1 = re.sub("None",'null',str1)
   return str1

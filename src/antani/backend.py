import os, sys, gzip, random, csv, json, datetime, re, time
import numpy as np
import pandas as pd
import scipy as sp
import matplotlib.pyplot as plt
from flask import Flask, redirect, url_for, request, jsonify
from flask import Flask, request, render_template, jsonify
from flask_jsonpify import jsonpify
from celery import Celery
from celery.task.control import revoke
baseDir = os.environ.get('LAV_DIR')
sys.path.append(baseDir+'/src/')
import importlib
import etl as etl
import mallink.path_opt as p_o
import mallink.monte_carlo as m_c
import mallink.monte_markov as m_m
# import mallink.rein_learn as r_l

hostname = "127.0.0.1"
redishost = 'redis://localhost:6379/0'
if len(sys.argv) > 1:
   if sys.argv[1] == "supercazzola":
      hostname = "0.0.0.0" #sys.argv[1]
      redishost = 'redis://redis:6379/0'

conf = {"reset":False
        ,"cost_route":70.35,"cost_stop":.1,"max_n":50,"temp":.5,"link":5,"phantom":0,"cluster":False
        ,"moveProb":{"move":1,"distance":1,"markov":4,"extrude":3,"flat":1}
        ,"net_layer":[128,128],"load_model":"","init_chain":True}

solD = {"solution":[]}
jobR = {"request":[]}
solR = json.load(open(baseDir + "src/antani/conf/job_routific_sol.json"))
solR['status'] = "processing"
pathL = None
spotL = None
jobN = "supercazzola"
opsL = pd.DataFrame({"action":['collect','potential']})

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = redishost
app.config['CELERY_RESULT_BACKEND'] = redishost
app.config['JSON_SORT_KEYS'] = False
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@app.route('/',methods=['GET','POST'])
def status():
   return jsonify({"status":"working"})

@app.route('/conf',methods=['POST'])
def conf_file():
   sol = request.get_json()
   conf = sol
   return '', 204

@app.route('/solution',methods=['GET','POST'])
def get_solution():
   JSON_data = jsonpify(solD['solution'])
   return JSON_data

@celery.task(bind=True)
def long_task(self,sol):
   """Background task that runs a long function with progress reports"""
   self.update_state(state='pending',meta={'current':0,'total':100,'status':'MonteMarkov',"completion":0,"energy":0.,"result":{}})
   if not sol:
      print('empty request body')
      return '', 404
   spotL, pathL = etl.dict2frame(sol)
   print(spotL.shape,pathL.shape)
   conf1 = conf.copy()
   conf1['phantom'] = 2
   mc = m_m.MonteMarkov(spotL,pathL=pathL,opsL=opsL,conf=conf1)
   mc.loop()
   n_iter = 2001
   total = int(pathL.loc[pathL['agent']>0,"capacity"].sum())
   for i in range(1,n_iter):
      status = mc.loop()
      if i%10 == 0:
         j = "%03d" % (i//100)
         j = int(mc.completion*total)
         spotL, pathL = mc.getPath()
         sol = etl.frame2dict(spotL,pathL)
         self.update_state(state='processing'
                           ,meta={'current':j,'total':total,'status':'MonteMarkov'
                                  ,"completion":mc.completion,"energy":mc.En,"result":sol})
      if mc.completion >= .99: break

   spotL, pathL = mc.getPath()
   #spotL, pathL = mc.spotL, mc.pathL
   sol = etl.frame2dict(spotL,pathL)
   n = int(pathL.loc[pathL['agent']>0,"load"].sum())
   solD['solution'] = sol
   return {'current':100,'total':100,'status':'finished','result':sol,"completion":mc.completion,"energy":mc.En}

@app.route('/solve',methods=['POST'])
def solve():
   print("parsing/converting solution")
   sol = request.get_json()
   if not sol:
      print('empty request body')
      return '', 404
   spotL, pathL, options = etl.inputRoutific(sol)
   sol = etl.frame2dict(spotL,pathL)
   jobR['request'] = sol
   task = long_task.apply_async(args=[sol])
   jobN = task.id
   solR['id'] = jobN
   solR['status'] = "processing"
   return jsonify({"job_id":jobN}), 202, {'Location': url_for('taskstatus',task_id=task.id)}

@app.route('/longtask', methods=['POST','GET'])
def longtask():
   print("parsing/converting solution")
   sol = request.get_json()
   if not sol:
      print('empty request body')
      return '', 404
   spotL, pathL = etl.dict2frame(sol)
   jobR['request'] = sol
   task = long_task.apply_async(args=[sol])
   jobN = task.id
   return jsonify({"job_id":jobN}), 202, {'Location': url_for('taskstatus',task_id=task.id)}

@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
    response = {'state':"pending",'current':0,'total':1,'status':'Pending...',"result":{}}
    if task.state != 'FAILURE':
       if task.info == None:
          response = {'state':"pending",'current':0,'total':100,'status':"setting up",'energy':0.,'result':{}}
       else:
          response = {'state':task.state,'current':task.info.get('current',0),'total':task.info.get('total', 1),'status':task.info.get('status',''),'energy':task.info.get('energy',''),'result':{}}
          if 'result' in task.info:
             response['result'] = task.info['result']
          else:
             response = {'state':task.state,'current':1,'total':1,'status':str(task.info)}
    return jsonify(response)

@app.route('/jobs/<task_id>')
def jobstatus(task_id):
   task = long_task.AsyncResult(task_id)
   response = {'status':"pending",'current':0,'total':1,'state':'Pending...',"result":{}}
   if task.state != 'FAILURE':
      if task.info == None:
         response = {'status':"pending",'current':0,'total':100,'state':"setting up",'energy':0.,'result':{}}
      else:
         if 'result' in task.info:
            sol = task.info['result']
            if sol:
               solR = json.load(open(baseDir+"src/antani/conf/job_routific_sol.json"))
               solR['status'] = "processing"
               spotL, pathL = etl.dict2frame(sol)
               response = etl.frameRoutific(spotL,pathL,solR)
               print(spotL[spotL['agent']>0])
               response = solR
         else:
            response = {'status':task.state,'current':1,'total':1,'state':str(task.info)}
   return jsonify(response)

@app.route('/publish/<task_id>',methods=['GET'])
def publish(task_id):
   task = long_task.AsyncResult(task_id)
   revoke(task_id,terminate=True)
   task.state = "finished"
   solR['status'] = 'finished'
   return '', 204
 
@app.route('/kill/<task_id>')
def taskkill(task_id):
   #app.control.revoke(task_id,terminate=True,signal='SIGKILL')
   revoke(task_id, terminate=True)
   return '', 204

@app.route('/simplify',methods=['POST'])
def route_simplify():
   sol = request.get_json()
   if not sol:
      print('empty request body')
      return '', 404
   spotL, pathL = etl.dict2frame(sol)
   pO = p_o.pathOpt(spotL,pathL=pathL,conf=conf)
   print("simplify - calc distances")
   spotL1 = pO.simplifyRoute(spotL)
   pathL1 = pO.calcDistance()
   sol = etl.frame2dict(spotL1,pathL1)
   solD['solution'] = sol
   return jsonify(sol)

@app.route('/cluster',methods=['POST'])
def route_cluster():
   sol = request.get_json()
   if not sol:
      print('empty request body')
      return '', 404
   print("clustering - calc distances")
   spotL, pathL = etl.dict2frame(sol)
   pO = p_o.pathOpt(spotL,pathL=pathL,conf=conf)
   pO.startPos(complete=True)
   spotL1 = pO.simplifyRoute(pO.spotL)
   pathL1 = pO.calcDistance()
   sol = etl.frame2dict(spotL1,pathL1)
   solD['solution'] = sol
   return jsonify(sol)

@app.route('/test',methods=['POST','GET'])
def test():
   sol = request.get_json()
   print(list(sol))
   if not sol:
      print('empty request body')
      return '', 404
   # print(sol)
   solR = json.load(open(baseDir+"src/antani/conf/job_routific_sol.json"))
   #spotL, pathL = etl.routificFrame(sol)
   spotL, pathL, options = etl.inputRoutific(sol)
   print(spotL)
   sol = etl.frameRoutific(spotL,pathL,solR)
   #sol = etl.frame2dict(spotL,pathL)
   sol = solR
   return jsonify(sol)

@app.route('/init',methods= ['POST'])
def process():
   sol = request.get_json()
   spotL, pathL = etl.dict2frame(sol)
   conf1 = conf.copy()
   conf1['init_chain'] = True
   mc = m_m.MonteMarkov(spotL,pathL=pathL,opsL=opsL,conf=conf1)
   #mc.loop()
   sol = etl.frame2dict(mc.spotL,mc.pathL)
   solD['solution'] = sol
   return jsonify(sol)

if __name__ == '__main__':
   app.run(debug=True,host=hostname)
   print('-----------------te-se-qe-te-ve-be-te-ne------------------------')

#curl 127.0.0.1:5000/simplify -d @src/ui/antani_viz/data/sol_routific.json --header "Content-Type: application/json"
#curl 127.0.0.1:5000/solution --header "Content-Type: application/json"
#curl http://10.0.49.178/antani/solve -d @raw/opt/job_winter.json --header "Content-Type: application/json"

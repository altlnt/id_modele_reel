#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug  4 23:45:53 2021

@author: alex
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import json


base_path=os.path.join(os.getcwd(),"results")

# %%  PLOT ONE OPTI
opti_to_plot="5s_struc_all"

def detect_nans(x,y):
    nx,ny=[],[]
    for j,i in enumerate(y):
        if np.isnan(i):
            nx.append(x[j])
            ny.append(i)
            
    return nx,ny
    

def plot_opti(opti_to_plot):
    
    dirpath=os.path.join(base_path,opti_to_plot)
    
    "listing all json files except data.json which has the metaparams"
    json_list=[]
    
    for file in os.listdir(dirpath):
        json_list.append(file) if file!="data.json" else None
        
    print(json_list)
    "constructing key list"
    for file in json_list:
        if ("epoch" in file) or ("start" in file):
            print("Epoch data found...")
            with open(os.path.join(dirpath,file),"r") as f:
                data=json.load(f)
                keys_=data.keys()
            break
    
    "here we declare the data dict structure from these keys"
    data_dict={}
    
    for k in keys_:
        data_dict[k]=[]
        
    for file in json_list:
        with open(os.path.join(dirpath,file),"r") as f:
            json_data=json.load(f)
            for k in keys_:
                data_dict[k]=data_dict[k]+[json_data[k]] if isinstance(json_data[k],(int,float)) else data_dict[k]+json_data[k] 
    # print(data_dict)
    
    N_sp=len(keys_)
    # data_df=pd.DataFrame(data=[data_dict[i] for i in data_dict],columns=data_dict.keys())
    f=plt.figure()
    f.suptitle(opti_to_plot)
    score_ax=f.add_subplot(2,2,2)
    
    y0,y1,y2=data_dict['train_sc_a'],data_dict['val_sc_a'],data_dict['total_sc_a']

    xnan0,y0nans=detect_nans(range(len(y0)), y0)
    xnan1,y1nans=detect_nans(range(len(y1)), y1)
    xnan2,y2nans=detect_nans(range(len(y2)), y2)
    x=range(len(y0))
    y0,y1,y2=np.nan_to_num([y0,y1,y2],nan=0.0)
    score_ax.plot(x,y0,label="train_sc_a")
    score_ax.scatter(xnan0,y0nans,color="red")
    score_ax.plot(x,y1,label="val_sc_a")
    score_ax.scatter(xnan1,y1nans,color="red")
    score_ax.plot(x,y2,label="total_sc_a")
    score_ax.scatter(xnan2,y2nans,color="red")

    score_ax.grid(),score_ax.legend(),score_ax.set_ylim(0,)
    
    score_vx=f.add_subplot(2,2,4)

    y0,y1,y2=data_dict['train_sc_v'],data_dict['val_sc_v'],data_dict['total_sc_v']
    xnan0,y0nans=detect_nans(range(len(y0)), y0)
    xnan1,y1nans=detect_nans(range(len(y1)), y1)
    xnan2,y2nans=detect_nans(range(len(y2)), y2)
    
    y0,y1,y2=np.nan_to_num([y0,y1,y2],nan=0.0)
    score_vx.plot(x,y0,label="train_sc_v")
    score_ax.scatter(xnan0,y0nans,color="red")
    score_vx.plot(x,y1,label="val_sc_v")
    score_ax.scatter(xnan1,y1nans,color="red")
    score_vx.plot(x,y2,label="total_sc_v")
    score_ax.scatter(xnan2,y2nans,color="red")

    score_vx.grid(),score_vx.legend(),score_vx.set_ylim(0,)
    
    j=0
    for i,k in enumerate(data.keys()):
        if ('train_sc' in k) or  ("val_sc" in k) or ('total_sc' in k):
            pass
        else:   
            
            temp_ax=f.add_subplot(N_sp-6,2,2*j+1)
            y=np.nan_to_num(data_dict[k],nan=-1)
            x=np.arange(len(y))
            temp_ax.plot(x,y,label=k,marker="x")
            temp_ax.legend(),temp_ax.grid()
            j+=1

# plot_opti(opti_to_plot)


# %%  PLOT ALL optis

list_optis=os.listdir("./results/")
# list_optis=['fit_v_True_lr_0.001000_ns_-1.000000']
[plot_opti(i) for i in list_optis]
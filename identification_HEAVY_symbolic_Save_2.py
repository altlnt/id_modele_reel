#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug  1 01:40:24 2021

@author: alex
"""

import  numpy as np
# %%   ####### PARAMETERS
import sys

# generic booleans
model_motor_dynamics=True
used_logged_v_in_model=False
with_ct3=False
vanilla_force_model=False

structural_relation_idc1=True
structural_relation_idc2=False
eqs_in_body_frame=False


if vanilla_force_model and (structural_relation_idc1 or structural_relation_idc2):
    print("INVALID :")
    print("vanilla force model and structural_relation cannot be true at the same time")
    sys.exit()
    
if structural_relation_idc1 and structural_relation_idc2:
    print("INVALID :")
    print("structural_relation_idc1 and structural_relation_idc2 cannot be true at the same time")
    sys.exit()

fit_on_v=True
assume_nul_wind=False
approx_x_plus_y=False
di_equal_dj=False


# ID coeffs
id_mass=False
id_blade_coeffs=True
id_c3=with_ct3
id_blade_geom_coeffs=False
id_body_liftdrag_coeffs=False
id_wind=not assume_nul_wind
id_time_const=model_motor_dynamics

base_lr=1e-3
normalize_grad=False
n_epochs=250
nsecs=10
train_proportion=0.8
grad_autoscale=False


# Log path

log_path="/logs/vol1_ext_alcore/log_real.csv"
log_name=""


mass=369 #batterie
mass+=1640-114 #corps-carton
mass/=1e3
Area=np.pi*(11.0e-02)**2
r0=11e-02
rho0=1.204
kv_motor=800.0
pwmmin=1075.0
pwmmax=1950.0
U_batt=16.8

b10=14.44

c10=5.8e-6
c20=0.0
c30=0.0
ch10=0.0
ch20=0.0
di0=0.0
dj0=0.00
dk0=0.0
vwi0=0.0
vwj0=0.0
kt0=5.0

physical_params=[mass,
Area,
r0,
rho0,
kv_motor,
pwmmin,
pwmmax,
U_batt,
b10,
c10,
c20,
c30,
ch10,
ch20,
di0,
dj0,
dk0,
vwi0,
vwj0,
kt0]

bounds={}
bounds['m']=(0,np.inf)
bounds['A']=(0,np.inf)
bounds['r']=(0,np.inf)
bounds['c1']=(0,np.inf)
bounds['c2']=(-np.inf,np.inf)
bounds['c3']=(-np.inf,np.inf)
bounds['ch1']=(-np.inf,np.inf)
bounds['ch2']=(-np.inf,np.inf)
bounds['di']=(0,np.inf)
bounds['dj']=(0,np.inf)
bounds['dk']=(0,np.inf)
bounds['vw_i']=(-15,15)
bounds['vw_j']=(-15,15)
bounds['kt']=(0,np.inf)

scalers={}
scalers['m']=1.0
scalers['A']=1.0
scalers['r']=1.0
scalers['c1']=1e-8
scalers['c2']=1.0
scalers['c3']=1.0
scalers['ch1']=1e-5
scalers['ch2']=1e-5
scalers['di']=1.0
scalers['dj']=1.0
scalers['dk']=1.0
scalers['vw_i']=1.0
scalers['vw_j']=1.0
scalers['kt']=1.0



metap={"model_motor_dynamics":model_motor_dynamics,
        "used_logged_v_in_model":used_logged_v_in_model,
        "with_ct3":with_ct3,
        "vanilla_force_model":vanilla_force_model,
        "structural_relation_idc1":structural_relation_idc1,
        "structural_relation_idc2":structural_relation_idc2,
        "fit_on_v":fit_on_v,
        "assume_nul_wind":assume_nul_wind,
        "approx_x_plus_y":approx_x_plus_y,
        "di_equal_dj":di_equal_dj,
        "log_path":log_path,
        "base_lr":base_lr,
        "grad_autoscale":grad_autoscale,
        "n_epochs":n_epochs,
        "nsecs":nsecs,
        "train_proportion":train_proportion,
        "[mass,Area,r,rho,kv_motor,pwmmin,pwmmax,U_batt,b1,c10,c20,c30,ch10,ch20,di0,dj0,dk0,vwi0,vwj0,kt0]":physical_params,
        "bounds":bounds}



print(" META PARAMS \n")
[print(i,":", metap[i]) for i in metap.keys()]



# %%   ####### Saving utility
import os
import json
import datetime
import time
if log_name=="":
    log_name=str(datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S"))
    
spath=os.path.join(os.getcwd(),"results",log_name)

os.makedirs(spath)

with open(os.path.join(spath,'data.json'), 'w') as fp:
    json.dump(metap, fp)

import pandas as pd
def saver(name=None,save_path="/home/alex/Documents/identification_modele_hélice/results/",**kwargs):
    
    D={}
    dname=str(int(time.time())) if (name is None) else name
    
    for i in kwargs:
        if type(kwargs[i])==dict:
            for j in kwargs[i]:
                D[j]=kwargs[i][j]
        else:
            D[i]=kwargs[i].tolist() if isinstance(kwargs[i],np.ndarray) else kwargs[i]
    
    with open(os.path.join(save_path,'%s.json'%(dname)), 'w') as fp:
        json.dump(D, fp)



# %%   ####### SYMPY PROBLEM 

import time
from sympy import *

t0=time.time()


print("\nElapsed : %f s , Prev step time: -1 s \\ Generating first symbols ..."%(time.time()-t0))
dt=symbols('dt',positive=True,real=True)

m=symbols('m',reals=True,positive=True)

m_scale=symbols('m_scale',real=True,positive=True)
vw_i_scale,vw_j_scale=symbols('vw_i_scale,vw_j_scale',real=True,positive=True)
kt_scale=symbols('kt_scale',real=True,positive=True)
A_scale,r_scale=symbols('A_scale,r_scale',real=True,positive=True)
c1_scale,c2_scale,c3_scale=symbols('c1_scale,c2_scale,c3_scale',real=True,positive=True)
ch1_scale,ch2_scale=symbols('ch1_scale,ch2_scale',real=True,positive=True)
di_scale,dj_scale,dk_scale=symbols('di_scale,dj_scale,dk_scale',real=True,positive=True)

m_s=m*m_scale

r1,r2,r3,r4,r5,r6,r7,r8,r9=symbols("r1,r2,r3,r4,r5,r6,r7,r8,r9",real=True)
R=Matrix([[r1,r2,r3],
          [r4,r5,r6],
          [r7,r8,r9]])


alog_i,alog_j,alog_k=symbols("alog_i,alog_j,alog_k",real=True)

alog=Matrix([[alog_i],[alog_j],[alog_k]])

vnext_i,vnext_j,vnext_k=symbols("vnext_i,vnext_j,vnext_k",real=True)

vnext_log=Matrix([[vnext_i],[vnext_j],[vnext_k]])

vlog_i,vlog_j,vlog_k=symbols("vlog_i,vlog_j,vlog_k",real=True)
vpred_i,vpred_j,vpred_k=symbols("vpred_i,vpred_j,vpred_k",real=True)


v_i,v_j,v_k=(vlog_i,vlog_j,vlog_k) if used_logged_v_in_model else (vpred_i,vpred_j,vpred_k)

v=Matrix([[v_i],
          [v_j],
          [v_k]])

vw_i,vw_j=symbols('vw_i,vw_j',real=True)
vw_i_s,vw_j_s=vw_i*vw_i_scale,vw_j*vw_j_scale


if not assume_nul_wind:
    va_NED=Matrix([[v_i-vw_i_s],
                    [v_j-vw_j_s],
                    [v_k]]) 
else :
    va_NED=Matrix([[v_i],
                   [v_j],
                   [v_k]])

va_body=R.T@va_NED



k_vect=Matrix([[0],
            [0],
            [1.0]])


"motor dynamics"
t1=time.time()
print("Elapsed : %f s , Prev step time: -1 s \\ Generating motor dynamics ..."%(t1-t0))

kt=symbols('kt',real=True,positive=True)
kt_s=kt*kt_scale
omega_1,omega_2,omega_3,omega_4,omega_5,omega_6=symbols('omega_1,omega_2,omega_3,omega_4,omega_5,omega_6',real=True,positive=True)
omega_c1,omega_c2,omega_c3,omega_c4,omega_c5,omega_c6=symbols('omega_c1,omega_c2,omega_c3,omega_c4,omega_c5,omega_c6',real=True,positive=True)

omegas_c=Matrix([omega_c1,omega_c2,omega_c3,omega_c4,omega_c5,omega_c6])
omegas=Matrix([omega_1,omega_2,omega_3,omega_4,omega_5,omega_6])

omegas=omegas+dt*kt_s*(omegas_c-omegas) if model_motor_dynamics else omegas_c

t2=time.time()
print("Elapsed : %f s , Prev step time: %f s \\ Solving blade model ..."%(t2-t0,t2-t1))

"blade dynamics"

b1=symbols('b1',real=True,positive=True)

rho,A,omega,r=symbols('rho,A,omega,r',real=True,positive=True)
A_s,r_s=A*A_scale,r*r_scale
c1,c2,c3=symbols('c1,c2,c3',real=True)
c1_s,c2_s,c3_s=c1*c1_scale,c2*c2_scale,c3*c3_scale

ch1,ch2=symbols('ch1,ch2',real=True)
ch1_s,ch2_s=c1*ch1_scale,c2*ch2_scale

vi=symbols('eta',reals=True)

v3=Matrix([va_body[2,0]])
v2=sqrt(Matrix([va_body[0,0]**2+va_body[1,0]**2]))

v3=symbols('v3')
v2=symbols("v2")

if vanilla_force_model:
    T=-c1_s*sum([ omegas[i]**2 for i in range(6)])
    H_sum=0*k_vect
else:

    

    
    
    T_BET=rho*A_s*r_s*omega*(c1_s*r_s*omega-c2_s*(vi-v3)) if not with_ct3 else rho*A_s*r_s*omega*(c1_s*omega*r_s-c2_s*(vi-v3)+c3_s*v2**2)
    if structural_relation_idc1:
        T_BET=T_BET.subs(c2, b1*c1-2/b1)
    if structural_relation_idc2:
        T_BET=T_BET.subs(c1, c2/b1+2/b1*b1)
        
    T_MOMENTUM_simp=2*rho*A_s*vi*((vi-v3)+v2) if approx_x_plus_y else 2*rho*A_s*vi*(vi-v3)
    eq_MOMENTUM_simp=T_BET-T_MOMENTUM_simp
    
    eta=simplify(Matrix([solve(eq_MOMENTUM_simp,vi)[0]])).subs(v3,va_body[2,0]).subs(v2,sqrt(va_body[0,0]**2+va_body[1,0]**2))
    
    etas=Matrix([eta.subs(omega,omegas[i]) for i in range(6)])
    
    def et(expr):
        return expr.subs(v3,va_body[2,0]).subs(v2,sqrt(va_body[0,0]**2+va_body[1,0]**2))
    
    T=simplify(sum([et(T_BET).subs(omega,omegas[i]).subs(vi,etas[i]) for i in range(6)]))
    
    H_tmp=-rho*A_s*simplify(sum([r_s*omegas[i]*ch1_s+ch2_s*(etas[i]-va_body[2,0]) for i in range(6)]))
    
    vh_body=va_body-va_body.dot(k_vect)*k_vect
    
    H_sum=H_tmp*R.T@vh_body if not eqs_in_body_frame else H_tmp*vh_body



T_sum=T*R.T@k_vect if not eqs_in_body_frame else T*k_vect


t3=time.time()
"liftdrag forces"
print("Elapsed : %f s , Prev step time: %f s \\ Solving lifrdrag model ..."%(t3-t0,t3-t2))

di,dj,dk=symbols('di,dj,dk',real=True,positive=True)
di_s,dj_s,dk_s=di*di_scale,dj*dj_scale,dk*dk_scale
D=diag(di_s,di_s,dk_s) if di_equal_dj else diag(di_s,dj_s,dk_s)
Fa=-simplify(rho*A_s*va_NED.norm()*R@D*R.T@va_NED)


t35=time.time()
print("Elapsed : %f s , Prev step time: %f s \\ Solving Dynamics ..."%(t35-t0,t35-t3))

g=9.81
grav=g*k_vect if not eqs_in_body_frame else g*R.T@k_vect

new_acc=simplify(grav+T_sum/m_s+H_sum/m+Fa/m_s)
new_v=v+dt*new_acc if not eqs_in_body_frame else v+dt*R@new_acc

t37=time.time()
print("Elapsed : %f s , Prev step time: %f s \\ Generating costs ..."%(t37-t0,t37-t35))

err_a=Matrix(alog-new_acc)
err_v=Matrix(vnext_log-new_v)

cost_scaler_a=symbols('C_sa',real=True,positive=True)
cost_scaler_v=symbols('C_sv',real=True,positive=True)

sqerr_a=Matrix([1.0/cost_scaler_a*(err_a[0,0]**2+err_a[1,0]**2+err_a[2,0]**2)])
sqerr_v=Matrix([1.0/cost_scaler_v*(err_v[0,0]**2+err_v[1,0]**2+err_v[2,0]**2)])

" constructing opti variables "
" WARNING SUPER WARNING : the order must be the same as in id_variables !!!"

id_variables_sym=[]

id_variables_sym.append(m) if id_mass else None 

id_variables_sym.append(A) if id_blade_geom_coeffs else None
id_variables_sym.append(r) if id_blade_geom_coeffs else None

id_variables_sym.append(c1) if id_blade_coeffs*(not structural_relation_idc2) or vanilla_force_model else None
id_variables_sym.append(c2) if id_blade_coeffs*(not structural_relation_idc1) and (not vanilla_force_model) else None
id_variables_sym.append(c3) if id_blade_coeffs*id_c3 else None
id_variables_sym.append(ch1) if id_blade_coeffs*(not vanilla_force_model) else None
id_variables_sym.append(ch2) if id_blade_coeffs*(not vanilla_force_model) else None


id_variables_sym.append(di) if id_body_liftdrag_coeffs else None
id_variables_sym.append(dj) if id_body_liftdrag_coeffs*(not di_equal_dj) else None
id_variables_sym.append(dk) if id_body_liftdrag_coeffs else None

id_variables_sym.append(vw_i) if id_wind else None
id_variables_sym.append(vw_j) if id_wind else None
    
id_variables_sym.append(kt) if id_time_const else None


id_variables_sym=Matrix(id_variables_sym)

print("\n ID VARIABLES:")
print(id_variables_sym,"\n")



t4=time.time()
print("Elapsed : %f s , Prev step time: %f s \\ Gathering identification parameters  ..."%(t4-t0,t4-t37))

t5=time.time()

Ja=sqerr_a.jacobian(id_variables_sym)
Jv=sqerr_v.jacobian(id_variables_sym)

t6=time.time()
print("Elapsed : %f s , Prev step time: %f s \\ Lambdification ..."%(t6-t0,t6-t5))



X=(m,A,r,rho,
b1,
c1,c2,c3,
ch1,ch2,
di,dj,dk,
vw_i,vw_j,
kt,
dt,cost_scaler_a,cost_scaler_v,
vlog_i,vlog_j,vlog_k,
vpred_i,vpred_j,vpred_k,
alog_i,alog_j,alog_k,
vnext_i,vnext_j,vnext_k,r1,r2,r3,r4,r5,r6,r7,r8,r9,
omega_1,omega_2,omega_3,omega_4,omega_5,omega_6,
omega_c1,omega_c2,omega_c3,omega_c4,omega_c5,omega_c6,
m_scale,A_scale,r_scale,c1_scale,c2_scale,c3_scale,
ch1_scale,ch2_scale,di_scale,dj_scale,dk_scale,
vw_i_scale,vw_j_scale,kt_scale)


# acc_pred_func=lambdify(X,new_acc, modules='numpy')
# print(" ..... Acc ok, 1/3")

# speed_pred_func=lambdify(X,new_v, modules='numpy')
# print(" ..... Speed ok, 2/3")

# omega_pred=lambdify(X,omegas, modules='numpy')
# print(" ..... Omega ok, 3/3")

Y=Matrix([new_acc,new_v,omegas,sqerr_a,sqerr_v,Ja.T,Jv.T])
model_func=lambdify(X,Y, modules='numpy')

t7=time.time()
print("Elapsed : %f s , Prev step time: %f s \\ Done ..."%(t7-t0,t7-t6))

"cleansing memory"
del(dt,m,cost_scaler_a,cost_scaler_v,
vlog_i,vlog_j,vlog_k,
vpred_i,vpred_j,vpred_k,
alog_i,alog_j,alog_k,
vnext_i,vnext_j,vnext_k,
vw_i,vw_j,
kt,
b1,
c1,c2,c3,
ch1,ch2,
di,dj,dk,
rho,A,r,r1,r2,r3,r4,r5,r6,r7,r8,r9,R,
omega_1,omega_2,omega_3,omega_4,omega_5,omega_6,
omega_c1,omega_c2,omega_c3,omega_c4,omega_c5,omega_c6)


"test "



# %%   ####### Identification Data Struct


non_id_variables={"m":mass,
                  "A":Area,
                  "r":r0,
                  "rho":rho0,
                  "b1":b10,
                  "c1":c10,
                  "c2":c20,
                  "c3":c30,
                  "ch1":ch10,
                  "ch2":ch20,
                  "di":di0,
                  "dj":dj0,
                  "dk":dk0,
                  "vw_i":vwi0,
                  "vw_j":vwj0,
                  "kt":kt0}
id_variables={}

if id_mass:
    id_variables['m']=mass  
    
if id_blade_coeffs:
    if vanilla_force_model:
        id_variables['c1']=c10
    if not structural_relation_idc2:
        id_variables['c1']=c10
    if not structural_relation_idc1 and not vanilla_force_model:
        id_variables['c2']=c20
    if id_c3:
        id_variables['c3']=c30
    if not vanilla_force_model:
        id_variables['ch1']=ch10
        id_variables['ch2']=ch20
  
if id_blade_geom_coeffs:
    id_variables['A']=Area
    id_variables['r']=r0

if id_body_liftdrag_coeffs:
    id_variables['di']=di0
    if not di_equal_dj:
        id_variables['dj']=dj0
    id_variables['dk']=dk0
    
if id_wind:
    id_variables['vw_i']=vwi0
    id_variables['vw_j']=vwj0
    
if id_time_const:
    id_variables['kt']=kt0

"cleaning non_id_variables to avoid having variables in both dicts"
rem=[]
for i in non_id_variables.keys():
    if i in id_variables.keys():
        rem.append(i)
        
for j in rem:
    del(non_id_variables[j])


print("\n ID VARIABLES:")
print(id_variables,"\n")


print("\n NON ID VARIABLES:")
print(non_id_variables,"\n")

# %%   ####### IMPORT DATA 
print("LOADING DATA...")
import pandas as pd

log_path="./logs/vol1_ext_alcore/log_real_processed.csv"
# log_path="./logs/vol12/log_real.csv"

raw_data=pd.read_csv(log_path)

print("PROCESSING DATA...")


prep_data=raw_data.drop(columns=[i for i in raw_data.keys() if (("forces" in i ) or ('pos' in i) or ("joy" in i)) ])
prep_data=prep_data.drop(columns=[i for i in raw_data.keys() if (("level" in i ) or ('Unnamed' in i) or ("index" in i)) ])
# print(prep_data)

if "vol1_ext_alcore" in log_path:
    tmin,tmax=(41,265) 
if "vol2_ext_alcore" in log_path:
    tmin,tmax=(10,140) 
if "vol12" in log_path:
    tmin,tmax=(-1,1e10) 
    
prep_data=prep_data[prep_data['t']>tmin]
prep_data=prep_data[prep_data['t']<tmax]
prep_data=prep_data.reset_index()
for i in range(3):
    prep_data['speed_pred[%i]'%(i)]=np.r_[prep_data['speed[%i]'%(i)].values[1:len(prep_data)],0]
    
    

prep_data['dt']=np.r_[prep_data['t'].values[1:]-prep_data['t'].values[:-1],0]
prep_data['t']-=prep_data['t'][0]
prep_data=prep_data.drop(index=[0,len(prep_data)-1])




for i in range(6):
    prep_data['omega_c[%i]'%(i+1)]=(prep_data['PWM_motor[%i]'%(i+1)]-pwmmin)/(pwmmax-pwmmin)*U_batt*kv_motor*2*np.pi/60

"splitting the dataset into nsecs sec minibatches"
print("SPLIT DATA...")

N_minibatches=round(prep_data["t"].max()/nsecs) if nsecs >0 else  len(prep_data)# 22 for flight 1, ?? for flight 2

"if you don't want to minibatch"
# N_minibatches=len(data_prepared)
data_batches=[i.drop(columns=[i for i in raw_data.keys() if (("level" in i ) or ("index") in i) ]) for i in np.array_split(prep_data, N_minibatches)]
# print(data_batches)
data_batches=[i.reset_index() for i in data_batches]

N_train_batches=round(train_proportion*N_minibatches)
N_val_batches=N_minibatches-N_train_batches
print("DATA PROCESS DONE")




# %%   ####### MODEL function
import transforms3d as tf3d 

def pred_on_batch(batch,id_variables,scalers):

    acc_pred=np.zeros((len(batch),3))
    speed_pred=np.zeros((len(batch),3))
    omegas=np.zeros((len(batch),6))    
        
    square_error_a=np.zeros((len(batch),1))    
    square_error_v=np.zeros((len(batch),1))    
    jac_error_a=np.zeros((len(batch),len(id_variables)))
    jac_error_v=np.zeros((len(batch),len(id_variables)))
    
    t0=time.time()
    
    cost_scaler_v=max(batch['speed[0]']**2+batch['speed[1]']**2+batch['speed[2]']**2)
    cost_scaler_a=max(batch['acc[0]']**2+batch['acc[1]']**2+batch['acc[2]']**2)
    for i in batch.index:
        
        dt=min(batch['dt'][i],1e-2)
        m=mass
        vlog_i,vlog_j,vlog_k=batch['speed[0]'][i],batch['speed[1]'][i],batch['speed[2]'][i]
        vpred_i,vpred_j,vpred_k=speed_pred[i]
        
        if eqs_in_body_frame:
            alog_i,alog_j,alog_k=batch['acc_body_grad[0]'][i],batch['acc_body_grad[1]'][i],batch['acc_body_grad[2]'][i]
        else:
            alog_i,alog_j,alog_k=batch['acc_ned_grad[0]'][i],batch['acc_ned_grad[1]'][i],batch['acc_ned_grad[2]'][i]
        
        
        vnext_i,vnext_j,vnext_k=batch['speed_pred[0]'][i],batch['speed_pred[1]'][i],batch['speed_pred[2]'][i]
        
        m=non_id_variables['m'] if 'm' in non_id_variables else id_variables['m']
        vw_i=non_id_variables['vw_i'] if 'vw_i' in non_id_variables else id_variables['vw_i']
        vw_j=non_id_variables['vw_j'] if 'vw_j' in non_id_variables else id_variables['vw_j']
        kt=non_id_variables['kt'] if 'kt' in non_id_variables else id_variables['kt']
        b1=non_id_variables['b1'] if 'b1' in non_id_variables else id_variables['b1']
        c1=non_id_variables['c1'] if 'c1' in non_id_variables else id_variables['c1']
        c2=non_id_variables['c2'] if 'c2' in non_id_variables else id_variables['c2']
        c3=non_id_variables['c3'] if 'c3' in non_id_variables else id_variables['c3']
        ch1=non_id_variables['ch1'] if 'ch1' in non_id_variables else id_variables['ch1']
        ch2=non_id_variables['ch2'] if 'ch2' in non_id_variables else id_variables['ch2']
        di=non_id_variables['di'] if 'di' in non_id_variables else id_variables['di']
        dj=non_id_variables['dj'] if 'dj' in non_id_variables else id_variables['dj']
        dk=non_id_variables['dk'] if 'dk' in non_id_variables else id_variables['dk']
        rho=non_id_variables['rho'] if 'rho' in non_id_variables else id_variables['rho']
        A=non_id_variables['A'] if 'A' in non_id_variables else id_variables['A']
        r=non_id_variables['r'] if 'r' in non_id_variables else id_variables['r']
        
        R=tf3d.quaternions.quat2mat(np.array([batch['q[%i]'%(j)][i] for j in range(4)])).T
        
        omega_c1,omega_c2,omega_c3,omega_c4,omega_c5,omega_c6=np.array([batch['omega_c[%i]'%(j)][i] for j in range(1,7,1)])
        omega_1,omega_2,omega_3,omega_4,omega_5,omega_6=omegas[i-1] if i>0 else np.array([batch['omega_c[%i]'%(j)][i] for j in range(1,7,1)])
        
        
        
        m_scale=scalers['m']
        A_scale=scalers['A']
        r_scale=scalers['r']
        c1_scale,c2_scale,c3_scale=scalers['c1'],scalers['c2'],scalers['c3']
        ch1_scale,ch2_scale=scalers['ch1'],scalers['ch2']
        di_scale,dj_scale,dk_scale=scalers['di'],scalers['dj'],scalers['dk']
        vw_i_scale,vw_j_scale=scalers['vw_i'],scalers['vw_j']
        kt_scale=scalers['kt']
        
        X=(m,A,r,rho,
        b1,
        c1,c2,c3,
        ch1,ch2,
        di,dj,dk,
        vw_i,vw_j,
        kt,
        dt,cost_scaler_a,cost_scaler_v,
        vlog_i,vlog_j,vlog_k,
        vpred_i,vpred_j,vpred_k,
        alog_i,alog_j,alog_k,
        vnext_i,vnext_j,vnext_k,*R.flatten(),
        omega_1,omega_2,omega_3,omega_4,omega_5,omega_6,
        omega_c1,omega_c2,omega_c3,omega_c4,omega_c5,omega_c6,
        m_scale,A_scale,r_scale,c1_scale,c2_scale,c3_scale,
        ch1_scale,ch2_scale,di_scale,dj_scale,dk_scale,
        vw_i_scale,vw_j_scale,kt_scale)
    
        # print(*X)
        # input("OUI?")
        Y=model_func(*X)
        # print(Y)
        acc_pred[i]=Y[:3].reshape(3,)
        speed_pred[i]=Y[3:6].reshape(3,)
        omegas[i]=Y[6:12].reshape(6,)
        square_error_a[i]=Y[12:13].reshape(1,)
        square_error_v[i]=Y[13:14].reshape(1,)
        jac_error_a[i]=Y[14:14+len(id_variables)].reshape(len(id_variables),)
        jac_error_v[i]=Y[14+len(id_variables):14+2*len(id_variables)].reshape(len(id_variables),)
    # print("TOTAL TIME:",time.time()-t0)
    return acc_pred,speed_pred,omegas,square_error_a,square_error_v,jac_error_a,jac_error_v



# %%   ####### Gradient propagation function and train loop
import copy
import random


def propagate_gradient(jac_array,id_variables,
                       lr=base_lr,
                       max_deltarel=0.1,
                       normalize=normalize_grad,
                       adaptative_scaling=False):
    
    used_jac=np.mean(jac_array,axis=0)
    print("Propagate %s grad : ")
    print(pd.DataFrame(data=[used_jac,[id_variables[i] for i in id_variables.keys()]],columns=id_variables.keys(),index=['J','value']))
    max_delta_value=0
    
    alpha=1.0 if lr<0 else lr
    
    # if lr<0:
    
    #     for j,key in enumerate(id_variables):
    #         max_delta_value=max_deltarel*max(abs(id_variables[key]),1e-8)
    #         # print("J",-np.mean(jac_array,axis=0),"val",abs(id_variables[key]),"max delta",max_delta_value,"valid",alpha*abs(used_jac[j])<=max_delta_value)
    #         if alpha*abs(used_jac[j])<=max_delta_value:
    #             pass
    #         else:
    #             alpha=max_delta_value/abs(used_jac[j])
    #         # print("J",-np.mean(jac_array,axis=0),"val",abs(id_variables[key]),"max delta",max_delta_value,"valid",alpha*abs(used_jac[j])<=max_delta_value,"alpha",alpha)
    
    new_dic=copy.deepcopy(id_variables)
    
    for i,key in enumerate(id_variables):
        if normalize and lr>0:
            used_jac/=np.linalg.norm(used_jac)+1e-10
        new_dic[key]=np.clip(id_variables[key]-alpha*used_jac[i],bounds[key][0],bounds[key][1])
        
        
    return new_dic,alpha
    
def train_loop(data_batches,id_var,n_epochs=n_epochs):

    id_variables=copy.deepcopy(id_var)
    print("Copy ...")
    temp_shuffled_batches=copy.deepcopy(data_batches)
    print("Done")
    print("INIT")
    ti0=time.time()
    # acc_pred,speed_pred,omegas,square_error_a,square_error_v,jac_error_a,jac_error_v=pred_on_batch(data_prepared,id_variables)
    # print("Inference on full dataset takes : %i"%(round(time.time()-ti0)))
    
    # total_sc_a=np.sqrt(np.mean(square_error_a,axis=0))
    # total_sc_v=np.sqrt(np.mean(square_error_v ,axis=0))
    total_sc_a=-1
    total_sc_v=-1
    print('\n###################################')
    print('############# Begin ident ###########')
    print("id_variables=",id_variables,
          "train_sc_a=",-1,
          "train_sc_v=",-1,
          "val_sc_a=",-1,
          "val_sc_v=",-1,
          "total_sc_a=",total_sc_a,
          "total_sc_v=",total_sc_v,)
    print('###################################\n')

    saver(name="start_",save_path=spath,
          id_variables=id_variables,
          train_sc_a=-1,
          train_sc_v=-1,
          val_sc_a=-1,
          val_sc_v=-1,
          total_sc_a=total_sc_a,
          total_sc_v=total_sc_v)
    print("Entering training loop...")
    for n in range(n_epochs):
        "begin epoch"
        
        train_sc_a,train_sc_v=0,0
        val_sc_a,val_sc_v=0,0
        total_sc_a,total_sc_v=0,0
        
        random.shuffle(temp_shuffled_batches)
        
        
        for k,batch_ in enumerate(temp_shuffled_batches[:N_train_batches]):
            
            
            acc_pred,speed_pred,omegas,square_error_a,square_error_v,jac_error_a,jac_error_v=pred_on_batch(batch_,id_variables,scalers)
            # print(acc_pred,speed_pred,omegas)
            id_variables,alpha=propagate_gradient(jac_error_v if fit_on_v else jac_error_a,id_variables)
            
            train_sc_a+=np.mean(square_error_a,axis=0)
            train_sc_v+=np.mean(square_error_v,axis=0)
            print(" EPOCH : %i/%i || Train batch : %i/%i || PROGRESS: %i/%i [ta,tv]=[%f,%f], alpha=%f"%(n,
                                                                                              n_epochs,
                                                                                              k,N_train_batches,
                                                                                              k,len(temp_shuffled_batches),
                                                                                              np.mean(square_error_a,axis=0),
                                                                                              np.mean(square_error_v,axis=0),
                                                                                              alpha))
        
            # print("id_variables=",id_variables)                                                                                

        for k,batch_ in enumerate(temp_shuffled_batches[N_train_batches:]):

            acc_pred,speed_pred,omegas,square_error_a,square_error_v,jac_error_a,jac_error_v=pred_on_batch(batch_,id_variables)
            
            val_sc_a+=np.mean(square_error_a,axis=0)
            val_sc_v+=np.mean(square_error_v ,axis=0)   
            print(" EPOCH : %i/%i || Eval batch : %i/%i || PROGRESS: %i/%i [va,vv]=[%f,%f], alpha=%f"%(n,
                                                                                              n_epochs,
                                                                                              k,N_val_batches,
                                                                                              k+N_train_batches,len(temp_shuffled_batches),
                                                                                              np.mean(square_error_a,axis=0),
                                                                                              np.mean(square_error_v,axis=0),
                                                                                              alpha))

        
        train_sc_a/=N_train_batches
        train_sc_v/=N_train_batches
        
        val_sc_a/=N_val_batches
        val_sc_v/=N_val_batches

        acc_pred,speed_pred,omegas,square_error_a,square_error_v,jac_error_a,jac_error_v=pred_on_batch(data_prepared,id_variables,scalers)
        total_sc_a=np.sqrt(np.mean(square_error_a,axis=0))
        total_sc_v=np.sqrt(np.mean(square_error_v ,axis=0) )
        
        print('\n###################################')
        print('############# END EPOCH ###########')
        print("id_variables=",id_variables,
              "train_sc_a=",train_sc_a,
              "train_sc_v=",train_sc_v,
              "val_sc_a=",val_sc_a,
              "val_sc_v=",val_sc_v,
              "total_sc_a=",total_sc_a,
              "total_sc_v=",total_sc_v,)
        print('###################################\n')

        saver(name="epoch_%i"%(n),save_path=spath,
              id_variables=id_variables,
              train_sc_a=train_sc_a,
              train_sc_v=train_sc_v,
              val_sc_a=val_sc_a,
              val_sc_v=val_sc_v,
              total_sc_a=total_sc_a,
              total_sc_v=total_sc_v)

        "end epoch"
        
        "compute train and val score"
        
train_loop(data_batches,id_variables,n_epochs=n_epochs)        
        
        
        
        
        
        
        
        
        
        
        
        
        
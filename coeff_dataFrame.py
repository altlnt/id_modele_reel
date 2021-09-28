import numpy as np
import transforms3d as tf3d
import scipy
from scipy import optimize, sort 
import pandas as pd
import matplotlib.pyplot as plt 
import pandas as pd
import json 
import os

log_path="./logs/avion/vol123/log_real_processed.csv"
raw_data=pd.read_csv(log_path)
#%% Prepocced data
  
prep_data=raw_data.drop(columns=[i for i in raw_data.keys() if (("forces" in i ) or ('pos' in i) or ("joy" in i)) ])
prep_data=prep_data.drop(columns=[i for i in raw_data.keys() if (("level" in i ) or ('Unnamed' in i) or ("index" in i)) ])



prep_data=prep_data.reset_index()

for i in range(3):
    prep_data['speed_pred[%i]'%(i)]=np.r_[prep_data['speed[%i]'%(i)].values[1:len(prep_data)],0]
    
    
prep_data['dt']=np.r_[prep_data['t'].values[1:]-prep_data['t'].values[:-1],0]
prep_data['t']-=prep_data['t'][0]
prep_data=prep_data.drop(index=[0,len(prep_data)-1])
prep_data=prep_data.reset_index()

data_prepared=prep_data[:len(prep_data)]



def scale_to_01(df):

    return (df-df.min())/(df.max()-df.min())

data_prepared.insert(data_prepared.shape[1],'omega_c[5]',(data_prepared['PWM_motor[5]']-1000)*925.0/1000)
"splitting the dataset into nsecs sec minibatches"


df=data_prepared.copy()


df.insert(data_prepared.shape[1],
          'R',
          [tf3d.quaternions.quat2mat([i,j,k,l]) for i,j,k,l in zip(df['q[0]'],df['q[1]'],df['q[2]'],df['q[3]'])])

R_array=np.array([i for i in df["R"]])


Aire_1,Aire_2,Aire_3,Aire_4,Aire_0 =    0.62*0.262* 1.292 * 0.5,\
                                    0.62*0.262* 1.292 * 0.5, \
                                    0.34*0.1* 1.292 * 0.5,\
                                    0.34*0.1* 1.292 * 0.5, \
                                    1.08*0.31* 1.292 * 0.5
                                    
Aire_list = [Aire_0,Aire_1,Aire_2,Aire_3,Aire_4]

cp_1,cp_2,cp_3,cp_4,cp_0 = np.array([-0.013,0.475,-0.040],       dtype=float).flatten(), \
                        np.array([-0.013,-0.475,-0.040],      dtype=float).flatten(), \
                        np.array([-1.006,0.17,-0.134],    dtype=float).flatten(),\
                        np.array([-1.006,-0.17,-0.134],   dtype=float).flatten(),\
                        np.array([0.021,0,-0.064],          dtype=float).flatten()
cp_list=[cp_0,cp_1,cp_2,cp_3,cp_4]

#0 : aile centrale
#1 : aile droite
#2 : aile gauche
#3 : vtail droit 
#4 : vtail gauche

theta=45.0/180.0/np.pi

Rvd=np.array([[1.0,0.0,0.0],
              [0.0,np.cos(theta),np.sin(theta)],
              [0.0,-np.sin(theta),np.cos(theta)]])

Rvg=np.array([[1.0,0.0,0.0],
              [0.0,np.cos(theta),-np.sin(theta)],
              [0.0,np.sin(theta),np.cos(theta)]])


forwards=[np.array([1.0,0,0])]*3
forwards.append(Rvd@np.array([1.0,0,0]))
forwards.append(Rvg@np.array([1.0,0,0]))

upwards=[np.array([0.0,0,1.0])]*3
upwards.append(Rvd@np.array([0.0,0,-1.0]))
upwards.append(Rvg@np.array([0.0,0,-1.0]))

crosswards=[np.cross(i,j) for i,j in zip(forwards,upwards)]



def skew_to_x(S):
    SS=(S-S.T)/2
    return np.array([SS[1,0],SS[2,0],S[2,1]])

def skew(x):
    return np.array([[0,-x[2],x[1]],
                     [x[2],0,-x[0]],
                     [-x[1],x[0],0]])

omegas=np.zeros((R_array.shape[0],3))
omegas[1:]=[skew_to_x(j@(i.T)-np.eye(3)) for i,j in zip(R_array[:-1],R_array[1:])]
omegas[:,0]=omegas[:,0]*1.0/df['dt']
omegas[:,1]=omegas[:,1]*1.0/df['dt']
omegas[:,2]=omegas[:,2]*1.0/df['dt']

def filtering(X,k=0.05):
    Xnew=[X[0]]
    for i,x in enumerate(X[1:]):
        xold=Xnew[-1]
        xnew=xold+k*(x-xold)
        Xnew.append(xnew)
    return np.array(Xnew)

omegas_new=filtering(omegas)

v_ned_array=np.array([df['speed[%i]'%(i)] for i in range(3)]).T

v_body_array=np.array([(i.T@(j.T)).T for i,j in zip(R_array,v_ned_array)])

gamma_array=np.array([(i.T@(np.array([0,0,9.81]).T)).T for i in R_array])

for i in range(3):
    df.insert(df.shape[1],
              'speed_body[%i]'%(i),
              v_body_array[:,i])
    df.insert(df.shape[1],
              'gamma[%i]'%(i),
              gamma_array[:,i])
    df.insert(df.shape[1],
              'omega[%i]'%(i),
              omegas_new[:,i])
    
dragdirs=np.zeros((v_body_array.shape[0],3,5))
liftdirs=np.zeros((v_body_array.shape[0],3,5))
slipdirs=np.zeros((v_body_array.shape[0],3,5))

alphas=np.zeros((v_body_array.shape[0],1,5))
sideslips=np.zeros((v_body_array.shape[0],1,5))

for k,v_body in enumerate(v_body_array):
    
    
    v_in_ldp=np.cross(crosswards,np.cross((v_body-np.cross(cp_list,omegas_new[k])),crosswards))
    
    dd=-v_in_ldp
    dd=dd.T@np.diag(1.0/(np.linalg.norm(dd,axis=1)+1e-8))

    ld=np.cross(crosswards,v_in_ldp)
    ld=ld.T@np.diag(1.0/(np.linalg.norm(ld,axis=1)+1e-8))
              
    sd=-(v_body-np.cross(cp_list,omegas_new[k])-v_in_ldp)
    sd=sd.T@np.diag(1.0/(np.linalg.norm(sd,axis=1)+1e-8))
    
    dragdirs[k,:,:]=R_array[k]@(dd@np.diag(Aire_list)*np.linalg.norm(v_in_ldp)**2)
    liftdirs[k,:,:]=R_array[k]@(ld@np.diag(Aire_list)*np.linalg.norm(v_in_ldp)**2)
    slipdirs[k,:,:]=R_array[k]@(sd@np.diag(Aire_list)*np.linalg.norm(v_in_ldp)**2)
    
    alphas_d=np.diag(v_in_ldp@(np.array(forwards).T))/(np.linalg.norm(v_in_ldp,axis=1)+1e-8)
    alphas_d=np.arccos(alphas_d)
    alphas_d=np.sign(np.diag(v_in_ldp@np.array(upwards).T))*alphas_d
    
    x=np.linalg.norm(v_in_ldp,axis=1)
    y=np.linalg.norm(v_body-np.cross(cp_list,omegas_new[k])-v_in_ldp,axis=1)
    sideslips_d=np.arctan2(y,x)
        
    alphas[k,:,:]=alphas_d
    sideslips[k,:,:]=sideslips_d

    
df.insert(df.shape[1],
          'liftdirs',
          [i for i in liftdirs])
        
df.insert(df.shape[1],
          'dragdirs',
          [i for i in dragdirs])     

df.insert(df.shape[1],
          'slipdirs',
          [i for i in slipdirs])  
        
df.insert(df.shape[1],
          'alphas',
          [i for i in alphas])    

df.insert(df.shape[1],
          'sideslips',
          [i for i in sideslips])    

df.insert(df.shape[1],
          'thrust_dir_ned',
          [i[:,0]*j**2 for i,j in zip(df['R'],df['omega_c[5]'])])

import numpy as np
delt=np.array([df['PWM_motor[%i]'%(i)] for i in range(1,5)]).T
delt=np.concatenate((np.zeros((len(df),1)),delt),axis=1).reshape(-1,1,5)
delt=(delt-1530)/500*15.0/180.0*np.pi
delt[:,:,0]*=0
delt[:,:,2]*=-1.0
delt[:,:,4]*=-1.0

df.insert(df.shape[1],
          'deltas',
          [i for i in delt])


def compute_params_simple():
          ct = 1.1e-4
          a_0 =  0.07
          a_s =  0.3391
          d_s =  15.0*np.pi/180
          cl1sa = 5
          cd1fp = 2.5
          k0 = 0.1
          k1 = 0.1
          k2 = 0.1
          cd0fp =  1e-2
          cd0sa = 0.3
          cd1sa = 1.0
          m= 8.5
          
          coeffs_0=np.array([ct,
                             a_0,
                             a_s,
                             d_s, 
                             cl1sa, 
                             cd1fp, 
                             k0, k1, k2, 
                             cd0fp, 
                             cd0sa, cd1sa,m])
          return coeffs_0

coeffs_0=compute_params_simple()


def compute_params_complex():
    ct = 1.1e-4
    a_0 =  0.07
    a_s =  0.3391
    d_s =  15.0*np.pi/180
    cl1sa = 5
    cd1fp = 2.5
    k0 = 0.1
    k1 = 0.1
    k2 = 0.1
    cd0fp =  1e-2
    cs= 0.5
    cl1fp=5
    cd0sa = 0.3
    cd1sa = 1.0
    m= 8.5
    
    coeffs_0_complex=np.array([ct,
                        a_0,
                        a_s,
                        d_s, 
                        cl1sa, 
                        cl1fp,
                        k0, k1, k2, 
                        cs,
                        cd0fp, cd0sa, 
                        cd1sa, cd1fp,
                        a_0,
                        a_s,
                        d_s, 
                        cl1sa, 
                        cl1fp,
                        k0, k1, k2,
                        cs,
                        cd0fp, cd0sa, 
                        cd1sa, cd1fp,
                        m])
    return coeffs_0_complex
coeffs_0_complex=compute_params_complex()



#%% modeling with new params 
opti_path = "/home/mehdi/Documents/id_mod_helice/scipy_solve/"
for name in sort(os.listdir(opti_path)):
    if ".json" in name:
        with open(opti_path+name,'r') as f:
            print(name)
            
            # print(len(coeff_complex))
    
    #%%
import pandas as pd 
list_keys_simple=["cost","ct","a_0", "a_s", "d_s", "cl1sa", "cd1fp", "k0", "k1", "k2", "cd0fp", "cd0sa", "cd1sa","m"]
data_simple={keys : list() for keys in list_keys_simple}
list_keys_complex=["cost","ct",\
    "a_0", "a_s", "d_s", "cl1sa", "cl1fp", "k0", "k1", "k2", "cs", "cd0fp", "cd0sa", "cd1sa", "cd1fp", \
    "a_0_v", "a_s_v", "d_s_v", "cl1sa_v", "cl1fp_v", "k0_v", "k1_v", "k2_v", "cs_v", "cd0fp_v", "cd0sa_v", "cd1sa_v", "cd1fp_v", \
    "m"]
data_complex={keys : list() for keys in list_keys_complex}

for name in sort(os.listdir(opti_path)):
    if ".json" in name:
        with open(opti_path+name,'r') as f:
            opti_params = json.load(f)
            coeff =opti_params['X']
    
        if "fm_False" in name:
            fix_mass=False
        else:
            fis_mass=True
        if "fc_False" in name:
            fix_ct=False
        else:
            fis_ct=True
        if "sideslip_False" in name:
            no_slip=True
        else:
            no_slip=False
        if "INITONES" in name:
            X0=np.ones(len(coeff))
        elif "GOODINIT" in name:
            X0=np.ones(len(coeff))
        else:
            X0=coeffs_0
            
        if "COMPLEX" in name :
            for p,keys in enumerate(list_keys_complex):
                if p==0:
                    data_complex['cost'].append(opti_params['cost'])
                else:
                    data_complex[keys].append(coeff[p-1])
        elif "SIMPLE" in name:
            for p,keys in enumerate(list_keys_simple):
                if p==0:
                    data_simple['cost'].append(opti_params['cost'])
                else:
                    data_simple[keys].append(coeff[p-1]*X0[p-1])
                
                
data_simple=pd.DataFrame(data=data_simple)
data_complex=pd.DataFrame(data=data_complex)     

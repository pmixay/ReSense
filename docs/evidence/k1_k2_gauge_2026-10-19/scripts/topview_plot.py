import sys, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
d=np.load(sys.argv[1]); xyz=d['xyz']; z0=np.percentile(xyz[:,2],3)
fig,ax=plt.subplots(2,1,figsize=(18,10))
for a,(lo,hi) in zip(ax,((0.0,0.5),(0.6,3.0))):
    m=(xyz[:,2]-z0>lo)&(xyz[:,2]-z0<hi)
    a.scatter(xyz[m,0],xyz[m,1],s=0.4,c='0.3')
    for n,col in (('base','r'),('cand','m')):
        y=d[n]; a.plot(d['X'],y,col,label=n+' axis'); a.plot(d['X'],y+1.05,col+':'); a.plot(d['X'],y-1.05,col+':')
    for x in sys.argv[3:]: a.axvline(float(x),color='b',lw=0.5)
    a.set_ylim(-9,9); a.set_title(f'{sys.argv[2]}  height above lowest returns {lo}-{hi} m'); a.legend(loc='upper left')
plt.tight_layout(); plt.savefig(sys.argv[1].replace('.npz','.png'),dpi=70)

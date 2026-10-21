import json,sys
sys.path.insert(0,'/home/user/ReSense/scripts')
import gauge_stability as g
tr=json.load(open(sys.argv[1]))['rows']; ps=g.driven_path(json.load(open(sys.argv[2]))['rows'])
xs=[40.,60.,90.,120.]
e=g.path_errors(tr,ps,xs)
step=int(sys.argv[3]) if len(sys.argv)>3 else 8
for k in sorted(e):
    if k%step==0: r=tr[k]; print(k, 'valid=%.0f'%r['axis_valid'], ' '.join('%g:%.2f'%(x,v) for x,v in e[k].items()), 'curv=%.2e'%(2*r['half_curv']), 'step' if 'half_step' in r else '')

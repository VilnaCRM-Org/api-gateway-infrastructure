"""Planning check: no forward dependency in the epics ordered story list.

Run from anywhere with `python3 -B evidence/check_ordered_list.py`. It parses
the "Ordered story list" table and the dependency bullets of
epics-stories.md and checks four orders: D-A12 branch A (rows 21a and 31b
dropped), branch B, the branch-B fallback found in TEST (contingency halves
before the row-23 retry and before 31c; 31b not applicable), and the
fallback found only in PROD (a PROD 23-F3 after 31b). The two fallback
orders are model checks: their contingency edges are encoded below from
the epics "Contingency rows" bullet, not parsed. Exit 1 on any violation.
"""
import os,re,sys
s=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','epics-stories.md')).read()
sec=s[s.index('## Ordered story list'):]
rows=re.findall(r'^\| (\d+[a-c]?) \|',sec[:sec.index('Revision 1\'s rows')],re.M)
print('rows',len(rows),rows)
needs={}
for m in re.finditer(r'^- (G[\d.]+[ab]?|XP-A\d+)[^(\n]*\((\w+)(?:, branch B)?\) needs ([^\n]*)',sec,re.M):
    row=m.group(2); txt=m.group(3)
    base,_,extra=txt.partition('under branch B also')
    base=re.split(r'\.\s',base)[0]  # first sentence only; later prose is not a dependency
    n=lambda t:[x for x in re.findall(r'\b(\d+[a-c]?)\b',re.sub(r'\([^)]*\)','',t)) if x in rows]
    needs[row]=(n(base),n(extra))
for m in re.finditer(r'^- (G[\d.]+) \((\d+)\) and (G[\d.]+) \((\d+)\) need ([^\n]*)',sec,re.M):
    ns=[x for x in re.findall(r'\b(\d+[a-c]?)\b',m.group(5)) if x in rows]
    needs[m.group(2)]=(ns,[]); needs[m.group(4)]=(ns,[])
needs['12']=(['7','9','10'],[])
print("parsed",len(needs))
def check(order,branchB,label):
    pos={r:i for i,r in enumerate(order)}; bad=[]
    for r,(b,e) in needs.items():
        if r not in pos: continue
        for d in b+(e if branchB else []):
            if d not in pos: bad.append((r,d,'missing'))
            elif pos[d]>=pos[r]: bad.append((r,d,'forward'))
    print(label,'rows',len(order),'violations',bad)
    return bad
A=[r for r in rows if r not in('21a','31b')]
B=list(rows)
# branch B with fallback: TEST halves after 21a,22 before 23 retry; PROD halves after 31a before 31c; 31b n/a
F=list(rows); i=F.index('23'); F[i:i]=['23-F3T','23-F1T','23-F2T']; F.remove('31b'); j=F.index('31c'); F[j:j]=['23-F1P','23-F2P']
needs['23-F3T']=(['21a','22'],[]); needs['23-F1T']=(['23-F3T'],[]); needs['23-F2T']=(['23-F1T'],[])
needs['23-F1P']=(['31a','23-F2T'],[]); needs['23-F2P']=(['23-F1P'],[])
needs_fb=dict(needs); needs_fb['23']=(needs['23'][0]+['23-F2T'],[]); needs_fb['31c']=(['31a','23-F2P'],[])
bad=check(A,False,'branch A')+check(B,True,'branch B')
saved=needs; needs=needs_fb; bad+=check(F,False,'branch B fallback (TEST)'); needs=saved
P=list(rows); j=P.index('31c'); P[j:j]=['23-F3P','23-F1P','23-F2P']
needs_p=dict(needs); needs_p['23-F3P']=(['31b'],[]); needs_p['23-F1P']=(['23-F3P'],[]); needs_p['23-F2P']=(['23-F1P'],[]); needs_p['31c']=(['31a','31b','23-F2P'],[])
saved=needs; needs=needs_p; bad+=check(P,True,'branch B fallback (PROD only)'); needs=saved
sys.exit(1 if bad else 0)

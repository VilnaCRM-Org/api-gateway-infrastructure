"""Planning check: no forward dependency in the epics ordered story list.

Run from anywhere with `python3 -B evidence/check_ordered_list.py`. It parses
the "Ordered story list" table and the dependency bullets of
epics-stories.md and checks four orders: D-A12 branch A (rows 21a and 31b
dropped), branch B, the branch-B fallback found in TEST (23-F3 and 23-F2
before the row-23 retry, 23-F1 after it, PROD halves before 31c; 31b not
applicable), and the
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
bad=check(A,False,'branch A')+check(B,True,'branch B')
# Model of the branch-B fallback found in TEST (revision 9, R5-4): the TEST
# halves of 23-F3 and 23-F2 run after 21a and 22 and before the row-23
# retry; the TEST half of 23-F1 follows the retry; the PROD halves (23-F2,
# 23-F1) run after 31a and before 31c; row 31b is not applicable.
F=list(rows); F.remove('31b')
i=F.index('23'); F[i:i]=['23-F3T','23-F2T']; F.insert(F.index('23')+1,'23-F1T')
j=F.index('31c'); F[j:j]=['23-F2P','23-F1P']
nf=dict(needs)
nf['23-F3T']=(['21a','22'],[]); nf['23-F2T']=(['23-F3T'],[])
nf['23']=(needs['23'][0]+['21a','23-F3T','23-F2T'],[])
nf['23-F1T']=(['23'],[])
nf['23-F2P']=(['31a','23-F2T'],[]); nf['23-F1P']=(['23-F2P','23-F1T'],[])
nf['31c']=(['31a','23-F2P','23-F1P'],[])
saved=needs; needs=nf; bad+=check(F,False,'branch B fallback (TEST)'); needs=saved
# Model of the fallback found only in PROD: a PROD 23-F3 after 31b, then the
# PROD halves of 23-F2 and 23-F1, then the 31c retry; TEST stays on branch B.
P=list(rows); j=P.index('31c'); P[j:j]=['23-F3P','23-F2P','23-F1P']
np_=dict(needs); np_['23-F3P']=(['31b'],[]); np_['23-F2P']=(['23-F3P'],[]); np_['23-F1P']=(['23-F2P'],[]); np_['31c']=(['31a','31b','23-F3P','23-F2P','23-F1P'],[])
saved=needs; needs=np_; bad+=check(P,True,'branch B fallback (PROD only)'); needs=saved
sys.exit(1 if bad else 0)

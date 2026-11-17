#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
from pathlib import Path
import concurrent.futures as cf
import hashlib,json,os,re,shutil,subprocess,tempfile
import argparse
parser=argparse.ArgumentParser(description='Conservative inventory hunk audit; reads sources, never applies changes. Requires gh/API access unless cached.')
parser.add_argument('--foundation-root',type=Path,required=True)
parser.add_argument('--inventory',type=Path,required=True)
parser.add_argument('--cache',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
NEW=args.foundation_root.resolve();CACHE=args.cache.resolve();CACHE.mkdir(parents=True,exist_ok=True)
s=args.inventory.read_text()
rows=[]
for m in re.finditer(r'^\| (E\d+) \| \[`([0-9a-f]+)`\]\((https://[^)]+)/(?:-/)?commit/([0-9a-f]{40})\) \| (.*?) \| (.*?) \|$',s,re.M):
 rows.append(dict(id=m[1],repository=m[3],sha=m[4],change=m[5],original_mode=m[6]))
assert len(rows)==143,len(rows)
SNAPSHOTS={
'c72c7c0ec132ad2ce2fe9fad7b0c728d9faee2fc':('different-codec-review','lib/lz4/lz4.h','Updated base declares1.11.1, not old Electro1.11.0; kernel integration blockers recorded separately.'),
'90210de4b779d40496dee0b89081780eeddf2a60':('missing-import','net/ipv4/tcp_bbr3.c','BBRv3 implementation is absent; native tcp_bbr.c is not evidence of BBRv3.'),
'ae63c92098d94bdad1696c74a3ad2e96692118bf':('missing-import','drivers/kernelsu/UPSTREAM.json','Vendored backslashxx KSU+50 is absent.'),
'2d5786b9129a254a87ac358c8bec0203ccd53351':('missing-import','drivers/kernelsu/manager/manager_identity.h','FinaSU KSU manager adapter is absent; this SHA was an app review pin, not a kernel cherry-pick.'),
'5e9feb6f3fce42423f56b37e344052c59ec16b66':('missing-import','fs/nomount/nomount.c','NoMount vendored source is absent; do not test this pin’s installer-only commit patch.'),
'45a057536ddba12fd59fb583a8f5375f83be703e':('missing-import','fs/susfs.c','Native SUSFS port is absent; canonical GitLab pin is not a native4.14 patch.'),
}
def runpatch(patch,files,reverse):
 with tempfile.TemporaryDirectory(prefix='electro-base-probe-') as d:
  d=Path(d)
  for name in files:
   p=NEW/name
   if p.is_file() and not p.is_symlink():
    q=d/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
  args=['git','apply','--check','--whitespace=nowarn']+(['--reverse'] if reverse else [])+['-']
  r=subprocess.run(args,cwd=d,input=patch,text=True,capture_output=True)
  return r.returncode==0,r.stderr[:1500]
def audit(row):
 row=row.copy();sha=row['sha']
 if sha.startswith('40213eb4'):
  row.update(status='excluded-bbrplus',evidence='Explicit user exclusion. Updated16 has no BBRplus file/config; none carried over.');return row
 if sha in SNAPSHOTS:
  status,path,note=SNAPSHOTS[sha];row.update(status=status,paths=[path],evidence=note)
  if status=='missing-import':assert not (NEW/path).exists(),path
  return row
 repo=row['repository'].replace('https://github.com/','');file=CACHE/(sha+'.json')
 if not file.exists():
  r=subprocess.run(['gh','api',f'repos/{repo}/commits/{sha}'],text=True,capture_output=True,timeout=80)
  if r.returncode:
   row.update(status='unresolved-metadata',evidence=r.stderr[:300]);return row
  file.write_text(r.stdout)
 m=json.loads(file.read_text());files=m.get('files',[])
 row['subject']=m['commit']['message'].splitlines()[0]
 row['paths']=[f['filename'] for f in files]
 row['files_total']=len(files);patch='';covered=[]
 for f in files:
  if 'patch' not in f:continue
  name=f['filename'];prev=f.get('previous_filename',name)
  if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError(name)
  patch+='diff --git a/'+prev+' b/'+name+'\n'
  if f['status']=='added':patch+='new file mode 100644\n'
  elif f['status']=='removed':patch+='deleted file mode 100644\n'
  elif f['status']=='renamed':
   # Rename/mode-only changes need actual Git patch metadata; not guessed here.
   continue
  patch+='--- '+('/dev/null' if f['status']=='added' else 'a/'+prev)+'\n'
  patch+='+++ '+('/dev/null' if f['status']=='removed' else 'b/'+name)+'\n'
  patch+=f['patch']+'\n';covered.append(name)
 row['files_with_text_patch']=len(covered);row['patch_sha256']=hashlib.sha256(patch.encode()).hexdigest()
 # Reject a partial API diff instead of turning omitted files into false passes.
 if len(files)!=len(covered) or not patch:
  row.update(status='unresolved-partial-diff',evidence='API diff omitted/renamed/binary files; no whole-change equivalence conclusion.');return row
 reverse,revmsg=runpatch(patch,covered,True);forward,fwdmsg=runpatch(patch,covered,False)
 row['reverse_check']=reverse;row['forward_check']=forward
 if reverse and not forward:row.update(status='reverse-hunks-match',evidence='All recorded donor text hunks reverse-apply to pinned16. Hunk equivalence only, NOT proof of all native correction semantics.')
 elif forward and not reverse:row.update(status='forward-candidate',evidence='All donor text hunks forward-apply to pinned16. Candidate for missing change, NOT approval to apply raw donor or proof equivalent code is absent.')
 else:row.update(status='semantic-review-required',evidence='Patch-direction test is ambiguous or neither direction applies. Need final-code/native-correction comparison; do not overwrite maintainer changes.',reverse_diagnostic=revmsg,forward_diagnostic=fwdmsg)
 return row
results=[]
with cf.ThreadPoolExecutor(max_workers=6) as ex:
 for i,r in enumerate(ex.map(audit,rows),1):
  results.append(r)
  if i%20==0:print('audited',i,flush=True)
out={'foundation':'766a32ab1c8b889ac049ccd367e82786e5953bc0','previous_electro':'402566a8597ae7f0ecf3f87054b77aa7c18acdf0','method':'Safe donor text-hunk probes on disposable minimal files copied from pinned16, outside any Git checkout; snapshot imports handled by specific source-presence checks. Conservative mechanical screen, not complete semantic equivalence audit.','rows':results}
args.output.write_text(json.dumps(out,indent=2)+'\n')
from collections import Counter
print(Counter(r['status'] for r in results))

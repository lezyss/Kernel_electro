#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted SUSFS 2.4 registry/statfs/FD models, not live kernel execution."""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

from provenance_240 import reviewed_preimages, SCOPE
from test_integration import ROOT, extract


def registry(root, negative=None):
    text = (root / 'fs/susfs.c').read_text()
    names = ['susfs_add_sus_type', 'susfs_is_sus_type_rcu', 'susfs_av_rule_hash',
             'susfs_add_sus_avd_allowed_by_type', 'susfs_spoof_avd_allowed_rcu']
    bodies = '\n'.join(extract(text, name) for name in names)
    if negative == 'type-bucket':
        bodies = bodies.replace('if (entry->type_value == type_value)', 'if (true)')
    elif negative == 'av-tuple':
        bodies = re.sub(r'\bentry->t_type == t_type &&', 'true &&', bodies)
    return r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
typedef uint32_t u32; typedef uint16_t u16;
#define GFP_ATOMIC 1
#define SUSFS_LOGI_RL(...) ((void)0)
#define SUSFS_LOGE(...) ((void)0)
struct hlist_node {struct hlist_node *next;};
struct st_susfs_sus_type_hlist {struct hlist_node node; u32 type_value;};
struct susfs_sus_av_rule {struct hlist_node node;u32 s_type,t_type,c_type,orig_avd_allowed;};
static struct hlist_node *SUS_TYPE_HLIST[8], *SUS_AVD_ALLOWED_HLIST[8];
static int susfs_lock_sus_type, susfs_lock_sus_avd_allowed_hlist;
static bool locked, fail_alloc;
#define spin_lock_irqsave(lock,flags) do {assert(!locked);locked=true;(flags)=0;(void)(lock);}while(0)
#define spin_unlock_irqrestore(lock,flags) do {assert(locked);locked=false;(void)(lock);(void)(flags);}while(0)
static void *kzalloc(size_t size,int mode) {assert(locked && mode==GFP_ATOMIC);return fail_alloc?NULL:calloc(1,size);}
#define kfree free
#define bucket(k) ((k)&7)
/* Deliberately tiny hash table: unrelated type/AV keys collide frequently. */
#define hash_for_each_possible_rcu(table,entry,member,key) \
 for(entry=(void *)(table)[bucket(key)];entry;entry=(void *)entry->member.next)
#define hash_for_each_possible_safe(table,entry,tmp,member,key) \
 for(entry=(void *)(table)[bucket(key)];entry && ((tmp)=entry->member.next,1);entry=(void *)(tmp))
#define hash_add_rcu(table,node,key) do {(node)->next=(table)[bucket(key)];(table)[bucket(key)]=(node);}while(0)
static u32 hash_32(u32 v,unsigned bits) {(void)bits;return v*UINT32_C(0x61c88647);}
static u32 rol32(u32 x,unsigned n) {return (x<<n)|(x>>(32-n));}
''' + bodies + r'''
int main(void) {
 unsigned cases=0;
 fail_alloc=true; assert(susfs_add_sus_type("fail",10)==-ENOMEM);assert(!locked);
 assert(susfs_add_sus_avd_allowed_by_type(1,2,3,4)==-ENOMEM);assert(!locked);fail_alloc=false;
 for(u32 t=1;t<1024;t+=2) {assert(!susfs_add_sus_type("test",t));cases++;}
 for(u32 t=0;t<1200;t++) {assert(susfs_is_sus_type_rcu(t)==(t<1024 && (t&1)));cases++;}
 assert(susfs_add_sus_type("duplicate",1)==-EINVAL);
 for(u32 s=1;s<12;s++)for(u32 t=1;t<20;t++)for(u32 c=1;c<5;c++) {
  assert(!susfs_add_sus_avd_allowed_by_type(s,t,c,(s<<20)|(t<<8)|c));cases++;
 }
 for(u32 s=0;s<14;s++)for(u32 t=0;t<22;t++)for(u32 c=0;c<6;c++) {
  u32 allowed=UINT32_MAX;
  susfs_spoof_avd_allowed_rcu(s,t,c,&allowed);
  assert(allowed==((s>0&&s<12&&t>0&&t<20&&c>0&&c<5)?((s<<20)|(t<<8)|c):UINT32_MAX));cases++;
 }
 assert(!susfs_add_sus_avd_allowed_by_type(1,2,3,0));
 u32 allowed=0;susfs_spoof_avd_allowed_rcu(1,2,3,&allowed);assert(allowed==((1<<20)|(2<<8)|3));
 assert(!locked);printf("PASS: %u extracted type/AV full-key, collision, first-value and allocation cases\n",cases);
 for(unsigned b=0;b<8;b++) {
  struct hlist_node *n,*next;
  for(n=SUS_TYPE_HLIST[b];n;n=next){next=n->next;free(n);}
  for(n=SUS_AVD_ALLOWED_HLIST[b];n;n=next){next=n->next;free(n);}
 }
}
'''


def fd(root, negative=None):
    body = extract((root / 'drivers/kernelsu/feature/sucompat.c').read_text(),
                   'ksu_susfs_post_execve')
    if negative == 'pre-exec-fd':
        body = body.replace('su_session && !retval &&', 'su_session &&')
    return r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define CONFIG_KSU_SUSFS 1
#define CONFIG_KSU_TAMPER_SYSCALL_TABLE 1
#undef __always_inline
#define __always_inline inline
static bool root_uid,ksu_domain;static int installs;
#define GLOBAL_ROOT_UID 0
static int current_uid(void) {return root_uid?0:10000;}
static bool uid_eq(int a,int b) {return a==b;}
static bool is_ksu_domain(void) {return ksu_domain;}
static int ksu_install_su_fd(void) {installs++;return 42;}
''' + body + r'''
int main(void) {
 unsigned cases=0;long results[]={-1,-14,-2,0,1};
 for(unsigned session=0;session<2;session++)for(unsigned root=0;root<2;root++)
 for(unsigned domain=0;domain<2;domain++)for(unsigned r=0;r<5;r++) {
  root_uid=root;ksu_domain=domain;installs=0;
  assert(ksu_susfs_post_execve(session,results[r])==results[r]);
  assert(installs==(session&&root&&domain&&!results[r]));cases++;
 }
 printf("PASS: %u extracted post-exec SU-session FD authorization/result cases\n",cases);
}
'''


def statfs(root, negative=None):
    text = (root / 'fs/statfs.c').read_text()
    body = extract(text, 'susfs_statfs_by_dentry') + '\n' + extract(text, 'vfs_statfs')
    if negative == 'overwrite-flags':
        body = body.replace('return susfs_statfs_by_dentry(path->dentry, path->mnt, buf, &is_fuse);',
                            'error = susfs_statfs_by_dentry(path->dentry, path->mnt, buf, &is_fuse);\n\t\t\tif (!error) buf->f_flags = calculate_f_flags(path->mnt);\n\t\t\treturn error;')
    return r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#define CONFIG_KSU_SUSFS_SUS_KSTAT 1
struct kstatfs {int f_flags,f_frsize,f_bsize;};
struct inode {int unused;};
struct dentry;
struct super_operations {int (*statfs)(struct dentry *,struct kstatfs *);};
struct super_block {struct super_operations *s_op;};
struct dentry {struct super_block *d_sb;struct inode *inode;};
struct vfsmount {int flags;};
struct path {struct dentry *dentry;struct vfsmount *mnt;};
static bool app,spoof,marked;static int deny,fail,fallbacks,spoofs;
static bool susfs_is_current_app_uid(void) {return app;}
static struct inode *d_backing_inode(struct dentry *d) {return d->inode;}
static bool susfs_is_inode_sus_kstat(struct inode *i,bool *f) {(void)i;*f=false;return marked;}
static int security_sb_statfs(struct dentry *d) {(void)d;return deny;}
static int calculate_f_flags(struct vfsmount *m) {return m->flags;}
static int susfs_sus_kstat_spoof_vfs_statfs(struct inode *i,struct kstatfs *b,bool *f) {
 (void)i;(void)f;spoofs++;if(!spoof)return 1;b->f_flags=101;b->f_bsize=4096;return 0;
}
static int native_statfs(struct dentry *d,struct kstatfs *b) {(void)d;fallbacks++;b->f_bsize=8192;return fail;}
static int statfs_by_dentry(struct dentry *d,struct kstatfs *b) {
 if(!d->d_sb->s_op->statfs)return -ENOSYS;
 memset(b,0,sizeof(*b));if(deny)return deny;return native_statfs(d,b);
}
''' + body + r'''
int main(void) {
 struct inode inode={0};struct super_operations op={native_statfs};struct super_block sb={&op};
 struct dentry d={&sb,&inode};struct vfsmount m={222};struct path p={&d,&m};struct kstatfs b;
 unsigned cases=0;
 for(unsigned a=0;a<2;a++)for(unsigned mark=0;mark<2;mark++)for(unsigned s=0;s<2;s++)
 for(unsigned denial=0;denial<2;denial++)for(unsigned failure=0;failure<2;failure++) {
  app=a;marked=mark;spoof=s;deny=denial?-EACCES:0;fail=failure?-EIO:0;fallbacks=spoofs=0;
  int got=vfs_statfs(&p,&b);bool hidden=a&&mark&&s;
  assert(got==(deny?deny:(!hidden?fail:0)));
  assert(fallbacks==(!deny&&!hidden));
  if(!got)assert(b.f_flags==(hidden?101:222));
  if(!got&&a&&mark)assert(b.f_frsize==b.f_bsize);
  cases++;
 }
 app=marked=true;deny=fail=0;op.statfs=NULL;assert(vfs_statfs(&p,&b)==-ENOSYS);
 printf("PASS: %u extracted statfs flags/fallback/security/error cases\n",cases+1);
}
'''


def lookup(root, negative=None):
    body = extract((root / 'fs/namei.c').read_text(), '__lookup_hash')
    if negative == 'lookup-before-inode':
        body = body.replace('\tdentry = lookup_real(base->d_inode, dentry, flags);', '')
        body = body.replace('\treturn dentry;\n}', '\treturn lookup_real(base->d_inode, dentry, flags);\n}')
    return r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#define CONFIG_KSU_SUSFS_SUS_PATH 1
#define LOOKUP_RCU 1
#define LOOKUP_CREATE 2
#define LOOKUP_EXCL 4
#define FUSE_SUPER_MAGIC 0x65735546
#define unlikely(x) (x)
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
struct qstr {int fake;};
struct super_block {unsigned long s_magic;};
struct inode {struct super_block *i_sb;bool hidden;};
struct dentry {struct inode *d_inode;bool fake;};
static struct qstr susfs_fake_qstr_name={1};
static struct dentry target,replacement;
static struct inode inode;
static bool allocation_fails;
static int lookups,put_count,lookup_error;
static struct dentry *lookup_dcache(const struct qstr *n,struct dentry *b,unsigned f) {(void)n;(void)b;(void)f;return NULL;}
static struct dentry *d_alloc(struct dentry *b,const struct qstr *n) {
 (void)b;if(allocation_fails)return NULL;
 struct dentry *d=n->fake?&replacement:&target;d->d_inode=NULL;d->fake=n->fake;return d;
}
static struct dentry *lookup_real(struct inode *dir,struct dentry *d,unsigned flags) {
 (void)dir;(void)flags;lookups++;if(lookup_error)return ERR_PTR(lookup_error);
 if(!d->fake)d->d_inode=&inode;
 return d;
}
static bool susfs_is_inode_sus_path(struct inode *i) {return i->hidden;}
static bool d_in_lookup(struct dentry *d) {(void)d;return false;}
static void d_lookup_done(struct dentry *d) {(void)d;}
/* Poison the released object: reading d_inode after dput would fail this test. */
static void dput(struct dentry *d) {put_count++;d->d_inode=NULL;}
''' + body + r'''
int main(void) {
 struct super_block sb;struct inode dir={&sb,false};struct dentry base={&dir,false};struct qstr name={0};
 unsigned cases=0;
 for(unsigned hidden=0;hidden<2;hidden++)for(unsigned fuse=0;fuse<2;fuse++)
 for(unsigned flags=0;flags<8;flags+=2)for(unsigned fault=0;fault<2;fault++) {
  inode=(struct inode){&sb,hidden};sb.s_magic=fuse?FUSE_SUPER_MAGIC:0;
  allocation_fails=fault;lookups=put_count=lookup_error=0;
  struct dentry *result=__lookup_hash(&name,&base,flags);
  if(fault)assert(result==ERR_PTR(-ENOMEM));
  else if(hidden&&fuse&&(flags&(LOOKUP_CREATE|LOOKUP_EXCL)))assert(result==ERR_PTR(-EACCES));
  else assert(result==(hidden?&replacement:&target));
  assert(put_count==(!fault&&hidden));
  bool rejected=hidden&&fuse&&(flags&(LOOKUP_CREATE|LOOKUP_EXCL));
  assert(lookups==(fault?0:(hidden&&!rejected?2:1)));cases++;
 }
 allocation_fails=false;lookup_error=-ENOENT;assert(__lookup_hash(&name,&base,0)==ERR_PTR(-ENOENT));
 printf("PASS: %u extracted post-lookup SUS_PATH/FUSE/create/fault/lifetime cases\n",cases+1);
}
'''


def abi(root, negative=None):
    old = reviewed_preimages(root)['include/linux/susfs.h'].decode()
    new = (root / 'include/linux/susfs.h').read_text()
    structs = dict(re.findall(r'struct (st_susfs_\w+) \{([^}]+)\};', old))
    definitions, checks = [], []
    fields = 0
    for name, body in structs.items():
        if 'struct ' in body:
            continue  # private kernel hash/list nodes are not command payloads
        replacement = re.search(r'struct ' + name + r' \{([^}]+)\};', new)
        assert replacement, name
        definitions += ['struct old_' + name + '{' + body + '};',
                        'struct new_' + name + '{' + replacement[1] + '};']
        checks.append('_Static_assert(sizeof(struct old_' + name + ')==sizeof(struct new_' + name + '), "size");')
        for field in re.findall(r'(\w+)(?:\[[^;]*\])?;', body):
            checks.append('_Static_assert(__builtin_offsetof(struct old_' + name + ',' + field +
                          ')==__builtin_offsetof(struct new_' + name + ',' + field + '), "offset");')
            fields += 1
    assert fields >= 40
    return '\n'.join(['#include <stdio.h>', '#define bool _Bool', '#define __NEW_UTS_LEN 64',
                      '#define SUSFS_MAX_LEN_PATHNAME 256',
                      '#define SUSFS_FAKE_CMDLINE_OR_BOOTCONFIG_SIZE 8192',
                      '#define SUSFS_ENABLED_FEATURES_SIZE 8192',
                      '_Static_assert(sizeof(long)==8, "SUSFS target is LP64");'] + definitions + checks +
                     ['int main(void) {puts("PASS: extracted LP64 command-payload sizes and ' + str(fields) + ' field offsets");}'])


def contracts(root, previous):
    old = previous['security/selinux/ss/services.c'].decode()
    current = (root / 'security/selinux/ss/services.c').read_text()
    for name in ['security_compute_av', 'security_compute_av_user',
                 'string_to_context_struct', 'security_context_to_sid_core']:
        assert extract(old, name) == extract(current, name), 'real SELinux core changed: ' + name
    old = previous['drivers/kernelsu/feature/kernel_umount.c'].decode()
    current = (root / 'drivers/kernelsu/feature/kernel_umount.c').read_text()
    # Physical unmount eligibility and credential restoration stay in production.
    for token in ['if (!ksu_kernel_umount_enabled)', 'if (!ksu_module_mounted)',
                  'if (!is_zygote_child)', 'if (!ksu_uid_should_umount(new_uid)',
                  'override_creds(ksu_cred)', 'revert_creds(saved)', 'susfs_try_umount(new_uid)']:
        assert token in old and token in current, token
    assert current.index('if (!is_zygote_child)') < current.index('susfs_set_current_proc_umounted()')
    assert current.index('revert_creds(saved)') < current.index('out_susfs:') < current.index('susfs_set_current_proc_umounted()')
    assert current.count('goto out_susfs;') == 2
    for path, count in [('hook/syscall_table_hook_arm64.c', 8)]:
        source = (root / 'drivers/kernelsu' / path).read_text()
        assert len(re.findall(r'bool su_session = ksu_handle_sys_execve(?:at)?\(', source)) == count
        assert source.count('return ksu_susfs_post_execve(su_session, retval);') == count
    sepolicy = (root / 'drivers/kernelsu/selinux/sepolicy.c').read_text()
    assert 'if (effect == AVTAB_ALLOWED)\n\t\t\tsusfs_add_sus_avd_allowed_by_type' in sepolicy
    for name in ['susfs_add_sus_type', 'susfs_add_sus_avd_allowed_by_type']:
        body = extract((root / 'fs/susfs.c').read_text(), name)
        assert 'spin_lock_irqsave' in body and 'GFP_ATOMIC' in body and 'mutex_lock' not in body
    # Existing kallsyms hooks still declare/call this global 4.14 helper.
    assert extract(previous['fs/susfs.c'].decode(), 'susfs_starts_with') == extract((root / 'fs/susfs.c').read_text(), 'susfs_starts_with')
    assert 'static inline bool susfs_starts_with' not in (root / 'include/linux/susfs_def.h').read_text()
    # Preserve the established 4.14 mutex-based cmdline snapshot/fallback ABI.
    for name in ['susfs_set_cmdline_or_bootconfig', 'susfs_spoof_cmdline_or_bootconfig']:
        assert extract(previous['fs/susfs.c'].decode(), name) == extract((root / 'fs/susfs.c').read_text(), name)
    print('PASS: real SELinux core preserved; physical-unmount guards, 8 ARM64 native/compat ABI wrappers, atomic writers and cmdline contracts')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    previous = reviewed_preimages(ROOT)
    assert set(previous) == SCOPE
    contracts(ROOT, previous)
    with tempfile.TemporaryDirectory(prefix='susfs-240-model-') as directory:
        directory = Path(directory)
        def run(builder, negative=None):
            source, binary = directory / 'model.c', directory / 'model'
            source.write_text(builder(ROOT, negative))
            subprocess.run(shlex.split(args.cc) + ['-std=gnu11', '-O1', '-g', '-Wall', '-Wextra',
                           '-Werror', '-Wno-unused-parameter', '-Wno-unused-function',
                           '-fsanitize=undefined', '-fno-sanitize-recover=all', str(source),
                           '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            if negative:
                assert result.returncode != 0, 'negative control survived: ' + negative
                print('PASS: rejected ' + negative)
            else:
                assert result.returncode == 0, result.stderr
                print(result.stdout, end='')
        for builder in [registry, fd, statfs, lookup, abi]:
            run(builder)
        if args.self_test_negatives:
            for builder, name in [(registry, 'type-bucket'), (registry, 'av-tuple'),
                                  (fd, 'pre-exec-fd'), (statfs, 'overwrite-flags'),
                                  (lookup, 'lookup-before-inode')]:
                run(builder, name)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

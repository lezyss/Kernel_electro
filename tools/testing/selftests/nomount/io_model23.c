/* SPDX-License-Identifier: GPL-2.0 */
/* Native 4.14 VFS fixtures. Does NOT call a real VFS, filesystem or LSM. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#undef __always_inline
#define __always_inline inline
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define smp_load_acquire(p) (*(p))
#define unlikely(x) (x)
#define IDMAP_ARG
#define IDMAP_PATH(p)
#define IDMAP_CALL
#define FLAGS_ARG
#define FLAGS_VAL
#define O_LARGEFILE 0100000
#define SEEK_DATA 3
#define SEEK_HOLE 4
#define EXT4_SUPER_MAGIC 0xEF53
#define F2FS_SUPER_MAGIC 0xF2F52010
#define S_ISREG(m) (((m)&S_IFMT)==S_IFREG)
#define GFP_KERNEL 0
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
struct rcu_head { int unused; };
struct super_block { unsigned long s_magic; bool ro; };
struct inode_operations { int id; };
static const struct inode_operations nm_file_iops={1},nm_dir_iops={2};
struct inode { void *i_private; const struct inode_operations *i_op; struct super_block *i_sb; int i_mode; loff_t size; };
struct dentry { struct inode *d_inode; struct super_block *d_sb; };
struct path { struct dentry *dentry; };
struct file { void *private_data,*f_cred; unsigned f_flags; loff_t f_pos; struct inode *inode; int refs; };
struct nm_dir_node { struct nm_leaf *owner; int refs; };
struct nm_rule_array { struct nm_rule_array *next; };
struct nm_leaf { int refs; struct nm_rule_array *rules; struct nm_leaf *next; struct nm_dir_node *this_dir; };
struct nm_inode_info { struct path r_path; union { struct nm_dir_node *dir_node; struct nm_leaf *leaf; }; struct file *r_file; struct rcu_head rcu; };
static struct nm_rule_array *nm_retired_arrays;
static struct nm_leaf *nm_retired_leaves;
static int nm_mutex,nm_reclaim_work,locks,scheduled,graces,leaf_frees,array_frees,info_frees,paths_put,dir_puts;
struct work_struct { int unused; };
#define mutex_lock(p) ((void)(p),locks++)
#define mutex_unlock(p) ((void)(p),locks--)
#define rcu_dereference_protected(x,l) (x)
#define lockdep_is_held(p) true
#define RCU_INIT_POINTER(p,v) ((p)=(v))
#define schedule_work(p) ((void)(p),scheduled++)
static void synchronize_rcu(void) { assert(!locks);graces++; }
static bool atomic_dec_and_test(int *p) { assert(*p>0);return --*p==0; }
static void nm_free_leaf(struct nm_leaf *l,bool deferred) { assert(graces && deferred && l->refs==0);leaf_frees++; }
static void nm_rule_array_free(struct nm_rule_array *a) { assert(graces && a);array_frees++; }
static void nm_dir_put(struct nm_dir_node *d) { if(d){assert(d->refs>0);d->refs--;dir_puts++;} }
static void path_put(struct path *p) { assert(p->dentry);paths_put++; }
#define kfree_rcu(p,m) do { info_frees++;free(p); } while(0)
static void fput(struct file *f) { assert(f->refs>0);f->refs--; }
static struct file pool[16];static int opened,open_error;static struct file *race_winner;
static struct file *dentry_open(struct path *p,unsigned flags,void *cred)
{ if(open_error)return ERR_PTR(open_error);assert(opened<16);struct file *f=&pool[opened++];*f=(struct file){.f_flags=flags,.f_cred=cred,.inode=p->dentry->d_inode,.refs=1};return f; }
static struct file *cas_file(struct file **p,struct file *old,struct file *new)
{ if(race_winner){*p=race_winner;race_winner=NULL;}struct file *v=*p;if(v==old)*p=new;return v; }
#define cmpxchg(p,o,n) cas_file(p,o,n)
#define file_inode(f) ((f)->inode)
#define i_size_read(i) ((i)->size)
static loff_t vfs_llseek(struct file *f,loff_t offset,int whence)
{ (void)whence;if(offset==999)return -ENXIO;return f->f_pos=offset+7; }
struct xattr_handler {
 int (*get)(const struct xattr_handler *,struct dentry *,struct inode *,const char *,void *,size_t);
 int (*__get)(const struct xattr_handler *,struct dentry *,struct inode *,const char *,void *,size_t);
 int (*set)(const struct xattr_handler *,struct dentry *,struct inode *,const char *,const void *,size_t,int);
};
struct nm_xattr_proxy { struct xattr_handler fake; const struct xattr_handler *orig; };
#define NM_HAS_XATTR__GET 1
#define nm_inode_is_virtual(i) ((i)->i_op==&nm_file_iops || (i)->i_op==&nm_dir_iops)
#define sb_rdonly(sb) ((sb)->ro)
#define d_backing_inode(d) ((d)->d_inode)
#define d_inode(d) ((d)->d_inode)
static const char *xattr_full_name(const struct xattr_handler *h,const char *n) { (void)h;(void)n;return "user.test"; }
static struct dentry *expected;static int set_calls,remove_calls,get_calls,orig_calls,vfs_error;
static int __vfs_getxattr(struct dentry *d,struct inode *i,const char *n,void *b,size_t z)
{ (void)n;(void)b;(void)z;assert(d==expected && i==d->d_inode);get_calls++;return 3; }
static int vfs_setxattr(struct dentry *d,const char *n,const void *b,size_t z,int flags)
{ (void)n;(void)b;(void)z;(void)flags;assert(d==expected);set_calls++;return vfs_error; }
static int vfs_removexattr(struct dentry *d,const char *n) { (void)n;assert(d==expected);remove_calls++;return vfs_error; }
static int orig_get(const struct xattr_handler *h,struct dentry *d,struct inode *i,const char *n,void *b,size_t z)
{ (void)h;(void)d;(void)i;(void)n;(void)b;(void)z;orig_calls++;return 8; }
static int orig_set(const struct xattr_handler *h,struct dentry *d,struct inode *i,const char *n,const void *b,size_t z,int f)
{ (void)h;(void)d;(void)i;(void)n;(void)b;(void)z;(void)f;orig_calls++;return 9; }
/* ACTUAL */
int main(void)
{
 struct super_block sb={.s_magic=EXT4_SUPER_MAGIC};
 struct inode backing={.i_sb=&sb,.i_mode=S_IFREG,.size=100};
 struct dentry dent={.d_inode=&backing,.d_sb=&sb};expected=&dent;
 struct nm_leaf leaf={.refs=1};
 struct nm_inode_info *info=calloc(1,sizeof(*info));assert(info);info->r_path.dentry=&dent;info->leaf=&leaf;
 struct inode inode={.i_sb=&sb,.i_mode=S_IFREG,.i_op=&nm_file_iops,.i_private=info};
 int cred1,cred2;
 struct file a={.f_cred=&cred1},b={.f_cred=&cred1},c={.f_cred=&cred2};
 assert(nm_open(&inode,&a)==0);struct file *cached=a.private_data;
 assert(info->r_file==cached && cached->refs==1 && opened==1);
 assert(nm_open(&inode,&b)==0 && b.private_data==cached && opened==1);
 assert(nm_open(&inode,&c)==0 && c.private_data!=cached && opened==2);
 nm_release(&inode,&c);assert(pool[1].refs==0);
 a.f_pos=3;b.f_pos=20;cached->f_pos=777;
 assert(nm_llseek(&a,4,SEEK_CUR)==7 && a.f_pos==7 && b.f_pos==20 && cached->f_pos==777);
 assert(nm_llseek(&b,-1,SEEK_SET)==-EINVAL && b.f_pos==20);
 assert(nm_llseek(&a,2,SEEK_END)==102);
 assert(nm_llseek(&a,10,SEEK_DATA)==17 && a.f_pos==17);
 assert(nm_llseek(&a,999,SEEK_HOLE)==-ENXIO && a.f_pos==17);
 nm_release(&inode,&a);nm_release(&inode,&b);assert(cached->refs==1);
 struct xattr_handler orig={.get=orig_get,.__get=orig_get,.set=orig_set};struct nm_xattr_proxy proxy={.orig=&orig};
 assert(nm_xattr_get(&proxy.fake,&dent,&inode,"test",NULL,0)==3);
 assert(nm_xattr__get(&proxy.fake,&dent,&inode,"test",NULL,0)==3);
 vfs_error=-EACCES;assert(nm_xattr_set(&proxy.fake,&dent,&inode,"test","x",1,0)==-EACCES);
 assert(set_calls==1 && !orig_calls);
 vfs_error=0;assert(nm_xattr_set(&proxy.fake,&dent,&inode,"test",NULL,0,0)==0 && remove_calls==1);
 sb.ro=true;assert(nm_xattr_set(&proxy.fake,&dent,&inode,"test","x",1,0)==-EROFS && set_calls==1);sb.ro=false;
 assert(nm_xattr_get(&proxy.fake,&dent,&backing,"test",NULL,0)==8);
 assert(nm_xattr__get(&proxy.fake,&dent,&backing,"test",NULL,0)==8);
 assert(nm_xattr_set(&proxy.fake,&dent,&backing,"test","x",1,0)==9);
 assert(orig_calls==3);
 inode.i_private=NULL;assert(nm_open(&inode,&a)==-ENODEV);
 assert(nm_xattr_set(&proxy.fake,&dent,&inode,"test",NULL,0,0)==-ENODATA);
 inode.i_private=info;
 open_error=-EACCES;c.f_cred=&cred2;assert(nm_open(&inode,&c)==-EACCES);open_error=0;
 /* Actual retire/reclaim preserves the extra virtual-inode leaf reference. */
 struct nm_rule_array rules={0};struct nm_dir_node dir={.owner=&leaf};leaf.this_dir=&dir;leaf.rules=&rules;leaf.refs=2;
 nm_retire_leaf_locked(&leaf);assert(!leaf.rules && !dir.owner && !leaf_frees && scheduled);
 nm_reclaim(NULL);assert(graces==1 && array_frees==1 && leaf.refs==1 && !leaf_frees);
 nm_destroy_virtual_inode(&inode);
 assert(!inode.i_private && cached->refs==0 && leaf_frees==1 && paths_put==1 && info_frees==1 && !locks);
 /* Failed cache publication leaves the losing opened file owned by its opener. */
 struct nm_inode_info info2={.r_path={&dent}};inode.i_private=&info2;
 struct file winner={.refs=1,.f_cred=&cred1};race_winner=&winner;
 a=(struct file){.f_cred=&cred1};assert(nm_open(&inode,&a)==0 && info2.r_file==&winner);
 struct file *loser=a.private_data;assert(loser!=&winner && loser->refs==1);
 nm_release(&inode,&a);assert(!loser->refs && winner.refs==1);
 puts("PASS: actual cache ownership/release, independent seek, backing xattr dispatch/errors and retire/RCU-order fixtures");
 return 0;
}

/* SPDX-License-Identifier: GPL-2.0 */
/* Single-threaded extraction models: no actual VFS or keyring operations. */
#undef NDEBUG
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#undef __always_inline
#define __always_inline inline
#define __read_mostly
#define __rcu
#define unlikely(x) (x)
#define likely(x) (x)
#define READ_ONCE(x) (x)
#define GFP_KERNEL 0
#define CAP_SYS_ADMIN 21
#define NM_SIG_16 0x6E6DULL
#define CONFIG_COMPAT 1
typedef uint64_t u64;
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
#define NM_MAGIC_SIG 0x4E4F4D4F554E54ULL
#define max(a,b) ((a)>(b)?(a):(b))
#define min(a,b) ((a)<(b)?(a):(b))
#define swap(a,b) do { __typeof__(a) t=(a);(a)=(b);(b)=t; } while(0)
#define ALIGN(x,a) (((x)+(a)-1)&~((a)-1))
static bool compat;
static bool privileged;
static int calls, rcu_depth, allocations;
static unsigned long observed_addr;
static bool in_compat_syscall(void) { return compat; }
static bool capable(int cap) { assert(cap == CAP_SYS_ADMIN); return privileged; }
struct key_preparsed_payload { size_t datalen; const void *data; };
static int nm_process_payload(unsigned long address) { assert(privileged); observed_addr = address; calls++; return 0; }
struct nm_uid_array { int count; uint64_t bloom_mask[4]; uint32_t uids[]; };
static inline bool nm_uid_bloom_test(struct nm_uid_array *arr, uid_t uid);
static struct nm_uid_array *nm_uids;
static bool nm_block_isolated_uids;
static int nm_mutex;
#define lockdep_is_held(x) true
#define rcu_access_pointer(x) (x)
#define rcu_dereference(x) (x)
#define rcu_dereference_protected(x, locked) (x)
#define rcu_dereference_check(x, locked) (x)
#define rcu_assign_pointer(x, val) ((x) = (val))
static void rcu_read_lock(void) { rcu_depth++; }
static void rcu_read_unlock(void) { assert(rcu_depth > 0); rcu_depth--; }
static void unlock_guard(int *p) { rcu_read_unlock(); }
#define rcu_guard() rcu_read_lock(); int guard __attribute__((cleanup(unlock_guard), unused))
static void *kmalloc(size_t size, int flags) { void *p = malloc(size); assert(p); allocations++; return p; }
static void free_rcu(void *p) { assert(p && allocations > 0); allocations--; free(p); }
#define kfree_rcu(p, member) free_rcu(p)
struct nm_rule { unsigned target_uid, uid_end, deny_start, deny_end; int identity; };
struct nm_rule_array { int count, uid_count; struct nm_rule rules[8]; };
struct nm_leaf { struct nm_rule_array *rules; u16 v_len, child_len; char paths[32]; };
struct rcu_head { void *unused; };
struct nm_child { struct nm_leaf *leaf; u32 hash; };
struct nm_child_array { struct rcu_head rcu; int count; u16 bucket_slots; u32 starts[] __attribute__((aligned(4))); };
struct nm_dir_node { struct nm_child_array *children; };
#define nm_get_child_name(l) ((l)->paths+(l)->v_len-(l)->child_len)
static bool force_collision;
static u32 full_name_hash(const void *salt,const char *name,size_t len)
{ (void)salt;if(force_collision)return 0x12345678;u32 h=2166136261U;for(size_t i=0;i<len;i++)h=(h^(u8)name[i])*16777619U;return h; }

/* PRODUCTION */

static void test_gate(void)
{
    unsigned count = 0;
    for (unsigned cap = 0; cap < 2; cap++)
    for (size_t length = 0; length <= 10; length++)
    for (unsigned value = 0; value < 2; value++) {
        u64 address = value ? 0x12345678UL : 0;
        struct key_preparsed_payload prep = { .datalen = length, .data = &address };
        privileged = cap; calls = 0; observed_addr = 0;
        int got = nm_key_preparse(&prep);
        int want = !cap ? -EPERM : (length == 4 || length == 8) ? -ECANCELED : -EINVAL;
        assert(got == want);
        assert(calls == (cap && value && (length == 4 || length == 8)));
        if (calls) assert(observed_addr == address);
        count++;
    }
    printf("Capability/payload-pointer gate: %u cases PASS\n", count);
}
static void test_positions(void)
{
    unsigned count = 0;
    for (unsigned is_compat = 0; is_compat < 2; is_compat++) {
        compat = is_compat;
        for (unsigned id = 0; id < 65536; id++) {
            u32 frag=(id*17U)&65535U;
            loff_t position = nm_pack_pos(id,frag);
            assert(nm_is_virtual_pos(position));
            assert(nm_unpack_pos(position) == id);
            assert(nm_unpack_frag(position) == (compat ? 0:frag));
            assert(!nm_is_virtual_pos(id));
            if (compat) assert(position <= INT32_MAX);
            count++;
        }
    }
    printf("Native/compat directory-cookie roundtrips: %u cases PASS\n", count);
}
static void test_uids(void)
{
    unsigned calls_count = 0;
    for (unsigned i = 0; i < 64; i++) {
        assert(nm_uid_add(10000 + i * 17) == 0);
        assert(nm_uid_add(10000 + i * 17) == -EEXIST);
        assert(nm_is_uid_blocked(10000 + i * 17));
        assert(rcu_depth == 0);
        calls_count += 3;
    }
    for (unsigned i = 0; i < 64; i++) {
        assert(nm_uid_del(10000 + i * 17) == 0);
        assert(nm_uid_del(10000 + i * 17) == -ENOENT);
        assert(!nm_is_uid_blocked(10000 + i * 17));
        assert(rcu_depth == 0);
        calls_count += 3;
    }
    assert(nm_uids == NULL && allocations == 0);
    for (unsigned block = 0; block < 2; block++) {
        nm_block_isolated_uids = block;
        for (unsigned uid = 0; uid < 200000; uid++) {
            assert(nm_is_uid_blocked(uid) == (block && uid % 100000 >= 90000));
            assert(rcu_depth == 0);
            calls_count++;
        }
    }
    printf("UID bloom/add/delete/isolation checks: %u cases PASS\n", calls_count);
}
static void test_rule_selection(void)
{
    struct nm_rule_array arr = { .count = 3, .uid_count=2, .rules = {
        { .target_uid = 0, .uid_end = 0, .identity = 1 },
        { .target_uid = 100, .uid_end = 199, .deny_start = 140, .deny_end = 149, .identity = 2 },
        { .target_uid = 300, .uid_end = 300, .identity = 3 }
    }};
    struct nm_leaf leaf = { .rules = &arr };
    for (unsigned uid = 0; uid < 1000; uid++) {
        struct nm_rule *got = nm_select_rule(&leaf, uid);
        int want = uid >= 100 && uid <= 199 && !(uid >= 140 && uid <= 149) ? 2 : uid == 300 ? 3 : 1;
        assert((got ? got->identity : 0) == want);
    }
    arr.count=1;arr.uid_count=1;arr.rules[0]=(struct nm_rule){.target_uid=0,.uid_end=9,.identity=4};
    assert(nm_select_rule(&leaf,0)==&arr.rules[0]);assert(nm_select_rule(&leaf,10)==NULL);
    arr.uid_count=0;arr.rules[0]=(struct nm_rule){.identity=5};
    assert(nm_select_rule(&leaf,UINT32_MAX)==&arr.rules[0]);
    leaf.rules = NULL;
    assert(nm_select_rule(&leaf, 0) == NULL);
    puts("Rule range/exclusion/fallback selection: 1001 cases PASS");
}
static bool includes(const struct nm_rule *r,unsigned u)
{ return u>=r->target_uid && u<=r->uid_end && !(r->deny_start && u>=r->deny_start && u<=r->deny_end); }
static void test_overlap(void)
{
 struct nm_rule rules[1024];unsigned n=0,cases=0;
 for(unsigned a=0;a<8;a++)for(unsigned b=a;b<8;b++) {
  if(!a && !b)continue; /* 0..0 is the default rule, not a scoped UID range */
  rules[n++]=(struct nm_rule){.target_uid=a,.uid_end=b};
  for(unsigned lo=a ? a:1;lo<=b;lo++)for(unsigned hi=lo;hi<=b;hi++)
   rules[n++]=(struct nm_rule){.target_uid=a,.uid_end=b,.deny_start=lo,.deny_end=hi};
 }
 assert(n<1024);
 for(unsigned i=0;i<n;i++)for(unsigned j=0;j<n;j++) {
  bool want=false;for(unsigned u=0;u<8;u++)want|=includes(&rules[i],u)&&includes(&rules[j],u);
  assert(nm_rules_overlap(&rules[i],&rules[j])==want);cases++;
 }
 struct nm_rule a={.target_uid=UINT32_MAX-3,.uid_end=UINT32_MAX,.deny_start=UINT32_MAX-1,.deny_end=UINT32_MAX};
 struct nm_rule b={.target_uid=UINT32_MAX,.uid_end=UINT32_MAX};
 assert(!nm_rules_overlap(&a,&b));a.deny_start=0;assert(nm_rules_overlap(&a,&b));
 printf("UID overlap/exclusion oracle: %u pairs + UINT_MAX boundaries PASS\n",cases);
}
static void test_children(void)
{
 unsigned checks=0;const int sizes[]={0,1,2,3,16,17,64,65,256,257,1024,1025};
 for(int collision=0;collision<2;collision++)for(unsigned trial=0;trial<sizeof(sizes)/sizeof(*sizes);trial++) {
  force_collision=collision;int count=sizes[trial];
  struct nm_leaf *leaves=calloc(count?count:1,sizeof(*leaves));assert(leaves);
  struct nm_child_array *arr=NULL;
  for(int i=0;i<count;i++) {
   snprintf(leaves[i].paths,sizeof(leaves[i].paths),"x%04dx",i);
   leaves[i].v_len=leaves[i].child_len=strlen(leaves[i].paths);
   struct nm_child extra={&leaves[i],full_name_hash(NULL,leaves[i].paths,leaves[i].child_len)};
   struct nm_child_array *next=nm_alloc_child_array(i+1);assert(next);
   nm_rebuild_children(next,arr,extra,-1);if(arr)free_rcu(arr);arr=next;
  }
  struct nm_dir_node dir={.children=arr};
  assert(!nm_find_leaf_in_dir(NULL,"x0000x",6));
  assert(!nm_find_leaf_in_dir(&dir,"x9999x",6));
  for(int i=0;i<count;i++){assert(nm_find_leaf_in_dir(&dir,leaves[i].paths,leaves[i].child_len)==&leaves[i]);checks++;}
  if(arr && count)for(int which=0;which<3;which++) {
   int skip=which==0 ? 0:which==1 ? count/2:count-1;
   struct nm_child_array *next=nm_alloc_child_array(count-1);assert(next);
   nm_rebuild_children(next,arr,(struct nm_child){0},skip);
   struct nm_leaf *removed=nm_entries(arr)[skip].leaf;
   dir.children=next;
   for(int i=0;i<count;i++){assert(nm_find_leaf_in_dir(&dir,leaves[i].paths,leaves[i].child_len)==(&leaves[i]==removed ? NULL:&leaves[i]));checks++;}
   free_rcu(next);
  }
  if(arr)free_rcu(arr);free(leaves);
 }
 assert(!allocations);printf("Child bucket rebuild/lookup/removal/collision/singleton: %u checks PASS\n",checks);
}
int main(void)
{
    (void)nm_mutex;
    setbuf(stdout, NULL);
    test_gate(); test_positions(); test_uids(); test_rule_selection(); test_overlap(); test_children();
    return 0;
}

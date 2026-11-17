// SPDX-License-Identifier: GPL-2.0
/* Platform mocks, independent concrete arithmetic, and malformed ELF inputs. */
#include <assert.h>
#include <errno.h>
#include <elf.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <linux/tnum.h>
#define EXPORT_SYMBOL_GPL(x)
#define PAGE_SIZE 4096
#define BUILD_ID 3
#define BUILD_ID_SIZE_MAX 20
#define S32_MIN INT32_MIN
#define S32_MAX INT32_MAX
#define U32_MAX UINT32_MAX
#define S64_MIN LLONG_MIN
#define S64_MAX LLONG_MAX
#define U64_MAX ULLONG_MAX
#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define is_power_of_2(x) ((x) && !((x)&((x)-1)))
#define fls64(x) ((x)?64-__builtin_clzll(x):0)
struct bpf_reg_state {
 s64 smin_value,smax_value; u64 umin_value,umax_value;
 s32 s32_min_value,s32_max_value; u32 u32_min_value,u32_max_value;
};
struct pid { int references; };
struct file_operations { int unused; };
static const struct file_operations pidfd_fops={0},other_fops={1};
struct file { const struct file_operations *f_op; unsigned int f_flags; void *private_data; };
struct fd { struct file *file; };
static struct file *fd_table[4];
static unsigned int fd_puts;
static struct fd fdget(unsigned int fd) { return (struct fd){fd<4?fd_table[fd]:NULL}; }
static void fdput(struct fd fd) { assert(fd.file); fd_puts++; }
static inline struct pid *get_pid(struct pid *pid) { pid->references++; return pid; }
#define ERR_PTR(e) ((struct pid *)(intptr_t)(e))
/* EXTRACTED */
static unsigned long checks;
static u64 state=0x1515b0f;
static u64 rnd(void) { state^=state<<13;state^=state>>7;state^=state<<17;return state; }
static void buildid_tests(void)
{
 unsigned char page[PAGE_SIZE],out[20]; __u32 size;
 for(int offset=512;offset<516;offset++) for(unsigned int length=1;length<=20;length++) {
  memset(page,0,sizeof(page)); Elf32_Nhdr hdr={4,length,BUILD_ID};
  memcpy(page+offset,&hdr,sizeof(hdr));memcpy(page+offset+12,"GNU",4);
  for(unsigned int i=0;i<length;i++) page[offset+16+i]=i+1;
  unsigned int note_size=16+((length+3)&~3U);
  assert(parse_build_id(page,out,&size,page+offset,note_size)==0 && size==length);
  for(unsigned int i=0;i<20;i++) assert(out[i]==(i<length?i+1:0));
  for(unsigned int truncated=0;truncated<note_size;truncated++) {
   memset(out,0x5a,sizeof(out));size=99;
   assert(parse_build_id(page,out,&size,page+offset,truncated)==-EINVAL);
   assert(out[0]==0x5a && size==99); checks++;
  }
  page[offset+12]='X';assert(parse_build_id(page,out,&size,page+offset,note_size)==-EINVAL);checks++;
 }
 for(int bits=32;bits<=64;bits+=32) {
  memset(page,0,sizeof(page));Elf32_Nhdr n={4,4,BUILD_ID};
  memcpy(page+512,&n,sizeof(n));memcpy(page+524,"GNU",4);memcpy(page+528,"test",4);
  if(bits==32) {
   Elf32_Ehdr e={.e_ehsize=sizeof(e),.e_phoff=131,.e_phentsize=sizeof(Elf32_Phdr),.e_phnum=1};
   Elf32_Phdr p={.p_type=PT_NOTE,.p_offset=512,.p_filesz=20};
   memcpy(page,&e,sizeof(e));memcpy(page+131,&p,sizeof(p));
   assert(get_build_id_32(page,out,&size)==0 && !memcmp(out,"test",4));
   for(unsigned int off=PAGE_SIZE-2;off<UINT32_MAX;off=(off==PAGE_SIZE-2?UINT32_MAX-1:UINT32_MAX)) {
    e.e_phoff=off;memcpy(page,&e,sizeof(e));assert(get_build_id_32(page,out,&size)==-EINVAL);checks++;
   }
  } else {
   Elf64_Ehdr e={.e_ehsize=sizeof(e),.e_phoff=131,.e_phentsize=sizeof(Elf64_Phdr),.e_phnum=1};
   Elf64_Phdr p={.p_type=PT_NOTE,.p_offset=512,.p_filesz=20};
   memcpy(page,&e,sizeof(e));memcpy(page+131,&p,sizeof(p));
   assert(get_build_id_64(page,out,&size)==0 && !memcmp(out,"test",4));
   e.e_phoff=UINT64_MAX;memcpy(page,&e,sizeof(e));assert(get_build_id_64(page,out,&size)==-EINVAL);checks++;
  }
 }
 for(int i=0;i<100000;i++) {
  Elf32_Nhdr hdr={(u32)rnd(),(u32)rnd(),(u32)rnd()};
  memset(page,0,sizeof(page));memcpy(page+512,&hdr,sizeof(hdr));
  assert(parse_build_id(page,out,&size,page+512,rnd()%256)==-EINVAL);checks++;
 }
}
static void pidfd_tests(void)
{
 struct pid pid={1}; struct file valid={&pidfd_fops,0x800,&pid},wrong={&other_fops,0x400,&pid};
 unsigned int flags=0xdead;fd_table[1]=&valid;fd_table[2]=&wrong;
 assert(pidfd_get_pid(0,&flags)==ERR_PTR(-EBADF));assert(flags==0xdead && !fd_puts);
 assert(pidfd_get_pid(2,&flags)==ERR_PTR(-EINVAL));assert(flags==0xdead && fd_puts==1);
 assert(pidfd_get_pid(1,&flags)==&pid);assert(flags==0x800 && pid.references==2 && fd_puts==2);
 fd_table[1]=NULL;pid.references--; /* close original pidfd */
 assert(pid.references==1);pid.references--;assert(!pid.references);
 assert(pidfd_get_pid(1,&flags)==ERR_PTR(-EBADF));checks+=4;
}
static bool contains(struct tnum t,u64 value) { return !(t.value&t.mask) && ((value&~t.mask)==t.value); }
static void tnum_tests(void)
{
 for(int trial=0;trial<2000;trial++) {
  u64 am=0,bm=0;
  for(int j=0;j<4;j++) { am|=1ULL<<(rnd()%64);bm|=1ULL<<(rnd()%64); }
  struct tnum a={rnd()&~am,am},b={rnd()&~bm,bm};
  struct tnum results[]={tnum_add(a,b),tnum_sub(a,b),tnum_mul(a,b),tnum_and(a,b),tnum_or(a,b),tnum_xor(a,b)};
  u64 sa=am;
  do {
   u64 sb=bm;
   do {
    u64 x=a.value|sa,y=b.value|sb;
    u64 expected[]={x+y,x-y,x*y,x&y,x|y,x^y};
    for(int op=0;op<6;op++) { assert(contains(results[op],expected[op]));checks++; }
    if(!sb) break;
    sb=(sb-1)&bm;
   } while(1);
   if(!sa) break;
   sa=(sa-1)&am;
  } while(1);
 }
}
static struct bpf_reg_state interval(u64 a,u64 b)
{
 struct bpf_reg_state r={.smin_value=min((s64)a,(s64)b),.smax_value=max((s64)a,(s64)b),
  .umin_value=min(a,b),.umax_value=max(a,b),.s32_min_value=min((s32)a,(s32)b),
  .s32_max_value=max((s32)a,(s32)b),.u32_min_value=min((u32)a,(u32)b),.u32_max_value=max((u32)a,(u32)b)};
 return r;
}
static void scalar_tests(void)
{
 const u64 edge[]={0,1,UINT32_MAX,INT32_MAX,0x80000000ULL,ULLONG_MAX,LLONG_MAX,1ULL<<63};
 for(int trial=0;trial<30000;trial++) {
  u64 a[]={trial<64?edge[trial%8]:rnd(),rnd()},b[]={trial<64?edge[trial/8]:rnd(),rnd()};
  for(int op=0;op<4;op++) {
   struct bpf_reg_state dest=interval(a[0],a[1]),src=interval(b[0],b[1]);
   if(op==0) scalar_min_max_add(&dest,&src);
   if(op==1) scalar_min_max_sub(&dest,&src);
   if(op==2) scalar32_min_max_add(&dest,&src);
   if(op==3) scalar32_min_max_sub(&dest,&src);
   for(int i=0;i<2;i++) for(int j=0;j<2;j++) {
    u64 value=(op%2)?a[i]-b[j]:a[i]+b[j];
    if(op<2) { assert(value>=dest.umin_value && value<=dest.umax_value);
     assert((s64)value>=dest.smin_value && (s64)value<=dest.smax_value);
    } else { assert((u32)value>=dest.u32_min_value && (u32)value<=dest.u32_max_value);
     assert((s32)value>=dest.s32_min_value && (s32)value<=dest.s32_max_value);
    }
    checks++;
   }
  }
 }
}
int main(void)
{
 buildid_tests();pidfd_tests();tnum_tests();scalar_tests();
 printf("PASS: %lu build-ID/pidfd/tnum/scalar-bound checks (extracted production functions, mocked fd primitives)\n",checks);
 return 0;
}

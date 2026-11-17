/* SPDX-License-Identifier: GPL-2.0 */
/* Host fixtures only: actual sysfs functions/macros are inserted by runner. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <stdarg.h>
#include <ctype.h>
#include <sys/types.h>
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef u8 __u8;
#define PAGE_SIZE 4096
#define F2FS_EXTENSION_LEN 8
#define CONFIG_F2FS_FAULT_INJECTION 1
#define FAULT_MAX 8
#define FAULT_INFO_TYPE 1
#define FAULT_INFO_RATE 2
#define RESERVED_BLOCKS 3
#define GC_THREAD 4
#define F2FS_SBI 5
#define STAT_INFO 6
#define MAX_PLIST_NUM 512
#define GC_NORMAL 0
#define GC_URGENT 1
#define GC_IDLE_CB 2
#define GC_IDLE_GREEDY 3
#define MIN_IOSTAT_PERIOD_MS 100
#define MAX_IOSTAT_PERIOD_MS 10000
#define sizeof_field(t,m) sizeof(((t *)0)->m)
#define __stringify(x) #x
#define min(a,b) ((a)<(b)?(a):(b))
#define le32_to_cpu(x) (x)
#define scnprintf snprintf
static int locks, wakeups, resets, bugs, logs, trylock_ok = 1;
#define spin_lock(p) ((void)(p),locks++)
#define spin_unlock(p) ((void)(p),locks--)
#define down_write(p) spin_lock(p)
#define up_write(p) spin_unlock(p)
#define up_read(p) spin_unlock(p)
#define down_read_trylock(p) ((void)(p),trylock_ok ? (++locks,1):0)
#define wake_up_interruptible_all(p) ((void)(p),wakeups++)
#define f2fs_bug_on(s,c) ((void)(s),bugs += !!(c))
#define f2fs_err(s,...) ((void)(s),logs++)
struct attribute { const char *name; int mode; };
struct raw_super { u8 extension_list[4][8]; u32 extension_count; u8 hot_ext_count; };
struct super_block { int s_umount; };
struct gc_thread { int gc_wake, gc_wait_queue_head; };
struct f2fs_sb_info {
 struct raw_super *raw_super; struct super_block *sb; struct gc_thread *gc_thread;
 int sb_lock, stat_lock, iostat_lock;
 u32 user_block_count, root_reserved_blocks, reserved_blocks, current_reserved_blocks;
 u32 segs_per_sec, gc_mode, iostat_period_ms;
 bool iostat_enable;
 u8 adjacent[7];
 u64 gc_pin_file_threshold;
 u32 slot;
 long interval_time[2];
};
struct f2fs_stat_info { u64 count; };
#define F2FS_OPTION(s) (*(s))
#define valid_user_blocks(s) 2U
static unsigned char *__struct_ptr(struct f2fs_sb_info *s, int t)
{ return t == -1 ? NULL : (unsigned char *)s; }
static int sysfs_emit(char *b, const char *fmt, ...)
{ va_list a; va_start(a,fmt); int n=vsnprintf(b,PAGE_SIZE,fmt,a); va_end(a); return n; }
static char *skip_spaces(const char *s) { while(isspace((unsigned char)*s))s++;return (char *)s; }
static char *strim(char *s) { char *b=skip_spaces(s), *e=b+strlen(b);while(e>b && isspace((unsigned char)e[-1]))--e;*e=0;return b; }
static int kstrtoul(const char *s, unsigned int base, unsigned long *v)
{ char *e; if (*s=='-')return -EINVAL;errno=0;*v=strtoul(s,&e,base);if(errno==ERANGE)return -ERANGE;if(e==s || (*e && strcmp(e,"\n")))return -EINVAL;return 0; }
static int f2fs_update_extension_list(struct f2fs_sb_info *s,const char *n,bool h,bool set)
{ (void)s;(void)n;(void)h;(void)set;return 0; }
static int f2fs_commit_super(struct f2fs_sb_info *s,bool b) { (void)s;(void)b;return 0; }
static void wake_up_discard_thread(struct f2fs_sb_info *s,bool b) { (void)s;(void)b;wakeups++; }
static void f2fs_reset_iostat(struct f2fs_sb_info *s) { (void)s;resets++; }
/* ACTUAL */
F2FS_RW_ATTR(F2FS_SBI, f2fs_sb_info, test_bool, iostat_enable);
F2FS_RW_ATTR(F2FS_SBI, f2fs_sb_info, test_u64, gc_pin_file_threshold);
F2FS_RW_ATTR(F2FS_SBI, f2fs_sb_info, test_array, interval_time[1]);
F2FS_STAT_ATTR(STAT_INFO, f2fs_stat_info, test_stat, count);
static ssize_t store(struct f2fs_sb_info *s,const char *name,int type,size_t off,int size,const char *text)
{ struct f2fs_attr a={.attr={.name=name},.struct_type=type,.offset=off,.size=size};return f2fs_sbi_store(&a,s,text,strlen(text)); }
#define STORE(name,field,type,text) store(&s,name,type,offsetof(struct f2fs_sb_info,field),sizeof(s.field),text)
int main(void)
{
 struct f2fs_sb_info s={0}; char buf[PAGE_SIZE];
 struct raw_super raw={0}; struct super_block sb={0}; struct gc_thread gc={0};
 s.raw_super=&raw;s.sb=&sb;s.gc_thread=&gc;
 assert(sizeof(unsigned long)==8); /* target profile is ARM64; not 32-bit parsing proof */
 assert(f2fs_attr_test_bool.size==sizeof(bool));
 assert(f2fs_attr_test_u64.size==8 && f2fs_attr_test_stat.size==8);
 assert(f2fs_attr_test_array.size==sizeof(unsigned long));
 /* Guard bytes detect writes past 1/2/4/8-byte fields; distinct tail poisons reads. */
 union { u64 alignment; unsigned char b[32]; } mem;
 const unsigned long values[]={0,1,255,256,65535,65536,0xffffffffUL,0x100000001UL,ULONG_MAX};
 for(int width=1;width<=8;width*=2)for(size_t i=0;i<sizeof(values)/sizeof(*values);i++) {
  memset(mem.b,0xa5,sizeof(mem.b));
  struct f2fs_attr a={.size=width};unsigned char *v=mem.b+8;
  __sbi_store_value(&a,&s,v,values[i]);
  for(int j=0;j<32;j++)if(j<8 || j>=8+width)assert(mem.b[j]==0xa5);
  u64 want=values[i] & (~0ULL >> (64-width*8));
  __sbi_show_value(&a,&s,buf,v);
  assert(strtoull(buf,NULL,10)==want);
 }
 /* Actual dispatch: bool show ignores adjacent bytes, custom bool store remains intact. */
 memset(s.adjacent,0xa5,sizeof(s.adjacent));s.iostat_enable=true;
 f2fs_sbi_show(&f2fs_attr_test_bool,&s,buf);assert(!strcmp(buf,"1\n"));
 assert(STORE("iostat_enable",iostat_enable,F2FS_SBI,"0")==1 && resets==1);
 for(size_t i=0;i<sizeof(s.adjacent);i++)assert(s.adjacent[i]==0xa5);
 assert(STORE("gc_pin_file_thresh",gc_pin_file_threshold,F2FS_SBI,"4294967297")==10);
 assert(s.gc_pin_file_threshold==0x100000001ULL);
 f2fs_sbi_show(&f2fs_attr_test_u64,&s,buf);assert(!strcmp(buf,"4294967297\n"));
 assert(STORE("gc_pin_file_thresh",gc_pin_file_threshold,F2FS_SBI,"18446744073709551615")==20);
 assert(s.gc_pin_file_threshold==~0ULL);
 assert(STORE("gc_pin_file_thresh",gc_pin_file_threshold,F2FS_SBI,"18446744073709551616")==-ERANGE);
 assert(STORE("gc_pin_file_thresh",gc_pin_file_threshold,F2FS_SBI,"bad")==-EINVAL);
 assert(STORE("gc_pin_file_thresh",gc_pin_file_threshold,F2FS_SBI,"-1")==-EINVAL);
 assert(s.gc_pin_file_threshold==~0ULL);
 assert(f2fs_attr_test_array.store(&f2fs_attr_test_array,&s,"4294967297",10)==10);
 assert(s.interval_time[1]==4294967297L && s.interval_time[0]==0);
 f2fs_attr_test_array.show(&f2fs_attr_test_array,&s,buf);assert(!strcmp(buf,"4294967297\n"));
 /* Existing validation, lock/unlock, wakeup, custom paths and NULL routing. */
 s.user_block_count=100;s.root_reserved_blocks=10;
 assert(STORE("reserved_blocks",reserved_blocks,RESERVED_BLOCKS,"91")==-EINVAL);
 assert(STORE("reserved_blocks",reserved_blocks,RESERVED_BLOCKS,"20")==2 && s.current_reserved_blocks==20);
 assert(STORE("discard_granularity",slot,F2FS_SBI,"0")==-EINVAL);
 assert(STORE("discard_granularity",slot,F2FS_SBI,"2")==1 && s.slot==2);
 s.segs_per_sec=4;
 assert(STORE("migration_granularity",slot,F2FS_SBI,"5")==-EINVAL);
 assert(STORE("trim_sections",slot,F2FS_SBI,"1")==-EINVAL);
 assert(STORE("gc_urgent",gc_mode,F2FS_SBI,"1")==1 && s.gc_mode==GC_URGENT && wakeups==2);
 assert(STORE("gc_idle",gc_mode,F2FS_SBI,"3")==1 && s.gc_mode==GC_IDLE_GREEDY);
 assert(STORE("gc_idle",gc_mode,F2FS_SBI,"99")==2 && s.gc_mode==GC_NORMAL);
 trylock_ok=0;assert(STORE("gc_urgent",gc_mode,F2FS_SBI,"1")==-EAGAIN);trylock_ok=1;
 assert(STORE("iostat_period_ms",iostat_period_ms,F2FS_SBI,"99")==-EINVAL);
 assert(STORE("iostat_period_ms",iostat_period_ms,F2FS_SBI,"100")==3 && s.iostat_period_ms==100);
 assert(STORE("inject_type",slot,FAULT_INFO_TYPE,"256")==-EINVAL);
 assert(STORE("inject_rate",slot,FAULT_INFO_RATE,"4294967295")==-EINVAL);
 assert(STORE("unused",slot,-1,"1")==-EINVAL);
 struct f2fs_attr null={.struct_type=-1};assert(f2fs_sbi_show(&null,&s,buf)==-EINVAL);
 char ext[]="[h]apk"; assert(STORE("extension_list",slot,F2FS_SBI,ext)==6);
 struct f2fs_attr extattr={.attr={.name="extension_list"}};
 f2fs_sbi_show(&extattr,&s,buf);assert(strstr(buf,"cold file extension:"));
 assert(!locks && !bugs && !logs);
 struct f2fs_attr invalid={.size=3};__sbi_store_value(&invalid,&s,mem.b,1);
 __sbi_show_value(&invalid,&s,buf,mem.b);assert(bugs==2 && logs==1);
 puts("PASS: actual F2FS sysfs helpers/dispatch/macros: widths, canaries, u64, special cases, locking and parser errors");
 return 0;
}

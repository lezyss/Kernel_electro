/* SPDX-License-Identifier: GPL-2.0 */
/* Extracted-source tests; single-threaded mocks, NOT real VFS/RCU execution. */
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
#define __user
#define unlikely(x) (x)
#define likely(x) (x)
#define CONFIG_KSU_SUSFS 1
#define CONFIG_KSU_SUSFS_TRY_UMOUNT 1
#define CONFIG_KSU_SUSFS_SUS_PATH 1
#define CONFIG_KSU_SUSFS_SUS_MOUNT 1
#define CONFIG_KSU_SUSFS_SUS_KSTAT 1
#define CONFIG_KSU_SUSFS_SPOOF_UNAME 1
#define CONFIG_KSU_SUSFS_ENABLE_LOG 1
#define CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG 1
#define CONFIG_KSU_SUSFS_OPEN_REDIRECT 1
#define CONFIG_KSU_SUSFS_SUS_MAP 1
#define IS_ENABLED(x) 0
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
#define SUSFS_LOGI(...) ((void)0)
#define SUSFS_LOGE(...) ((void)0)
#define CAP_SYS_ADMIN 21
#define TIF_KSU_UNMOUNTABLE 61
#define TIF_KSU_MANAGED 60
#define PAGE_SIZE 4096UL
#define PM_END_OF_BUFFER 1
#define VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT 0x80000000
/* CONSTANTS */
typedef struct { unsigned val; } kuid_t;
#define GLOBAL_ROOT_UID ((kuid_t){0})
static unsigned caller_uid;
static bool admin, want_umount, manager, allowed, overridden, copy_fault;
static int payload_calls, last_cmd, normal_umounts, extra_umounts, queued;
static int fd_installs, seccomp, srcu_depth, freed_ids;
struct thread_info { uint64_t flags; };
struct { struct thread_info thread_info; int pid; char comm[8]; } task;
#define current (&task)
static kuid_t current_uid(void) { return (kuid_t){caller_uid}; }
static bool uid_eq(kuid_t a, kuid_t b) { return a.val == b.val; }
static bool capable(int cap) { assert(cap == CAP_SYS_ADMIN); return admin; }
static int test_ti_thread_flag(struct thread_info *ti, int bit) { return !!(ti->flags & (1ULL << bit)); }
static void set_ti_thread_flag(struct thread_info *ti, int bit) { ti->flags |= 1ULL << bit; }
#define set_thread_flag(bit) set_ti_thread_flag(&task.thread_info, bit)
static bool test_bit(unsigned bit, unsigned long *v) { return !!(*v & (1UL << bit)); }
struct cred { kuid_t uid; bool zygote; };
static struct cred privileged_cred;
static struct cred *ksu_cred = &privileged_cred;
static bool ksu_kernel_umount_enabled, ksu_module_mounted;
static unsigned ksu_get_uid_t(kuid_t id) { return id.val; }
static bool ksu_uid_should_umount(unsigned id) { return want_umount; }
static bool is_zygote(const struct cred *cred) { return cred->zygote; }
static bool is_uid_manager(unsigned uid) { return manager; }
static bool ksu_is_allow_uid_for_current(unsigned uid) { return allowed; }
static int ksu_install_fd(void) { fd_installs++; return 5; }
static void disable_seccomp(void) { seccomp++; }
static const struct cred *override_creds(struct cred *cred) { assert(!overridden); overridden = true; return NULL; }
static void revert_creds(const struct cred *cred) { assert(overridden); overridden = false; }
static void susfs_try_umount(unsigned uid) { assert(overridden); extra_umounts++; }
static void susfs_queue_extra_work(void) { assert(!overridden); queued++; }
struct mount_entry { const char *umountable; unsigned flags; };
static struct mount_entry entries[2];
static int mount_list, mount_list_lock;
#define down_read(x) ((void)(x))
#define up_read(x) ((void)(x))
#define list_for_each_entry(e, h, member) for (e = entries; e != entries + 2; e++)
static void try_umount(const char *name, int flags) { assert(overridden); normal_umounts++; }
static int copy_to_user(void *dest, const void *src, size_t len) { if (copy_fault && len) return 1; memcpy(dest, src, len); return 0; }
static void ksu_close_fd(int fd) {}
static void toolkit_handle_sys_reboot(int a, int b, unsigned cmd, void **arg) {}
/* STUBS */
struct st_susfs_open_redirect_hlist {
    struct st_susfs_open_redirect_hlist *next;
    unsigned long target_ino, target_dev;
    bool reversed_lookup_only;
    struct { char target_pathname[256], redirected_pathname[256]; } info;
};
static struct st_susfs_open_redirect_hlist *OPEN_REDIRECT_HLIST;
static int susfs_srcu_open_redirect;
static int srcu_read_lock(int *lock) { srcu_depth++; return 0; }
static void srcu_read_unlock(int *lock, int index) { assert(srcu_depth == 1); srcu_depth--; }
#define hash_for_each_possible_rcu(table, e, member, key) for (e = table; e; e = e->next)
struct super_block { unsigned long s_dev; };
struct inode { unsigned long i_ino, i_state; struct super_block *i_sb; };
#define min_t(type, a, b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
typedef struct { uint64_t pme; } pagemap_entry_t;
struct pagemapread { unsigned pos, len; pagemap_entry_t buffer[512]; };
static pagemap_entry_t make_pme(uint64_t frame, uint64_t flags) { return (pagemap_entry_t){frame | flags}; }
static int add_to_pagemap(unsigned long addr, pagemap_entry_t *pme, struct pagemapread *pm)
{ pm->buffer[pm->pos++] = *pme; return pm->pos == pm->len ? PM_END_OF_BUFFER : 0; }
struct mount { int mnt_id; struct { unsigned mnt_flags; } mnt; };
static int mnt_id_ida;
static void ida_free(int *ida, int id) { freed_ids++; }
/* FUNCTIONS */

static void test_auth(void)
{
    unsigned commands[] = { /* COMMANDS */ };
    unsigned uids[] = { 0, 1000, 10000, 100000 };
    void *arg = NULL;
    int count = 0;
    for (unsigned u = 0; u < 4; u++)
    for (unsigned cap = 0; cap < 2; cap++)
    for (unsigned good = 0; good < 2; good++)
    for (unsigned i = 0; i < sizeof(commands)/sizeof(commands[0]); i++) {
        caller_uid = uids[u]; admin = cap; payload_calls = 0; last_cmd = 0;
        ksu_handle_sys_reboot(good ? KSU_INSTALL_MAGIC1 : 0, SUSFS_MAGIC, commands[i], &arg);
        bool accepted = uids[u] == 0 && cap && good;
        assert(payload_calls == accepted);
        if (accepted) assert(last_cmd == (int)commands[i] ||
            (commands[i] == CMD_SUSFS_ADD_SUS_KSTAT && last_cmd == CMD_SUSFS_ADD_SUS_KSTAT_STATICALLY));
        count++;
    }
    printf("SUSFS reboot command authorization: %d cases PASS\n", count);
}
static void test_unmount(void)
{
    unsigned uids[] = {0, 1000, 1053, 2000, 9999, 10000, 19999, 20000, 98999, 99000, 99999, 110000, 119999, 199000};
    int count = 0;
    for (unsigned bits = 0; bits < 128; bits++)
    for (unsigned i = 0; i < sizeof(uids)/sizeof(uids[0]); i++) {
        ksu_kernel_umount_enabled = bits & 1; ksu_module_mounted = bits & 2;
        want_umount = bits & 4; manager = bits & 8; allowed = bits & 16;
        struct cred old = { .uid = { bits & 32 ? 0 : 1000 }, .zygote = !!(bits & 64) };
        struct cred new = { .uid = { uids[i] } };
        normal_umounts = extra_umounts = queued = fd_installs = seccomp = 0;
        task.thread_info.flags = 0; overridden = false;
        ksu_handle_setresuid_cred(&new, &old);
        unsigned appid = uids[i] % 100000;
        bool isolated = appid >= 99000;
        bool eligible = (appid >= 10000 && appid <= 19999) || isolated || uids[i] == 1053;
        bool umount = !old.uid.val && !manager && !allowed && ksu_kernel_umount_enabled &&
            ksu_module_mounted && old.zygote && eligible && (want_umount || isolated);
        assert(normal_umounts == (umount ? 2 : 0));
        assert(extra_umounts == umount && queued == umount);
        assert(susfs_is_current_proc_umounted() == umount);
        assert(fd_installs == (!old.uid.val && manager));
        assert(seccomp == (!old.uid.val && (manager || allowed)));
        assert(!overridden);
        count++;
    }
    printf("KSU manager/allowlist/zygote/unmount safeguards: %d cases PASS\n", count);
}
static void test_readlink(void)
{
    struct super_block sb = { .s_dev = 7 };
    struct inode inode = { .i_ino = 42, .i_sb = &sb };
    struct st_susfs_open_redirect_hlist match = { .target_ino = 42, .target_dev = 7, .reversed_lookup_only = true };
    struct st_susfs_open_redirect_hlist collision = { .target_ino = 43, .target_dev = 7, .reversed_lookup_only = true, .next = &match };
    strcpy(collision.info.redirected_pathname, "wrong");
    OPEN_REDIRECT_HLIST = &collision;
    unsigned lengths[] = { 0, 1, 2, 254, 255 };
    int count = 0;
    for (unsigned i = 0; i < 5; i++) {
        unsigned length = lengths[i]; memset(match.info.redirected_pathname, 'x', length);
        match.info.redirected_pathname[length] = 0;
        for (unsigned cap = 0; cap <= 300; cap++)
        for (unsigned fail = 0; fail < 2; fail++) {
            char output[302]; memset(output, 'z', sizeof(output)); copy_fault = fail;
            int len = length < cap ? length : cap;
            int got = susfs_open_redirect_spoof_vfs_readlink(&inode, output + 1, cap);
            assert(got == (fail && len ? -EFAULT : len));
            assert(output[0] == 'z' && output[cap + 1] == 'z');
            if (!fail) for (int j = 1; j <= len; j++) assert(output[j] == 'x');
            assert(srcu_depth == 0); count++;
        }
    }
    printf("Readlink truncation/count/fault/hash collision: %d cases PASS\n", count);
}
static void test_pagemap(void)
{
    unsigned sizes[] = {1, 2, 16, 512}; int count = 0;
    for (unsigned s = 0; s < 4; s++)
    for (unsigned pages = 0; pages <= 600; pages++) {
        struct pagemapread pm = { .len = sizes[s] };
        memset(pm.buffer, 0xFF, sizeof(pm.buffer));
        int result = susfs_pagemap_hidden_range(0, pages * PAGE_SIZE, &pm);
        unsigned want = pages < sizes[s] ? pages : sizes[s];
        assert(pm.pos == want && result == (pages >= sizes[s] ? PM_END_OF_BUFFER : 0));
        for (unsigned i = 0; i < want; i++) assert(pm.buffer[i].pme == 0);
        count++;
    }
    printf("Pagemap byte accounting/buffer bounds: %d cases PASS\n", count);
}
static void test_flags_ids(void)
{
    struct inode ino = { .i_state = 1UL << AS_FLAGS_SUS_MAP };
    caller_uid = 10000; task.thread_info.flags = 0;
    assert(!SUSFS_IS_INODE_SUS_MAP(&ino));
    assert(!(!SUSFS_IS_INODE_SUS_MAP(&ino)) == false);
    susfs_set_current_proc_umounted();
    assert(SUSFS_IS_INODE_SUS_MAP(&ino)); assert(!(!SUSFS_IS_INODE_SUS_MAP(&ino)));
    assert(!SUSFS_IS_INODE_SUS_MAP((struct inode *)NULL));
    for (unsigned borrowed = 0; borrowed < 2; borrowed++) {
        struct mount m = { .mnt_id = 7, .mnt.mnt_flags = borrowed ? VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT : 0 };
        freed_ids = 0; mnt_free_id(&m); assert(freed_ids == !borrowed);
    }
    puts("Flag negation and mount-ID ownership: PASS");
}
int main(void)
{
    setbuf(stdout, NULL); (void)mount_list;
    test_auth(); test_unmount(); test_readlink(); test_pagemap(); test_flags_ids();
    return 0;
}

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
struct nm_rule_array { int count; struct nm_rule rules[8]; };
struct nm_leaf { struct nm_rule_array *rules; };
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
            loff_t position = nm_pack_pos(id);
            assert(nm_is_virtual_pos(position));
            assert(nm_unpack_pos(position) == (int)id);
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
    struct nm_rule_array arr = { .count = 3, .rules = {
        { .target_uid = 0, .uid_end = 0, .deny_start = 90, .deny_end = 99, .identity = 1 },
        { .target_uid = 100, .uid_end = 199, .deny_start = 140, .deny_end = 149, .identity = 2 },
        { .target_uid = 300, .uid_end = 300, .identity = 3 }
    }};
    struct nm_leaf leaf = { .rules = &arr };
    for (unsigned uid = 0; uid < 1000; uid++) {
        struct nm_rule *got = nm_select_rule(&leaf, uid);
        int want = uid >= 90 && uid <= 99 ? 0 :
            uid >= 100 && uid <= 199 && !(uid >= 140 && uid <= 149) ? 2 : uid == 300 ? 3 : 1;
        assert((got ? got->identity : 0) == want);
    }
    leaf.rules = NULL;
    assert(nm_select_rule(&leaf, 0) == NULL);
    puts("Rule range/exclusion/fallback selection: 1001 cases PASS");
}
int main(void)
{
    (void)nm_mutex;
    setbuf(stdout, NULL);
    test_gate(); test_positions(); test_uids(); test_rule_selection();
    return 0;
}

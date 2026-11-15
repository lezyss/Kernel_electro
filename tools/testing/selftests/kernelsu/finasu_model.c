/* SPDX-License-Identifier: GPL-2.0 */
/* Host harness. test_finasu.py inserts production functions at SOURCE markers.
 * Filesystem, credentials and certificate-parser results are mocks, not Android.
 */
#define _GNU_SOURCE
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <dirent.h>
#include <sys/types.h>
#include <sys/ioctl.h>
typedef uint64_t u64;
#define PER_USER_RANGE 100000
#define KSU_MAX_PACKAGE_NAME 256
#define KSU_PACKAGE_NAME "me.weishu.kernelsu"
#define EXPECTED_SIZE 0x33b
#define EXPECTED_HASH "c371061b19d8c7d7d6133c6a9bafe198fa944e50c1b31c9d8daa8d7f1fc2d2d6"
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, v) ((x) = (v))
#define unlikely(x) (x)
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
#define noinline __attribute__((noinline))
#define GFP_KERNEL 0
#define kzalloc(n, f) calloc(1, (n))
#define kfree(p) free(p)
#define IS_ERR(p) (!(p))
#define PTR_ERR(p) (-ENOENT)
#define container_of(p, t, f) ((t *)((char *)(p) - offsetof(t, f)))
#define KERNEL_VERSION(a, b, c) (((a) << 16) | ((b) << 8) | (c))
#define LINUX_VERSION_CODE KERNEL_VERSION(4, 14, 0)
#define __user
static uid_t caller_uid;
struct kuid_mock { uid_t val; };
static struct kuid_mock current_uid(void) { return (struct kuid_mock){ caller_uid }; }
/* SOURCE_IDENTITY */
uid_t ksu_manager_appid = KSU_INVALID_APPID;
#define DATA_PATH_LEN 384
static char cached_manager_apk_path[DATA_PATH_LEN];
static void offstack_free(void *p) { free(*(void **)p); }
#define __offstack(n) __attribute__((cleanup(offstack_free))) = calloc(1, (n))
static ssize_t strscpy(char *dst, const char *src, size_t n)
{
	size_t len = strlen(src), copy = len < n ? len : n - 1;
	assert(n); memcpy(dst, src, copy); dst[copy] = 0;
	return len < n ? (ssize_t)len : -E2BIG;
}
struct list_head { struct list_head *next, *prev; };
#define INIT_LIST_HEAD(h) ((h)->next = (h)->prev = (h))
static void list_add_tail(struct list_head *n, struct list_head *h)
{ n->prev = h->prev; n->next = h; h->prev->next = n; h->prev = n; }
static void list_del(struct list_head *n) { n->prev->next = n->next; n->next->prev = n->prev; }
#define list_entry(p, t, m) container_of(p, t, m)
#define list_for_each_entry(p, h, m) \
	for (p = list_entry((h)->next, __typeof__(*p), m); &p->m != (h); \
	     p = list_entry(p->m.next, __typeof__(*p), m))
#define list_for_each_entry_safe(p, n, h, m) \
	for (p = list_entry((h)->next, __typeof__(*p), m), n = list_entry(p->m.next, __typeof__(*p), m); \
	     &p->m != (h); p = n, n = list_entry(n->m.next, __typeof__(*n), m))
struct uid_data { struct list_head list; uint32_t uid; char package[KSU_MAX_PACKAGE_NAME]; };
struct dir_context { int (*actor)(struct dir_context *, const char *, int, off_t, uint64_t, unsigned int); };
struct super_mock { unsigned long s_magic; };
struct inode_mock { struct super_mock *i_sb; };
struct file { struct inode_mock *f_inode; int index; };
static struct super_mock sb = { 0xef53 };
static struct inode_mock inode = { &sb };
struct fixture { const char *path; const char *names[4]; unsigned int types[4]; };
static const struct fixture fs[] = {
	{ "/data/app", {"~~outer"}, {DT_DIR} },
	{ "/data/app/~~outer", {"me.yuki.fina-one", "me.weishu.kernelsu-two"}, {DT_DIR, DT_DIR} },
	{ "/data/app/~~outer/me.yuki.fina-one", {"base.apk"}, {DT_REG} },
	{ "/data/app/~~outer/me.weishu.kernelsu-two", {"base.apk"}, {DT_REG} },
};
static struct file *ksu_filp_open_nonotify(const char *path, int flags)
{
	(void)flags;
	for (int i = 0; i < 4; ++i) if (!strcmp(path, fs[i].path)) {
		struct file *f = malloc(sizeof(*f)); assert(f); *f = (struct file){ &inode, i }; return f;
	}
	return NULL;
}
static void filp_close(struct file *f, void *unused) { (void)unused; free(f); }
static void iterate_dir(struct file *f, struct dir_context *ctx)
{
	const struct fixture *d = &fs[f->index];
	for (int i = 0; i < 4 && d->names[i]; ++i)
		if (ctx->actor(ctx, d->names[i], strlen(d->names[i]), 0, 1, d->types[i])) break;
}
static int fina_cert, other_cert;
/* Certificate parser is deliberately mocked; no APK cryptographic claim. */
static bool check_v2_signature(char *path, unsigned int size, const char *hash)
{
	int cert = strstr(path, "/me.yuki.fina-") ? fina_cert : other_cert;
	if (cert == 1) return size == 0x2cc && !strcmp(hash, "2d89b50aaf1db013c2b6738f973f48b62ea21a3a8d7216bfec3521065d448458");
	if (cert == 2) return size == EXPECTED_SIZE && !strcmp(hash, EXPECTED_HASH);
	return false;
}
/* SOURCE_SIGN */
/* SOURCE_CROWN */
/* SOURCE_SCANNER */
static int copy_fault;
static int copy_to_user(void *dst, const void *src, size_t n)
{ if (copy_fault) return 1; memcpy(dst, src, n); return 0; }
/* SOURCE_METADATA_STRUCTS */
/* SOURCE_METADATA */
static unsigned long checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "FAILED %s:%d: %s\n", __FILE__, __LINE__, #x); abort(); } } while (0)
static void add_uid(struct list_head *h, struct uid_data *p, const char *pkg, uid_t uid)
{ memset(p, 0, sizeof(*p)); strscpy(p->package, pkg, sizeof(p->package)); p->uid = uid; list_add_tail(&p->list, h); }
static void test_auth(void)
{
	const char *packages[] = {"me.yuki.fina", "me.yuki.fina.pr", "me.yuki.fina.pr123", "me.yuki.fina.evil", "me.yuki.finaevil", "com.attacker.app", KSU_PACKAGE_NAME, "com.kowx712.supermanager", "com.midori.supermanager"};
	char path[DATA_PATH_LEN], pkg[KSU_MAX_PACKAGE_NAME];
	for (unsigned int i = 0; i < sizeof(packages)/sizeof(*packages); ++i) {
		bool fina = !strcmp(packages[i], "me.yuki.fina");
		bool old = i >= 6;
		snprintf(path, sizeof(path), "/data/app/~~id/%s-one/base.apk", packages[i]);
		CHECK(!ksu_package_from_apk_path(pkg, path)); CHECK(!strcmp(pkg, packages[i]));
		CHECK(ksu_is_manager_package(pkg) == (fina || old));
		for (int cert = 0; cert < 3; ++cert) {
			fina_cert = other_cert = cert;
			CHECK(is_manager_apk(path) == ((fina && cert == 1) || (old && cert == 2)));
		}
	}
	CHECK(ksu_package_from_apk_path(pkg, "base.apk") < 0);
	CHECK(ksu_package_from_apk_path(pkg, "/data/app/me.yuki.fina/base.apk") < 0);
	CHECK(ksu_package_from_apk_path(pkg, "/data/app/me.yuki.fina-one/split.apk") < 0);
	CHECK(ksu_package_from_apk_path(pkg, "/data/app/me.yuki.fina-one/base.apk.evil") < 0);
	memset(path, 'x', sizeof(path)); strcpy(path, "/data/app/"); memset(path + 10, 'x', 300);
	strcpy(path + 310, "/me.yuki.fina-one/base.apk");
	CHECK(ksu_package_from_apk_path(pkg, path) < 0);
}
static void test_selection(void)
{
	const char *fina = "/data/app/~~outer/me.yuki.fina-one/base.apk";
	const uid_t uids[] = {10000, 12345, 99000, 110000, 1012345};
	for (unsigned int u = 0; u < sizeof(uids)/sizeof(*uids); ++u)
	for (int reverse = 0; reverse < 2; ++reverse)
	for (int present = 0; present < 2; ++present)
	for (int cert = 0; cert < 3; ++cert) {
		struct list_head head; struct uid_data a, b; INIT_LIST_HEAD(&head);
		if (reverse) add_uid(&head, &b, KSU_PACKAGE_NAME, 12346);
		if (present) add_uid(&head, &a, KSU_FINASU_PACKAGE_NAME, uids[u]);
		if (!reverse) add_uid(&head, &b, KSU_PACKAGE_NAME, 12346);
		ksu_invalidate_manager_uid();
		CHECK(crown_manager(fina, &head) == !!present);
		CHECK(ksu_get_manager_appid() == (present ? uids[u] % KSU_PER_USER_RANGE : (uid_t)KSU_INVALID_APPID));
		ksu_invalidate_manager_uid(); cached_manager_apk_path[0] = 0;
		fina_cert = cert; other_cert = 2;
		search_manager("/data/app", 2, &head);
		uid_t expected = present && cert == 1 ? uids[u] % KSU_PER_USER_RANGE : 12346;
		CHECK(ksu_get_manager_appid() == expected);
		CHECK(strstr(cached_manager_apk_path, expected == 12346 ? "/me.weishu.kernelsu-" : "/me.yuki.fina-") != NULL);
		caller_uid = expected; CHECK(is_manager()); CHECK(is_uid_manager(expected + 100000));
		caller_uid = expected + 1; CHECK(!is_manager()); CHECK(!is_uid_manager(expected + 1));
		caller_uid = 0; CHECK(!is_manager());
	}
	ksu_set_manager_appid(KSU_INVALID_APPID); CHECK(!ksu_is_manager_appid_valid());
	fina_cert = other_cert = 0; cached_manager_apk_path[0] = 0;
	struct list_head head; INIT_LIST_HEAD(&head);
	search_manager("/data/app", 2, &head);
	CHECK(!ksu_is_manager_appid_valid()); CHECK(!cached_manager_apk_path[0]);
}
static void test_metadata(void)
{
	CHECK(_IOC_SIZE(KSU_IOCTL_GET_FULL_VERSION_FINASU) == 64);
	CHECK(_IOC_NR(KSU_IOCTL_GET_FULL_VERSION_FINASU) == 29);
	CHECK(_IOC_DIR(KSU_IOCTL_GET_FULL_VERSION_FINASU) == _IOC_READ);
	CHECK(_IOC_SIZE(KSU_IOCTL_GET_FULL_VERSION) == 0);
	CHECK(_IOC_NR(KSU_IOCTL_HOOK_TYPE) == 101);
	int (*handlers[])(void *) = {do_get_full_version_finasu, do_get_full_version, do_get_version_tag, do_get_hook_mode, do_get_hook_type};
	const size_t sizes[] = {64, 255, 32, 16, 32};
	const char *texts[] = {KSU_COMPAT_VERSION_FULL, KSU_COMPAT_VERSION_FULL, KSU_COMPAT_VERSION_TAG, EXPECTED_HOOK_TYPE, EXPECTED_HOOK_TYPE};
	for (unsigned int i = 0; i < sizeof(sizes)/sizeof(*sizes); ++i) {
		unsigned char data[260]; memset(data, 0xa5, sizeof(data));
		CHECK(!handlers[i](data + 1)); CHECK(!strcmp((char *)data + 1, texts[i]));
		CHECK(data[0] == 0xa5); CHECK(data[sizes[i]+1] == 0xa5);
		for (size_t j = strlen(texts[i]) + 1; j < sizes[i]; ++j) CHECK(data[j + 1] == 0);
		copy_fault = 1; CHECK(handlers[i](NULL) == -EFAULT); copy_fault = 0;
	}
}
int main(void)
{
	test_auth(); test_selection(); test_metadata();
	printf("FinaSU extracted-source auth/UID/scanner/metadata: %lu checks PASS (%s)\n", checks, EXPECTED_HOOK_TYPE);
	return 0;
}

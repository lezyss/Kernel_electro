// SPDX-License-Identifier: GPL-2.0
/* Actual extracted KGSL functions; mocked fences, file descriptors and IRQ context. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>

struct list_head { struct list_head *next, *prev; };
#define INIT_LIST_HEAD(p) do { (p)->next = (p); (p)->prev = (p); } while (0)
#define list_entry(p, type, member) ((type *)((char *)(p) - offsetof(type, member)))
#define list_for_each_entry_safe(pos, next_entry, head, member) \
    for ((pos) = list_entry((head)->next, __typeof__(*(pos)), member), \
         (next_entry) = list_entry((pos)->member.next, __typeof__(*(pos)), member); \
         &(pos)->member != (head); \
         (pos) = (next_entry), \
         (next_entry) = list_entry((next_entry)->member.next, __typeof__(*(pos)), member))
static void list_add_tail(struct list_head *p, struct list_head *head)
{
    p->prev = head->prev; p->next = head;
    head->prev->next = p; head->prev = p;
}
static void list_del_init(struct list_head *p)
{
    assert(p->prev->next == p && p->next->prev == p);
    p->next->prev = p->prev; p->prev->next = p->next;
    INIT_LIST_HEAD(p);
}
static unsigned irq_disabled, lock_calls, put_calls;
static void spin_lock(unsigned *lock)
{
    /* Model the hard-IRQ fence-lock recursion hazard on a process-context holder. */
    assert(irq_disabled && !*lock);
    *lock = 1; lock_calls++;
}
static void spin_unlock(unsigned *lock) { assert(*lock); *lock = 0; }
#define spin_lock_irqsave(lock, flags) do { (flags) = irq_disabled; irq_disabled = 1; spin_lock(lock); } while (0)
#define spin_unlock_irqrestore(lock, flags) do { spin_unlock(lock); irq_disabled = (flags); } while (0)
struct dma_fence { unsigned *lock, refs; bool signaled; };
struct kgsl_syncsource { unsigned lock; struct list_head child_list_head; };
struct kgsl_syncsource_fence {
    struct dma_fence fence;
    struct list_head child_list;
    struct kgsl_syncsource *parent;
};
struct kgsl_process_private { struct kgsl_syncsource *source; };
struct kgsl_device_private { struct kgsl_process_private *process_priv; void *device; };
struct kgsl_syncsource_create_fence { unsigned id; int fence_fd; };
struct sync_file { struct sync_file *file; struct dma_fence *fence; };
static struct sync_file *installed;
static bool fail_alloc, fail_file, fail_fd;
static const int kgsl_syncsource_fence_ops;
#define GFP_KERNEL 0
#define KGSL_DRV_ERR(...) ((void)0)
static void *kzalloc(size_t n, int flags) { return fail_alloc ? NULL : calloc(1, n); }
static struct kgsl_syncsource *kgsl_syncsource_get(struct kgsl_process_private *p, unsigned id)
{ return id == 1 ? p->source : NULL; }
static void kgsl_syncsource_put(struct kgsl_syncsource *p) { if (p) put_calls++; }
static unsigned dma_fence_context_alloc(unsigned n) { return n; }
static void dma_fence_init(struct dma_fence *f, const int *ops, unsigned *lock,
                           unsigned context, unsigned seq)
{ f->lock = lock; f->refs = 1; }
static void dma_fence_put(struct dma_fence *f)
{
    assert(f->refs);
    if (!--f->refs) free(list_entry(f, struct kgsl_syncsource_fence, fence));
}
static struct sync_file *sync_file_create(struct dma_fence *f)
{
    struct sync_file *s;
    if (fail_file) return NULL;
    s = malloc(sizeof(*s)); assert(s);
    s->file = s; s->fence = f; f->refs++;
    return s;
}
static int get_unused_fd_flags(unsigned flags) { return fail_fd ? -1 : 17; }
static void fd_install(int fd, struct sync_file *s) { assert(fd == 17 && !installed); installed = s; }
static void fput(struct sync_file *s) { dma_fence_put(s->fence); free(s); }
static void dma_fence_signal_locked(struct dma_fence *f)
{ assert(irq_disabled && *f->lock); f->signaled = true; }
/* FUNCTIONS */
int main(void)
{
    unsigned incoming, failure;
    for (incoming = 0; incoming < 2; incoming++) {
        struct kgsl_syncsource source = {0};
        struct kgsl_process_private private = { .source = &source };
        struct kgsl_device_private dev = { .process_priv = &private };
        struct kgsl_syncsource_create_fence param = { .id = 1 };
        struct dma_fence other = {0};
        struct sync_file *first;
        INIT_LIST_HEAD(&source.child_list_head);
        irq_disabled = incoming; lock_calls = put_calls = 0;
        assert(kgsl_ioctl_syncsource_create_fence(&dev, 0, &param) == 0);
        assert(param.fence_fd == 17 && irq_disabled == incoming && !source.lock);
        assert(lock_calls == 1 && installed && !installed->fence->signaled);
        first = installed; installed = NULL;
        assert(kgsl_syncsource_signal(&source, &other) == -EINVAL);
        assert(irq_disabled == incoming && !source.lock);
        assert(kgsl_syncsource_signal(&source, first->fence) == 0);
        assert(first->fence->signaled && source.child_list_head.next == &source.child_list_head);
        assert(irq_disabled == incoming && !source.lock && lock_calls == 3);
        fput(first);
        /* Cleanup signals and removes all remaining children under IRQ-safe locking. */
        assert(kgsl_ioctl_syncsource_create_fence(&dev, 0, &param) == 0);
        first = installed; installed = NULL;
        assert(kgsl_ioctl_syncsource_create_fence(&dev, 0, &param) == 0);
        kgsl_syncsource_cleanup(&private, &source);
        assert(first->fence->signaled && installed->fence->signaled && put_calls == 1);
        assert(source.child_list_head.next == &source.child_list_head);
        assert(source.child_list_head.prev == &source.child_list_head);
        assert(irq_disabled == incoming && !source.lock && lock_calls == 6);
        fput(first); fput(installed); installed = NULL;
        /* Pre-lock failure paths must not alter IRQ state or leave a held lock. */
        for (failure = 0; failure < 4; failure++) {
            fail_alloc = failure == 0; fail_file = failure == 1; fail_fd = failure == 2;
            param.id = failure == 3 ? 99 : 1;
            assert(kgsl_ioctl_syncsource_create_fence(&dev, 0, &param) < 0);
            assert(!installed && !source.lock && irq_disabled == incoming && lock_calls == 6);
        }
        fail_alloc = fail_file = fail_fd = false;
    }
    puts("PASS: extracted KGSL create/signal/cleanup; incoming IRQ states; fence list operations; allocation/file/FD/lookup failures");
    return 0;
}

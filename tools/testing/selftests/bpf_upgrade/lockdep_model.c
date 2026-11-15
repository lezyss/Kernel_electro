// SPDX-License-Identifier: GPL-2.0
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct hlist_node { struct hlist_node *next;struct hlist_node **pprev; };
struct hlist_head { struct hlist_node *first; };
struct lock_class_key { struct hlist_node hash_entry;char subkeys[8]; };
#define KEYHASH_BITS 4
#define KEYHASH_SIZE (1U<<KEYHASH_BITS)
static struct hlist_head lock_keys_hash[KEYHASH_SIZE];
static struct lock_class_key static_key;
static bool debug_locks=true,irq_disabled,graph_held;
static int warnings,rcu_done,sched_done;
static unsigned long retired;
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define hlist_for_each_entry_rcu(k,h,m) \
 for(struct hlist_node *it=(h)->first;it && ((k)=container_of(it,typeof(*(k)),m));it=it->next)
static void hlist_add_head_rcu(struct hlist_node *n,struct hlist_head *h)
{ assert(graph_held);n->next=h->first;if(n->next)n->next->pprev=&n->next;h->first=n;n->pprev=&h->first; }
static void hlist_del_rcu(struct hlist_node *n)
{ assert(graph_held);*n->pprev=n->next;if(n->next)n->next->pprev=n->pprev; }
#define hash_long(p,b) (((p)>>4)&((1U<<(b))-1))
#define static_obj(p) ((p)==&static_key)
#define WARN_ON_ONCE(x) ((x)?(++warnings,true):false)
#define raw_local_irq_save(f) do { (f)=irq_disabled;irq_disabled=true; } while(0)
#define raw_local_irq_restore(f) (irq_disabled=(f))
static bool graph_lock(void) { assert(irq_disabled && !graph_held);if(!debug_locks)return false;graph_held=true;return true; }
static void graph_unlock(void) { assert(graph_held);graph_held=false; }
#define EXPORT_SYMBOL_GPL(x)
#define rcu_read_lock() ((void)0)
#define rcu_read_unlock() ((void)0)
#define might_sleep() assert(!irq_disabled && !graph_held)
static inline void synchronize_rcu(void) { assert(!irq_disabled && !graph_held);rcu_done++; }
static void synchronize_sched(void) { assert(!irq_disabled && !graph_held);sched_done++; }
static void lockdep_free_key_range(void *p,unsigned long size)
{
 struct lock_class_key *key=p;
 assert(rcu_done && sched_done && !irq_disabled && !graph_held);
 for(int i=0;i<8;i++) assert((char *)&key->subkeys[i]>=(char *)p && (char *)&key->subkeys[i]<(char *)p+size);
 rcu_done=sched_done=0;retired++;
}
/* EXTRACTED */
int main(void)
{
 unsigned long checks=0;
 assert(!is_dynamic_key(&static_key));
 lockdep_register_key(&static_key);assert(warnings==2);warnings=0;
 for(int i=0;i<20000;i++) {
  struct lock_class_key *key=calloc(1,sizeof(*key));assert(key);
  assert(!is_dynamic_key(key));irq_disabled=i%2;
  lockdep_register_key(key);assert(irq_disabled==!!(i%2));assert(is_dynamic_key(key));
  lockdep_register_key(key);assert(warnings==1);warnings=0;
  irq_disabled=false;lockdep_unregister_key(key);
  assert(!is_dynamic_key(key) && !irq_disabled);free(key);checks+=4;
 }
 assert(retired==20000);
 /* Debug-disabled code must not walk a registry containing freed keys. */
 struct lock_class_key *key=calloc(1,sizeof(*key));assert(key);
 lockdep_register_key(key);debug_locks=false;lockdep_unregister_key(key);free(key);
 struct lock_class_key other={0};assert(is_dynamic_key(&other));checks++;
 printf("PASS: %lu dynamic lockdep key checks; registration, duplicate rejection, full-subkey retirement, grace/IRQ context and debug-disabled UAF avoidance (mocked platform)\n",checks);
 return 0;
}

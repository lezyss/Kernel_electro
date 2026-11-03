#ifndef __KSU_H_MANAGER_IDENTITY
#define __KSU_H_MANAGER_IDENTITY

// #include "allowlist.h"

#define KSU_INVALID_APPID -1
#define KSU_PER_USER_RANGE 100000

extern uid_t ksu_manager_appid; // DO NOT DIRECT USE

static inline bool ksu_is_manager_appid_valid()
{
	return READ_ONCE(ksu_manager_appid) != KSU_INVALID_APPID;
}

static inline bool is_manager()
{
	return unlikely(READ_ONCE(ksu_manager_appid) == current_uid().val % KSU_PER_USER_RANGE);
}

static inline bool is_uid_manager(uid_t uid)
{
	return unlikely(READ_ONCE(ksu_manager_appid) == uid % KSU_PER_USER_RANGE);
}

static inline uid_t ksu_get_manager_appid()
{
	return READ_ONCE(ksu_manager_appid);
}

static inline void ksu_set_manager_appid(uid_t appid)
{
	WRITE_ONCE(ksu_manager_appid, appid == KSU_INVALID_APPID ?
		   KSU_INVALID_APPID : appid % KSU_PER_USER_RANGE);
}

static inline void ksu_invalidate_manager_uid()
{
	WRITE_ONCE(ksu_manager_appid, KSU_INVALID_APPID);
}

#endif

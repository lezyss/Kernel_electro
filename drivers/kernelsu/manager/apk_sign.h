#ifndef __KSU_H_APK_V2_SIGN
#define __KSU_H_APK_V2_SIGN

/* Production FinaSU only: no PR/debug package suffix or unrelated fork keys. */
#define KSU_FINASU_PACKAGE_NAME "me.yuki.fina"
#define KSU_FINASU_CERT_SIZE 0x2cc
#define KSU_FINASU_CERT_SHA256 "2d89b50aaf1db013c2b6738f973f48b62ea21a3a8d7216bfec3521065d448458"

bool is_manager_apk(char *path);
bool ksu_is_manager_package(const char *package);
int ksu_package_from_apk_path(char *package, const char *path);
int get_pkg_from_apk_dir_path(char *pkg, const char *path);

#endif

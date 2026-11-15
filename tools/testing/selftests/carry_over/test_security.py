#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Current-source security models and vendoring identities, NOT live VFS/LSM proof."""
import hashlib
import json
from pathlib import Path
import resource
import sys

ROOT = Path(__file__).resolve().parents[4]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    driver = ROOT / 'drivers/kernelsu'
    manifest = json.loads((driver / 'UPSTREAM.json').read_text())
    assert manifest['commit'] == 'ae63c92098d94bdad1696c74a3ad2e96692118bf'
    assert manifest['finasu_overlay']['manager_review_commit'] == '2d5786b9129a254a87ac358c8bec0203ccd53351'
    for name, oid in manifest['git_blob_sha1'].items():
        data = (driver / name).read_bytes()
        if name in manifest['local_sha256']:
            assert hashlib.sha256(data).hexdigest() == manifest['local_sha256'][name], name
        else:
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == oid, name
    nm = ROOT / 'fs/nomount'
    manifest = json.loads((nm / 'UPSTREAM.json').read_text())
    assert manifest['commit'] == '5e9feb6f3fce42423f56b37e344052c59ec16b66'
    for name, record in manifest['upstream_files'].items():
        data = (nm / name).read_bytes()
        if name in manifest['local_sha256']:
            assert hashlib.sha256(data).hexdigest() == manifest['local_sha256'][name], name
        else:
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == record['git_blob'], name
    print('PASS: exact KSU +50/FinaSU and NoMount API23 vendored identities/local adaptations', flush=True)
    sys.path.insert(0, str(ROOT / 'tools/testing/selftests/kernelsu'))
    import test_update50 as ksu
    ksu.current_models(True)
    ksu.helper_models(True)
    sys.path.insert(0, str(ROOT / 'tools/testing/selftests/nomount'))
    import test_update23 as nomount
    nomount.current_models(True)
    nomount.io_models(True)
    # Supplement the extracted models with guards for native merge resolutions.
    fork = (ROOT / 'kernel/fork.c').read_text()
    assert 'struct multiprocess_signals delayed;' in fork
    assert 'hlist_add_head(&delayed.node, &current->signal->multiprocess);' in fork
    assert 'if (IS_ERR(pidfile)) {\n\t\t\tretval = PTR_ERR(pidfile);' in fork
    assert 'args->pidfd == args->parent_tid)' in fork
    assert 'bool legacy_clone_args_valid(' in fork
    namei = (ROOT / 'fs/namei.c').read_text()
    assert 'dir_inode->i_op->atomic_open && likely(!hidden)' in namei
    assert 'inode_lock_killable(dir->d_inode)' in namei
    writeback = (ROOT / 'fs/fs-writeback.c').read_text()
    tail = writeback[writeback.index('if (!was_dirty) {'):]
    assert tail.index('if (inode->i_state & (I_WILL_FREE | I_FREEING))') < tail.index('wakeup_bdi = inode_io_list_move_locked')
    assert tail.count('trace_writeback_dirty_inode_enqueue(inode);') == 1
    superblock = (ROOT / 'fs/super.c').read_text()
    assert 'bool ksu_dev = !READ_ONCE(susfs_is_sdcard_android_data_decrypted)' in superblock
    assert 'ksu_dev ? DEFAULT_KSU_MNT_MINOR_DEV :' in superblock
    print('PASS: native signal/clone3/vendor-path preservation, pidfd errors/nonaliasing, writeback ordering and IDA decision snapshot')
    print('LIMITS: mocked authorization/RCU/VFS; no runtime security certification, APK fingerprint audit or installation test')


if __name__ == '__main__':
    main()

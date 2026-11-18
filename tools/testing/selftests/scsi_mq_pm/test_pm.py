#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Compile real extracted PM helpers with host mocks. Not kernel/RCU proof."""
import argparse
from pathlib import Path
import re
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def function(source, name):
    match = re.search(r'^(?:static (?:inline )?)?(?:int|bool|void) ' + name + r'\([^;]*?\)\n\{',
                      source, re.M)
    assert match, name
    start = source.index('{', match.start())
    level = 1
    end = start + 1
    while level:
        level += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end] + '\n'


def generated():
    core = (ROOT / 'block/blk-core.c').read_text()
    mq = (ROOT / 'block/blk-mq.c').read_text()
    ref = (ROOT / 'lib/percpu-refcount.c').read_text()
    header = (ROOT / 'block/blk-mq-pm.h').read_text()
    header = re.sub(r'^#include.*\n', '', header, flags=re.M)
    pieces = [header, function(ref, 'percpu_ref_resurrect'), function(ref, 'percpu_ref_reinit'),
              function(mq, 'blk_mq_unfreeze_queue'), function(core, 'blk_pm_runtime_init'),
              '#ifdef CONFIG_BLK_MQ_RUNTIME_PM\n', function(core, 'blk_mq_pm_pre_suspend'), '#endif\n']
    for name in ('blk_queue_enter_pm', 'blk_queue_enter', 'blk_queue_exit',
                 'blk_pre_runtime_suspend', 'blk_post_runtime_suspend',
                 'blk_pre_runtime_resume', 'blk_set_runtime_active', 'blk_post_runtime_resume'):
        pieces.append(function(core, name))
    return '\n'.join(pieces)


def integration_checks():
    core = (ROOT / 'block/blk-core.c').read_text()
    mq = (ROOT / 'block/blk-mq.c').read_text()
    scsi = (ROOT / 'drivers/scsi/scsi_lib.c').read_text()
    header = (ROOT / 'include/linux/blk-mq.h').read_text()
    assert 'BLK_MQ_REQ_PREEMPT\t= (1 << 3)' in header
    assert 'BLK_MQ_REQ_INTERNAL\t= (1 << 2)' in header
    for name in ('blk_mq_alloc_request', 'blk_mq_alloc_request_hctx'):
        body = mq.split('struct request *' + name + '(', 1)[1].split('EXPORT_SYMBOL', 1)[0]
        assert 'blk_queue_enter_pm(q,' in body and 'flags & BLK_MQ_REQ_PREEMPT' in body
        assert 'rq->rq_flags |= RQF_PREEMPT' in body
    free = function(mq, 'blk_mq_free_request')
    assert free.index('blk_mq_pm_mark_last_busy(rq)') < free.index('blk_queue_exit(q)')
    start = scsi.index('int scsi_execute(')
    allocation = scsi[start:scsi.index('rq = scsi_req(req);', start)]
    assert 'IS_ENABLED(CONFIG_BLK_MQ_RUNTIME_PM)' in allocation
    assert 'blk_mq_alloc_request(' in allocation and 'BLK_MQ_REQ_PREEMPT' in allocation
    assert 'initialize_rq_fn(req)' in allocation
    assert 'blk_get_request(' in allocation  # unchanged legacy fallback
    assert 'q->mq_ops && !IS_ENABLED(CONFIG_BLK_MQ_RUNTIME_PM)' in core
    kconfig = (ROOT / 'block/Kconfig').read_text().split('config BLK_MQ_RUNTIME_PM\n', 1)[1].split('\nconfig ', 1)[0]
    assert 'depends on PM && SCSI_MQ_DEFAULT' in kconfig and 'default n' in kconfig
    workflow = (ROOT / '.github/workflows/build-kernel.yml').read_text()
    assert 'TEST_SCSI_MQ_PM:' in workflow and '      scsi_mq_pm:' in workflow
    assert '        default: false' in workflow.split('      scsi_mq_pm:', 1)[1].split('\npermissions:', 1)[0]
    assert "inputs.scsi_mq_pm && '-pm'" in workflow
    print('PASS: Kconfig default-off, allocation-time SCSI bypass, completion and workflow wiring')


def run(cc, out, source, enabled, expected=True, name='base'):
    path = out / (name + '.c')
    path.write_text((HERE / 'harness.c').read_text().replace('/* EXTRACTED_FUNCTIONS */', source))
    binary = out / (name + '-' + str(enabled))
    cmd = [*cc, '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
           '-Wno-unused-function', '-Wno-unused-parameter', '-DENABLE_PM=' + str(enabled),
           '-fsanitize=undefined', '-fno-sanitize-recover=all', str(path), '-o', str(binary)]
    subprocess.run(cmd, check=True)
    result = subprocess.run([str(binary)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert (result.returncode == 0) == expected, (name, result.stdout)
    if expected:
        print('ENABLE_PM=' + str(enabled) + ': ' + result.stdout.strip())
    else:
        print('PASS: rejected mutation ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    integration_checks()
    code = generated()
    with tempfile.TemporaryDirectory(prefix='mq-pm-host-') as tmp:
        out = Path(tmp)
        cc = shlex.split(args.cc)
        run(cc, out, code, 0)
        run(cc, out, code, 1)
        mutations = [
            ('bypass-all-io', 'if (pm || !blk_mq_pm_only(q))', 'if (true)'),
            ('block-pm-commands', 'if (pm || !blk_mq_pm_only(q))', 'if (!blk_mq_pm_only(q))'),
            ('omit-busy-gate-release', '\n\t\tblk_mq_pm_clear_only(q);\n\t}\n\treturn ret;', '\n\t}\n\treturn ret;'),
            ('omit-completion-busy', 'pm_runtime_mark_last_busy(rq->q->dev);', '(void)rq;'),
            ('omit-percpu-restore', 'percpu_ref_switch_to_percpu(&q->q_usage_counter);', '(void)q;'),
            ('release-gate-on-every-resume', 'if (old_status != RPM_ACTIVE)', 'if (old_status >= RPM_ACTIVE)'),
        ]
        for name, old, new in mutations:
            assert old in code, name
            run(cc, out, code.replace(old, new, 1), 1, False, name)
    print('Host mocks do not validate real RCU ordering, SCSI/UFS hardware, crypto or PM safety.')


if __name__ == '__main__':
    main()

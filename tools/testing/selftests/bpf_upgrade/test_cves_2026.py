#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted BPF CVE regressions; host mocks, not a live kernel exploit test."""
import argparse
from pathlib import Path
import resource
import subprocess
import tempfile
from test_jmp32 import ROOT, HERE, function


def macro(text, name):
    lines = text[text.index('#define ' + name + '('):].splitlines(True)
    out = ''
    for line in lines:
        out += line
        if not line.rstrip().endswith('\\'):
            return out
    raise AssertionError(name)


def source(mutation=None):
    core = (ROOT / 'kernel/bpf/core.c').read_text()
    verifier = (ROOT / 'kernel/bpf/verifier.c').read_text()
    inode = (ROOT / 'kernel/bpf/bpf_inode_storage.c').read_text()
    hooks = (ROOT / 'security/bpf/hooks.c').read_text()
    header = (ROOT / 'include/linux/bpf_lsm.h').read_text()
    assert 'extern bool bpf_lsm_initialized __ro_after_init;' in header
    assert '#define bpf_lsm_initialized false' in header
    assert 'bool bpf_lsm_initialized __ro_after_init;' in hooks
    filt = (ROOT / 'include/linux/filter.h').read_text()
    code = '\n'.join(macro(filt, name) for name in (
        'BPF_ALU64_REG', 'BPF_ALU32_REG', 'BPF_ALU64_IMM', 'BPF_ALU32_IMM',
        'BPF_JMP_REG', 'BPF_JMP32_REG', 'BPF_ZEXT_REG', 'BPF_STX_MEM'))
    code += '\n' + function(core, 'static int bpf_jit_blind_insn(')
    code += '\n' + function(core, 'struct bpf_prog *bpf_jit_blind_constants(')
    code += '\n' + function(hooks, 'static int __init bpf_lsm_init(')
    code += '\n' + function(inode, 'static struct bpf_map *inode_storage_map_alloc(')
    for sig in ('static int __check_buffer_access(', 'static int check_tp_buffer_access(',
                'static int check_buffer_access('):
        code += '\n' + function(verifier, sig)
    if mutation == 'jump64':
        code = code.replace('if (off < S16_MIN)\n\t\t\treturn -ERANGE;', '', 1)
    elif mutation == 'jump32':
        pos = code.index('case BPF_JMP32 | BPF_JEQ')
        code = code[:pos] + code[pos:].replace('if (off < S16_MIN)\n\t\t\treturn -ERANGE;', '', 1)
    elif mutation == 'propagation':
        code = code.replace('if (rewritten < 0)', 'if (false)')
    elif mutation == 'inode-guard':
        code = code.replace('if (!bpf_lsm_initialized)', 'if (false)')
    elif mutation == 'lsm-init':
        code = code.replace('bpf_lsm_initialized = true;', ';')
    elif mutation == 'buffer-offset':
        code = code.replace('!tnum_is_const(reg->var_off) || reg->var_off.value',
                            '!tnum_is_const(reg->var_off)')
    return (HERE / 'cves_2026_host.c').read_text().replace('/* EXTRACTED */', code)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cc', default='cc')
    a = p.parse_args()
    with tempfile.TemporaryDirectory(prefix='bpf-cves-') as tmp:
        c, binary = Path(tmp) / 'test.c', Path(tmp) / 'test'
        # Use this tree's BPF UAPI with host-exported types, not raw kernel
        # internal types/stddef headers (which require a configured build).
        uapi = Path(tmp) / 'uapi/linux'
        uapi.mkdir(parents=True)
        for name in ('bpf.h', 'bpf_common.h'):
            (uapi / name).write_text((ROOT / 'include/uapi/linux' / name).read_text())
        for mutation in (None, 'jump64', 'jump32', 'propagation', 'inode-guard',
                         'lsm-init', 'buffer-offset'):
            c.write_text(source(mutation))
            subprocess.run([a.cc, '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra',
                            '-Werror', '-Wno-unused-parameter', '-Wno-sign-compare', '-fsanitize=undefined',
                            '-fno-sanitize-recover=all', '-I' + str(uapi.parent),
                            str(c), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True,
                                    preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if (result.returncode == 0) != (mutation is None):
                raise AssertionError(f'{mutation}: {result.stdout}\n{result.stderr}')
            print(f'{mutation or "fixed source"}: ' + ('rejected as expected' if mutation else result.stdout.strip()))


if __name__ == '__main__':
    main()

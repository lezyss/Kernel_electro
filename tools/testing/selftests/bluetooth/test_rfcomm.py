#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted RFCOMM socket/MCC regressions with mocked kernel primitives."""
import argparse
from pathlib import Path
import resource
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def source(mutation=None):
    core = (ROOT / 'net/bluetooth/rfcomm/core.c').read_text()
    sock = (ROOT / 'net/bluetooth/rfcomm/sock.c').read_text()
    header = (ROOT / 'include/net/bluetooth/rfcomm.h').read_text()
    definitions = '\n'.join(line for line in header.splitlines()
                            if line.startswith('#define RFCOMM_'))
    definitions += '\n' + core[core.index('#define __get_dlci'):core.index('static DECLARE_WAIT_QUEUE_HEAD')]
    for name in ('mcc', 'pn', 'rpn', 'rls', 'msc'):
        definitions += '\n' + function(header, 'struct rfcomm_' + name + ' {') + ' __packed;'
    code = function(sock, 'static struct sock *rfcomm_get_sock_by_channel(')
    code += '\n' + function(sock, 'int rfcomm_connect_ind(')
    for name in ('pn', 'rpn', 'rls', 'msc', 'mcc'):
        code += '\n' + function(core, 'static int rfcomm_recv_' + name + '(')
    if mutation == 'listener-ref':
        code = code.replace('sock_hold(sk);', ';')
    elif mutation == 'listener-state':
        code = code.replace('if (parent->sk_state != BT_LISTEN)', 'if (false)')
    elif mutation == 'listener-put':
        code = code.replace('sock_put(parent);', ';')
    elif mutation in ('pn', 'rls', 'msc', 'mcc'):
        code = code.replace('if (!pskb_may_pull(skb, sizeof(*' + mutation + ')))', 'if (false)')
    elif mutation == 'rpn':
        code = code.replace('if (!pskb_may_pull(skb, len == 1 ? 1 : sizeof(*rpn)))', 'if (false)')
    elif mutation == 'rpn-short':
        code = code.replace('len == 1 ? 1 : sizeof(*rpn)', 'sizeof(*rpn)')
    return (HERE / 'rfcomm_host.c').read_text().replace('/* DEFINITIONS */', definitions).replace('/* FUNCTIONS */', code)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cc', default='cc')
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix='rfcomm-') as tmp:
        c, binary = Path(tmp) / 'test.c', Path(tmp) / 'test'
        for mutation in (None, 'listener-ref', 'listener-state', 'listener-put',
                         'pn', 'rls', 'msc', 'mcc', 'rpn', 'rpn-short'):
            c.write_text(source(mutation))
            subprocess.run([args.cc, '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra',
                            '-Werror', '-Wno-unused-parameter', '-fsanitize=undefined',
                            '-fno-sanitize-recover=all', str(c), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True,
                                    preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if (result.returncode == 0) != (mutation is None):
                raise AssertionError(f'{mutation}: {result.stdout}\n{result.stderr}')
            print(f'{mutation or "fixed source"}: ' + ('caught' if mutation else result.stdout.strip()))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Host checks of the actual suspend-state predicates, not device suspend tests."""
import argparse
import os
from pathlib import Path
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


MODEL = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
typedef int suspend_state_t;
enum { PM_SUSPEND_ON, PM_SUSPEND_TO_IDLE, PM_SUSPEND_STANDBY,
       PM_SUSPEND_MEM, PM_SUSPEND_MAX };
struct platform_suspend_ops {
    int (*valid)(suspend_state_t);
    int (*enter)(suspend_state_t);
};
static const struct platform_suspend_ops *suspend_ops;
static unsigned valid_mask, valid_calls, enter_calls;
static int callback_valid(suspend_state_t state)
{
    valid_calls++;
    return !!(valid_mask & (1U << state));
}
static int callback_enter(suspend_state_t state)
{
    (void)state;
    enter_calls++;
    return 0;
}
/* FUNCTIONS */
int main(void)
{
    unsigned has_ops, has_valid, has_enter, bits, checks = 0;
    suspend_state_t state;
    for (has_ops = 0; has_ops < 2; has_ops++)
    for (has_valid = 0; has_valid < 2; has_valid++)
    for (has_enter = 0; has_enter < 2; has_enter++)
    for (bits = 0; bits < 8; bits++) {
        struct platform_suspend_ops ops = {
            .valid = has_valid ? callback_valid : NULL,
            .enter = has_enter ? callback_enter : NULL,
        };
        suspend_ops = has_ops ? &ops : NULL;
        valid_mask = bits << PM_SUSPEND_TO_IDLE;
        for (state = PM_SUSPEND_TO_IDLE; state <= PM_SUSPEND_MEM; state++) {
            bool deep_valid = has_ops && has_valid && has_enter &&
                              (valid_mask & (1U << state));
            bool expected = state == PM_SUSPEND_TO_IDLE || deep_valid;
            valid_calls = enter_calls = 0;
            assert(sleep_state_supported(state) == expected);
            assert(valid_calls == (unsigned)(state != PM_SUSPEND_TO_IDLE &&
                                            has_ops && has_valid));
            assert(enter_calls == 0); /* Validation must not enter suspend. */
            checks++;
            if (state != PM_SUSPEND_TO_IDLE) {
                valid_calls = enter_calls = 0;
                assert(valid_state(state) == deep_valid);
                assert(valid_calls == (has_ops && has_valid));
                assert(enter_calls == 0);
                checks++;
            }
        }
    }
    assert(checks == 320);
    puts("PASS: 320 extracted-predicate cases; callback guards; s2idle independence");
    return 0;
}
'''


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    text = (ROOT / 'kernel/power/suspend.c').read_text()
    funcs = '\n'.join(function(text, signature) for signature in (
        'static bool valid_state(', 'static bool sleep_state_supported('))
    variants = {'current': funcs}
    if args.self_test_negatives:
        assert funcs.count('&&\n\t\tsuspend_ops->enter') == 1
        assert funcs.count('PM_SUSPEND_TO_IDLE || valid_state(state)') == 1
        variants['missing-enter-check'] = funcs.replace('&&\n\t\tsuspend_ops->enter', '')
        variants['bypass-valid-callback'] = funcs.replace(
            'PM_SUSPEND_TO_IDLE || valid_state(state)',
            'PM_SUSPEND_TO_IDLE || (suspend_ops && suspend_ops->enter)')
    with tempfile.TemporaryDirectory(prefix='suspend-validation-') as tmp:
        tmp = Path(tmp)
        for name, source in variants.items():
            cfile, exe = tmp / (name + '.c'), tmp / name
            cfile.write_text(MODEL.replace('/* FUNCTIONS */', source))
            subprocess.run([*shlex.split(args.cc), '-std=gnu11', '-O2', '-g',
                            '-UNDEBUG', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            str(cfile), '-o', str(exe)], check=True)
            result = subprocess.run([str(exe)], capture_output=True, text=True,
                                    preexec_fn=no_core)
            if name == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                print(result.stdout.strip(), flush=True)
            else:
                assert result.returncode != 0, 'mutant survived: ' + name
                assert 'Assertion' in result.stderr, result.stderr
                print('PASS: rejected ' + name, flush=True)


if __name__ == '__main__':
    main()

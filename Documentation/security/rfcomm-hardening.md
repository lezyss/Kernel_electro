# RFCOMM listener lifetime and MCC length-check backports

## Sources

- Listener lifetime: upstream `43c441edacf953b39517a44f5e5e10a93618b226`,
  compared with the older-API backport at
  https://github.com/Madara273/Sakura.MTX-OP9-Pro/commit/34a0bd1755fee872f1653f965c5f84d2e8f40709
- MCC validation: upstream
  https://github.com/torvalds/linux/commit/23882b828c3c8c51d0c946446a396b10abb3b16b

## Changes

`rfcomm_get_sock_by_channel()` now returns a referenced socket. Exact and
wildcard matches acquire references under the socket-list read lock; replaced
or superseded wildcard candidates release their temporary references.
`rfcomm_connect_ind()` is its only caller. It rechecks BT_LISTEN after taking
the socket lock, caches the deferred-setup flag under that lock, and releases
the reference after the final parent use, including notification and failure
paths. This closes the lookup-versus-listener-close use-after-free window.

PN, RPN, RLS, MSC and MCC receive handlers now validate and linearize the bytes
they will read before deriving a protocol pointer or dereferencing fields.
This includes fields passed as debug arguments. Short input returns -EILSEQ.
A one-byte RPN request remains valid and never reads the rest of the full RPN
structure, including for debug output.

The modern upstream patch uses `skb_pull_data()`, absent from this tree. The
backport uses existing `pskb_may_pull()` and then obtains a fresh `skb->data`
pointer, since linearization can move the head. Body handlers retain this
tree's non-consuming access pattern; MCC retains its existing two-byte header
pull. No generic skb API, unrelated frame parsing, locking model or Bluetooth
configuration is changed.

## Configuration and validation

Miatoll's current defconfig does not enable CONFIG_BT_RFCOMM; the symbol has no
default enablement or selectors. These changes harden the optional source
without enabling it. They are not a claim of a runtime security improvement in
an image that omits kernel RFCOMM.

Run the local host regression suite with:

```
python3 tools/testing/selftests/bluetooth/test_rfcomm.py
```

The suite extracts the complete modified lookup, connection-indication and
five receive-handler functions, plus protocol structures/constants from this
tree. Kernel socket, network, locking and skb primitives are mocked. It checks:

- Exact/wildcard selection and temporary-reference balance.
- Successful accept, allocation failure, full backlog and a deterministic
  simulated listener close between list unlock and socket locking.
- Parent lifetime through the deferred-setup callback and final put.
- Short and minimum-sized PN/RLS/MSC inputs in command and response modes.
- RPN actual lengths 0 through 8 and declared lengths 0 through 9, including
  valid one-byte queries and full-size requests/responses.
- Truncated MCC headers and MCC dispatch of a one-byte RPN query.

The host suite runs with UBSan. Guard pages catch reads beyond available packet
bytes, and a mocked successful linearization relocates data and protects the
old mapping to catch pointers obtained before the check. Nine deliberately
broken variants must fail (missing listener ref/state check/put, each of the
five missing receive checks, and disallowing short RPN).

These checks are bounded regressions, not a real concurrent socket race test,
full kernel compile, Bluetooth-device test or general RFCOMM security audit.
No CI is dispatched as part of this change.

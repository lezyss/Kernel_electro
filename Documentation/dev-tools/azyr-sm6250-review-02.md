# Azyr sm6250 review 02 — continued items #11–#25

Status: **all items #11–#25 explicitly skipped by the user.**
No kernel patch from this batch applied, committed, pushed or sent to CI.
This continues [items #1–#10](azyr-sm6250-review-01.md). Stable IDs remain
**A01-011 through A01-025**, in the user's submitted order; this is not a new
numbering series and does not change the separate Phoenix ledger. Continuations [#26–#33](azyr-sm6250-review-03.md) and
[#34–#43](azyr-sm6250-review-04.md) are recorded; the next unassigned number is
**#95 / A01-095**; [#54–#63 are recorded here](azyr-sm6250-review-06.md).

Repository: <https://github.com/AzyrRuthless/kernel_xiaomi_sm6250>.
All fifteen exact commit objects were inspected through the GitHub API,
including all changed-file patches. The later donor Boeffla C/header sources
and the #22 wakeup implementation were also inspected for context. These are
original recommendations, retained for history. The later instruction
**“Apply #6, skip other”** explicitly skips all fifteen entries here; it does
not authorize Boeffla activation.

## Shared applicability finding

**Every item in this batch belongs to Boeffla wakelock blocker.** The user
previously excluded that framework. In the reviewed Electro working tree:

- `drivers/base/power/boeffla_wl_blocker.c` and its header do not exist.
- `drivers/base/power/Makefile`, `drivers/base/Kconfig`, `kernel/power/Kconfig`
  and the miatoll defconfig contain no BOEFFLA selection/wiring.
- `drivers/base/power/wakeup.c` has no `check_for_block()`/Boeffla path. Native
  `wakeup_source_report_event()` accounts and activates wake sources normally;
  `__pm_stay_awake()` and `pm_wakeup_ws_event()` retain their native locking and
  activation/deactivation protocol.

Thus none of these patches fixes an existing Boeffla bug in Electro. Bringing
in the absent driver, sysfs controls, default lists and native wakeup hooks
would be a separate behavioral feature addition, contrary to the previous
exclusion unless the user explicitly reverses it. No such addition is made.

The individual assessments distinguish reasonable donor-local cleanups from
risky blocking policies. A sound cleanup inside an excluded driver is not a
reason to introduce that driver.

## #11 / A01-011 — size the default-list buffer from its initializer

Commit: [`f18dda2b7f1553c2cbfb7f9b789469e011de7b17`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/f18dda2b7f1553c2cbfb7f9b789469e011de7b17)

Changes `LENGTH_LIST_WL_DEFAULT` from a fixed 100 to
`strlen(LIST_WL_DEFAULT) + 1`.

**Assessment:** reasonable initializer-size coupling inside Boeffla, not a
performance or battery optimization. With an empty initializer the buffer
shrinks to one byte; its writable sysfs store must still enforce room for the
terminator. The inspected donor store allows `n == capacity` and uses an
unbounded `%s` conversion, so this macro is not a complete input-safety fix.
**Recommendation for Electro: skip, absent/excluded framework.**

## #12 / A01-012 — bound sysfs show output

Commit: [`f4ed7d5ef3443c115b5fb19e30d075fd2534d052`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/f4ed7d5ef3443c115b5fb19e30d075fd2534d052)

Changes four sysfs show callbacks from `sprintf()` to
`scnprintf(buf, PAGE_SIZE, ...)`, including the combined debug output.

**Assessment:** sensible bounded-output hygiene for that driver's sysfs
interface. It does not bound the store callbacks or make arbitrary wake-source
blocking safe. **Recommendation: skip here; no such callbacks exist.**

## #13 / A01-013 — sysfs attribute permissions/helpers

Commit: [`8b2e8c2d5922bf1696a3bd5aed238fac78ac49c7`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/8b2e8c2d5922bf1696a3bd5aed238fac78ac49c7)

Uses `DEVICE_ATTR_RO(version)` and `DEVICE_ATTR_RW()` for the writable list and
debug attributes. In addition to making version read-only, the debug mode
changes from 0664 to the RW helper's 0644; the two list modes remain 0644.

**Assessment:** appropriate donor-local permission/API cleanup, not an Electro
security fix. **Recommendation: skip; these sysfs attributes are absent.**

## #14 / A01-014 — signed return status in debug_store

Commit: [`fbe64730f71630c49db65a52214534c4ad6df121`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/fbe64730f71630c49db65a52214534c4ad6df121)

Changes `unsigned int ret = -EINVAL` to `ssize_t ret = -EINVAL` in
`debug_store()`.

**Assessment:** sensible signed errno/scanf-result handling in that callback.
The initial value is subsequently overwritten by scanf, so this should not be
credited as a demonstrated runtime PM fix. It does not validate every input or
store bound.
**Recommendation: skip here, absent driver.**

## #15 / A01-015 — replace debug-mode scanf parsing

Commit: [`41af37bc1d950a7aac70c35bc28a723c6d86bbed`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/41af37bc1d950a7aac70c35bc28a723c6d86bbed)

Despite the subject saying `debug_show()`, this adds a `simple_strtoul()`
wrapper for **debug_store()**. It checks trailing non-space text and restricts
the converted value to 0 or 1, improving on the earlier scanf path.

**Assessment:** not ideal as submitted. There is no check that a digit was
consumed, so empty/whitespace-only input is accepted as zero. `simple_strtoul()`
is obsolete in the current kernel sources and does not report conversion
overflow to this wrapper. For a new implementation, use a checked kernel
conversion API and a defined boolean input grammar instead of copying this
parser. **Recommendation: skip as-is; also inapplicable without Boeffla.**

## #16 / A01-016 — remove redundant length narrowing

Commit: [`c97336d534f5cf660c634c97e6adafa50bf1460c`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/c97336d534f5cf660c634c97e6adafa50bf1460c)

Removes `int len = n` from both sysfs list stores and compares the original
`size_t n` directly with each capacity.

**Assessment:** a sensible type cleanup, but not complete buffer hardening.
The guard still permits equality, and `sscanf(buf, "%s", destination)` has no
field width. A capacity-byte non-whitespace token plus its NUL needs
capacity+1 bytes. Increasing capacity in #18 does not fix this boundary.
**Recommendation: skip here, absent driver; do not credit it as a complete
memory-safety fix.**

## #17 / A01-017 — const inputs and literal initialization copy

Commit: [`03598647605ceb5ce974e4519c9ebc55f0b6392e`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/03598647605ceb5ce974e4519c9ebc55f0b6392e)

Marks the search-string builder inputs const and replaces the initialization
`sprintf(default_list, "%s", LIST_WL_DEFAULT)` with `strcpy()`.

**Assessment:** minor donor-local cleanup. A destination sized from the same
literal plus NUL fits this particular initialization; this does not make
`strcpy()` generally safer or repair runtime list parsing. No meaningful
runtime performance gain is established. **Recommendation: skip here.**

## #18 / A01-018 — enlarge the user blocklist

Commit: [`a8e139be19d7650486079d3c77e1e4bed9194c1c`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/a8e139be19d7650486079d3c77e1e4bed9194c1c)

Increases `LENGTH_LIST_WL` from 255 to 1024. The message motivates it using
Samsung wake-source lists; that is not evidence of safe defaults for miatoll.

**Assessment:** a capacity expansion, not a wakeup bug fix. It permits larger
policies and enlarges dependent storage without fixing the store boundary in
#16. **Recommendation: skip, no justified blocker/capacity requirement here.**

## #19 / A01-019 — populate the default blacklist

Commit: [`17b84e5413e14387ac4437adf134ceec17de17bd`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/17b84e5413e14387ac4437adf134ceec17de17bd)

Replaces the empty default list with `qcom_rx_wakelock`, `wlan`,
`wlan_wow_wl`, `wlan_extscan_wl`, `netmgr_wl` and `NETLINK`.

**Assessment:** an active default policy change, not a general battery fix.
Those wake sources can protect real Wi-Fi/network work; suppressing their
hold does not remove that work or prove energy savings. Notifications,
connectivity and suspend-time processing require device-specific validation.
**Recommendation: reject for this kernel's defaults; preserve native handling.**

## #20 / A01-020 — expand the default blacklist substantially

Commit: [`2b914ef8d8d676376618c73636c4fafa208b6614`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/2b914ef8d8d676376618c73636c4fafa208b6614)

Adds modem/IPA, diagnostic, input, timer, USB, UART/Bluetooth and SPI names,
including `[timerfd]`, `alarmtimer`, `event5`, `input5` and
`hal_bluetooth_lock`.

**Assessment:** broad and risky default suppression across unrelated device
subsystems. It may permit suspend while legitimate work still needs the CPU.
The later removals in #23–#25 are a warning against copying this list as a
battery optimization. `rmnet_ipa%d` in these strings is literal text, not a
wildcard or printf expansion performed by `strstr()`.
**Recommendation: reject; do not import blanket device-specific defaults.**

## #21 / A01-021 — expand/reformat the default blacklist again

Commit: [`26f3e888130789b02567ff2f3f5d092df2ed4f08`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/26f3e888130789b02567ff2f3f5d092df2ed4f08)

Adds more WLAN authentication/roaming/PNO and IPA names, event/input sources,
`elliptic_wake_source`, `bq2597x-standalone` and `CHG_PLCY_MAIN_WL`.
It also removes `0-0028` while reorganizing the literal; it is not purely an
addition or formatting-only change.

**Assessment:** expands the same unsupported suppression policy to additional
network, sensor/input and charging-related work. Names alone do not establish
that a wake source is unnecessary. **Recommendation: reject for production.**

## #22 / A01-022 — change blocklist matching semantics

Commit: [`a84dcd4eb63d58b162f13f689d30cbf165968eaf`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/a84dcd4eb63d58b162f13f689d30cbf165968eaf)

Changes the query from `;wake_source_name;` to bare `wake_source_name` before
`strstr(list_wl_search, query)`. The accompanying `== NULL` to `!pointer`
change is equivalent; the meaningful policy change is dropping delimiters.

**Assessment: reject the substring matching.** With a list containing only
`;sensor_long;`, a source named `sensor` becomes blocked despite not being a
listed entry. Exact matching already handles first/last entries when the
search string is correctly built with its surrounding separators. If list
normalization is broken, fix that instead of masking it with partial matching.

There is a separate real boundary issue in the inspected donor context:
`wakelock_name[52]` accepts names up to 50 bytes. Formatting semicolon + name +
semicolon + NUL requires **53 bytes** at that limit. The new unwrapped query
fits, but a proper correction would bound the formatting/size correctly while
retaining exact-name semantics. The patch does not introduce the existing
active-source deactivation code or a general wake-event balancing repair.
Electro has none of this blocker hook and needs neither version imported.

## #23 / A01-023 — remove specific input/event entries

Commit: [`2b395efb4441720d5a612394a6ac2b9a37d0f47c`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/2b395efb4441720d5a612394a6ac2b9a37d0f47c)

Removes `input5`, `event1`, `event2`, `eventpoll` and `event5`. The author cites
delayed screen turn-on when input wake sources are blocked.

**Assessment:** sensible regression mitigation for a donor that adopted those
bad defaults; not a reason to adopt the framework. The patch does not remove
all remaining risky defaults. **Recommendation: no patch needed in Electro;
these sources are already not blacklisted by Boeffla here.** This is equivalent
policy outcome, not a claim that the commit is already cherry-picked.

## #24 / A01-024 — remove SPI entries

Commit: [`a9a7948a53473b0919d6909bb684cd8630b283ab`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/a9a7948a53473b0919d6909bb684cd8630b283ab)

Removes `spi0.0` and `spi1.0` from the default list.

**Assessment:** another rollback of unnecessary blocking, not a generic SPI
controller fix. **Recommendation: no patch needed; no Boeffla list exists in
Electro and native SPI wake-source behavior is retained.**

## #25 / A01-025 — remove timer entries

Commit: [`958b3ed0b601c8c8ed18c18d832f5d91f28ae42b`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/958b3ed0b601c8c8ed18c18d832f5d91f28ae42b)

Removes `[timerfd]` and `alarmtimer`. The author cites delays for processes
needing short timers.

**Assessment:** a useful rollback in a tree that previously suppressed those
wake sources; it does not fix the timer subsystem or justify the remaining
blacklist. **Recommendation: no patch needed; Electro does not suppress those
sources through Boeffla.** Preserve timer/alarm wake-processing protections.

## Decision summary and validation limits

- **Recommend leaving all fifteen out** under the existing no-Boeffla decision.
- #11–#14, #16 and #17 contain donor-local sizing/output/type/permission or
  cleanup ideas, not missing fixes for Electro's native PM path.
- #15 needs better parsing even in a blocker-enabled tree; #18 is capacity only.
- #19–#21 introduce/expand unvalidated suppression defaults; #22 trades exact
  matching for potentially broader unintended blocking.
- #23–#25 are donor-policy rollbacks whose desired non-blocking outcome is
  already retained here without introducing the blocker.
- Static checks confirmed absent files/wiring, the substring counterexample,
  the 53-byte formatted-name requirement, and the equal-capacity store issue.
  These checks are not execution of a donor driver, an AArch64 build, suspend
  stress testing or measured battery results. No target build was attempted
  for an absent/excluded framework.
- Only review documentation is changed. No source/configuration edits, new
  blacklist, blocker activation, commit, push or CI dispatch are authorized
  or performed by this review. **Next review number: #95; see [review 09](azyr-sm6250-review-09.md).**

Latest continuation: [#64–#73](azyr-sm6250-review-07.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#74–#83](azyr-sm6250-review-08.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#84–#94](azyr-sm6250-review-09.md). Next unused number: **#95 / A01-095**.

Final submitted batch [review10, #95–#109](azyr-sm6250-review-10.md) is complete.
Next unassigned: **#110 / A01-110**. Historical recommendations are not approvals.

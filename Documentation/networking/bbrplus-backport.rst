BBRplus backport
================

Source and integration
----------------------
This ports manipvlator/los_kernel_xiaomi_sm6150 commit
40213eb493f20807f05e830d5777ed58d3d47f39, which references UJX6N/bbrplus-5.4.
It adds a separate ``bbrplus`` congestion-control implementation; the existing
BBR, CUBIC and Westwood implementations are retained.  This is not BBRv2 or
BBRv3, and the port makes no throughput, latency or fairness improvement claim.

The donor's drain-to-target probing and ACK-aggregation compensation are
retained.  Necessary integration corrections are:

* Wire the new tso_segs_goal() callback into tcp_tso_segs().  A missing
  callback or a zero return retains the old autosizing/min_tso_segs behavior;
  all results still respect sk_gso_max_segs.  The donor added the callback
  field and initializer without actually dispatching it in TCP output.
* Export tcp_tso_autosize() with EXPORT_SYMBOL_GPL so BBRplus can also be
  built as a GPL-compatible module, not just built in.
* Make BBRplus's bbr_max_bw()/bbr_inflight() helpers private and remove the
  duplicate forward declaration.  Drop trailing whitespace and stray
  separator comments, and identify BBRplus in the module description.
* Retain the existing global CUBIC build/default choices and fallback string
  instead of taking the donor's unrelated system-wide default changes.
  The miatoll defconfig now explicitly selects BBRplus, as requested below.

The congestion-control private storage grows from 88 to 112 bytes, as in the
donor.  This increases the inline private buffer in every inet connection
socket by 24 bytes, even for other algorithms; final structure/slab sizes also
depend on alignment.  Header/layout changes require a consistent kernel and
module rebuild.  BUILD_BUG_ON checks that BBRplus fits the private buffer.

Configuration and trying it
---------------------------
The miatoll defconfig contains::

    CONFIG_TCP_CONG_ADVANCED=y
    CONFIG_TCP_CONG_BBRPLUS=y
    CONFIG_DEFAULT_BBRPLUS=y
    CONFIG_DEFAULT_TCP_CONG="bbrplus"

This builds BBRplus in and selects it as the build-time default for new TCP
connections. CUBIC and BBR remain available as alternatives. The global
Kconfig default/fallback remains CUBIC for configurations that do not select
BBRplus explicitly. Existing qdisc selections are unchanged, including::

    CONFIG_DEFAULT_FQ_CODEL=y

The fq qdisc can provide pacing if enabled/configured separately; fq_codel is
not fq.  As with this tree's BBR, TCP also supports internal per-socket pacing.

After building and booting the updated kernel, a root shell can check and
select BBRplus for new TCP connections in its network namespace::

    cat /proc/sys/net/ipv4/tcp_available_congestion_control
    sysctl -w net.ipv4.tcp_congestion_control=bbrplus
    cat /proc/sys/net/ipv4/tcp_congestion_control

Restore with ``sysctl -w net.ipv4.tcp_congestion_control=cubic``.  Existing
connections and applications that select their own algorithm may differ;
Android boot scripts can also override defaults.  TCP congestion control does
not change UDP/QUIC congestion control, and local TCP selection primarily
controls locally transmitted data, not a remote sender's download algorithm.

Validation (2026-11-01)
-----------------------
Local checks used Clang 19.1.7/LLD from Zig 0.14.1, NOT production AOSP r614150.
All outputs and temporary configuration changes stayed outside the repository.
Signature/trusted-key dependencies and Polly were disabled only in validation
output configs to match available build dependencies.

* The miatoll-derived ThinLTO/SCS configuration built BBRplus, BBR, CUBIC,
  Westwood, TCP output/input/core/congestion control, inet_connection_sock and
  IPv6 TCP objects (ten selected objects).  MGLRU remained enabled at boot.
* Built-in BBRplus, BBR and TCP output passed a combined relocatable LTO link.
  Both implementations coexist with private helper symbols.  The resulting
  ELF contains tcp_tso_autosize and its GPL export table entry.
* BBRplus=m and TCP output compiled and passed a combined relocatable LTO
  link.  tcp_tso_autosize is resolved in that link.  This is not a complete
  kernel/module modpost or a module-loading test.
* BBRplus-disabled TCP output/BBR/CUBIC objects built successfully.
* Kconfig checks passed for built-in/module/disabled support, optional
  DEFAULT_BBRPLUS selecting "bbrplus", and TCP_CONG_ADVANCED=n falling back
  to "cubic".  The initial port's output config used default CUBIC and
  fq_codel; the subsequent requested default change is validated below.
* Extracted-source host models passed 1,080 TSO callback/fallback/GSO-cap
  cases plus probe/drain/receiver-window and ACK-aggregation cases.  Modeled
  BBRplus private state is 112 bytes.  Removing callback dispatch deliberately
  failed a C assertion.  See tools/testing/selftests/bbrplus/README.
* Existing procfs tests (58,806 formatting cases plus PSS/rollup checks) and
  MGLRU tests (2,006 shadow cleanup cases plus source guards) passed again.
* Scoped whitespace checks passed.

These are selected-object, partial-link and single-threaded model checks.
They do not establish full-image linking, production-toolchain compatibility,
bootability, module loading, real TCP state-machine correctness, congestion
fairness or cellular/Wi-Fi performance.  Actual network testing should compare
BBRplus with CUBIC/BBR under controlled RTT/loss/queue conditions after boot.
No push or CI run was performed for this port.

Default and TCP memory follow-up (2026-11-01)
--------------------------------------------
After the initial port, BBRplus was explicitly selected as miatoll's default.
Commit 075c7a0e036611756212490bbbf32567509aae87 from the same donor repository
was then applied unchanged to net/ipv4/tcp.c. It raises the cap used to
initialize the TCP send/receive maximum buffer limits from 4/6 MiB to 16/16
MiB. The RAM-dependent limit and existing minimum floors remain intact.
Initial buffer values (16 KiB send and 87380 bytes receive), tcp_mem pressure
thresholds and the qdisc default are unchanged. These are buffer ceilings,
not a reservation of 16 MiB per socket. Larger ceilings can allow increased
memory use under load; they do not guarantee higher throughput. Userspace
sysctl configuration may override these boot-time values.

The local miatoll-derived output config resolves DEFAULT_BBRPLUS=y and
DEFAULT_TCP_CONG="bbrplus", with DEFAULT_CUBIC unset, CUBIC/BBR still built,
fq_codel unchanged and MGLRU enabled. The ten selected TCP/IPv6 objects above
passed again with ThinLTO/SCS, followed by a relocatable LTO link of TCP core,
congestion control, BBRplus and TCP output. The host selftest now also extracts
the production TCP memory-limit assignments and checks seven modeled 4-KiB
page-count cases, including low-memory floors and the 16-MiB ceilings. Restoring
the old 4/6-MiB caps deliberately fails a C assertion. The existing BBRplus,
procfs and MGLRU host checks were rerun successfully. This follow-up still has
no full image/production-compiler build, boot, performance test, push or CI.

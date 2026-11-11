Native BBRv3 EDT pacing/forecast adaptation
=========================================

Status: user authorized publication of the EDT work and switching miatoll's
default from BBRplus to BBRv3. CONFIG_DEFAULT_BBR3=y now resolves to "bbr3".
BBRplus/BBR/CUBIC remain available; generic CUBIC fallback and16MiB TCP caps
are unchanged. A subsequent user-authorized followup builds in fq and selects
it as miatoll's default qdisc; fq_codel stays built in as an alternative. No CI dispatched. No production AOSP r614150 ARM64
compilation, linked image or device test. Commit/remote identity is verified
externally after creating the commit containing this record.

Design/provenance
-----------------

This is a scoped native4.14 adaptation, not a wholesale modern TCP replacement:

* Linux ab408b6dc7449c0f791e9e5f8de72fa7428584f2 (TCP/fq EDT model), and
  08e14fe429a07475ee9f29a283945d602e4a6d92 (preserve fq maxrate for EDT).
* Google's BBRv3 at90210de4b779d40496dee0b89081780eeddf2a60,
  bbr_packets_in_net_at_edt(), provides the forecast calculation.
* Native timestamp/rate/retransmit interfaces and watchdog clock were inspected
  directly. No full donor patch or different device's defaults were applied.

The receipt bbr3-edt-validation.json contains endpoints and scoped overlay patch
hash. bbr3-edt.diff is relative to the previously integrated working sources, not
bare branch base. Historical bbr3-validation.json and BPF receipts are immutable;
test_provenance.py peels off this overlay on temporary copies and verifies the
old chain, then reapplies the overlay and verifies its endpoints. The older BBR
receipt predates the already-approved SUSFS/KSU defconfig followups. Its exact
historical config (e734f530...) is retained in the new receipt and used only on
temporary copies while replaying that old seal. Current62a05a02... config is
separately protected and is never replaced in the working tree. This known
pre-existing config-endpoint difference is not silently resealed as EDT work.

Timestamp and pacing contract
-----------------------------

4.14 aliases skb_mstamp (microseconds, TCP RTT/rate accounting) and skb->tstamp
(receive/software timestamp). Writing nanosecond departure times into that union
would corrupt the legacy contract. This adaptation adds separate tcp_edt_ns,
zero for unconstrained packets, using CLOCK_MONOTONIC nanoseconds. It costs8bytes
of metadata per skb before any allocator/cacheline rounding. tcp_sock gains an
8byte monotonic cache, and fq_flow gains an8byte effective wakeup deadline.
Native layout-dependent code/modules must be rebuilt; no stable binary ABI claim.

Only BBRv3 opts into TCP_CONG_EDT. That native-only flag is deliberately excluded
from TCP_CONG_MASK accepted by the older BPF struct_ops ABI. BBR/BBRplus/CUBIC do
not opt in, and do not get EDT socket-rate scheduling. All TCP sockets do refresh
an additional monotonic cache; there is a small extra clock-read/metadata cost.

TCP schedules each paced data skb from max(next_departure, cached_now). It stamps
the initial packet while pacing is NEEDED, before fq first advertises FQ support,
so the first packet does not receive an extra legacy fq socket-rate charge.
Only successful queue_xmit advances the schedule; no timestamp is written into
the consumed skb afterward. Finite nonzero pacing rates serialize the actual
TCP buffer including its TCP header; one skb's delay is capped at1second, matching
native fq's defensive cap. No unlimited/zero-rate division. ACK/control traffic
does not erase outstanding reservations. Pure ACK/SYN/RST packets retain the native non-EDT treatment. FIN follows
the data departure frontier, preserving sequence order; no new TFO policy.

Other qdiscs retain tcp_internal_pacing and tcp_pacing_check unchanged. Native
hrtimer pacing gates sends there; BBR's forecast stays conservative until
SK_PACING_FQ advertises an EDT-consuming fq. This does not solve the old4.14
sticky SK_PACING_FQ behavior when qdiscs are replaced or pacing is disabled on a
live connection. Validate with new connections after qdisc changes; dynamic
qdisc replacement/nopacing transitions are NOT certified by this implementation.
SO_TXTIME, UDP EDT, NIC timing-wheel offload and arbitrary user deadlines are
not introduced. No sysctl, socket option or automatic tc command is added.

Packet lifetime and fq
----------------------

* Header copy/clone/GSO copy propagates EDT; IPv4/IPv6 fragmentation metadata
  copies it too. Allocation's existing zero initialization covers the new field.
* Only the outgoing TCP clone/copy is stamped, not the retransmit queue original.
  Refragmented/retransmitted originals get a fresh deadline at the next send.
* The receive core clears local TX deadlines, avoiding real-time receive stamps
  or loopback forwarding becoming accidental future transmit deadlines.
* skb_scrub_packet clears EDT across namespace boundaries. Same-namespace tunnel
  copies retain it. Specialized offloads/tunnel paths need device validation;
  no universal driver/pacing-offload compatibility claim.
* fq uses the same monotonic clock as its existing watchdog. Effective deadline
  is max(head EDT, native fq rate deadline); separate rate/delayed fields prevent
  stale old-head EDT from blocking an earlier newly arriving packet.
* Normal monotonic TCP deadlines append O(1); exceptional earlier arrivals use
  stable linear insertion within the flow packet limit. Untagged data retains
  FIFO order across CC changes; only immediate pure ACKs may pass future data. This is NOT the full
  upstream per-flow packet RB tree or a UDP out-of-order EDT API. Existing flow
  limit is unchanged; extreme custom limits can increase insertion cost.
* An earlier enqueue reactivates a throttled flow. Immediate ACKs cannot remain
  behind future EDT data. Allocation-failure/internal-queue packets also honor
  deadlines, with a watchdog when no ordinary flow is runnable.
* EDT packets do not get socket-rate charged twice. An explicit fq maxrate still
  applies independently. Legacy non-EDT socket pacing and rate_enable0 operation
  retain their policies; the miatoll qdisc default is now fq (see followup below).

BBRv3 forecast
--------------

With advertised fq support, estimate delivery during the interval between actual
monotonic now and the next departure; subtract it from observed flight, including
the prospective TSO burst when increasing flight. Clamp at0 rather than unsigned
underflow, bound interval multiplication and saturate large estimates. Past
frontiers produce zero forecast interval. Without fq, keep conservative observed
flight plus prospective burst, not invented delivery timestamps.

Importantly, RTT/rate skb timestamps remain the actual native TCP handoff samples.
This does NOT claim the modern EDT conversion's full removal of local pacing
latency from RTT samples. It deliberately avoids mixing clocks or future values
into native RTT/RTO/TLP arithmetic. Those timing samples still include local
queueing as before, and very low rates/large queues still require timer testing.
ECN_LOW/precise ECN, PLB, fast ACKs and native BBRv3 BPF kfuncs remain excluded.

Validation and limits
---------------------

Run from root::

  python3 tools/testing/selftests/bbr3/test_edt.py --self-test-negatives
  python3 tools/testing/selftests/bbr3/test_backport.py --cc gcc --self-test-negatives
  python3 tools/testing/selftests/bbr3/test_backport.py --cc 'gcc -fsanitize=undefined -fno-sanitize-recover=all'
  python3 tools/testing/selftests/bbr3/test_provenance.py

The EDT runner compiles actual TCP helpers and complete fq enqueue-support/
dequeue/throttle bodies with the repository's userspace RB implementation and
mock socket/device/watchdog primitives. Checks6,400 sorted packets, control and
failed-send scheduling, clock domains, earlier-head rearming, allocation-failure
queue, legacy/nopacing and independent maxrate. Eight compiled semantic mutants
must fail runtime assertions. Clone/fragment/RX/cross-namespace wiring checks
are source assertions, not actual IP fragmentation or driver execution.

Extended BBRv3 tests cover120 forecast rate/gain/fallback/horizon combinations
plus a past deadline, in addition to previous wrap/segmentation/TSO/loss/CC-switch/
TLP/BPF tests. Fifteen compiled negative controls are rejected. Host GCC/UBSan
models are not production compiler or real TCP concurrency/network execution.
An attempted x86 API-object Kbuild was blocked before network compilation by
existing ARM-only mtune flags and missing bc (earlier ORC setup also lacked
libelf); it is NOT a successful kernel-object build. No production config/source
was changed to accommodate this host attempt.

Before release: build with the pinned AOSP compiler, then controlled TCP tests
using fresh bbr3 connections with fq and non-fq qdiscs, both IP families, TSO/GSO,
loss/retransmissions, app-limited traffic, explicit maxrate, low pacing rates,
Wi-Fi/mobile/tethering/tunnels and repeated suspend/resume. Compare BBRplus and
record queue timing, throughput, RTT/latency, CPU/memory and faults. Root/device
execution, power/fairness improvement and universal stability are not proven.

Default-selection followup and publication scope
------------------------------------------------

User request: "Change from bbrplus to bbr3 as default and push to branch".
The built-in-only DEFAULT_BBR3 choice and its string mapping are added without
changing the generic DEFAULT_CUBIC choice default. Only miatoll selects it;
no other defconfig or runtime sysctl/boot script is modified. The later qdisc
followup below supersedes the original decision to retain fq_codel. BBRplus tests
now check availability with BBRv3 default, rather than requiring BBRplus default.
Both source selection and resolved config are verified with shipped Kconfig tools.

The original default-only publication retained fq_codel and did not build fq;
that profile could not consume EDT through fq. The user subsequently authorized
making EDT usable: CONFIG_NET_SCH_FQ=y and CONFIG_DEFAULT_FQ=y now resolve to
CONFIG_DEFAULT_NET_SCH="fq". CONFIG_NET_SCH_FQ_CODEL=y remains available for A/B
and rollback, but DEFAULT_FQ_CODEL is no longer selected. No TCP/FQ algorithm
source changes are needed for this activation followup. Internal pacing still
provides fallback when the actual egress qdisc is not fq.

Publication is scoped to the EDT source/metadata/FQ/forecast adaptation, this
explicit default-selection followup, and their tests/docs/evidence. Build on
published61be86e3b (the13 Azyr selection). Do not include other local approved
#6/memlat/#36/#41 or unrelated dirty work. No force push or automatic CI.

Device verification and controlled EDT A/B
-----------------------------------------

These config changes apply only after building/installing the new image; no
phone has been modified remotely. A production ARM64 compile/link/boot remains
required. Android/netd, init scripts, VPNs and vendor networking may install a
different qdisc. Neither the compiled default nor the sysctl proves the active
interface uses fq. Interfaces marked noqueue/offloaded paths need special care.

With suitable iproute2 tools and privileges, record::

  cat /proc/version
  cat /proc/sys/net/ipv4/tcp_congestion_control
  cat /proc/sys/net/core/default_qdisc
  ip route get <server-IP>
  tc -s qdisc show dev <egress-interface>

Expected kernel defaults are bbr3 and fq. Check the route/interface used by the
actual upload (including a VPN path); the relevant transmitting qdisc must be
fq, not fq_codel. For multiqueue devices, inspect the leaf qdiscs too. The fq
enqueue path advertises SK_PACING_FQ and BBRv3's native TCP_CONG_EDT flag then
enables the EDT-based forecast; generic fq statistics alone do not measure
per-packet deadline accuracy or prove hardware transmission timing.

Do not blindly replace Android multiqueue, shaped or vendor-managed qdisc trees.
Save the complete layout first and use a device-specific reversible procedure
if policy overrides fq. Changing default_qdisc alone does not replace qdiscs
already attached. A clean boot/interface recreation may attach the default,
but runtime policy still wins. No automatic init/boot override is added here.

To isolate the effect of this EDT path, keep BBRv3 constant and compare fq_codel
with fq on the same validated image, using fresh connections after each change.
This compares the whole qdisc+pacing path, not EDT in isolation: fq_codel also
has CoDel AQM and fq does not. Use a controlled TCP upload (for example iperf3
-C bbr3, not -R), alternate order for at least five trials, and record the
active qdisc each time. Compare upload throughput, retransmissions and latency
under upload load; watch CPU/battery cost and stability. Keep TCP caps, pacing
rate tunables, ECN, radio conditions/server and other settings constant.

Also compare BBRplus and BBRv3 on the same qdisc separately if desired. A better
BBRv3 result on fq_codel does not establish an EDT benefit. RTT/loss conditions,
radio/driver queues, VPNs and offloads may dominate. EDT may improve pacing
precision or loaded latency, but no speed/latency improvement is guaranteed.
This governs locally generated TCP sending, not QUIC/UDP or the remote server's
TCP sending in a download. No device performance result is claimed by the
host harness or the config/provenance checks.

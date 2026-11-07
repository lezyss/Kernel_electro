BBRv3 comparison port for Electro 4.14
=====================================

Source and scope
----------------

``net/ipv4/tcp_bbr3.c`` is adapted from Google's BBRv3 implementation at
``90210de4b779d40496dee0b89081780eeddf2a60`` (the Google ``v3`` branch,
Linux 6.13.7). It is not BBRv1/BBRplus renamed to version 3. It retains
Google's loss/in-flight bounds, bandwidth model, STARTUP/DRAIN/PROBE_RTT,
and PROBE_BW UP/DOWN/CRUISE/REFILL state machine.

Pinned source:
https://github.com/google/bbr/blob/90210de4b779d40496dee0b89081780eeddf2a60/net/ipv4/tcp_bbr.c

This is a **loss-based Internet-mode port**, not the entire 6.13 TCP stack.
The native 4.14 API and pacing facilities require explicit adaptations:

* ECN_LOW is unavailable: there is no per-route shallow-threshold ECN
  contract or precise ECE ACK facility. ``bbr_can_use_ecn()`` therefore
  explicitly denies this capability. Standard TCP ECN negotiation and
  genuine cumulative CE accounting remain; classic Internet ECE is NOT
  interpreted as datacenter ECN feedback. The source's ECN sender model
  remains gated off, rather than being fed fabricated zero CE samples.
* PLB, permanent ECT retransmission policy and fast ACK mode are not
  imported or advertised. Receiver ACK scheduling remains native 4.14.
* There are no EDT timestamps in this stack. ``bbr_packets_in_net()`` uses
  the observed flight as a conservative upper bound (including local
  queues), including a prospective TSO burst during increasing pacing
  gain. It does NOT invent timestamps or forecast deliveries to an EDT.
  Existing fq/internal hrtimer pacing is retained. This is not equivalent
  to Google's EDT-aware optimization on a modern stack.
* The congestion-control callback retains this tree's two-argument ABI;
  Google's unused ACK/flag arguments are omitted. cwnd accessors, GSO
  constant, global min-TSO sysctl and probe randomization use native 4.14
  APIs (``prandom_u32_max`` is for probe mixing, not security). The existing
  global ``sysctl_tcp_min_tso_segs`` gets a GPL export so modular BBRv3 can
  use it; its default and behavior do not change. There are no other
  ``tcp.c`` changes, verified by removing exactly that export line and
  comparing the complete file to its pre-port hash.
* BBRv3 kfunc/BTF registration is not imported. New native ``tso_segs``
  and ``skb_marked_lost`` callbacks are explicitly unsupported as BPF
  program attachment points in the existing 5.15-era BPF port. NULL
  callbacks remain accepted; the older ``tso_segs_goal`` is optional.
  No unrelated BPF UAPI/helper IDs or verifier permissions are changed.

Selection and compatibility
---------------------------

``CONFIG_TCP_CONG_BBR3`` builds the separate algorithm named ``bbr3``.
The miatoll defconfig enables it, but the default stays **bbrplus**.
BBR and CUBIC remain built in. TCP buffer caps stay at 16 MiB. There is no
``DEFAULT_BBR3`` choice or automatic migration of existing connections.

With BBRv3 built in or modular, congestion-control private storage grows
from 112 to 144 bytes: 32 additional bytes per inet connection socket.
Without BBRv3 it stays 112 bytes. The BBRv3 module has a compile-time size
check. There is no new per-ACK allocation or allocation-failure fallback.
Existing BBR/BBRplus algorithm sources are unchanged.

The 48-byte TCP skb control block and 24-byte outgoing metadata budget are
preserved. Two skb timestamp snapshots become 32-bit microseconds, with
signed modular elapsed-time arithmetic, following Google's prerequisite.
Intervals must be below 2^31 microseconds (about 35.8 minutes); the zero
snapshot sentinel and invalid rate samples are respected. Full connection
timestamps remain 64-bit, including BBRplus's cycle/ACK-aggregation clocks.

This tree's old ``tx.in_flight`` is **bytes**, not packets. Its spare bit
now tags packet-valued snapshots requested by ``TCP_CONG_RATE_IN_FLIGHT``.
Only BBRv3 requests that format. Legacy algorithms continue recording the
same byte count. Successful non-cloning retransmits also refresh that byte
count before clearing a previous packet-format tag. On a live CC switch, BBRv3 must not update its packet-flight
model or per-skb loss bound from legacy-tagged packets; it can still
release/grow cwnd as they are acknowledged. TCP-NV skips packet-valued old
samples until fresh byte-valued transmissions arrive, using its existing
zero/absent-sample convention, rather than treating packets as bytes.

Cumulative ``tp->lost`` and ``tp->delivered_ce`` already exist and are
really updated by TCP. The new skb snapshots and interval deltas use those
full-width counters, including unsigned wraparound. ``rate_sample.lost``
is the loss over the sampled interval, distinct from ``losses`` (fresh loss
on this ACK). Loss notification occurs only after a newly counted loss.
Split and SACK-merge adjustments are conditional on each snapshot's units;
legacy bytes are not adjusted as if they were packets. TCP_REPAIR-restored
unsampled data is explicitly invalidated rather than using uninitialized
metadata. App-limited checks at ACK and write-timer entry are added only
for controllers requesting the packet-snapshot API, preserving legacy
controllers' existing app-limited detection paths.

TLP captures the original data's app-limited status before retransmission,
notifies CC only when advancing ACKs prove a repaired loss, and marks exact
ambiguous TLP sequence ACKs. DSACK/new-data/pure-dupack cases are not claimed
as repaired loss. The native TLP recovery actions are retained.

Diagnostics preserve the old 20-byte ``tcp_bbr_info`` and its return sizes.
The separate 52-byte ``tcp_bbr3_info`` shares that prefix, adds Google's
bounds/phase/version fields, and is fully zero-initialized before export.
It uses the existing BBR diagnostic attribute; older readers can consume
the common prefix. Enlarging the original struct instead would make old
BBR implementations export an uninitialized tail and is deliberately
avoided. Kernel/modules must be rebuilt together after internal TCP layout
changes; there is no stable out-of-tree kernel module ABI promise.

TCP-core prerequisite provenance
-------------------------------

The selectively adapted Google changes include the following commit
prefixes (in https://github.com/google/bbr):

* ``a627517bdfe0``: compact timestamp snapshots, modular elapsed time.
* ``0e6b4413cb4a``: transmit packet-flight snapshot and rate sample.
* ``3679f3b8da5a``: loss over the rate-sampling interval.
* ``500bcfec22c4``: ECE in the rate sample.
* ``f2078939d4a8``: per-skb loss notification.
* ``88e09e2b7c84`` / ``5093de531d14``: SACK merge / fragment accounting.
* ``a631934cbcd8``: original TLP app-limited status.
* ``3ee83ca004fa`` / ``703f20a1052d``: repaired-loss event / ambiguous TLP ACK.
* ``137a508c9508``: ACK/timer application-limited detection.

The additive ``bbr3-backport.diff`` and ``bbr3-validation.json`` record both
source endpoints without resealing the older BPF report. For the three overlapping
BPF-sealed files (``include/net/tcp.h``, ``net/ipv4/bpf_tcp_ca.c`` and
``net/ipv4/tcp.c``), the BBRv3
before hash must equal the historical BPF after hash. The current source must
then match the BBRv3 after hash. Run
``python3 tools/testing/selftests/bbr3/test_provenance.py`` to check that chain
and reverse/forward patch replay; the old BPF hashes alone describe the earlier
state, not these subsequent TCP changes.

The delayed-ACK heuristic is selectively adapted from the pinned
``tcp_clean_rtx_queue()``: a single fully ACKed runt, no prior SACKs, a
matching delivery count, and no congestion-alert/SYN event. It is reported
to BBRv3 without changing other algorithms' RTT-min filter policy.

Validation boundaries
---------------------

Run the extracted-source models::

  python3 tools/testing/selftests/bbrplus/test_backport.py
  python3 tools/testing/selftests/bbr3/test_backport.py --self-test-negatives
  python3 tools/testing/selftests/bbr3/test_backport.py \
      --cc /path/to/pinned/aosp/clang --sanitize --self-test-negatives

The BBRv3 fixture compiles the actual algorithm and delivery-rate functions,
the actual outgoing metadata/diagnostic definitions, loss function,
split/merge accounting blocks, TLP classification function, and BPF member
policy. Its mock socket/queue/clock/BTF environment is not a running kernel.
It checks 10,000 timestamp cases, 74,100 split/merge cases, 1,188 MSS-aware TSO dispatch cases, real-counter
snapshots/deltas and wrap, mixed-format CC switches, invalid/reneged samples,
loss callback ordering/deduplication, loss-bound reactions, all four PROBE_BW
phases, STARTUP/DRAIN/PROBE_RTT transitions, TLP classification, diagnostic
sizes, and optional/unsupported BPF members. Thirteen intentional mutations
must fail a runtime assertion, not fail compilation. Sanitizer/model success
is not production-target or device proof by itself.

Production target validation must use the exact AOSP r614150 snapshot
``3b86e40facfff1eab4065614255d573293c10373``, full LLVM/no GCC. Target object
compilation, complete image/module/DTB linking, and device boot/network tests
are separate gates. Consult ``bbr3-validation.json`` for the recorded state;
do not infer device/performance results from successful builds.

Phone A/B procedure (after a validated image is installed)
--------------------------------------------------------

Record ``/proc/version`` and the actual built image/config provenance.
SUSFS may intentionally spoof ``uname``; that alone is not a wrong-image
failure. Confirm availability and that the default has not changed::

  cat /proc/sys/net/ipv4/tcp_available_congestion_control
  cat /proc/sys/net/ipv4/tcp_congestion_control

Prefer per-socket selection on a controlled iperf3 server. In Termux, use
normal TCP **uploads** from the phone (not ``-R``, UDP, QUIC or an unrelated
public speed-test service)::

  iperf3 -c <your-server> -t 30 -O 5 -P 1 -C bbrplus
  iperf3 -c <your-server> -t 30 -O 5 -P 1 -C bbr3

Use an iperf3 build supporting ``-C`` and check its reported congestion
algorithm/error status. A device policy may require root or an allowed-CC
list change; a failed selection is NOT a BBRv3 benchmark. Repeat in
alternating order at least five times, on the same network/server with
comparable signal, temperature, load and time. Compare throughput, TCP
retransmissions, and latency under upload load. Keep congestion marks/loss,
CPU/battery cost and coexistence in mind, not just the highest speed result.

If a global setting is needed for an application without per-socket
selection, first record the old value. As root, set
``net.ipv4.tcp_congestion_control=bbr3`` for new sockets only, and restore
``bbrplus`` after the experiment. Do not change TCP memory caps, qdisc,
pacing, ECN, scheduler, or other tunables between trials. Existing sockets
do not automatically migrate when the default sysctl changes.

A sender's TCP congestion control governs that sender's outgoing data.
Changing the phone's algorithm cannot by itself select the remote server's
congestion control for downloads, and does not control QUIC. Neither v3 nor
BBRplus is guaranteed to win on every cellular/Wi-Fi path. No device
performance or stability advantage is claimed before actual tests.

Approved configuration follow-up (2026-11-07)
--------------------------------------------

The miatoll profile now also selects ``CONFIG_KSU_FEATURE_ADBROOT=y`` at
the user's request. This builds the existing vendored backslashxx feature;
its runtime toggle still initializes off. No KSU source, manager, SELinux
mode or unconditional shell-SU policy was changed.

The historical full AOSP builds and module-link evidence recorded in the
validation manifest used ADBROOT disabled. They remain evidence for the
unchanged BBRv3/TCP sources, not proof of the newly enabled KSU code path.
The current ADB-root-enabled profile still needs a new target build and
device validation. CI is manual-only and was not dispatched for publication.
The source-delta patch deliberately includes this approved config follow-up;
its original before-images and all three historical BPF chains are retained.

#!/usr/bin/env bash
# Bounded real-header object builds, NOT an image build or device qualification.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"
TOOLCHAIN_DIR=${TOOLCHAIN_DIR:-"$ROOT/.toolchains/r614150"}
TOOLCHAIN_DIR=$(cd "$TOOLCHAIN_DIR" && pwd)
OUTPUT_DIR=${OUTPUT_DIR:-"$ROOT/out/carry-over-remaining"}
JOBS=${JOBS:-2}
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || { echo 'Invalid JOBS' >&2; exit 1; }
expected=3b86e40facfff1eab4065614255d573293c10373
[[ -f "$TOOLCHAIN_DIR/aosp-prebuilts-commit.txt" ]] &&
    [[ "$(cat "$TOOLCHAIN_DIR/aosp-prebuilts-commit.txt")" == "$expected" ]] ||
    { echo 'Expected pinned AOSP Clang r614150 toolchain' >&2; exit 1; }
export PATH="$TOOLCHAIN_DIR/bin:$PATH"
for tool in clang clang++ ld.lld llvm-ar llvm-nm llvm-strip llvm-objcopy llvm-objdump llvm-readelf; do
    [[ -x "$TOOLCHAIN_DIR/bin/$tool" ]] || { echo "Missing LLVM tool: $tool" >&2; exit 1; }
done
"$TOOLCHAIN_DIR/bin/clang" --version
"$TOOLCHAIN_DIR/bin/ld.lld" --version
args=(O="$OUTPUT_DIR" ARCH=arm64 LLVM=1 LLVM_IAS=1
      CROSS_COMPILE=aarch64-linux-gnu- CLANG_TRIPLE=aarch64-linux-gnu-
      CC="$TOOLCHAIN_DIR/bin/clang" AS="$TOOLCHAIN_DIR/bin/clang"
      LD="$TOOLCHAIN_DIR/bin/ld.lld" AR="$TOOLCHAIN_DIR/bin/llvm-ar"
      NM="$TOOLCHAIN_DIR/bin/llvm-nm" STRIP="$TOOLCHAIN_DIR/bin/llvm-strip"
      OBJCOPY="$TOOLCHAIN_DIR/bin/llvm-objcopy" OBJDUMP="$TOOLCHAIN_DIR/bin/llvm-objdump"
      READELF="$TOOLCHAIN_DIR/bin/llvm-readelf"
      HOSTCC="$TOOLCHAIN_DIR/bin/clang" HOSTCXX="$TOOLCHAIN_DIR/bin/clang++"
      HOSTLDFLAGS=-fuse-ld=lld
      HOSTCFLAGS="-O2 ${EXTRA_HOSTCFLAGS:-}")
mkdir -p "$OUTPUT_DIR"
if [[ ${REUSE_CONFIG:-0} != 1 ]]; then
make "${args[@]}" vendor/xiaomi/miatoll_defconfig
scripts/config --file "$OUTPUT_DIR/.config" --disable LLVM_POLLY
make "${args[@]}" olddefconfig
cp "$OUTPUT_DIR/.config" "$OUTPUT_DIR/miatoll-default.config"
fi
objects=(kernel/fork.o kernel/exit.o kernel/sched/core.o kernel/sched/fair.o
 mm/swap.o mm/swap_state.o mm/swapfile.o mm/vmscan.o
 mm/memory.o mm/page_alloc.o mm/page_io.o mm/pagewalk.o mm/rmap.o
 mm/vmalloc.o mm/workingset.o mm/filemap.o mm/readahead.o mm/compaction.o
 fs/proc/task_mmu.o fs/proc/base.o fs/seq_file.o fs/eventpoll.o fs/fs-writeback.o
 fs/f2fs/data.o fs/f2fs/file.o fs/f2fs/segment.o fs/f2fs/gc.o fs/f2fs/checkpoint.o
 fs/f2fs/super.o fs/f2fs/sysfs.o drivers/block/zram/zram_drv.o
 arch/arm64/net/bpf_jit_comp.o kernel/bpf/verifier.o kernel/bpf/helpers.o
 kernel/bpf/btf.o kernel/bpf/syscall.o kernel/bpf/arraymap.o kernel/bpf/hashtab.o
 kernel/time/hrtimer.o kernel/time/tick-sched.o
 net/core/filter.o net/core/xdp.o net/xdp/xskmap.o
 net/ipv4/tcp.o net/ipv4/tcp_input.o net/ipv4/tcp_output.o net/ipv4/tcp_rate.o
 net/ipv4/tcp_timer.o net/ipv4/tcp_bbr3.o net/ipv4/bpf_tcp_ca.o
 net/core/dev.o net/core/skbuff.o net/sched/sch_fq.o
 fs/namei.o fs/namespace.o fs/super.o fs/open.o fs/stat.o fs/statfs.o fs/readdir.o
 fs/susfs.o fs/nomount/nomount.o drivers/kernelsu/ksu.o
 kernel/pid.o kernel/module.o kernel/events/core.o
 lib/buildid.o mm/slub.o mm/maccess.o
 net/core/bpf_sk_storage.o net/ipv4/tcp_ipv4.o
 net/xdp/xsk.o net/ipv4/af_inet.o net/ipv6/af_inet6.o)
make -j"$JOBS" "${args[@]}" "${objects[@]}"
for object in "${objects[@]}"; do test -s "$OUTPUT_DIR/$object"; done
make -j"$JOBS" "${args[@]}" kernel/bpf/
echo "PASS: ${#objects[@]} ARM64 objects, pinned LLVM, miatoll BORE/MGLRU/BBR3/security profile plus selected kernel/bpf directory"
echo 'LIMITS: object compilation only; no full image/module link or device qualification'

# Additional configurations are generated only in OUTPUT_DIR.
scripts/config --file "$OUTPUT_DIR/.config" --enable DEBUG_KERNEL --enable MEMCG --enable MEMCG_SWAP --enable PROVE_LOCKING --enable F2FS_FS_COMPRESSION --enable FTRACE --enable KPROBES --enable KPROBE_EVENTS --enable BPF_STREAM_PARSER
make "${args[@]}" olddefconfig
for opt in MEMCG LRU_GEN SCHED_BORE LOCKDEP F2FS_FS_COMPRESSION BPF_EVENTS NET_SOCK_MSG; do grep -qx "CONFIG_$opt=y" "$OUTPUT_DIR/.config"; done
cp "$OUTPUT_DIR/.config" "$OUTPUT_DIR/memcg-lockdep-compression.config"
make -j"$JOBS" "${args[@]}" mm/memcontrol.o mm/vmscan.o mm/memory.o mm/swap.o mm/swap_state.o mm/workingset.o kernel/fork.o kernel/sched/core.o kernel/sched/fair.o kernel/locking/lockdep.o fs/f2fs/file.o kernel/trace/bpf_trace.o net/core/skmsg.o net/core/sock_map.o net/ipv4/tcp_bpf.o
printf 'PASS: MEMCG/LOCKDEP/F2FS-compression/BPF-events/stream-parser real-header profile\n'
scripts/config --file "$OUTPUT_DIR/.config" --disable LRU_GEN --disable SCHED_BORE --disable DEBUG_FS
make "${args[@]}" olddefconfig
cp "$OUTPUT_DIR/.config" "$OUTPUT_DIR/bore-mglru-debugfs-off.config"
make -j"$JOBS" "${args[@]}" kernel/sched/core.o kernel/sched/fair.o kernel/fork.o mm/vmscan.o mm/swap.o mm/swap_state.o mm/memory.o mm/memcontrol.o
printf 'PASS: BORE/MGLRU/DEBUG_FS off real-header profile\n'

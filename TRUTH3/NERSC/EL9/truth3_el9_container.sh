# shellcheck shell=bash
# Sourced inside the ALRB container by run_truth3_el9_batch.sh.
#
# This is a separate file because atlasLocalSetup.sh evaluates every $ in the
# -r string once, before running any of it, so variables assigned and $(date)
# calls made within that string do not behave as written. A sourced file runs
# like an ordinary shell.

asetup Athena,24.0.53,here || return 1

echo "SETUP_COMPLETE=$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> split.log

# /usr/bin/time -v may not exist in every ALRB container -- guard rather
# than assume, so append_benchmark is never asked to extract metrics from
# output that was never produced.
if [ -x /usr/bin/time ]; then
  TIME_CMD=(/usr/bin/time -v)
  BENCH_MODE=time_v
else
  TIME_CMD=()
  BENCH_MODE=none
fi
echo "BENCH_MODE=${BENCH_MODE}" >> split.log

"${TIME_CMD[@]}" Derivation_tf.py --CA True --inputEVNTFile EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3 2>&1 | tee pipe_file.log

# time -v's report lands in the tee'd pipe, not in Derivation_tf.py's own
# log.Derivation -- fold it in so append_benchmark can read it.
cat pipe_file.log >> log.Derivation

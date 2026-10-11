# shellcheck shell=bash
# Sourced inside the ALRB container by run_fastframes.sh.
#
# This is a separate file because atlasLocalSetup.sh evaluates every $ in the
# -r string once, before running any of it, so variables assigned and $(date)
# calls made within that string do not behave as written. A sourced file runs
# like an ordinary shell.

asetup StatAnalysis,0.6.2 || return 1
# shellcheck disable=SC1091
source /srv/FastFramesTutorial/TutorialClass/build/setup.sh || return 1

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

"${TIME_CMD[@]}" python3 /srv/FastFramesTutorial/FastFrames/python/FastFrames.py -c /srv/fastframes_input/mc20e_example_config.yml 2>&1 | tee fastframes.log

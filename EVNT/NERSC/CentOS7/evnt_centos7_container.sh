# shellcheck shell=bash
# Sourced inside the ALRB container by run_evnt_centos7_batch.sh, which passes
# the job-config directory and random seed as arguments.
#
# This is a separate file because atlasLocalSetup.sh evaluates every $ in the
# -r string once, before running any of it, so variables assigned and $(date)
# calls made within that string do not behave as written. A sourced file runs
# like an ordinary shell.

config_dir=$1
seed=$2

asetup AthGeneration,23.6.31,here || return 1
export LHAPATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current
export LHAPDF_DATA_PATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current:/cvmfs/atlas.cern.ch/repo/sw/software/23.6/sw/lcg/releases/LCG_104d_ATLAS_13/MCGenerators/lhapdf/6.5.3/x86_64-centos7-gcc11-opt/share/LHAPDF:/cvmfs/atlas.cern.ch/repo/sw/Generators/lhapdfsets/current

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

"${TIME_CMD[@]}" Gen_tf.py --ecmEnergy=13000.0 --jobConfig="${config_dir}" --outputEVNTFile=EVNT.root --maxEvents=1000 --randomSeed="${seed}" 2>&1 | tee pipe_file.log

# time -v's report lands in the tee'd pipe, not in Gen_tf.py's own
# log.generate -- fold it in so append_benchmark can read it.
cat pipe_file.log >> log.generate

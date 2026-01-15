#!/bin/bash

MODE="${1:-local}"
shift || true

echo "::group::setupATLAS"
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ALRB_localConfigDir=$HOME/localConfig
# shellcheck disable=SC1091
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh -q
asetup Athena,25.0.47
echo "::endgroup::"

SINGLE=false
BACKEND="local"

case "${MODE}" in
    local)
        BACKEND="local"
        ;;
    triton)
        BACKEND="triton"
        ;;
    local_single)
        BACKEND="local"
        SINGLE=true
        ;;
    triton_single)
        BACKEND="triton"
        SINGLE=true
        ;;
    *)
        echo "ERROR: Unknown mode '${MODE}'"
        echo "Valid modes: local | triton | local_single | triton_single"
        exit 1
        ;;
esac

# ------------------------------------------------------------------------------
# AthenaMP parallel settings
# ------------------------------------------------------------------------------
export ATHENA_PROC_NUMBER=8
export ATHENA_CORE_NUMBER=8

# ------------------------------------------------------------------------------
# Triton configuration
# ------------------------------------------------------------------------------
TRITON_POSTEXEC='NNSharingSvc=cfg.getService("FTagNNSharingSvc");\
NNSharingSvc.UseTriton=True;\
NNSharingSvc.TritonUrl="triton-traefik.triton.svc.cluster.local";\
NNSharingSvc.TritonPort=8001;\
NNSharingSvc.TritonUseSSL=False'

EXTRA_OPTS=""

if [[ "${BACKEND}" == "triton" ]]; then
    echo "Running with Triton-enabled NNSharingSvc"
    EXTRA_OPTS=(--outputDAODFile 00485051._0002.triton.pool.root.1)
    EXTRA_OPTS+=(--postExec "${TRITON_POSTEXEC}")
else
    echo "Running in normal (local) mode"
    EXTRA_OPTS=(--outputDAODFile 00485051._0002.pool.root.1)
fi

set -euxo pipefail
# ------------------------------------------------------------------------------
# Optional single-model setup
# ------------------------------------------------------------------------------
if [[ "${SINGLE}" == "true" ]]; then
    echo "Compiling and sourcing the setup for single-model"
    cmake -DATLAS_PACKAGE_FILTER_FILE=/data/kratsg/tritonTest/athena-singlemodel/package_filters.txt -S /data/kratsg/tritonTest/athena-singlemodel/Projects/WorkDir -B build
    cmake --build build -j 16
    source build/x86_64-el9-gcc14-opt/setup.sh
    # echo "Sourcing single-model setup"
    # # shellcheck disable=SC1091
    # source /data/kratsg/tritonTest/build_singlemodel/x86_64-el9-gcc14-opt/setup.sh
fi

mkdir "${MODE}"
pushd "${MODE}"

echo "::group::Derivation_tf.py"
# Run the transform
Derivation_tf.py \
  --inputAODFile /data/kratsg/tritonTest/data24_13p6TeV.00485051.physics_Main.merge.AOD.f1518_m2248._lb0092._0002.1 \
  --athenaMPMergeTargetSize "DAOD_*:0" \
  --multiprocess True --sharedWriter True \
  --formats PHYS \
  --outputDAODFile 00485051._0002.pool.root.1 \
  --multithreadedFileValidation True \
  --CA "all:True" \
  --parallelCompression False \
  --perfmon fullmonmt \
  "${EXTRA_OPTS[@]}"
set +euxo pipefail
echo "::endgroup::"

popd

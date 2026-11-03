#!/bin/bash
#
#SBATCH --account=atlas:usatlas
#SBATCH --partition=ampere
#SBATCH --gpus a100:0
#SBATCH --job-name=evnt_batch_centos7
#SBATCH --output=output-%j.txt
#SBATCH --error=output-%j.txt
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=3g
#SBATCH --time=0-02:00:00


unset KRB5CCNAME

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Use ALRB_CONT_CMDOPTS to provide bind mount, etc. options

export ALRB_CONT_CMDOPTS="-B /sdf"

export ALRB_CONT_RUNPAYLOAD="source $HOME/AF-Benchmarking/EVNT/SLAC/CentOS7/run_evnt_centos_container.sh"

# ALRB runs the payload in a clean environment (apptainer exec -e), so the
# SUBMIT_TIME that submit_and_upload.sh exports would not reach
# append_benchmark; apptainer sets APPTAINERENV_<NAME> as <NAME> inside.
# Empty when the job is submitted without the wrapper.
export APPTAINERENV_SUBMIT_TIME="${SUBMIT_TIME:-}"

# shellcheck disable=SC1091
source $ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh -c centos7 -m /sdf/data/atlas/

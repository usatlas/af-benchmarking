#!/bin/bash
# shellcheck disable=SC1091
#
#SBATCH --account=atlas:usatlas
#SBATCH --partition=ampere
#SBATCH --gpus a100:0
#SBATCH --job-name=truth3_batch
#SBATCH --output=output-%j.txt
#SBATCH --error=output-%j.txt
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=3g
#SBATCH --time=0-00:30:00

unset KRB5CCNAME

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Use ALRB_CONT_CMDOPTS to provide bind mount, etc. options

export ALRB_CONT_CMDOPTS="-B /sdf"

export ALRB_CONT_RUNPAYLOAD="source /sdf/home/q/qlei/AF-Benchmarking/TRUTH3/SLAC/EL9/run_truth3_el9_container.sh"

# shellcheck disable=SC1091
source $ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh -c el9

#!/bin/bash

#SBATCH -N 1
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -J eventloop_noarrays
#SBATCH --cpus-per-task=2
#SBATCH --constraint=cpu
#SBATCH --mail-type=ALL
#SBATCH -t 1:0:0
#SBATCH --mem=8G


# OpenMP settings:
export OMP_NUM_THREADS=1
export OMP_PLACES=threads
export OMP_PROC_BIND=spread

#run the application:
srun -n 1 -c 2 --cpu_bind=cores  "$HOME"/AF-Benchmarking/NTuple_Hist/event_loop/NERSC/standard/run_eventloop_noarrays.sh

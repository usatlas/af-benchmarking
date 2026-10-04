#!/bin/bash

#SBATCH -N 1
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -J coffea_el9
#SBATCH --cpus-per-task=4
#SBATCH --constraint=cpu
#SBATCH --mail-type=ALL
#SBATCH -t 1:0:0
#SBATCH --mem=16G


# OpenMP settings:
export OMP_NUM_THREADS=1
export OMP_PLACES=threads
export OMP_PROC_BIND=spread

#run the application:
srun -n 1 -c 4 --cpu_bind=cores  "$HOME"/AF-Benchmarking/NTuple_Hist/coffea/NERSC/run_example.sh

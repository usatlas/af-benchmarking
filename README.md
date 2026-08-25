# AF Benchmarking

Contains benchmarking scripts used at the Tier 3 Analysis Facilities:

- [UChicago](https://github.com/usatlas/af-benchmarking?tab=readme-ov-file#uchicago)
- [SLAC](https://github.com/usatlas/af-benchmarking#slac)
- [BNL](https://github.com/usatlas/af-benchmarking#bnl)

It now contains scripts used at NERSC.

The jobs used for benchmarking are of the following type:

- EVNT Generation
- TRUTH3
- Rucio Downloads
- NTuple-to-Histogram

Said jobs can either run interactively or in the batch system.

For more information on the Tier 3 AFs check out the docs page,
[here](https://usatlas.github.io/af-docs/).

Documentation for this repository's benchmarking pipeline, parsing, and CI is
published at
[usatlas.github.io/af-benchmarking](https://usatlas.github.io/af-benchmarking/).

## Batch System

To execute jobs within the batch system you'll need both a submission file and a
executable file. The submission file will give the batch system information
about your job; where the job script is located and the requested resources. The
executable file will contain the code we want the host to run; your code. Below
you can find examples to help you get started at the Tier 3 AFs.

The following sections display submission and executable files that can be used
at the respective analysis facilities. This assumes you've acquired your
accounts. If you have not done so, follow the account setup instructions for
your site: [UChicago](https://usatlas.github.io/af-docs/uchicago/account/),
[SLAC](https://usatlas.github.io/af-docs/slac/account/), or
[BNL](https://usatlas.github.io/af-docs/bnl/account/).

After logging into the desired AF, obtain the directory by following these
steps:

```bash
git clone https://github.com/usatlas/af-benchmarking.git af-benchmarking
```

### UChicago

[_TRUTH3 Executable File_](https://github.com/usatlas/af-benchmarking/blob/main/ExampleFiles/UC/example_truth3_executable.sh)

```bash
#!/bin/bash

# Input/large files should be stored in the /data/$USER directory
# Change <username> to your username
inputFile_dir="/data/<username>/TRUTH3_Native_input_file/"

# Creates the file directory
mkdir -p ${inputFile_dir}

# Moves input files to the input file directory
cp ~/af-benchmarking/TRUTH3/EVNT.root ${inputFile_dir}

# Sets up our environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh

# Sets the Athena version we want
asetup Athena,24.0.53,here
Derivation_tf.py --CA True --inputEVNTFile ${inputFile_dir}EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3

# Obtains and appends the host machine to the log file
hostname >> log.Derivation

```

[_TRUTH3 Submission File_](https://github.com/usatlas/af-benchmarking/blob/main/ExampleFiles/UC/example_truth3_submission.sub)

```bash
Universe = vanilla


Output = example_truth3_native.$(Cluster).$(Process).out
Error = example_truth3_native.$(Cluster).$(Process).err
Log = example_truth3_native.$(Cluster).$(Process).log

# Path to your job script, in this case
# Change <username> to your own username
Executable = /home/<username>/af-benchmarking/TRUTH3/UC/Native/example_run_truth3_native_batch.sh

request_memory = 3GB
request_cpus = 1

Queue 1
```

### SLAC

When working at SLAC, the jobs submitted must be containerized. The example
below outlines how to do this using a TRUTH3 job running in EL9 container.

[_TRUTH3 Executable File_](https://github.com/usatlas/af-benchmarking/blob/main/ExampleFiles/SLAC/example_truth3_executable.sh)

```bash
#!/bin/bash

# Defines the OS wanted for the container
OScontainer="el9"

# Initializes the container with the OS defined in the previous line
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh -c ${OScontainer} -r "cp -r /home/$USER/TRUTH3Files/ . && \
asetup Athena,24.0.53,here && \
Derivation_tf.py --CA True --inputEVNTFile /srv/TRUTH3Files/el9/EVNT.root --outputDAODFile=TRUTH3.root --formats TRUTH3"

# Appends the host-name to the end of the log file
hostname >> log.Derivation
```

[_TRUTH3 Submission File_](https://github.com/usatlas/af-benchmarking/blob/main/ExampleFiles/SLAC/example_truth3_submission.sub)

```bash
#!/bin/bash
#
#SBATCH --account=atlas:usatlas
#SBATCH --partition=ampere
#SBATCH --gpus a100:0
#SBATCH --job-name=truth3_batch
#SBATCH --output=output-%j.txt
#SBATCH --error=output-%j.txt
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4g
#SBATCH --time=0-00:30:00

unset KRB5CCNAME

export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Use ALRB_CONT_CMDOPTS to provide bind mount, etc. options

export ALRB_CONT_CMDOPTS="-B /sdf"

export ALRB_CONT_RUNPAYLOAD="source $HOME/af-benchmarking/TRUTH3/SLAC/EL9/run_truth3_el9_container.sh"

source $ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh -c el9
```

### BNL

[_TRUTH3 Executable File_](https://github.com/usatlas/af-benchmarking/blob/main/ExampleFiles/BNL/example_truth3_executable.sh)

```bash
#!/bin/bash

# Config Dir Needed
config_dir="TRUTH3Files/"

# Sets up the environment
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase

# Sets up the container:
## -c : used to make a container followed by the OS we want to use
## -m : mounts a specific directory
## -r : precedes the commands we want to run within the container
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh -c el9 -r "asetup Athena,24.0.53,here && \
  Derivation_tf.py --CA True --inputEVNTFile ${config_dir}EVNT_el9_batch.root --outputDAODFile=TRUTH3.root --formats TRUTH3"

# Obtains and appends the host name to the log file
hostname >> log.Derivation
```

[_TRUTH3 Submission File_](https://github.com/usatlas/af-benchmarking/blob/main/ExampleFiles/BNL/example_truth3_submission.sub)

```bash
Universe = vanilla


Output = /atlasgpfs01/usatlas/data/<username>/myjob.$(Cluster).$(Process).out
Error = /atlasgpfs01/usatlas/data/<username>/myjob.$(Cluster).$(Process).err
Log = /atlasgpfs01/usatlas/data/<username>/myjob.$(Cluster).$(Process).log

Executable = /usatlas/u/<username>/af-benchmarking/TRUTH3/BNL/EL9/run_truth3_el9_batch.sh

request_memory = 3GB
request_cpus = 1

Queue 1
```

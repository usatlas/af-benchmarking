# Benchmarking Tier 3 Analysis Facilities (and NERSC)

Series of jobs that run at NERSC and the
[Tier 3 Analysis Facilities](https://usatlas.github.io/af-docs/): UChicago,
SLAC, BNL. The jobs used to benchmark are:

## Rucio Download:

[Documentation](https://atlas-software.docs.cern.ch/analysis/analysis_tutorial/AnalysisSWTutorial/rucio_download_files/)

[Script used at AFs](https://github.com/usatlas/af-benchmarking/blob/main/Rucio/rucio_script.sh)

## EVNT:

[Documentation for EVNT Production](https://atlas-software.docs.cern.ch/analysis/analysis_tutorial/AnalysisSWTutorial/mc_generation/)

[Script used at the UC AF](https://github.com/usatlas/af-benchmarking/blob/main/EVNT/UC/run_evnt_native_batch.sh)

## TRUTH3:

[Documentation for TRUTH3 Derivation](https://atlas-software.docs.cern.ch/analysis/analysis_tutorial/AnalysisSWTutorial/mc_truth_derivation/)

[Script used at the UC AF](https://github.com/usatlas/af-benchmarking/blob/main/TRUTH3/UC/Native/run_truth3_native_batch.sh)

## Ntuple -> Histogram:

[Coffea](https://coffea-hep.readthedocs.io/en/latest/index.html) |
[Script used at the UC AF](https://github.com/usatlas/af-benchmarking/tree/main/NTuple_Hist/coffea)

[FastFrames](https://atlas-project-topreconstruction.web.cern.ch/fastframesdocumentation/latest/)
|
[Script used at the UC AF](https://github.com/usatlas/af-benchmarking/tree/main/NTuple_Hist/fastframes)

[EventLoop](https://github.com/usatlas/af-benchmarking/tree/main/NTuple_Hist/event_loop)

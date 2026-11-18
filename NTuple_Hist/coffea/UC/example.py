# this portion is done to ignore warnings from coffea for now
from __future__ import annotations

import argparse
import awkward as ak
import dask
import hist
import hist.dask as had
from coffea import processor
from distributed import Client, LocalCluster
from atlas_schema.schema import NtupleSchema
import json
import warnings
import time
import uproot

from pathlib import Path
from coffea.dataset_tools import apply_to_fileset
import numpy as np
from datetime import datetime, timezone

# The dataset JSONs are shared by all sites and live one directory up, in the
# checkout this script runs from. Each format's copy keeps the same per-file
# steps, so both formats are split into identical chunks; see
# docs/uchicago/rntuple-conversion.md.
DATASET_DIR = (
    Path(__file__).resolve().parent.parent / "single_campaign_mc20e_dataset_runnable"
)
DATASET_JSONS = {
    "ttree": DATASET_DIR / "af_v2_700402.json",
    "rntuple": DATASET_DIR / "af_v2_700402_rntuple.json",
}

# Target entries per chunk in virtual-array mode: the largest per-file step in
# the dataset JSONs. coffea splits each file evenly near this size, so the
# chunks are close to, but not exactly, the dask mode's steps.
RUNNER_CHUNKSIZE = 51134


warnings.filterwarnings("ignore", module="coffea.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore")


def iso_utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def runner_fileset(dataset, name):
    """
    Return the fileset that coffea's ``processor.Runner`` takes for ``dataset``.

    Virtual-array mode reads each file whole and splits it into chunks itself,
    so it needs only each file's object path, not the precomputed ``steps`` and
    ``form`` of the dask-mode dataset runnable. The dataset metadata is passed
    on, since the processor reads its normalisation from it.

    Args:
        dataset: One dataset entry with a ``files`` mapping of path -> file info
        name: Name of the dataset in the returned fileset
    """
    files = {path: info["object_path"] for path, info in dataset["files"].items()}
    return {name: {"files": files, "metadata": dict(dataset["metadata"])}}


class MyFirstProcessor(processor.ProcessorABC):
    def __init__(self):
        pass

    def process(self, events):
        # Accessing per-dataset meta-data
        dataset = events.metadata["dataset"]
        # Defining histogram properties
        h_ph_pt = (
            had.Hist.new.StrCat(["all"], name="isEM")
            .Regular(100, 0.0, 1000.0, name="pt", label="$pt_{\\gamma}$ [GeV]")
            .Double()
        )

        # Defining the cut
        cut = ak.any(events.ph.passes("tightID"), axis=1)
        phcut = events[cut].ph.passes("tightID")

        xs = events.metadata["xs"]
        lum = events.metadata["luminosity"]
        genFiltEff = events.metadata["genFiltEff"]
        # kfactor = events.metadata["kFactor"]
        kfactor = 1.0
        sumOfWeights = events.metadata["sum_of_weights"]
        # sumOfEvents = events.metadata["sum_of_events"]
        # sumOfWeights = 4345667100606464.0
        weight_norm = xs * genFiltEff * kfactor * lum / sumOfWeights
        h_ph_pt.fill(
            isEM="all",
            pt=ak.firsts(events[cut].ph[phcut].pt / 1000.0),
            weight=(weight_norm * events[cut].weight.mc * events[cut].weight.pileup),
        )
        # h_ph_pt.fill(isEM="pass", pt=ak.firsts(events[cut].ph.pt / 1.0e3))
        # h_ph_pt.fill(isEM="fail", pt=ak.firsts(events[~cut].ph.pt / 1.0e3))

        # Returns hist entries
        return {
            dataset: {
                "entries": ak.num(events, axis=0),
                "ph_pt": h_ph_pt,
            }
        }

    def postprocess(self, accumulator):
        pass


class VirtualProcessor(processor.ProcessorABC):
    """MyFirstProcessor for virtual-array mode, which reads RNTuple.

    coffea's dask-awkward mode crashes on RNTuple input (uproot's RNTuple fields
    have no ``title``, and chunks starting mid-cluster come back as unpacked
    jagged arrays), so the RNTuple benchmark runs through ``processor.Runner``.
    That works on plain awkward arrays, hence an eager ``hist.Hist``; the
    selection and weights are MyFirstProcessor's.
    """

    def process(self, events):
        dataset = events.metadata["dataset"]
        h_ph_pt = (
            hist.Hist.new.StrCat(["all"], name="isEM")
            .Regular(100, 0.0, 1000.0, name="pt", label="$pt_{\\gamma}$ [GeV]")
            .Double()
        )

        cut = ak.any(events.ph.passes("tightID"), axis=1)
        phcut = events[cut].ph.passes("tightID")

        md = events.metadata
        kfactor = 1.0
        weight_norm = (md["xs"] * md["genFiltEff"] * kfactor * md["luminosity"]) / md[
            "sum_of_weights"
        ]
        h_ph_pt.fill(
            isEM="all",
            pt=ak.firsts(events[cut].ph[phcut].pt / 1000.0),
            weight=(weight_norm * events[cut].weight.mc * events[cut].weight.pileup),
        )

        return {dataset: {"entries": len(events), "ph_pt": h_ph_pt}}

    def postprocess(self, accumulator):
        return accumulator


def run_dask(dataset_runnable):
    """Build the dask-awkward graph, then time only its computation."""
    # Defining "MyFirstProcessor" object
    p = MyFirstProcessor()
    print("Applying to fileset")
    out = apply_to_fileset(
        p,
        dataset_runnable,
        schemaclass=NtupleSchema,
    )

    start_time_utc = iso_utc_now()
    start_time = time.time()
    (computed,) = dask.compute(out["Wmunugamma"])
    return computed, start_time_utc, start_time


def run_virtual(dataset_runnable, client):
    """Run in virtual-array mode on the same dask cluster, timing the whole run."""
    fileset = runner_fileset(dataset_runnable["Wmunugamma"], "Wmunugamma")
    runner = processor.Runner(
        executor=processor.DaskExecutor(client=client, status=False),
        schema=NtupleSchema,
        chunksize=RUNNER_CHUNKSIZE,
    )
    print("Running in virtual-array mode")

    start_time_utc = iso_utc_now()
    start_time = time.time()
    computed = runner(fileset, processor_instance=VirtualProcessor())
    return computed, start_time_utc, start_time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=sorted(DATASET_JSONS), default="ttree")
    args = parser.parse_args()

    # client = Client()
    # Limit to 4 total CPU cores, across 2 workers with 2 threads each
    cluster = LocalCluster(n_workers=2, threads_per_worker=2)
    # local_directory = f"/tmp/dask-scratch-space-{os.getuid()}"
    with Client(cluster) as client:
        dataset_runnable = json.loads(DATASET_JSONS[args.format].read_text())
        nevents = 0
        for f in dataset_runnable["Wmunugamma"]["files"]:
            nevents += int(dataset_runnable["Wmunugamma"]["files"][f]["num_entries"])

        if args.format == "rntuple":
            computed, start_time_utc, start_time = run_virtual(dataset_runnable, client)
        else:
            computed, start_time_utc, start_time = run_dask(dataset_runnable)
        end_time_utc = iso_utc_now()
        end_time = time.time()
        execute_time = end_time - start_time

        print(
            f"... execution time: {end_time - start_time:6.2f} s ( {(nevents / 1000.0) / execute_time:6.2f} kHz)"
        )

        print(computed)
        print(f"start_time_utc={start_time_utc}")
        print(f"end_time_utc={end_time_utc}")

        # Plots using 'computed'
        # this_hist = computed["700402.Wmunugamma.mc20a.v2.1"]["ph_pt"]
        this_hist = computed["Wmunugamma"]["ph_pt"]
        with uproot.recreate("coffea.root") as fp:
            for i in np.arange(len(this_hist.axes[0])):
                fp[this_hist.axes[0].bin(i)] = this_hist[{0: i}].to_numpy()


if __name__ == "__main__":
    main()

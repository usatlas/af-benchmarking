# this portion is done to ignore warnings from coffea for now
from __future__ import annotations

import awkward as ak
import dask
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


warnings.filterwarnings("ignore", module="coffea.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore")


def iso_utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def main():
    # Defining "MyFirstProcessor" object
    p = MyFirstProcessor()

    # client = Client()
    # Limit to 4 total CPU cores, across 2 workers with 2 threads each
    cluster = LocalCluster(n_workers=2, threads_per_worker=2)
    # local_directory = f"/tmp/dask-scratch-space-{os.getuid()}"
    with Client(cluster):
        dataset_runnable = json.loads(
            Path(
                "/home/runner/_work/af-benchmarking/af-benchmarking/NTuple_Hist/coffea/single_campaign_mc20e_dataset_runnable/af_v2_700402.json"
            ).read_text()
        )
        nevents = 0
        for f in dataset_runnable["Wmunugamma"]["files"]:
            nevents += int(dataset_runnable["Wmunugamma"]["files"][f]["num_entries"])
        print("Applying to fileset")
        out = apply_to_fileset(
            p,
            dataset_runnable,
            schemaclass=NtupleSchema,
        )

        start_time_utc = iso_utc_now()
        start_time = time.time()

        (computed,) = dask.compute(out["Wmunugamma"])
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

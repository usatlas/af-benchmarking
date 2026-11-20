import argparse
import os
import ROOT as r
from pathlib import Path
from datetime import datetime, UTC
import time


def normalization(metadata):
    """Cross-section times luminosity over the sum of weights."""
    xs = metadata["xs"]
    lum = metadata["luminosity"]
    genFiltEff = metadata["genFiltEff"]
    kfactor = metadata.get("kfactor", 1.0)
    sumOfWeights = metadata["sum_of_weights"]
    return xs * genFiltEff * kfactor * lum / sumOfWeights


def photon_eventloop(f_name, h_baseline_pt, metadata):
    """Process one ROOT file and fill the given histogram."""
    fp = r.TFile.Open(f_name, "READ")
    # An unreadable ntuple must fail the job: skipping it would report fewer
    # events with a successful exit status
    if not fp or fp.IsZombie():
        raise RuntimeError(f"Could not open file: {f_name}")

    tree = fp.Get("analysis")
    if not tree:
        fp.Close()
        raise RuntimeError(f"No tree named 'analysis' in {f_name}")

    totalevents = tree.GetEntriesFast()
    print(f"  {f_name} has {totalevents} events")

    weight_norm = normalization(metadata)

    processed = 0

    # name of branches in tree
    # print(tree.GetListOfBranches())

    # Event loop
    for i, event in enumerate(tree):
        processed += 1
        if (i + 1) % 50000 == 0:
            print(f"    Processed {i + 1:6d}/{totalevents}")

        weight = weight_norm * event.weight_mc_NOSYS * event.weight_pileup_NOSYS

        for index, ph_pt in enumerate(event.ph_pt_NOSYS):
            ph_tight = ord(event.ph_select_tightID_NOSYS[index]) > 0
            if not ph_tight:
                continue

            h_baseline_pt.Fill(ph_pt / 1000.0, weight)  # Fill GeV
            break  # only fill with first passing photon

    fp.Close()
    return processed


def photon_eventloop_rntuple(f_name, h_baseline_pt, metadata):
    """Process one RNTuple file and fill the given histogram.

    The RNTuple counterpart of iterating a TTree and reading event.branch:
    every event loads the entry and looks each field up by name.
    """
    # ROOT 6.34 (LCG_107a) still has the reader under Experimental, and its
    # REntry has no name-indexing pythonization, so the lookup is GetPtr.
    reader = r.Experimental.RNTupleReader.Open("analysis", f_name)
    entry = reader.GetModel().GetDefaultEntry()

    totalevents = reader.GetNEntries()
    print(f"  {f_name} has {totalevents} events")

    weight_norm = normalization(metadata)

    processed = 0

    # Event loop
    for i in reader.GetEntryRange():
        processed += 1
        if (i + 1) % 50000 == 0:
            print(f"    Processed {i + 1:6d}/{totalevents}")

        reader.LoadEntry(i)

        # cppyy dereferences shared_ptr<vector> but not shared_ptr<float>.
        weight = (
            weight_norm
            * entry.GetPtr["float"]("weight_mc_NOSYS").get()[0]
            * entry.GetPtr["float"]("weight_pileup_NOSYS").get()[0]
        )

        ph_select_tightID = entry.GetPtr["std::vector<char>"]("ph_select_tightID_NOSYS")
        for index, ph_pt in enumerate(
            entry.GetPtr["std::vector<float>"]("ph_pt_NOSYS")
        ):
            ph_tight = ord(ph_select_tightID[index]) > 0
            if not ph_tight:
                continue

            h_baseline_pt.Fill(ph_pt / 1000.0, weight)  # Fill GeV
            break  # only fill with first passing photon

    return processed


EVENTLOOPS = {"ttree": photon_eventloop, "rntuple": photon_eventloop_rntuple}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=sorted(EVENTLOOPS), default="ttree")
    args = parser.parse_args()
    eventloop = EVENTLOOPS[args.format]

    # Define samples (all will contribute to one histogram)
    samples = [
        {
            "name": "Wmunugamma",
            # Directory holding the mc20e ntuples at this site
            "path": Path(os.environ["NTUPLE_DIR"]),
            "metadata": {
                "genFiltEff": 1.0,
                "luminosity": 58.7916,
                "xs": 364840.0,
                "sum_of_weights": 1816229744476160.0,
                "kfactor": 1.0,
            },
        }
    ]

    # Create a single histogram for all samples combined
    h_baseline_pt = r.TH1D(
        "baseline_pt_total",
        "Photon baseline pT (all samples); pT [GeV]; Events",
        100,
        0,
        1000,
    )

    start_time_utc = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    t0 = time.perf_counter()

    total_events_processed = 0
    # Process every file in every sample, filling the same histogram
    for s in samples:
        print(f"\nProcessing sample: {s['name']}")
        for f in sorted(s["path"].glob("*.root")):
            total_events_processed += eventloop(str(f), h_baseline_pt, s["metadata"])

    dt = time.perf_counter() - t0
    end_time_utc = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    event_rate_khz = (total_events_processed / dt) / 1000.0 if dt > 0 else 0.0

    # Save combined histogram
    output_file = r.TFile("event_loop_noarrays_output_hist.root", "RECREATE")
    h_baseline_pt.Write()
    output_file.Close()
    print("\nCombined histogram written to event_loop_output_hist.root")
    print("\n=== BENCHMARK ===")
    print(f"start_time_utc={start_time_utc}")
    print(f"end_time_utc={end_time_utc}")
    print(f"wall_time_sec={dt:.6f}")
    print(f"events_processed={total_events_processed}")
    print(f"event_rate_khz={event_rate_khz:.6f}")
    print("=================\n")


if __name__ == "__main__":
    main()

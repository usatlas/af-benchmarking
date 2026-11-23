import ROOT as r
from pathlib import Path
from array import array
from datetime import datetime, timezone
import time


ph_pt_array = r.std.vector("float")()
ph_select_tightID_array = r.std.vector("char")()
weight_mc_array = array("f", [0.0])
weight_pileup_array = array("f", [0.0])


def photon_eventloop(f_name, h_baseline_pt, metadata):
    """Process one ROOT file and fill the given histogram."""
    fp = r.TFile.Open(f_name, "READ")
    if not fp or fp.IsZombie():
        print(f"Could not open file: {f_name}")
        return

    tree = fp.Get("analysis")
    if not tree:
        print(f"No tree named 'analysis' in {f_name}")
        fp.Close()
        return

    tree.SetBranchAddress("ph_pt_NOSYS", ph_pt_array)
    tree.SetBranchAddress("ph_select_tightID_NOSYS", ph_select_tightID_array)
    tree.SetBranchAddress("weight_mc_NOSYS", weight_mc_array)
    tree.SetBranchAddress("weight_pileup_NOSYS", weight_pileup_array)

    totalevents = tree.GetEntriesFast()
    print(f"  {f_name} has {totalevents} events")

    # Normalization factors
    xs = metadata["xs"]
    lum = metadata["luminosity"]
    genFiltEff = metadata["genFiltEff"]
    kfactor = metadata.get("kfactor", 1.0)
    sumOfWeights = metadata["sum_of_weights"]
    weight_norm = xs * genFiltEff * kfactor * lum / sumOfWeights

    processed = 0

    # name of branches in tree
    # print(tree.GetListOfBranches())

    # Event loop
    numevents = tree.GetEntriesFast()
    for i in range(numevents):
        processed += 1
        if (i + 1) % 50000 == 0:
            print(f"    Processed {i + 1:6d}/{totalevents}")

        tree.GetEntry(i)

        weight = weight_norm * weight_mc_array[0] * weight_pileup_array[0]

        # print("--------------------------------------------")
        for index in range(len(ph_pt_array)):
            if not (ord(ph_select_tightID_array[index]) > 0):
                continue

            h_baseline_pt.Fill(ph_pt_array[index] / 1000.0, weight)  # Fill GeV
            break  # only fill with first passing photon

    fp.Close()
    return processed


def main():
    # Define samples (all will contribute to one histogram)
    samples = [
        {
            "name": "Wmunugamma",
            "path": Path(
                "/atlasgpfs01/usatlas/data/jroblesgo/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root/"
            ),
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

    start_time_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    t0 = time.perf_counter()

    total_events_processed = 0

    # Process every file in every sample, filling the same histogram
    for s in samples:
        print(f"\nProcessing sample: {s['name']}")
        for f in sorted(s["path"].glob("*.root")):
            total_events_processed += photon_eventloop(
                str(f), h_baseline_pt, s["metadata"]
            )

    dt = time.perf_counter() - t0
    end_time_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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

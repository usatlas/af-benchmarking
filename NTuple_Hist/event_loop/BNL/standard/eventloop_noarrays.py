import ROOT as r
from pathlib import Path
from datetime import datetime, timezone
import time


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

    totalevents = tree.GetEntriesFast()
    print(f"  {f_name} has {totalevents} events")

    # Normalization factors
    xs = metadata["xs"]
    lum = metadata["luminosity"]
    genFiltEff = metadata["genFiltEff"]
    kfactor = metadata.get("kfactor", 1.0)
    sumOfWeights = metadata["sum_of_weights"]
    weight_norm = xs * genFiltEff * kfactor * lum / sumOfWeights

    # name of branches in tree
    # print(tree.GetListOfBranches())

    processed = 0
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

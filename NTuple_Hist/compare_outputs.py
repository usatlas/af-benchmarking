#!/usr/bin/env python3
"""Compare photon pT histogram outputs across NTuple-to-histogram frameworks.

Requires: uproot, numpy, matplotlib
  pip install uproot numpy matplotlib

Usage:
    python compare_outputs.py \\
        --coffea coffea.root \\
        --eventloop event_loop_noarrays_output_hist.root \\
        --fastframes /srv/output/histograms.root

FastFrames histogram name: FastFrames uses the convention
{sample}_{region}_{variable}_{systematic}, so for the default BNL config
the histogram is "example_FS_Muon_ph_pt_NOSYS". Override with
--fastframes-hist if your config differs.

Key difference to look for: coffea and eventloop apply an event-level
tightID cut (skip events with no tightID photon), while FastFrames
fills the underflow with events where the sorted tightID list is empty
(ph1_pt1_NOSYS = -0.999 GeV). The in-range integrals should be close
but FastFrames will have extra entries in the underflow.
"""

import argparse

import numpy as np
import uproot
import matplotlib.pyplot as plt


def load_th1(path, name):
    """Return (bin_values, bin_edges) arrays for a TH1 in a ROOT file."""
    with uproot.open(path) as f:
        available = list(f.keys())
        if name not in available:
            raise KeyError(
                f"{name!r} not found in {path}.\nAvailable keys: {available}"
            )
        values, edges = f[name].to_numpy()
    return values, edges


def weighted_integral(values, edges):
    return float(np.sum(values * (edges[1:] - edges[:-1])))


def main():
    parser = argparse.ArgumentParser(
        description="Compare photon pT histograms across NTuple-to-histogram frameworks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--coffea", required=True, help="coffea output ROOT file")
    parser.add_argument(
        "--coffea-hist", default="all", metavar="NAME",
        help="histogram name in coffea ROOT file (default: all)",
    )
    parser.add_argument("--eventloop", required=True, help="eventloop output ROOT file")
    parser.add_argument(
        "--eventloop-hist", default="baseline_pt_total", metavar="NAME",
        help="histogram name in eventloop ROOT file (default: baseline_pt_total)",
    )
    parser.add_argument("--fastframes", required=True, help="fastframes output ROOT file")
    parser.add_argument(
        "--fastframes-hist", default="example_FS_Muon_ph_pt_NOSYS", metavar="NAME",
        help="histogram name in fastframes ROOT file (default: example_FS_Muon_ph_pt_NOSYS)",
    )
    parser.add_argument(
        "--plot", default="comparison.png", metavar="PATH",
        help="output plot file (default: comparison.png; pass empty string to skip)",
    )
    args = parser.parse_args()

    coffea_vals, coffea_edges = load_th1(args.coffea, args.coffea_hist)
    el_vals, el_edges = load_th1(args.eventloop, args.eventloop_hist)
    ff_vals, ff_edges = load_th1(args.fastframes, args.fastframes_hist)

    binning_consistent = np.allclose(coffea_edges, el_edges) and np.allclose(
        coffea_edges, ff_edges
    )
    if not binning_consistent:
        print("WARNING: histogram binning differs across frameworks")
        for label, edges in [
            ("coffea", coffea_edges),
            ("eventloop", el_edges),
            ("fastframes", ff_edges),
        ]:
            print(f"  {label}: {len(edges) - 1} bins, [{edges[0]:.1f}, {edges[-1]:.1f}]")

    # Summary table
    print(f"\n{'Framework':<12} {'Integral':>14} {'Peak bin':>12} {'Non-zero bins':>16}")
    print("-" * 58)
    for label, vals, edges in [
        ("coffea", coffea_vals, coffea_edges),
        ("eventloop", el_vals, el_edges),
        ("fastframes", ff_vals, ff_edges),
    ]:
        print(
            f"{label:<12}"
            f" {weighted_integral(vals, edges):>14.4f}"
            f" {float(np.max(vals)):>12.4f}"
            f" {int(np.sum(vals > 0)):>16d}"
        )

    if binning_consistent:
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio_el = np.where(coffea_vals != 0, el_vals / coffea_vals, np.nan)
            ratio_ff = np.where(coffea_vals != 0, ff_vals / coffea_vals, np.nan)
        print(f"\nMean bin ratio (where coffea > 0):")
        print(f"  EventLoop  / Coffea : {np.nanmean(ratio_el):.4f}")
        print(f"  FastFrames / Coffea : {np.nanmean(ratio_ff):.4f}")

    if not args.plot:
        return

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(8, 8),
        gridspec_kw={"height_ratios": [3, 1]},
        sharex=True,
    )

    for label, vals, edges, color, ls in [
        ("Coffea", coffea_vals, coffea_edges, "tab:blue", "-"),
        ("EventLoop", el_vals, el_edges, "tab:green", "--"),
        ("FastFrames", ff_vals, ff_edges, "tab:red", ":"),
    ]:
        ax_top.stairs(vals, edges, label=label, color=color, linestyle=ls, linewidth=1.5)

    ax_top.set_ylabel("Events / bin")
    ax_top.set_yscale("log")
    ax_top.legend()
    ax_top.set_title(r"Photon $p_\mathrm{T}$: Coffea vs EventLoop vs FastFrames")
    ax_top.set_xlim(coffea_edges[0], coffea_edges[-1])

    if binning_consistent:
        ax_bot.axhline(1.0, color="black", linewidth=0.8, linestyle="-")
        ax_bot.stairs(
            ratio_el, coffea_edges,
            label="EventLoop / Coffea", color="tab:green", linestyle="--", linewidth=1.5,
        )
        ax_bot.stairs(
            ratio_ff, coffea_edges,
            label="FastFrames / Coffea", color="tab:red", linestyle=":", linewidth=1.5,
        )
        ax_bot.set_ylim(0.5, 1.5)
        ax_bot.set_ylabel("Ratio to Coffea")
        ax_bot.legend(fontsize=9)
    else:
        ax_bot.text(
            0.5, 0.5, "Binning mismatch — ratio unavailable",
            ha="center", va="center", transform=ax_bot.transAxes,
        )

    ax_bot.set_xlabel(r"Photon $p_\mathrm{T}$ [GeV]")
    fig.tight_layout()
    fig.savefig(args.plot, dpi=150)
    print(f"\nPlot saved to: {args.plot}")


if __name__ == "__main__":
    main()

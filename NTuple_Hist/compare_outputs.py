#!/usr/bin/env python3
"""Compare photon pT histogram outputs across NTuple-to-histogram frameworks.

Requires: ROOT (PyROOT) — available on ATLAS analysis facilities.

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

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptTitle(0)


def load_th1(path, name):
    """Load a TH1 from a ROOT file, detached from the file."""
    f = ROOT.TFile.Open(path, "READ")
    if not f or f.IsZombie():
        raise OSError(f"Cannot open {path}")
    h = f.Get(name)
    if not h:
        keys = [k.GetName() for k in f.GetListOfKeys()]
        raise KeyError(f"{name!r} not found in {path}.\nAvailable keys: {keys}")
    h = h.Clone()
    h.SetDirectory(0)
    f.Close()
    return h


def check_binning(hists):
    ref_label, ref_h = hists[0]
    ok = True
    for label, h in hists[1:]:
        if (
            h.GetNbinsX() != ref_h.GetNbinsX()
            or h.GetXaxis().GetXmin() != ref_h.GetXaxis().GetXmin()
            or h.GetXaxis().GetXmax() != ref_h.GetXaxis().GetXmax()
        ):
            print(f"WARNING: binning of {label!r} differs from {ref_label!r}")
            ok = False
    return ok


def print_summary(hists):
    print(
        f"\n{'Framework':<12} {'Integral':>14} {'Peak bin':>12} {'Non-zero bins':>16}"
    )
    print("-" * 58)
    for label, h in hists:
        integral = h.Integral()
        peak = h.GetMaximum()
        nonzero = sum(1 for i in range(1, h.GetNbinsX() + 1) if h.GetBinContent(i) > 0)
        print(f"{label:<12} {integral:>14.4f} {peak:>12.4f} {nonzero:>16d}")


def make_ratio(h_num, h_den, name):
    ratio = h_num.Clone(name)
    ratio.SetDirectory(0)
    ratio.Divide(h_den)
    return ratio


def main():
    parser = argparse.ArgumentParser(
        description="Compare photon pT histograms across NTuple-to-histogram frameworks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--coffea", required=True, help="coffea output ROOT file")
    parser.add_argument(
        "--coffea-hist",
        default="all",
        metavar="NAME",
        help="histogram name in coffea ROOT file (default: all)",
    )
    parser.add_argument("--eventloop", required=True, help="eventloop output ROOT file")
    parser.add_argument(
        "--eventloop-hist",
        default="baseline_pt_total",
        metavar="NAME",
        help="histogram name in eventloop ROOT file (default: baseline_pt_total)",
    )
    parser.add_argument(
        "--fastframes", required=True, help="fastframes output ROOT file"
    )
    parser.add_argument(
        "--fastframes-hist",
        default="example_FS_Muon_ph_pt_NOSYS",
        metavar="NAME",
        help="histogram name in fastframes ROOT file (default: example_FS_Muon_ph_pt_NOSYS)",
    )
    parser.add_argument(
        "--plot",
        default="comparison.pdf",
        metavar="PATH",
        help="output plot file (default: comparison.pdf; pass empty string to skip)",
    )
    args = parser.parse_args()

    coffea_h = load_th1(args.coffea, args.coffea_hist)
    el_h = load_th1(args.eventloop, args.eventloop_hist)
    ff_h = load_th1(args.fastframes, args.fastframes_hist)

    hists = [("coffea", coffea_h), ("eventloop", el_h), ("fastframes", ff_h)]

    binning_ok = check_binning(hists)
    print_summary(hists)

    if binning_ok:
        ratio_el = make_ratio(el_h, coffea_h, "ratio_el")
        ratio_ff = make_ratio(ff_h, coffea_h, "ratio_ff")

        mean_el = sum(
            ratio_el.GetBinContent(i)
            for i in range(1, ratio_el.GetNbinsX() + 1)
            if coffea_h.GetBinContent(i) > 0
        ) / max(
            1,
            sum(
                1
                for i in range(1, coffea_h.GetNbinsX() + 1)
                if coffea_h.GetBinContent(i) > 0
            ),
        )
        mean_ff = sum(
            ratio_ff.GetBinContent(i)
            for i in range(1, ratio_ff.GetNbinsX() + 1)
            if coffea_h.GetBinContent(i) > 0
        ) / max(
            1,
            sum(
                1
                for i in range(1, coffea_h.GetNbinsX() + 1)
                if coffea_h.GetBinContent(i) > 0
            ),
        )
        print("\nMean bin ratio (where coffea > 0):")
        print(f"  EventLoop  / Coffea : {mean_el:.4f}")
        print(f"  FastFrames / Coffea : {mean_ff:.4f}")

    if not args.plot:
        return

    canvas = ROOT.TCanvas("comparison", "Framework Comparison", 800, 800)
    pad_top = ROOT.TPad("pad_top", "", 0, 0.3, 1, 1)
    pad_bot = ROOT.TPad("pad_bot", "", 0, 0, 1, 0.3)
    pad_top.SetBottomMargin(0.03)
    pad_top.SetTopMargin(0.08)
    pad_bot.SetTopMargin(0.03)
    pad_bot.SetBottomMargin(0.32)
    pad_top.Draw()
    pad_bot.Draw()

    # --- top pad ---
    pad_top.cd()
    pad_top.SetLogy()

    coffea_h.SetLineColor(ROOT.kBlue)
    coffea_h.SetLineWidth(2)
    coffea_h.GetYaxis().SetTitle("Events / bin")
    coffea_h.GetYaxis().SetTitleSize(0.05)
    coffea_h.GetYaxis().SetLabelSize(0.04)
    coffea_h.GetXaxis().SetLabelSize(0)
    coffea_h.Draw("HIST")

    el_h.SetLineColor(ROOT.kGreen + 2)
    el_h.SetLineWidth(2)
    el_h.SetLineStyle(2)
    el_h.Draw("HIST SAME")

    ff_h.SetLineColor(ROOT.kRed)
    ff_h.SetLineWidth(2)
    ff_h.SetLineStyle(3)
    ff_h.Draw("HIST SAME")

    legend = ROOT.TLegend(0.58, 0.68, 0.88, 0.88)
    legend.SetBorderSize(0)
    legend.AddEntry(coffea_h, "Coffea", "l")
    legend.AddEntry(el_h, "EventLoop", "l")
    legend.AddEntry(ff_h, "FastFrames", "l")
    legend.Draw()

    title_latex = ROOT.TLatex()
    title_latex.SetNDC()
    title_latex.SetTextSize(0.05)
    title_latex.DrawLatex(0.12, 0.93, "Photon p_{T}: Coffea vs EventLoop vs FastFrames")

    # --- bottom pad ---
    pad_bot.cd()

    if binning_ok:
        ratio_el.SetLineColor(ROOT.kGreen + 2)
        ratio_el.SetLineWidth(2)
        ratio_el.SetLineStyle(2)
        ratio_el.GetYaxis().SetTitle("Ratio to Coffea")
        ratio_el.GetYaxis().SetRangeUser(0.5, 1.5)
        ratio_el.GetYaxis().SetNdivisions(505)
        ratio_el.GetYaxis().SetTitleSize(0.11)
        ratio_el.GetYaxis().SetTitleOffset(0.45)
        ratio_el.GetYaxis().SetLabelSize(0.09)
        ratio_el.GetXaxis().SetTitle("Photon p_{T} [GeV]")
        ratio_el.GetXaxis().SetTitleSize(0.12)
        ratio_el.GetXaxis().SetLabelSize(0.10)
        ratio_el.Draw("HIST")

        ratio_ff.SetLineColor(ROOT.kRed)
        ratio_ff.SetLineWidth(2)
        ratio_ff.SetLineStyle(3)
        ratio_ff.Draw("HIST SAME")

        xmin = coffea_h.GetXaxis().GetXmin()
        xmax = coffea_h.GetXaxis().GetXmax()
        unity = ROOT.TLine(xmin, 1.0, xmax, 1.0)
        unity.SetLineColor(ROOT.kBlack)
        unity.SetLineWidth(1)
        unity.Draw()

        bot_legend = ROOT.TLegend(0.58, 0.78, 0.88, 0.95)
        bot_legend.SetBorderSize(0)
        bot_legend.SetTextSize(0.09)
        bot_legend.AddEntry(ratio_el, "EventLoop / Coffea", "l")
        bot_legend.AddEntry(ratio_ff, "FastFrames / Coffea", "l")
        bot_legend.Draw()
    else:
        msg = ROOT.TLatex()
        msg.SetNDC()
        msg.SetTextSize(0.08)
        msg.DrawLatex(0.15, 0.5, "Binning mismatch #font[52]{ratio unavailable}")

    canvas.SaveAs(args.plot)
    print(f"\nPlot saved to: {args.plot}")


if __name__ == "__main__":
    main()

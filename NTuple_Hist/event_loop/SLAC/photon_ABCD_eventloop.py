# Imports
import ROOT as r
import os


def photon_ABCD_eventloop(f_name):
    print(f_name)

    f = r.TFile(f_name, "RO")
    t = f.Get("analysis")
    h_baseline_pt = r.TH1F("baseline_pt", "baseline_pt", 10000, 0, 10000)

    h_notruth_it_ii_pt = r.TH1F(
        "notruth_istight_isiso_pt", "istight_isiso", 10000, 0, 10000
    )
    h_notruth_it_ni_pt = r.TH1F(
        "notruth_istight_noiso_pt", "istight_noiso", 10000, 0, 10000
    )
    h_notruth_nt_ii_pt = r.TH1F(
        "notruth_notight_isiso_pt", "notight_isiso", 10000, 0, 10000
    )
    h_notruth_nt_ni_pt = r.TH1F(
        "notruth_notight_noiso_pt", "notight_noiso", 10000, 0, 10000
    )

    eventcount = 0
    premindphicut = 0
    prejetscuts = 0
    postleadjetptcut = 0
    postmindphicut = 0
    postphotonpresel = 0
    totalevents = t.GetEntriesFast()
    for e in t:
        eventcount += 1
        if eventcount % 50000 == 0:
            print(f"Processed {eventcount:6d}/{totalevents} events")
        # if eventcount>10000:
        #    break

        # =================================================================
        # preselection
        #
        met = e.met_met_NOSYS
        met_phi = e.met_phi_NOSYS
        met_tlv = r.TLorentzVector()
        met_tlv.SetPtEtaPhiM(met, 0, met_phi, 0)

        # MET requirement, for now just look at low MET
        if met >= 250000.0:
            continue

        # veto events with leptons
        nelectrons = len(e.el_pt_NOSYS)
        nmuons = len(e.mu_pt_NOSYS)
        if (nelectrons + nmuons) > 0:
            continue

            ## overlap removal for vgamma samples
            # if not e.in_vgamma_overlap_7:
            #    continue

        prejetscuts += 1

        # no b-tagged jets, at least one jet with pT>100 GeV, no jets near MET
        jets = []
        mindphijetsmet = 999.0
        btags = 0
        leadjetpt = 0.0
        ljpt = max(e.jet_pt_NOSYS)
        if e.jet_pt_NOSYS[0] is None:
            print(e.jet_pt_NOSYS)
        for j in range(len(e.jet_pt_NOSYS)):
            tlv = r.TLorentzVector()
            tlv.SetPtEtaPhiM(e.jet_pt_NOSYS[j], e.jet_eta[j], e.jet_phi[j], 0)
            jets.append(tlv)
            mindphijetsmet = min(mindphijetsmet, abs(tlv.DeltaPhi(met_tlv)))
            if ord(e.jet_btag_select[j]) > 0:
                btags += 1
            # if int.from_bytes(bytes(e.jet_btag_select[j],'utf8'),'big')>0: btags+=1
            leadjetpt = max(leadjetpt, e.jet_pt_NOSYS[j])

        if ljpt != leadjetpt:
            print(e.jet_pt_NOSYS)
        if leadjetpt < 100000.0:
            continue

        postleadjetptcut += 1
        if btags > 0:
            continue

        premindphicut += 1

        if mindphijetsmet < 0.4:
            continue

        postmindphicut += 1

        # at least one loose photon with pT>10 GeV, no photons near jets
        photon_index = -1
        for p in range(len(e.ph_pt_NOSYS)):
            if not ord(e.ph_select_baseline_NOSYS[p]) > 0:
                continue

            tlv = r.TLorentzVector()
            tlv.SetPtEtaPhiM(e.ph_pt_NOSYS[p], e.ph_eta[p], e.ph_phi[p], 0)

            if tlv.Pt() < 10000.0:
                continue

            if (abs(tlv.Eta()) > 2.37) or (
                abs(tlv.Eta()) > 1.37 and abs(tlv.Eta()) < 1.52
            ):
                continue

            # not clear we need this, should be done via overlap removal?  not applying for now.
            # mindrphjet=999
            # for j in jets:
            #    mindrphjet=min(mindrphjet,tlv.DeltaPhi(j))
            # if mindrphjet<0.4: continue
            if not ord(e.ph_select_or_dR02Ph_NOSYS[p]) > 0:
                continue

            if (e.ph_isEM_NOSYS[p] & 0x45FC01) != 0:
                continue

            if photon_index < 0:
                photon_index = p

        if photon_index < 0:
            continue

        postphotonpresel += 1

        h_baseline_pt.Fill(e.ph_pt_NOSYS[photon_index] / 1000.0)

        # =================================================================

        # =================================================================
        # now we have the index of the photon to keep.  Now figure out if this is a truth-matched photon or not.
        # will need to fix this whenever Giordon et al decide on a truth matching scheme.
        # print(f"{e.ph_truthType[photon_index]} {e.ph_truthOrigin[photon_index]} {e.ph_truthpdgId[photon_index]}")
        # ph_truthmatch=((e.ph_truthType[photon_index]!=16) and (e.ph_truthType[photon_index]!=0))

        # the tight and isolated flags are easier:
        ph_tight = ord(e.ph_select_tightID_NOSYS[photon_index]) > 0
        ph_iso = ord(e.ph_select_tightIso_NOSYS[photon_index]) > 0

        if ph_tight and ph_iso:
            h_notruth_it_ii_pt.Fill(e.ph_pt_NOSYS[photon_index] / 1000.0)
        elif ph_tight and not ph_iso:
            h_notruth_it_ni_pt.Fill(e.ph_pt_NOSYS[photon_index] / 1000.0)
        elif not ph_tight and ph_iso:
            h_notruth_nt_ii_pt.Fill(e.ph_pt_NOSYS[photon_index] / 1000.0)
        elif not ph_tight and not ph_iso:
            h_notruth_nt_ni_pt.Fill(e.ph_pt_NOSYS[photon_index] / 1000.0)
    # =================================================================

    print(f"pre jets cuts {prejetscuts}")
    print(f"post leadjet  {postleadjetptcut}")
    print(f"pre mindphi   {premindphicut}")
    print(f"post mindphi  {postmindphicut}")
    print(f"post photonpr {postphotonpresel}")
    print(f"baseline:     {h_baseline_pt.GetSumOfWeights()}")

    print(f"A: !truth,  tight, !isolated: {h_notruth_it_ni_pt.GetSumOfWeights()}")
    print(f"B: !truth, !tight, !isolated: {h_notruth_nt_ni_pt.GetSumOfWeights()}")
    print(f"C: !truth,  tight,  isolated: {h_notruth_it_ii_pt.GetSumOfWeights()}")
    print(f"D: !truth, !tight,  isolated: {h_notruth_nt_ii_pt.GetSumOfWeights()}")


file_dir = (
    r"/sdf/data/atlas/u/qlei/user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root/"
)

files_full_path = [os.path.join(file_dir, i) for i in sorted(os.listdir(file_dir))]


for f in files_full_path:
    photon_ABCD_eventloop(f)

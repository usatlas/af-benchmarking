#include "TutorialClass/TutorialClass.h"

#include "FastFrames/DefineHelpers.h"
#include "FastFrames/UniqueSampleID.h"

ROOT::RDF::RNode TutorialClass::defineVariables(ROOT::RDF::RNode mainNode,
                                                const std::shared_ptr<Sample>& /*sample*/,
                                                const UniqueSampleID& /*id*/) {
  auto SortedTLVs = [](const std::vector<ROOT::Math::PtEtaPhiEVector>& fourVec,
      const std::vector<char>& selected) {
    return DefineHelpers::sortedPassedVector(fourVec,selected);
  };
  auto LeadingTLV = [](const std::vector<ROOT::Math::PtEtaPhiEVector>& fourVec) {
    return fourVec.empty() ? ROOT::Math::PtEtaPhiEVector{-999, -999, -999, -999} : fourVec.at(0);
  };
  auto tlvPtGEV = [this](const ROOT::Math::PtEtaPhiEVector& tlv) {
    return tlv.pt()/1.e3;
  };
  mainNode = MainFrame::systematicDefine(mainNode,
      "sorted_ph_pt_TLV_NOSYS",
      SortedTLVs,
      {"ph_TLV_NOSYS", "ph_select_tightID_NOSYS"});
  mainNode = MainFrame::systematicDefine(mainNode,
      "ph1_pt_NOSYS",
      LeadingTLV,
      {"sorted_ph_pt_TLV_NOSYS"});
  mainNode = MainFrame::systematicDefine(mainNode,
      "ph1_pt1_NOSYS",
      tlvPtGEV,
      {"ph1_pt_NOSYS"});

  // You can also use the UniqueSampleID object to apply a custom defione
  // based on the sample and the subsample
  //   sample->name(): is the name of the sample defined in the config
  //   id.dsid() returns sample DSID
  //   id.campaign() returns sample campaign
  //   id.simulation() return simulation flavour
  // You can use it in your functions to apply only per sample define

  return mainNode;
}

ROOT::RDF::RNode TutorialClass::defineVariablesNtuple(ROOT::RDF::RNode mainNode,
                                                      const std::shared_ptr<Sample>& /*sample*/,
                                                      const UniqueSampleID& /*id*/) {

  return mainNode;
}

ROOT::RDF::RNode TutorialClass::defineVariablesTruth(ROOT::RDF::RNode node,
                                                     const std::string& /*sample*/,
                                                     const std::shared_ptr<Sample>& /*sample*/,
                                                     const UniqueSampleID& /*sampleID*/) {
  return node;
}

ROOT::RDF::RNode TutorialClass::defineVariablesNtupleTruth(ROOT::RDF::RNode node,
                                                           const std::string& /*treeName*/,
                                                           const std::shared_ptr<Sample>& /*sample*/,
                                                           const UniqueSampleID& /*sampleID*/) {
  return node;
}

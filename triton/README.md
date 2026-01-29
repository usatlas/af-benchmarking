Reference URL for implementation: https://codimd.web.cern.ch/s/nibCTnjVI# .

Testing Triton from Athena derivation workflows for flavour-tagging algorithm
(models) that are loaded in on a Triton server deployed on UChicago AF via
kubernetes (k8s). Comparing between naive CPU running and deploying inference
running on a separate server.

## Single Model Compilation

On UChicago AF:

```
setupATLAS -q
asetup Athena,25.0.47
cmake -DATLAS_PACKAGE_FILTER_FILE=package_filters.txt -S /home/kratsg/tritonTest/athena/Projects/WorkDir -B /data/kratsg/tritonTest/build_singlemodel
cmake --build /data/kratsg/tritonTest/build_singlemodel -j 16
source /data/kratsg/tritonTest/build_singlemodel/*/setup.sh
```

The following patch was used

```diff
--- a/PhysicsAnalysis/JetTagging/FlavorTagInference/Root/NNSharingSvc.cxx
+++ b/PhysicsAnalysis/JetTagging/FlavorTagInference/Root/NNSharingSvc.cxx
@@ -75,34 +75,34 @@ namespace FlavorTagInference {
   // model paths to model names
   void NNSharingSvc::initTritonPathToName() {
     m_tritonPathToName = {
-      {"BTagging/20250527/GN3V01/antikt4empflow/network.onnx"
-       , "BTagging_network_93a858f5c730"},
-      {"BTagging/20231205/GN2v01/antikt4empflow/network_fold0.onnx"
-       , "BTagging_network_fold0_4812578c733e"},
-      {"BTagging/20231205/GN2v01/antikt4empflow/network_fold1.onnx"
-       , "BTagging_network_fold1_9280d77c131c"},
-      {"BTagging/20231205/GN2v01/antikt4empflow/network_fold2.onnx"
-       , "BTagging_network_fold2_25c6ad03db10"},
-      {"BTagging/20231205/GN2v01/antikt4empflow/network_fold3.onnx"
-       , "BTagging_network_fold3_0558b4924c49"},
-      {"BTagging/20250213/GN3V00/antikt4empflow/network.onnx"
-       , "BTagging_network_cce6be90efd1"},
-      {"BTagging/20250213/GN3PflowMuonsV00/antikt4empflow/network.onnx"
-       , "BTagging_network_d2138c4252e6"},
+      // {"BTagging/20250527/GN3V01/antikt4empflow/network.onnx"
+      //  , "BTagging_network_93a858f5c730"},
+      // {"BTagging/20231205/GN2v01/antikt4empflow/network_fold0.onnx"
+      //  , "BTagging_network_fold0_4812578c733e"},
+      // {"BTagging/20231205/GN2v01/antikt4empflow/network_fold1.onnx"
+      //  , "BTagging_network_fold1_9280d77c131c"},
+      // {"BTagging/20231205/GN2v01/antikt4empflow/network_fold2.onnx"
+      //  , "BTagging_network_fold2_25c6ad03db10"},
+      // {"BTagging/20231205/GN2v01/antikt4empflow/network_fold3.onnx"
+      //  , "BTagging_network_fold3_0558b4924c49"},
+      // {"BTagging/20250213/GN3V00/antikt4empflow/network.onnx"
+      //  , "BTagging_network_cce6be90efd1"},
+      // {"BTagging/20250213/GN3PflowMuonsV00/antikt4empflow/network.onnx"
+      //  , "BTagging_network_d2138c4252e6"},
 //      {"BTagging/20230705/gn2xv01/antikt10ufo/network.onnx" << This model is commented out because at the time of submitting
 //       , "BTagging_network_9f8aadb82b76"},                  << it did not work on Triton. The code falls back to direct ONNX reading
-      {"BTagging/20240925/GN2Xv02/antikt10ufo/network.onnx"
-       , "BTagging_network_09c2dddf15bf"},
-      {"BTagging/20250310/GN2XTauV00/antikt10ufo/network.onnx"
-       , "BTagging_network_e8d5e9a3059b"},
-      {"BTagging/20250912/GN3XPV01/antikt10ufo/network.onnx"
-       , "BTagging_network_08105bb8c1d6"},
+      // {"BTagging/20240925/GN2Xv02/antikt10ufo/network.onnx"
+      //  , "BTagging_network_09c2dddf15bf"},
+      // {"BTagging/20250310/GN2XTauV00/antikt10ufo/network.onnx"
+      //  , "BTagging_network_e8d5e9a3059b"},
+      // {"BTagging/20250912/GN3XPV01/antikt10ufo/network.onnx"
+      //  , "BTagging_network_08105bb8c1d6"},
       {"BTagging/20250912/GN3EPCLV01/antikt4empflow/network.onnx"
        , "BTagging_network_8085e6c5717c"},
-      {"JetCalibTools/CalibArea-00-04-83/CalibrationFactors/bbJESJMS_calibFactors_R22_MC20_CSSKUFO_bJR10v00Ext_20250212.onnx"
-       , "JetCalibTools_bbJESJMS_calibFactor_80138d800ac5"},
-      {"JetCalibTools/CalibArea-00-04-83/CalibrationFactors/bbJESJMS_calibFactors_R22_MC20MC23_CSSKUFO_bJR10v01_20250212.onnx"
-       , "JetCalibTools_bbJESJMS_calibFactor_fefb85f452f9"}
+      // {"JetCalibTools/CalibArea-00-04-83/CalibrationFactors/bbJESJMS_calibFactors_R22_MC20_CSSKUFO_bJR10v00Ext_20250212.onnx"
+      //  , "JetCalibTools_bbJESJMS_calibFactor_80138d800ac5"},
+      // {"JetCalibTools/CalibArea-00-04-83/CalibrationFactors/bbJESJMS_calibFactors_R22_MC20MC23_CSSKUFO_bJR10v01_20250212.onnx"
+      //  , "JetCalibTools_bbJESJMS_calibFactor_fefb85f452f9"}
     };
   }
 #endif
```

# TutorialClass

The FastFrames custom class used by the example FastFrames benchmark
(`custom_frame_name: "TutorialClass"` in `mc20e_example_config.yml`). It defines
the leading-photon `pT` variable the example histogram is filled from.

These are the sources of the copy UC builds, taken from the tree the UC-ODF
pilot used. `fetch_fastframes_sources.sh` copies them next to the FastFrames
clone and `build_fastframes.sh` builds them against it.

The same class is also kept as `../../TutorialClass.cc`; a test checks that the
two copies do not drift apart.

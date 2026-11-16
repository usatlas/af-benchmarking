# TTree to RNTuple Conversion

The NTuple-to-Histogram benchmarks read flat analysis ntuples: a TTree named
`analysis` in each file of a Rucio dataset under
`/data/kratsg/af-benchmarking/`. To benchmark
[RNTuple](https://root.cern/doc/master/group__tutorial__ntuple.html) alongside
TTree, every input file was converted once, and the RNTuple copies sit next to
the originals so both formats can be read from the same place.

## Where the RNTuple files are

Each dataset directory has a sibling with `_RNTuple` before the trailing
`.root`. File names are unchanged, and the RNTuple keeps the tree's name
(`analysis`):

| TTree dataset (original)                                    | RNTuple dataset                                                     |
| ----------------------------------------------------------- | ------------------------------------------------------------------- |
| `user.bhodkins.700402.Wmunugamma.mc20a.v2.1_ANALYSIS.root/` | `user.bhodkins.700402.Wmunugamma.mc20a.v2.1_ANALYSIS_RNTuple.root/` |
| `user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS.root/` | `user.bhodkins.700402.Wmunugamma.mc20e.v2.0_ANALYSIS_RNTuple.root/` |

The sum-of-weights histograms live in separate `_hist` datasets and were not
converted; the RNTuple benchmarks use the same sum-of-weights inputs as the
TTree ones.

## How the conversion works

The scripts are in `NTuple_Hist/rntuple_conversion/UC/`:

| File                          | Purpose                                                          |
| ----------------------------- | ---------------------------------------------------------------- |
| `convert_ttree_to_rntuple.py` | Converts one file and validates the result                       |
| `convert_job.sh`              | Condor job: sets up ROOT, picks the output path, runs the script |
| `convert.sub`                 | Condor submit file, one job per line of `inputs.txt`             |
| `inputs.txt`                  | Absolute paths of every TTree file to convert                    |

`convert_ttree_to_rntuple.py` uses ROOT's
[`RNTupleImporter`](https://root.cern/doc/master/ntpl008__import_8C.html), which
needs ROOT 6.34 or newer (the first release with a stable RNTuple on-disk
format). The jobs run in the `LCG_107a_ATLAS_2` view, the same one the
event-loop benchmarks use, which provides ROOT 6.34.04. In that release the
importer is still `ROOT.Experimental.RNTupleImporter`.

For each file, the script:

1. Imports the TTree into an RNTuple of the same name, written to
   `<output>.part`.
2. Copies every other top-level object from the input file unchanged. It refuses
   files with a second TTree or a subdirectory instead of silently dropping
   them.
3. Validates the RNTuple against the TTree in one RDataFrame event loop per
   file:
   - the entry counts match;
   - every scalar column has the same sum;
   - every vector column has the same total element count and element sum.

   A mismatch, an infinite sum, or a NaN sum on only one side fails the job and
   deletes the `.part` file.

4. Renames `<output>.part` to `<output>`, so a file under the final name has
   always passed validation.

`convert_job.sh` skips any input whose output already exists, so resubmitting
the whole list only converts what is missing.

## Running it

From a UChicago login node:

```bash
cd af-benchmarking/NTuple_Hist/rntuple_conversion/UC
condor_submit convert.sub
```

To convert a different dataset, list its files in `inputs.txt` (one absolute
path per line), for example:

```bash
find /data/<username>/<dataset>.root -name '*.root' -type f | sort > inputs.txt
```

Each job prints one summary line, such as:

```text
OK user.bhodkins.42165201._000002.ANALYSIS.root: 281597 entries, 240 columns checked, 314.1 MB -> 88.0 MB (0.28x), 114s; copied: nothing
```

## What to expect

On the Wmunugamma ntuples, about 240 branches per file (78 `vector<float>`, 99
`vector<char>`, and the rest scalars or other vectors):

- **Size:** each RNTuple file is about 0.27–0.28× the size of its TTree.
  RNTuple's defaults (zstd compression, plus type-aware encodings such as byte
  splitting) account for most of this.
- **Time:** about 2 minutes per 300 MB of input on one core, including
  validation, which reads both files.
- **Memory:** about 1 GB peak RSS.

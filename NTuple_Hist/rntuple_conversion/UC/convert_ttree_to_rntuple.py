#!/usr/bin/env python3
"""Convert a flat-ntuple TTree file into an RNTuple file with ROOT's RNTupleImporter.

The named TTree becomes an RNTuple of the same name. Every other top-level
object in the input (sum-of-weights histograms, metadata, ...) is copied over
unchanged, so the output can stand in for the input in the benchmarks.

After writing, the output is validated against the input: same entry count,
and the same per-column sum for every scalar arithmetic column, plus the
element count and element sum of every vector column (one RDataFrame event
loop per file). Any mismatch, an infinite sum, or a NaN sum on only one side
fails the conversion; a NaN sum on both sides is reported as a warning.

Requires ROOT >= 6.34 (first release with the stable RNTuple on-disk format).
"""

import argparse
import math
import os
import sys
import time

import ROOT

SCALAR_TYPES = {
    "bool",
    "char",
    "unsigned char",
    "short",
    "unsigned short",
    "int",
    "unsigned int",
    "long",
    "unsigned long",
    "long long",
    "unsigned long long",
    "float",
    "double",
    "Bool_t",
    "Char_t",
    "UChar_t",
    "Short_t",
    "UShort_t",
    "Int_t",
    "UInt_t",
    "Long64_t",
    "ULong64_t",
    "Float_t",
    "Double_t",
    "std::int8_t",
    "std::uint8_t",
    "std::int16_t",
    "std::uint16_t",
    "std::int32_t",
    "std::uint32_t",
    "std::int64_t",
    "std::uint64_t",
}


def import_tree(src, tree, dst):
    importer = ROOT.Experimental.RNTupleImporter.Create(src, tree, dst)
    importer.SetIsQuiet(True)
    importer.Import()


def copy_other_keys(src, tree, dst):
    """Copy every top-level object except the converted tree, highest cycle only."""
    fin = ROOT.TFile.Open(src, "READ")
    fout = ROOT.TFile.Open(dst, "UPDATE")
    copied = []
    seen = set()
    for key in fin.GetListOfKeys():
        name = key.GetName()
        if name == tree or name in seen:
            continue
        seen.add(name)
        obj = key.ReadObj()
        if obj.InheritsFrom("TTree"):
            # A second TTree would need its own import; refuse rather than drop it.
            raise RuntimeError(f"{src}: extra TTree '{name}' is not converted")
        if obj.InheritsFrom("TDirectory"):
            raise RuntimeError(f"{src}: subdirectory '{name}' is not handled")
        fout.cd()
        obj.Write(name)
        copied.append(f"{name} ({key.GetClassName()})")
    fout.Close()
    fin.Close()
    return copied


def is_vector(type_name):
    return "vector<" in type_name or "RVec<" in type_name


def column_sums(df, scalars, vectors):
    """Book every sum on one RDataFrame so the file is read in a single event loop.

    Scalars: sum of the value over entries. Vectors: total element count and
    sum of all elements over entries; elements are accumulated as double so
    vector<char> and friends cannot overflow their own type.
    """
    results = {c: df.Sum(c) for c in scalars}
    for i, c in enumerate(vectors):
        n, s = f"__n{i}", f"__s{i}"
        df = df.Define(n, f"static_cast<double>({c}.size())").Define(
            s, f"ROOT::VecOps::Sum({c}, 0.)"
        )
        results[f"{c} [n]"] = df.Sum(n)
        results[f"{c} [sum]"] = df.Sum(s)
    count = df.Count()
    return count.GetValue(), {c: r.GetValue() for c, r in results.items()}


def validate(src, dst, tree):
    df_tree = ROOT.RDataFrame(tree, src)
    types = {str(c): str(df_tree.GetColumnType(c)) for c in df_tree.GetColumnNames()}
    scalars = [c for c, t in types.items() if t in SCALAR_TYPES]
    vectors = [c for c, t in types.items() if is_vector(t)]
    unchecked = sorted(set(types) - set(scalars) - set(vectors))
    n_tree, s_tree = column_sums(df_tree, scalars, vectors)
    n_ntpl, s_ntpl = column_sums(ROOT.RDataFrame(tree, dst), scalars, vectors)
    problems = [f"{c}: type {types[c]} has no validation rule" for c in unchecked]
    if n_tree != n_ntpl:
        problems.append(f"entries differ: TTree {n_tree} vs RNTuple {n_ntpl}")
    for c in s_tree:
        a, b = s_tree[c], s_ntpl[c]
        if math.isnan(a) and math.isnan(b):
            # A NaN in the input propagates to the sum; matching NaN is not a conversion error.
            print(
                f"WARNING {src}: {c} sums to NaN in both TTree and RNTuple",
                file=sys.stderr,
            )
        elif not (math.isfinite(a) and math.isfinite(b)):
            problems.append(f"{c}: non-finite sum (TTree {a}, RNTuple {b})")
        elif not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9):
            problems.append(f"{c}: sum differs (TTree {a}, RNTuple {b})")
    return n_tree, len(scalars) + len(vectors), problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", help="input ROOT file holding the TTree")
    parser.add_argument("output", help="output ROOT file to write the RNTuple to")
    parser.add_argument(
        "--tree", default="analysis", help="TTree name (default: analysis)"
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output"
    )
    args = parser.parse_args()

    if os.path.exists(args.output):
        if not args.force:
            sys.exit(f"refusing to overwrite {args.output} (pass --force)")
        os.remove(args.output)

    tmp = args.output + ".part"
    if os.path.exists(tmp):
        os.remove(tmp)

    start = time.monotonic()
    import_tree(args.input, args.tree, tmp)
    copied = copy_other_keys(args.input, args.tree, tmp)
    entries, ncols, problems = validate(args.input, tmp, args.tree)
    elapsed = time.monotonic() - start

    if problems:
        os.remove(tmp)
        for p in problems:
            print(f"VALIDATION FAILED {args.input}: {p}", file=sys.stderr)
        sys.exit(1)

    # Rename only after validation, so a partial or bad file never appears under the final name.
    os.replace(tmp, args.output)
    in_mb = os.path.getsize(args.input) / 1e6
    out_mb = os.path.getsize(args.output) / 1e6
    print(
        f"OK {os.path.basename(args.input)}: {entries} entries, {ncols} columns checked, "
        f"{in_mb:.1f} MB -> {out_mb:.1f} MB ({out_mb / in_mb:.2f}x), {elapsed:.0f}s; "
        f"copied: {', '.join(copied) or 'nothing'}"
    )


if __name__ == "__main__":
    main()

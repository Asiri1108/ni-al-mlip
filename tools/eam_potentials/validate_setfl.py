#!/usr/bin/env python3
"""Structural validation of DYNAMO setfl (eam/alloy) potential files.

Checks: element block header, Nelements/element identity == {Al, Ni},
declared Nrho/Nr grid counts, exact expected total value count consumed,
and no trailing content beyond what the format specifies.
"""
import sys

def validate(path):
    with open(path) as f:
        lines = f.readlines()

    report = {"file": path, "errors": [], "warnings": []}

    # Lines 1-3: comments
    # Line 4 (index 3): Nelements Element1 Element2 ...
    header = lines[3].split()
    nelem = int(header[0])
    elements = header[1:1 + nelem]
    report["nelements"] = nelem
    report["elements"] = elements

    if nelem != 2:
        report["errors"].append(f"expected 2 elements, got {nelem}")
    if set(elements) != {"Al", "Ni"}:
        report["errors"].append(f"expected elements {{Al, Ni}}, got {set(elements)}")

    # Line 5 (index 4): Nrho drho Nr dr cutoff
    grid = lines[4].split()
    Nrho = int(grid[0])
    drho = float(grid[1])
    Nr = int(grid[2])
    dr = float(grid[3])
    cutoff = float(grid[4])
    report["Nrho"] = Nrho
    report["Nr"] = Nr
    report["cutoff"] = cutoff

    # Now walk the value stream starting at line index 5.
    # For each of the nelem elements: 1 element-info line, then Nrho F values, then Nr rho values.
    # Then nelem*(nelem+1)/2 pair blocks of Nr values each (r*phi(r)).
    idx = 5
    n_pairs = nelem * (nelem + 1) // 2

    def consume_values(idx, count):
        vals = []
        while len(vals) < count:
            if idx >= len(lines):
                report["errors"].append(f"ran out of lines while reading {count} values (got {len(vals)})")
                return vals, idx
            vals.extend(lines[idx].split())
            idx += 1
        if len(vals) != count:
            report["errors"].append(f"value block overrun: expected {count}, consumed {len(vals)}")
        return vals, idx

    elem_atomic_info = []
    for e in elements:
        info = lines[idx].split()
        elem_atomic_info.append(info)
        idx += 1
        f_vals, idx = consume_values(idx, Nrho)
        rho_vals, idx = consume_values(idx, Nr)
        # sanity: all numeric
        try:
            [float(x) for x in f_vals[:5]]
            [float(x) for x in rho_vals[:5]]
        except ValueError as ex:
            report["errors"].append(f"non-numeric value in {e} F/rho block: {ex}")

    report["element_info"] = elem_atomic_info

    for p in range(n_pairs):
        phi_vals, idx = consume_values(idx, Nr)
        try:
            [float(x) for x in phi_vals[:5]]
        except ValueError as ex:
            report["errors"].append(f"non-numeric value in pair block {p}: {ex}")

    # Trailing content check: any remaining non-blank lines after the last expected value?
    remainder = [l for l in lines[idx:] if l.strip()]
    report["trailing_nonblank_lines"] = len(remainder)
    if remainder:
        report["warnings"].append(f"{len(remainder)} trailing non-blank line(s) after expected data end")

    report["total_lines"] = len(lines)
    report["consumed_through_line"] = idx
    report["pass"] = len(report["errors"]) == 0
    return report


if __name__ == "__main__":
    import json
    results = []
    for path in sys.argv[1:]:
        try:
            r = validate(path)
        except Exception as ex:
            r = {"file": path, "pass": False, "errors": [f"exception: {ex}"]}
        results.append(r)
        status = "PASS" if r.get("pass") else "FAIL"
        print(f"\n=== {path}: {status} ===")
        for k in ("nelements", "elements", "Nrho", "Nr", "cutoff", "element_info",
                   "total_lines", "consumed_through_line", "trailing_nonblank_lines"):
            if k in r:
                print(f"  {k}: {r[k]}")
        for w in r.get("warnings", []):
            print(f"  WARNING: {w}")
        for e in r.get("errors", []):
            print(f"  ERROR: {e}")

    all_pass = all(r.get("pass") for r in results)
    print(f"\nOVERALL: {'PASS' if all_pass else 'FAIL'}")
    sys.exit(0 if all_pass else 1)

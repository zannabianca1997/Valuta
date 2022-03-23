#!/bin/env python3

import csv
import json
from pathlib import Path
from typing import List
import numpy as np
from numpy.random import default_rng

# ---            Programma di valutazione verifica:               ---
# --- Estrazione MonteCarlo delle difficoltà e delle preparazioni ---

# - results scanning


def get_results(inp_dir: Path):
    with open(inp_dir / "siminfo.json") as inp:
        data = json.load(inp)
    questions: List[str] = data["questions"]
    students: List[str] = data["students"]

    results = np.zeros((len(students), len(questions)), dtype=int)
    with open(inp_dir / "results.csv") as inp:
        reader = csv.reader(inp)
        # skip first line
        header = next(reader)
        # read others
        for line in reader:
            student = line[0]
            for j, res in enumerate(line[1:], start=1):
                try:
                    results[students.index(student.strip()), questions.index(
                        header[j].strip())] = 2*int(res) - 1
                except Exception as e:
                    raise ValueError(
                        f"Error while parsing {str(inp_dir)!r}, line {reader.line_num}, item {j+1}") from e

    if np.any(results**2 != 1):
        raise ValueError("Results are not complete")

    return results


def get_setup(inp_dir: Path):
    with open(inp_dir / "simsetup.json") as inp:
        return json.load(inp)

# - weight function


def get_g(results):
    def g(alpha, ds, ps):
        dss, pss = np.meshgrid(ds, ps)
        return np.prod(2/(1 + np.exp(alpha * results * (dss - pss))))
    return g

# - MonteCarlo random walk


def montecarlo(results, SEED, DELTA, ALPHADELTA, THERM_LEN, SIM_LEN, **kwargs):
    # use metropolis algorithm
    ds_log = []
    ps_log = []
    alpha_log = []

    ds = np.full(results.shape[1], 0.5)
    ps = np.full(results.shape[0], 0.5)
    alpha = 0

    accepted = 0

    rng = default_rng(SEED)

    g = get_g(results)

    oldg = g(alpha, ds, ps)

    for i in range(THERM_LEN + SIM_LEN):
        # slightly change the state
        nds = ds + DELTA * (2*rng.random(ds.shape)-1)
        nps = ps + DELTA * (2*rng.random(ps.shape)-1)
        nalpha = alpha + ALPHADELTA * (2*rng.random()-1)

        # asure bounds
        mask = nds > 1
        nds[mask] = 1-nds[mask]
        mask = nds < 0
        nds[mask] = -nds[mask]
        mask = nps > 1
        nps[mask] = 1-nps[mask]
        mask = nps < 0
        nps[mask] = -nps[mask]
        nalpha = np.abs(nalpha)

        # calculate new weight
        newg = g(nalpha, nds, nps)

        # reject step
        if newg > oldg or oldg * rng.random() < newg:
            # accepted
            ds = nds
            ps = nps
            alpha = nalpha
            oldg = newg

            accepted += 1

        # log the data
        if i >= THERM_LEN:
            ds_log.append(ds)
            ps_log.append(ps)
            alpha_log.append(alpha)

    ds_log = np.array(ds_log)
    ps_log = np.array(ps_log)
    alpha_log = np.array(alpha_log)

    accept_ratio = accepted / SIM_LEN

    return ds_log, ps_log, alpha_log, accept_ratio

# -- saving data


def save(out_dir, ds_log, ps_log, alpha_log, accept_ratio):
    with open(out_dir / "montecarlo.npz", "wb") as out:
        np.savez(
            out,
            ds_log=ds_log,
            ps_log=ps_log,
            alpha_log=alpha_log,
            accept_ratio=accept_ratio
        )


def main(work_dir):
    results = get_results(work_dir)
    setup = get_setup(work_dir)
    arrays = montecarlo(results, **setup)
    save(work_dir, *arrays)


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))

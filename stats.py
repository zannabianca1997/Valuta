#!/bin/env python3

import json
from pathlib import Path
import numpy as np

# --- Programma di valutazione verifica: ---
# ---         Analisi dei dati           ---

# -- loading data


def get_arrays(inp_dir: Path):
    with open(inp_dir / "montecarlo.npz", "rb") as inp:
        data = np.load(inp)
        return data["ps_log"], data["ds_log"],  data["alpha_log"], float(data["accept_ratio"])


def get_perfect_scorer_pts(inp_dir: Path):
    with open(inp_dir/"simsetup.json") as inp:
        return json.load(inp)["PERFECT_SCORER_PTS"]


# -- data analysis

# means and stdev
def mean_and_std(log):
    return np.mean(log, axis=0), np.std(log, axis=0)

# perfect and worse scorer data


def get_extremal_score(extreme: int, ds_log, alpha_log, PERFECT_SCORER_PTS):
    ps_lin = np.linspace(0, 1, PERFECT_SCORER_PTS)

    Pps = np.ones((PERFECT_SCORER_PTS, ds_log.shape[0]))
    for i in range(ds_log.shape[1]):
        dss, pss = np.meshgrid(ds_log[:, i], ps_lin)
        Pps *= (2/(1 + np.exp(extreme * alpha_log * (dss - pss))))
    Pps = Pps.sum(axis=1)
    Pps /= Pps.sum()

    mean = (Pps*ps_lin).sum()
    std = np.sqrt((Pps*(ps_lin**2)).sum() - mean**2)

    return mean, std


# correlations

def get_corrs(log, log_means):
    corrs = np.empty((log.shape[1],)*2)
    for i in range(log.shape[1]):
        for j in range(i+1, log.shape[1]):
            corrs[i, j] = np.mean(log[:, i] * log[:, j]) - \
                log_means[i] * log_means[j]
    p_corr_list = [corrs[i, j]
                   for i in range(log.shape[1])
                   for j in range(i+1, log.shape[1])]
    return corrs, np.mean(p_corr_list), np.std(p_corr_list)


def do_stats(inp_dir):
    ps_log, ds_log,  alpha_log, accept_ratio = get_arrays(inp_dir)
    PERFECT_SCORER_PTS = get_perfect_scorer_pts(inp_dir)

    p_means, p_stds = mean_and_std(ps_log)
    d_means, d_stds = mean_and_std(ds_log)
    alpha_stat = mean_and_std(alpha_log)

    perf_score = get_extremal_score(1, ds_log, alpha_log, PERFECT_SCORER_PTS)
    worse_score = get_extremal_score(-1, ds_log, alpha_log, PERFECT_SCORER_PTS)

    p_corrs, p_corr_mean, p_corr_std = get_corrs(ps_log, p_means)
    d_corrs, d_corr_mean, d_corr_std = get_corrs(ds_log, d_means)

    return {
        "accept_ratio": accept_ratio,

        "scores": list(zip(p_means, p_stds)),

        "perfect_score": perf_score,
        "worse_score": worse_score,

        "scores_corrs": (
            [[p_corrs[j, i] for j in range(i)]
             for i in range(ps_log.shape[1])],
            p_corr_mean, p_corr_std),

        "difficulties": list(zip(d_means, d_stds)),
        "difficulties_corrs": (
            [[d_corrs[j, i] for j in range(i)]
             for i in range(ds_log.shape[1])],
            d_corr_mean, d_corr_std),

        "alpha": alpha_stat
    }


def save(out_dir, stat_data):
    with open(out_dir / "stats.json", "w") as out:
        json.dump(stat_data, out, indent=2)


def main(argv):
    work_dir = Path(argv[1])
    stats = do_stats(work_dir)
    save(work_dir, stats)


if __name__ == "__main__":
    import sys
    main(sys.argv)

#!/bin/env python3

from cgi import test
from math import gamma
from pathlib import Path
import yaml
import json

# --- Programma di valutazione verifica: ---
# ---          Report testuale           ---


# - load data

def get_setup(inp_dir: Path):
    with open(inp_dir / "simsetup.json") as inp:
        return json.load(inp)


def get_stats(inp_dir: Path):
    with open(inp_dir / "stats.json") as inp:
        return json.load(inp)


def get_info(inp_dir: Path):
    with open(inp_dir / "siminfo.json") as inp:
        return json.load(inp)


def get_votes(inp_dir: Path):
    with open(inp_dir / "votes.json") as inp:
        return json.load(inp)


def get_comments(inp_dir: Path):
    with open(inp_dir / "comments.yml") as inp:
        return yaml.load(inp, Loader=yaml.SafeLoader)


def get_data(inp_dir: Path):
    return {
        "setup": get_setup(inp_dir),
        "stats": get_stats(inp_dir),
        "info": get_info(inp_dir),
        "votes": get_votes(inp_dir),
        "comments": get_comments(inp_dir)
    }

# - printing


def make_student_table(students, scores, votes, comments):
    name_len = max(len(name) for name in students)
    return "\n".join(
        f"    {name.ljust(name_len)}: {p:6.2%} +- {p_std:6.2%} -> {v:4.2} +- {v_std:4.2}" +
        (
            "" if not comments[name]["short"].strip()
            else f" ({comments[name]['short']})"
        )
        for name, (p, p_std), (v, v_std) in zip(students, scores, votes)
    )


def make_question_table(questions, difficulties):
    qname_len = max(len(qname) for qname in questions)
    return "\n".join(
        f"    {qname.ljust(qname_len)}: {d:6.2} +- {std:6.2}"
        for qname, (d, std) in zip(questions, difficulties)
    )


def make_corrs_table(corr_data, names, CORRS_WARN_THRESHOLD):
    table_stride = max(9+2, max(len(name) for name in names))
    corrs, corr_mean, corr_std = corr_data
    return "    " + " "*(table_stride+1) + " ".join(name.ljust(table_stride) for name in names) + "\n" \
        + "\n".join(
            f"    {name.ljust(table_stride)} " +
            " "*(i+1)*(table_stride+1) +
        " ".join((f" {corrs[j][i]:9.2e} "
                  if abs(corrs[j][i] - corr_mean) < corr_std*CORRS_WARN_THRESHOLD
                  else f"({corrs[j][i]:9.2e})").rjust(table_stride)
                 for j in range(i+1, len(names)))
            for i, name in enumerate(names)
    )


REPORT_FMT = """Result report for "{test_name}":
Test given to class {test_class} on {test_date}.
Arguments:
    {test_argument}
Test description:
    {test_description}

Scores:
{p_table}
- perfect score is {perf_mean:.2%} +- {perf_std:.2%}, worse score is {worse_mean:.2%} +- {worse_std:.2%}
- gamma used is {gamma}, votes goes from {MIN_VOTE} to {MAX_VOTE}

Score correlations (marked outlier of more than {CORRS_WARN_THRESHOLD} sigmas):
{p_corr_table}

Difficulties:
{d_table}

Difficulty correlations (marked outlier of more than {CORRS_WARN_THRESHOLD} sigmas):
{d_corr_table}

Technical data:
    Setup used:
        SEED={SEED}

        DELTA={DELTA}
        ALPHADELTA={ALPHADELTA}
        THERM_LEN={THERM_LEN}
        SIM_LEN={SIM_LEN}

    Accept ratio: {accept_ratio:.0%}
    Alpha: {alpha_mean:.2f} +- {alpha_std:.2}"""


def get_report(data):
    return REPORT_FMT.format(
        test_name=data["info"]["test"]["name"],
        test_class=data["info"]["test"]["class"],
        test_date=data["info"]["test"]["date"],
        test_argument=data["info"]["test"]["argument"],
        test_description=data["info"]["test"]["description"],


        p_table=make_student_table(
            data["info"]["students"],
            data["stats"]["scores"],
            data["votes"]["votes"],
            data["comments"]),
        perf_mean=data["stats"]["perfect_score"][0],
        perf_std=data["stats"]["perfect_score"][1],
        worse_mean=data["stats"]["worse_score"][0],
        worse_std=data["stats"]["worse_score"][1],
        gamma=data["votes"]["gamma"],

        p_corr_table=make_corrs_table(
            data["stats"]["scores_corrs"],
            data["info"]["students"],
            data["setup"]["CORRS_WARN_THRESHOLD"]),

        d_table=make_question_table(
            data["info"]["questions"],
            data["stats"]["difficulties"]),

        d_corr_table=make_corrs_table(
            data["stats"]["difficulties_corrs"],
            data["info"]["questions"],
            data["setup"]["CORRS_WARN_THRESHOLD"]),

        ** data["setup"],
        accept_ratio=data["stats"]["accept_ratio"],
        alpha_mean=data["stats"]["alpha"][0],
        alpha_std=data["stats"]["alpha"][1],
    )


def save(out_dir: Path, report: str):
    with open(out_dir/"report.txt", "w") as out:
        out.write(report)


def main(work_dir: Path):
    save(work_dir, get_report(get_data(work_dir)))


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))

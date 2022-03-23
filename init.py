#!/bin/env python3


import csv
import json
from pathlib import Path, PurePath
from sys import stderr
from typing import Any, Dict, List, Tuple
import yaml

# --- Programma di valutazione verifica: ---
# ---  Inizializzazione della directory  ---

DEFAULTS = {
    # - montecarlo
    "SEED": 35,

    "DELTA": 0.25,
    "ALPHADELTA": 1,

    "THERM_LEN": 1000,
    "SIM_LEN": 10000,

    # - stats
    "PERFECT_SCORER_PTS": 100,

    # - voting
    "GAMMA_START": 1,
    "MIN_VOTE": 1,
    "MAX_VOTE": 10,

    # - report
    "CORRS_WARN_THRESHOLD": 2.
}

# - arg checking


def check_args(argv):
    if len(argv) not in {2, 3}:
        print(f"Usage: {argv[0]} INPUTFILE.YML [OUTPUTDIR]", file=stderr)
        exit(1)


def get_input_f(argv) -> Path:
    input_f = Path(argv[1])
    if not input_f.is_file():
        print(f"{input_f} is not a file", file=stderr)
        exit(1)
    return input_f

# - results scanning


def parse_input(input_f) -> Tuple[Dict[str, Any], List[str], List[str]]:
    with open(input_f) as inp:
        data = yaml.load(inp, Loader=yaml.SafeLoader)
    return data["test"], data["students"], data["questions"]


# - deducing output

def get_output_dir(argv, input_f: PurePath, test_name: str) -> Path:
    if len(argv) == 3:
        output_dir = Path(argv[2])
    else:
        output_dir = Path(input_f.with_name(test_name))

    if output_dir.exists():
        print(f"{output_dir} exist", file=stderr)
        exit(1)
    return output_dir

# - saving data


def create_dir(output_dir: Path, metadata: Dict[str, Any], students: List[str], questions: List[str]):
    output_dir.mkdir()

    # info files
    with open(output_dir/"siminfo.json", "w") as out:
        json.dump(
            {
                "test": metadata,
                "students": students,
                "questions": questions,
            },
            out, indent=2
        )
    with open(output_dir/"simsetup.json", "w") as out:
        json.dump(DEFAULTS, out, indent=2)

    # file to edit
    with open(output_dir/"comments.yml", "w") as out:
        yaml.dump(
            {name: {
                "short": "",
                "long": "",
            } for name in students},
            out,
            Dumper=yaml.SafeDumper,
            sort_keys=False
        )
    with open(output_dir/"results.csv", "w") as out:
        writer = csv.writer(out)
        writer.writerow([metadata["name"]] + questions)
        writer.writerows([[name] + [""] * len(questions) for name in students])


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split()).title()


def main(argv):
    check_args(argv)
    input_f = get_input_f(argv)
    metadata, students, questions = parse_input(input_f)
    output_dir = get_output_dir(argv, input_f, metadata["name"])
    students = sorted(normalize_name(name) for name in students)
    questions = [q_name.strip() for q_name in questions]
    create_dir(output_dir, metadata, students, questions)


if __name__ == "__main__":
    import sys
    main(sys.argv)

#!/bin/env python3

import yaml
import json
from pathlib import Path

from gamma import get_students

# ---         Programma di valutazione verifica:           ---
# --- Preparazione del documento di valutazione definitivo ---


def get_comments(inp_dir: Path):
    with open(inp_dir / "comments.yml") as inp:
        return yaml.load(inp, Loader=yaml.SafeLoader)


def get_votes(inp_dir: Path, students):
    with open(inp_dir / "votes.json") as inp:
        data = json.load(inp)
    return {student: (vote, std) for student, (vote, std) in zip(students, data["votes"])}


def find_similar(student, votes):
    vote, std = votes[student]
    return [other_student for other_student, (other_vote, other_std) in votes.items() if (abs(vote - other_vote)**2 < std**2 + other_std**2)]


def get_finalizing_struct(inp_dir: Path):
    comments = get_comments(inp_dir)
    students = get_students(inp_dir)
    votes = get_votes(inp_dir, students)
    return {
        student: {
            "comment": comments[student],
            "suggested vote": f"{votes[student][0]} +- {votes[student][1]}",
            "similar votes": find_similar(student, votes),
            "final_vote": None
        }
        for student in students
    }


def main(argv):
    work_dir = Path(argv[1])
    finalizing_struct = get_finalizing_struct(work_dir)
    with open(work_dir / "final.yml", "w") as out:
        yaml.dump(finalizing_struct, out,
                  Dumper=yaml.SafeDumper, sort_keys=False)


if __name__ == "__main__":
    import sys
    main(sys.argv)

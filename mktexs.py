#!/bin/env python3

from datetime import date
import json
from pathlib import Path
import re
from statistics import mean, variance
import unicodedata
from warnings import warn
import yaml
from typing import Dict, List, Tuple
from os import chdir
from subprocess import Popen, DEVNULL
from shutil import copyfile

from montecarlo import get_results

# --- Programma di valutazione verifica: ---
# ---       Preparazione dei report      ---


LATEX_COMMAND = "pdflatex"


def get_infos(inp_dir: Path):
    with open(inp_dir / "siminfo.json") as inp:
        data = json.load(inp)
    return data["test"], data["students"], data["questions"]


def get_votes_and_comments(inp_dir: Path):
    with open(inp_dir / "final.yml") as inp:
        data = yaml.load(inp, Loader=yaml.SafeLoader)

    return {name: data[name]["final_vote"] for name in data}, {name: data[name]["comment"]["long"] for name in data}


def get_difficulties(inp_dir: Path, questions: List[str]) -> List[Tuple[str, str]]:
    with open(inp_dir / "stats.json") as inp:
        data = json.load(inp)
    difficulties = [difficulty for difficulty, _ in data["difficulties"]]
    diff_mean, diff_std = mean(difficulties), variance(difficulties)
    low_bar = diff_mean - 2*diff_std
    high_bar = diff_mean + 2*diff_std
    difficulties = (("\\difficultlow" if difficulty < low_bar else
                     ("\\difficultmedium" if difficulty < high_bar else
                      "\\difficulthigh"))
                    for difficulty in difficulties
                    )
    return list(zip(questions, difficulties))


def format_vote(vote: float) -> str:
    if vote is None:
        warn("Missing Vote!")
        return "Voto mancante"
    vote = int(4*vote + 0.5)
    ipart = vote // 4
    fpart = vote % 4
    if fpart == 0:
        return f"{ipart}"
    elif fpart == 1:
        return f"{ipart}+"
    elif fpart == 2:
        return f"{ipart} \\textonehalf"
    else:
        return f"{ipart+1}-"


def format_result(result):
    return '\\cmark' if result > 0 else '\\xmark'


def get_tex_subs(inp_dir) -> Dict[str, Dict[str, str]]:
    test_data, students, questions = get_infos(inp_dir)
    votes, comments = get_votes_and_comments(inp_dir)
    questions = get_difficulties(inp_dir, questions)
    results = get_results(inp_dir)

    return {
        student: {
            "@TestName@": test_data["name"],
            "@Class@": test_data["class"],
            "@TestDate@": test_data["date"],
            "@Arguments@": test_data["argument"],
            "@Description@": test_data["description"],

            "@Name@": student,
            "@Vote@": format_vote(votes[student]),
            "@Comment@": comments[student] if student in comments else "",

            "@TableBody@": "\n".join(
                f"{question} & {difficulty} & {format_result(result)} \\\\"
                for (question, difficulty), result in zip(questions, results[i])
            ),

            "@EvaluationDate@": date.today().strftime("%d/%m/%Y"),
        }

        for i, student in enumerate(students)
    }


def get_tex_stub(script_dir) -> str:
    with open(script_dir / "teststub.tex.stub") as inp:
        return inp.read()


def replace_all(string: str, subs: Dict[str, str]) -> str:
    for initial, final in subs.items():
        string = string.replace(initial, final)
    return string


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode(
            'ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def save(out_dir: Path, texs: Dict[str, str]):
    texs_path = out_dir / "texs" / "sources"
    texs_path.mkdir(parents=True, exist_ok=True)
    for student, tex in texs.items():
        with open((texs_path / slugify(student)).with_suffix(".tex"), "w") as out:
            out.write(tex)


def maketexs(argv):
    work_dir = Path(argv[1])
    subs = get_tex_subs(work_dir)
    stub = get_tex_stub(Path(argv[0]).parent)
    texs = {
        student: replace_all(stub, sub)
        for student, sub in subs.items()
    }
    save(work_dir, texs)


class Chdir:
    def __init__(self, dir_name):
        self.dir_name = dir_name

    def __enter__(self):
        self.original_dir = Path.cwd()
        chdir(self.dir_name)
        return self.dir_name

    def __exit__(self, exc_type, exc_value, traceback):
        chdir(self.original_dir)


def runtex(work_dir: Path):
    work_dir = work_dir / "texs"

    sources = (work_dir / "sources").glob("*.tex")
    run_dir = work_dir / "build"
    out_dir = work_dir / "output"

    run_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)

    tex_processes: List[Tuple[Path, Popen]] = []

    # starting tex engines...
    for file in sources:
        print(f"Running {LATEX_COMMAND} on {file.name}...")
        local_dir = run_dir / file.stem
        local_dir.mkdir(exist_ok=True)
        copyfile(file, local_dir / file.name)

        with Chdir(local_dir):
            tex_processes.append(
                (
                    file,
                    local_dir,
                    Popen([
                        LATEX_COMMAND,
                        file.name
                    ],
                        stdin=DEVNULL,
                        stdout=DEVNULL
                    )
                )
            )

    # collecting results
    for file, local_dir, process in tex_processes:
        print(f"Collecting {file.with_suffix('.pdf').name}")
        process.wait()

        out_file = (local_dir / file.name).with_suffix('.pdf')
        if not out_file.exists():
            warn(f"{out_file.name} was not generated...")
        else:
            copyfile(out_file, out_dir / out_file.name)


def main(argv):
    maketexs(argv)
    runtex(Path(argv[1]))


if __name__ == "__main__":
    import sys
    main(sys.argv)

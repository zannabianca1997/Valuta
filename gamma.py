#!/bin/env python3

import cmd
import json
from operator import le
from typing import IO, Dict, Union
import yaml
from pathlib import Path
import numpy as np
import readline
from init import normalize_name

from stats import get_arrays

# --- Programma di valutazione verifica: ---
# ---            gamma REPL              ---

# - load data


def get_ps_log(inp_dir: Path):
    ps_log, _, _, _ = get_arrays(inp_dir)
    return ps_log


def get_setup(inp_dir: Path):
    with open(inp_dir / "simsetup.json") as inp:
        data = json.load(inp)
    return data["MAX_VOTE"], data["MIN_VOTE"], data["GAMMA_START"]


def get_extremal_means(inp_dir: Path):
    with open(inp_dir / "stats.json") as inp:
        data = json.load(inp)
    return data["perfect_score"][0], data["worse_score"][0]


def get_students(inp_dir: Path):
    with open(inp_dir / "siminfo.json") as inp:
        data = json.load(inp)
    return data["students"]


def get_comments(inp_dir: Path):
    with open(inp_dir / "comments.yml") as inp:
        data = yaml.load(inp, Loader=yaml.SafeLoader)
    return {name: data[name]["short"] for name in data if data[name]["short"].strip()}


def get_gamma(inp_dir: Path, GAMMA_START):
    out_file = inp_dir / "votes.json"
    if not out_file.exists():
        return GAMMA_START
    with open(out_file) as inp:
        data = json.load(inp)
    return data["gamma"]


# - voting


def clamp(x):
    x[x < 0] = 0
    x[x > 1] = 1
    return x


def vote(gamma, ps_log, perf_mean, worse_mean, MAX_VOTE, MIN_VOTE):
    votes = (
        clamp((ps_log - worse_mean) / (perf_mean - worse_mean))**gamma
        * (MAX_VOTE - MIN_VOTE) + MIN_VOTE
    )
    return votes.mean(axis=0), votes.std(axis=0)


def cls():
    print("\033[H\033[J", end="")


def print_table(gamma, vote_args, students, comments):
    name_len = max(len(name) for name in students)
    print(f"Gamma: {gamma}")
    print()
    print("\n".join(f"{name.ljust(name_len)}: {vote_mean:4.2} +- {vote_std:4.2}"
                    + (f" -> {comments[name]}" if name in comments else "")
                    for name, vote_mean, vote_std in zip(students, *vote(gamma, *vote_args))))


def save(out_dir, gamma, comments: Dict[str, str], students, votes):
    with open(out_dir / "votes.json", "w") as out:
        json.dump({
            "gamma": gamma,
            "votes": list(zip(*votes))
        }, out, indent=2)
    with open(out_dir / "comments.yml", "r+") as edit:
        data = yaml.load(edit, Loader=yaml.SafeLoader)

        for name, comment in comments.items():
            data[name]["short"] = comment

        edit.seek(0)
        yaml.dump(data, edit, Dumper=yaml.SafeDumper)
        edit.truncate()


class CommandLine(cmd.Cmd):
    intro = 'Welcome to the gamma edit.\nType help or ? to list commands.\n'
    prompt = '> '

    def __init__(self, work_dir: Path, completekey: str = None, stdin: Union[IO[str], None] = None, stdout: Union[IO[str], None] = None) -> None:
        self.work_dir: Path = work_dir
        super().__init__(completekey, stdin, stdout)

    @property
    def content_hash(self):
        return hash(
            json.dumps({
                "gamma": self.gamma,
                "comments": self.comments
            },
                sort_keys=True)
        )

    def preloop(self) -> None:
        """Load the needed data"""
        self.ps_log = get_ps_log(self.work_dir)
        self.MAX_VOTE, self.MIN_VOTE, self.GAMMA_START = get_setup(
            self.work_dir)
        self.perf_mean, self.worse_mean = get_extremal_means(self.work_dir)
        self.students = get_students(self.work_dir)
        self.vote_args = self.ps_log, self.perf_mean, self.worse_mean, self.MAX_VOTE, self.MIN_VOTE

        self.gamma = get_gamma(self.work_dir, self.GAMMA_START)
        self.comments = get_comments(self.work_dir)

        self.saved_hash = self.content_hash

        self.cmdqueue.append("table")

        return super().preloop()

    def do_table(self, arg: str = None):
        "Print the vote table"
        print_table(self.gamma, self.vote_args,
                    self.students, self.comments)

    def do_comment(self, arg: str):
        "Edit the comment of a student: comment STUDENT"
        name = normalize_name(arg)
        matching = [
            student for student in self.students if student.startswith(name)]
        if not matching:
            print(f"Unknow student {name}")
            return False
        if len(matching) > 1:
            print(f"Multiple students match {name}: {', '.join(matching)}")
            return False
        name, = matching

        if name in self.comments:
            readline.set_startup_hook(
                lambda: readline.insert_text(self.comments[name]))
        try:
            self.comments[name] = input("Comment: ").strip()
        finally:
            readline.set_startup_hook()

        if not self.comments[name]:
            del self.comments[name]

    def do_gamma(self, arg: str):
        "Set the gamma: gamma NEW_GAMMA"
        try:
            self.gamma = float(arg.strip())
        except ValueError as e:
            print(e)
        else:
            self.do_table()

    def do_save(self, arg: str = None):
        "Save the gamma and comments"
        if self.saved_hash != self.content_hash:
            save(self.work_dir, self.gamma, self.comments,
                 self.students, vote(self.gamma, *self.vote_args))
            self.saved_hash = self.content_hash

    def do_quit(self, arg: str = None):
        "Exit from the program"
        if self.saved_hash != self.content_hash:
            print("File is not saved")
            ans = input(
                "Do you want to [q]uit without saving, [s]ave and quit, or [c]ancel: ")
            if ans == "q":
                return True
            if ans == "s":
                self.do_save()
                return True
            if ans == "c":
                return False
            print(f"Unknow option {ans}, cancelling")
            return False
        return True


def repl(work_dir: Path):
    CommandLine(work_dir).cmdloop()


if __name__ == "__main__":
    import sys
    repl(Path(sys.argv[1]))

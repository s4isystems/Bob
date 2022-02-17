#! /usr/bin/env python3

# Licensed Materials - Property of IBM
# 57XX-XXX
# (c) Copyright IBM Corp. 2021

import os
from pathlib import Path
from tempfile import mkstemp
from typing import Dict, Optional
from scripts.const import BOB_MAKEFILE, BOB_PATH
from scripts.utils import objlib_to_path, read_ibmi_json, read_iproj_json


class BuildEnv():
    color_tty: bool
    src_dir: Path
    target: str
    make_options: Optional[str]
    bob_path: Path
    bob_makefile: Path
    build_vars_path: Path
    build_vars_handle: Path
    curlib: str
    pre_usr_libl: str
    post_usr_libl: str
    includePath: str
    iproj_json_path: Path
    iproj_json: Dict[str, str]

    def __init__(self, target: str = 'all', make_options: Optional[str] = None):
        self.src_dir = Path.cwd()
        self.target = target
        self.make_options = make_options if make_options else ""
        self.bob_path = BOB_PATH
        self.bob_makefile = BOB_MAKEFILE
        self.build_vars_handle, path = mkstemp()
        self.build_vars_path = Path(path)
        self.iproj_json_path = self.src_dir / "iproj.json"
        self.iproj_json = read_iproj_json(self.iproj_json_path)
        self.create_build_vars()

    def __del__(self):
        self.build_vars_path.unlink()

    def generate_make_cmd(self):
        cmd = f'make -k BUILDVARSMKPATH="{self.build_vars_path}" -f "{self.bob_makefile}"'
        if self.make_options:
            cmd = f"{cmd} {self.make_options}"
        cmd = f"{cmd} {self.target}"
        return cmd

    def create_build_vars(self):
        target_file_path = self.build_vars_path

        rules_mks = list(Path(".").rglob("Rules.mk"))
        subdirs = list(map(lambda x: x.parents[0], rules_mks))

        subdirs.sort(key=lambda x: len(x.parts))
        dir_var_map = {Path('.'): (
            self.iproj_json['objlib'], self.iproj_json['tgtCcsid'])}

        def map_ibmi_json_var(path):
            if path != Path("."):
                dir_var_map[path] = read_ibmi_json(
                    path / ".ibmi.json", dir_var_map[path.parents[0]])

        list(map(map_ibmi_json_var, subdirs))

        with target_file_path.open("w") as f:
            f.write('\n'.join(["# This file is generated by makei, DO NOT EDIT.",
                               "# Modify .ibmi.json to override values",
                               "",
                               f"curlib := {self.iproj_json['curlib']}",
                               f"preUsrlibl := {self.iproj_json['preUsrlibl']}",
                               f"postUsrlibl := {self.iproj_json['postUsrlibl']}",
                               f"INCDIR := {self.iproj_json['includePath']}",
                               #    f"COLOR_TTY := {self.color}"
                               "",
                               "",
                               ]))

            for subdir in subdirs:
                f.write(
                    f"TGTCCSID_{subdir.absolute()} := {dir_var_map[subdir][1]}\n")
                f.write(
                    f"OBJPATH_{subdir.absolute()} := {objlib_to_path(dir_var_map[subdir][0])}\n")

            for rules_mk in rules_mks:
                with rules_mk.open('r') as r:
                    ls = r.readlines()
                    for l in ls:
                        l = l.rstrip()
                        if l and not l.startswith("#") and not "=" in l and not l.startswith((' ', '\t')):
                            f.write(
                                f"{l.split(':')[0]}_d := {rules_mk.parents[0].absolute()}\n")

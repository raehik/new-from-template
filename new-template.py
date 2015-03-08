#!/usr/bin/env python
#
# ayy lmao
#

import sys
import os
import re
import subprocess
import shlex

class FileTemplator:
    template_dir = os.environ["HOME"] + "/" + ".templates"
    # compile regex for efficiency
    command = re.compile("\$\((.*?)\)")
    info = {}
    lines = []

    def __init__(self, arglist):
        self.set_template_file(self.get_template_file_for(arglist[1]))
        self.info["@"] = " ".join(arglist[2:])
        self.set_outfile()

        # fill info dict
        for i in range(len(arglist)):
            self.info[str(i)] = arglist[i]

    def set_outfile(self):
        with open(self.info["template"], "r") as f:
            self.info["outfile"] = self.format_line(f.readline()).strip("\n")

    def set_template_file(self, filename):
        self.info["template"] = self.template_dir + "/" + filename

    def get_template_file_for(self, name):
        return name

    def run_command(self, arg_list):
        """Run a command, returning the output."""
        proc = subprocess.Popen(arg_list,stdout=subprocess.PIPE)
        out, err = proc.communicate()
        return out.decode("utf-8").strip()

    def format_line(self, line):
        for key, value in self.info.items():
            line = line.replace("%" + key + "%", value)
        # findall checks for matches anywhere in string
        # (match only checks at beginning)
        matches = self.command.findall(line)
        if matches:
            for match in matches:
                command_output = self.run_command(shlex.split(match))
                line = line.replace("$(" + match + ")", command_output)
        print(line)
        return line

    def format_template(self):
        with open(self.info["template"], "r") as template_file:
            next(template_file)
            for line in template_file:
                self.lines.append(self.format_line(line))

    def write_file(self):
        outfile = open(self.info["outfile"], "a")
        
        for line in self.lines:
            outfile.write(line)
        outfile.flush()

    def edit_file(self):
        editor = os.environ.get("EDITOR", "vim")
        subprocess.call([editor, self.info["outfile"]])

    def template(self):
        self.format_template()
        self.write_file()
        self.edit_file()



t = FileTemplator(sys.argv)

t.template()

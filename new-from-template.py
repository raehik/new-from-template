#!/usr/bin/env python
#
# ayy lmao
#

import sys
import os
import stat
import re
import subprocess

class FileTemplator:
    DEFAULT_FORMAT = ""
    FORMAT_START = "%{"
    FORMAT_END = "}%"
    CMD_START = "$("
    CMD_END = ")"
    CHAR_ENC = "utf-8"
    FALLBACK_SEP = "||"

    template_dir = os.environ["HOME"] + "/" + ".templates"

    # compile regex for efficiency
    commands = re.compile("\$\((.*?)\)")
    formats = re.compile("(%\{(.*?)(?:\|\|(.*?))?\}%)")

    info = {}
    lines = []

    def __init__(self, args):
        template_args = args[2:]

        # set name of template file from args
        self.set_template_file(self.template_filename_of(args[1]))

        # fill info dict
        self.info["@"] = " ".join(template_args)
        for i in range(len(template_args)):
            self.info[str(i+1)] = template_args[i]

        # set name of outfile
        # note that this must be done after filling info dict, since it
        # might use one of the keys in it (e.g. $1)
        self.set_outfile()

    def set_outfile(self):
        with open(self.info["template"], "r") as f:
            self.info["outfile"] = self.format_line(f.readline()).strip("\n")

    def set_template_file(self, filename):
        self.info["template"] = self.template_dir + "/" + filename

    def template_filename_of(self, name):
        return name

    def run_command(self, args):
        """Run a command, returning the output and a boolean value
        indicating whether the command failed."""
        was_successful = True

        # execute using a shell so we can use piping & redirecting
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()

        if proc.returncode != 0:
            was_successful = False

        return out.decode(self.CHAR_ENC).strip(), was_successful

    def replace_formats(self, line):
        replace = ""
        no_key = False

        matches = self.formats.findall(line)
        for match in matches:
            # A match is a 3-tuple with data organised as follows:
            #
            #     (format_string, info_key, fallback)
            #
            # If a fallback value was defined, it will be stored in
            # fallback -- otherwise fallback will be an empty string.

            try:
                # try to set replace string to value of info_key from
                # info dictionary
                replace = self.info[match[1]]
                if replace == "":
                    # key existed but was empty, so we don't use it
                    # e.g. %{@}% if you call without any arguments other
                    # than the template
                    no_key = True
            except KeyError:
                # key didn't exist
                # e.g. %{ayy lmao}% -- no info["ayy lmao"]
                no_key = True

            if no_key:
                # if no key/key was empty, use a default instead
                if match[2] != "":
                    # we found a 2nd capture group, which is the default
                    # value if no key for it in self.info, so use that
                    replace = match[2]
                else:
                    # key doesn't exist & no given fallback value --
                    # replace it with default fallback value
                    replace = self.DEFAULT_FORMAT

            # replace match with string
            line = line.replace(match[0], replace)

        return line

    def replace_commands(self,line):
        # findall checks for multiple matches anywhere in string
        matches = self.commands.findall(line)
        if matches:
            for match in matches:
                command_output, succeeded = self.run_command(match)
                line = line.replace(self.CMD_START + match + self.CMD_END, command_output)

        return line

    def format_line(self, line):
        """Format a single line, replacing format variables and command
        substitutions."""
        formatted = self.replace_formats(line)
        formatted = self.replace_commands(formatted)

        return formatted

    def format_template(self):
        with open(self.info["template"], "r") as template_file:
            next(template_file)
            for line in template_file:
                self.lines.append(self.format_line(line))

    def write_file(self):
        filename = self.info["outfile"]
        outfile = open(filename, "a")
        
        for line in self.lines:
            outfile.write(line)
        outfile.flush()

        # make it executable if the template is
        # we make chmod do the work because it works well with custom
        # umasks (e.g. if the file isn't set read to other, it won't be
        # set exec to others)
        out, is_executable = self.run_command(["test", "-x", self.info["template"]])

        if is_executable:
            self.run_command(["chmod", "+x", filename])

    def edit_file(self):
        editor = os.environ.get("EDITOR", "vim")
        subprocess.call([editor, self.info["outfile"]])

    def run(self):
        """Run the templating process."""
        self.format_template()
        self.write_file()
        self.edit_file()



t = FileTemplator(sys.argv)
t.run()

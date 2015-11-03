#!/usr/bin/env python3
#
# A simple templating program.
#

import sys
import os
import re
import subprocess

class FileTemplator:
    DEFAULT_FORMAT = "<placeholder>"
    REQ_PREFIX = "!"
    CHAR_ENC = "utf-8"

    # these are currently unused
    FORMAT_START = "%{"
    FORMAT_END = "}%"
    CMD_START = "%("
    CMD_END = ")%"
    FALLBACK_SEP = "||"

    # folder to store & look for templates in
    template_dir = os.environ["HOME"] + "/.local/share/templates"

    # compile regex for efficiency
    commands = re.compile("%\((.*?)\)%")
    formats = re.compile("(%\{(.*?)(?:\|\|(.*?))?\}%)")

    info = {}
    lines = []

    def __init__(self, args):
        if len(args) == 0:
            # no args provided
            print("error: no template to use provided")
            sys.exit(1)

        # set name of template file from args
        self.set_template_file(self.template_filename_of(args[0]))

        # fill info dict from arguments
        self.set_arg_info(args[1:])

        # fill info dict from other sources
        self.set_env_info()

        # set name of outfile
        # note that this must be done after filling info dict, since it
        # might use one of the keys in it (e.g. $1)
        self.set_outfile()

    def set_arg_info(self, args):
        """Add info from arguments."""
        self.set_info("@", " ".join(args))

        for i in range(len(args)):
            self.set_info(str(i+1), args[i])

    def set_env_info(self):
        """Add info from environment variables."""
        env_vars = [
                "USER",
                "HOME",
                "PWD",
                ["EDITOR", "vim"]
                ]

        for var in env_vars:
            if type(var) == list:
                # we provided a default value, so use it
                self.set_info(var[0], os.environ.get(var[0], var[1]))
            else:
                # no default (so it probably always exists)
                self.set_info(var, os.environ.get(var))

    def set_info(self, key, value):
        self.info[key] = value

    def get_info(self, key):
        return self.info[key]

    def set_outfile(self):
        with open(self.get_info("template"), "r") as f:
            self.set_info("outfile", self.format_line(f.readline()).strip("\n"))

    def set_template_file(self, filename):
        if not os.path.isdir(self.template_dir):
            print("error: template directory does not exist or is not a directory: %s"
                    % self.template_dir)
            sys.exit(10)

        template_file = self.template_dir + "/" + filename
        if not os.path.exists(template_file):
            print("error: no template file with that name: %s" % filename)
            sys.exit(11)

        self.set_info("template", template_file)

    def template_filename_of(self, name):
        return name

    def run_command(self, args):
        """Run a command, returning the output and a boolean value
        indicating whether the command failed or not."""
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
            #
            # TODO: what if fallback is set to an empty string? check if that is
            #       even possible with my code

            key_required = False

            key = match[1]
            if key.startswith(self.REQ_PREFIX):
                # key is *required*: if no default, fail instead of replacing
                # with fallback
                # note that if you make a key required, providing a default
                # would be a bit silly -- but I'm keeping it that way anyway
                # because it's safer
                key_required = True

                # remove the prefix
                key = key[len(self.REQ_PREFIX):]

            try:
                # try to set replace string to value of info_key from
                # info dictionary
                replace = self.get_info(match[1])
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
                # if no key/key was empty, use a fallback instead
                if match[2] != "":
                    # we found a 2nd capture group, which is the fallback
                    # value if no key for it in self.info, so use that
                    replace = match[2]
                else:
                    # no fallback value given
                    if key_required:
                        print("error: key/argument %s was required but not present/given" % key)
                        sys.exit(20)
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
        with open(self.get_info("template"), "r") as template_file:
            next(template_file)
            for line in template_file:
                self.lines.append(self.format_line(line))

    def write_file(self):
        filename = self.get_info("outfile")
        outfile = open(filename, "a")

        for line in self.lines:
            outfile.write(line)
        outfile.flush()

        # make it executable if the template is
        # we make chmod do the work because it works well with custom
        # umasks (e.g. if the file isn't set read to other, it won't be
        # set exec to others)
        out, is_executable = self.run_command("test -x " + self.get_info("template"))

        if is_executable:
            self.run_command("chmod +x " + filename)

    def edit_file(self):
        editor = os.environ.get("EDITOR", "vim")
        subprocess.call([editor, self.get_info("outfile")])

    def run(self):
        """Run the templating process."""
        # if file exists, do nothing
        if os.path.exists(self.get_info("outfile")):
            pass
        else:
            self.format_template()
            self.write_file()

        # open file for editing
        self.edit_file()



if __name__ == "__main__":
    t = FileTemplator(sys.argv[1:])
    t.run()

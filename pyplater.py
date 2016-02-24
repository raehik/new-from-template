#!/usr/bin/env python3
#
# A simple templating program.
#

import sys
import os
import re
import subprocess
import argparse

FILENAME = os.path.basename(sys.argv[0])


""" Print usage and exit depending on given exit code. """
def usage(exit_code):
    if exit_code == 0:
        pipe = sys.stdout
    else:
        # if argument was non-zero, print to STDERR instead
        pipe = sys.stderr

    parser.print_help(pipe)
    sys.exit(exit_code)

## Logging {{{
""" Log a message to a specific pipe (defaulting to stdout). """
def log_message(message, pipe=sys.stdout):
    print(FILENAME + ": " + message, file=pipe)

""" If verbose, log an event. """
def log(message):
    if not args.verbose:
        return
    log_message(message)

""" Log an error. If given a 2nd argument, exit using that error code. """
def error(message, exit_code=None):
    log_message("error: " + message, sys.stderr)
    if exit_code:
        sys.exit(exit_code)
## }}}

## Parsing arguments {{{
""" Argparse override to print usage to stderr on argument error. """
class ArgumentParserUsage(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        self.print_help(sys.stderr)
        sys.exit(2)

parser = ArgumentParserUsage(description="A simple templating program.")

# add arguments
parser.add_argument("template",
                    help="template to use")
parser.add_argument("template_args", metavar="args", nargs="*",
                    help="arguments provided to the template")
parser.add_argument("-d", "--template-dir",
                    help="specify directory to search for templates (default ~/.local/share/templates")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="be verbose (show when fallbacks are used etc.)")

# parse arguments
args = parser.parse_args()
## }}}

## class Pyplater {{{
class Pyplater:
    ERR_NOT_FOUND = 1
    ERR_MISSING_REQ_KEY = 2
    ERR_INVALID_TEMPLATE = 3
    ERR_WEIRD = 10

    DEFAULT_FORMAT = "<placeholder>"
    DEFAULT_TEMPLATE_DIR = os.environ["HOME"] + "/.local/share/templates"
    REQ_PREFIX = "!"
    ESC_PREFIX = "\\"
    CHAR_ENC = "utf-8"

    # these can be changed if you want
    FORMAT_START = "%{"
    FORMAT_END = "}%"
    CMD_START = "%("
    CMD_END = ")%"
    FALLBACK_SEP = "||"

    # compile regex for efficiency
    MATCH_PART = r"(.*?)"
    formats = re.compile(
            r"(" \
          + re.escape(FORMAT_START) \
          + MATCH_PART + r"(?:" \
          + re.escape(FALLBACK_SEP) \
          + MATCH_PART + r")?" \
          + re.escape(FORMAT_END) \
          + r")")
    commands = re.compile(
            re.escape(CMD_START) \
          + MATCH_PART \
          + re.escape(CMD_END))

    info = {}
    lines = []

    def __init__(self, template, template_dir, args):
        # fill info dict from arguments
        self.set_arg_info(template_dir, args)

        # set name of template file from args
        self.set_template_file(self.template_filename_of(template))

        # fill info dict from other sources
        self.set_env_info()

        # set name of outfile
        # this is done after filling info{}, since it might use one of the keys
        # in it (e.g. $1)
        self.set_outfile()

    def set_arg_info(self, template_dir, args):
        """ Add info from arguments. """
        self.set_info("@", " ".join(args))
        self.set_info("template_dir", template_dir)

        for i in range(len(args)):
            self.set_info(str(i+1), args[i])

    def set_env_info(self):
        """ Add info from environment variables. """
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
        """Set a key in the info dictionary."""
        self.info[key] = value

    def get_info(self, key):
        """Retrive the value of a key in the info dictionary."""
        return self.info[key]

    def set_outfile(self):
        """ Process the first line of a file and save as info["outfile"]. """
        with open(self.get_info("template"), "r") as f:
            self.set_info("outfile", self.format_line(f.readline()).strip("\n"))

    def set_template_file(self, filename):
        t_dir = self.get_info("template_dir")
        if not os.path.isdir(t_dir):
            error("template directory does not exist or is not a directory: {}".format(t_dir))
            sys.exit(Pyplater.ERR_NOT_FOUND)

        template_file = t_dir + "/" + filename
        if not os.path.exists(template_file):
            error("no template file with that name: %s" % filename)
            sys.exit(Pyplater.ERR_NOT_FOUND)
        if os.path.isdir(template_file):
            error("given template is a directory: %s" % filename)
            sys.exit(Pyplater.ERR_INVALID_TEMPLATE)

        self.set_info("template", template_file)

    def template_filename_of(self, name):
        return name

    def run_command(self, args):
        """Run a command, returning the output and a boolean value indicating
        whether the command failed or not."""
        was_successful = True

        # execute using a shell so we can use piping & redirecting
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()

        if proc.returncode != 0:
            was_successful = False

        return out.decode(self.CHAR_ENC).strip(), was_successful

    def replace_formats(self, line):
        match_indexes = [ match.start(0) for match in re.finditer(self.formats, line) ]
        match_texts = self.formats.findall(line)

        # combine matches with their indexes
        matches = []
        if len(match_indexes) != len(match_texts):
            error("indexes list length doesn't match text list length: why not?")
            sys.exit(Pyplater.ERR_WEIRD)
        for i in range(len(match_indexes)):
            matches.append([match_indexes[i], match_texts[i]])

        # now iterate over each match
        for match in matches:
            # A match is a list of an integer and a 3-tuple with data organised
            # as follows:
            #
            #     [ start_pos, (format_string, info_key, fallback) ]
            #
            # If a fallback value was defined, it will be stored in fallback --
            # otherwise fallback will be an empty string.
            #
            # TODO: what if fallback is set to an empty string? check if that is
            #       even possible with my code

            # initialise booleans
            key_required = False
            no_key = False

            # set variables for separate parts of match
            match_pos = match[0]
            match_text = match[1]

            key = match_text[1]
            if key.startswith(self.REQ_PREFIX):
                # key is *required*: if no default, fail instead of replacing
                # with fallback
                # note that if you make a key required, providing a default
                # would be a bit silly -- but I'm keeping it that way anyway
                # because it's safer
                key_required = True

                # remove the prefix
                key = key[len(self.REQ_PREFIX):]

            if key.startswith(self.ESC_PREFIX):
                # should *not* replace this (e.g. actually print '%{key}%'
                # verbosely, so we remove prefix and skip to next match
                line = line[:match_pos] + line[match_pos:].replace(self.ESC_PREFIX, "")
                # update all other indexes because we've removed a part of the
                # string of length len(ESC_PREFIX)
                # TODO: code duplication (I put in the same form now, but don't
                #       know how to skip all below
                for i in range(len(matches)):
                    matches[i][0] += len("") - len(self.ESC_PREFIX)
                continue

            try:
                # try to set replace string to value of info_key from
                # info dictionary
                replace = self.get_info(key)
                if replace == "":
                    # key existed but was empty, so we don't use it
                    # e.g. %{@}% if you call without any arguments other
                    # than the template
                    no_key = True
            except KeyError:
                # key didn't exist
                # e.g. %{ayy lmao}% -- no info["ayy lmao"]
                log("key '{}' wasn't found in info".format(key))
                no_key = True

            if no_key:
                # if no key/key was empty, use a fallback instead
                if match_text[2] != "":
                    # we found a 2nd capture group, which is the fallback
                    # value if no key for it in self.info, so use that
                    replace = match_text[2]
                    log("key '{}' wasn't found, so the provided fallback '{}' was used".
                            format(key, match_text[2]))
                else:
                    # no fallback value given
                    if key_required:
                        error("key/argument '{}' was required but not present/given".
                            format(key))
                        sys.exit(Pyplater.ERR_MISSING_REQ_KEY)
                    else:
                        # key doesn't exist & no given fallback value --
                        # replace it with default fallback value
                        log("key '{}' wasn't found, no fallback -- default fallback '{}' was used".
                                format(key, self.DEFAULT_FORMAT))
                        replace = self.DEFAULT_FORMAT

            # replace match with string
            line = line[:match_pos] + line[match_pos:].replace(match_text[0], replace, 1)

            # update all other indexes because changed the string
            # TODO: duplicated from ESC_PREFIX part
            for i in range(len(matches)):
                matches[i][0] += len(replace) - len(match_text[0])

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
            # skip first line (used for filename of outfile)
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
        """ Run the templating process. """
        # if file exists, do nothing
        if os.path.exists(self.get_info("outfile")):
            pass
        else:
            self.format_template()
            self.write_file()

        # open file for editing
        self.edit_file()
## }}}


# run the damn thing
if __name__ == "__main__":
    if args.template_dir:
        template_dir = args.template_dir
    else:
        template_dir = Pyplater.DEFAULT_TEMPLATE_DIR
    t = Pyplater(args.template, template_dir, args.template_args)
    t.run()

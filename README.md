Pyplater
========

Pyplater is a flexible automated file-templating program written in Python.
Specify the template file to use and any required/optional arguments and
Pyplater will copy the template to a new file, 'fill in' parts with information
from arguments and the environment, then open it in your `$EDITOR` for you.


Syntax
------

Pyplater's templating syntax is somewhat similar to Liquid's, but note that
**both** percentage signs '%' are on the *outside*.

Replacements are applied line by line. Variables are replaced first, then
shell commands with their output.


### Filename = First line

The first line of a file defines the **file name** for the new file. You can use
any and all templating syntax in this line. Relative and absolute filenames are
allowed.

Remember that you never pass a filename argument to Pyplater: the template
filename or first argument may well be used for the filename, but that's up to
the template file itself.


### Variable replacement

e.g. `%{HOME||/home/user}%`

Tries to match a word enclosed by `%{` and `}%` (e.g. `%{word}%`) and replaces
it the match with the value of `info[word]`. If the matched word is not a key in
the `info` dictionary, it is replaced with a placeholder string (currently
'\<placeholder\>'). If the word starts with an exclamation mark e.g. `%{!word}%`
then the variable is **required** -- if it isn't found, Pyplater exits.

**Note:** Requiring '$@' (i.e. all arguments) works as you would expect: given
no arguments, it fails, but with one or more arguments it is fine.

The `info` directory is filled with the command line arguments (discouting
argument '0', the name of the invoked program), certain environment variables
and some other variables used internally but made available for flexibility
purposes (like the full name of the template file at `info["template"]`). You
can find and edit the full list of environment variables copied over in the
program file -- currently it includes basic ones like $HOME and $PWD.

You can set a 'fallback' value to use if the variable isn't found by adding a
separator `||` and the string to fall back on, e.g. `%{1||No argument 1
supplied}%`. If the variable is *required*, it will use any provided fallback
before failing.

More on command line arguments: they begin from **1**, and that is the first
*template argument* you provide, **not** the template to use! (That's stored in
`info["template"]`.)


### Shell command replacement

e.g. `%(wc -w <<< "%{1}%")%`

Trid to match a string enclosed by `%(` and `)%` (e.g. `%(echo superfluous)%`)
and replaces the match with the output of the string run as a shell command.

Because **variables** are replaced first, you can put them *inside* command
replacements. It'll work just the same. The example given would count the words
in the first argument.

You can get pretty creative with these. The filename for a file made from the
`journal` template is/originally was:

    %{HOME}%/journal/%(date "+%Y-%m-%d")%-%(ezstring "%{@||New entry}%")%.md

where `ezstring` is a program which makes a filesystem-friendly filename from a
string.

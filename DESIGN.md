Classes
-------

### FileTemplator

Deals with creating template files. Includes reading template files and
filling them with dynamic information specified via arguments.


#### Requirements

  * Must form template filename from argument.
  * Must read template file and replace special formatting blocks with
    data from arguments/output from shell commands.


#### Methods

##### `__init__`

  * Take a list formatted like sys.argv as argument.
  * Take argument `word`, form template filename.
  * Read other arguments into info dictionary.

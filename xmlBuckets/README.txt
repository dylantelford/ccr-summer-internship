runBucket.py is a python script that will read an xml document from a file
or from stdin containing the location of all files in a bucket. 

Given a path through the xml tags to the tag we want, and a command, it will run
that command on each file in the bucket. The file name will be added to the end 
of the command, or will replace {} if it is found in the command. 

If no command is given, it will print a list of the files it found. -o can be used 
to specify an output file, otherwise stdout will be used. 

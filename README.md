# Usage

python find_matches.py "/path/to/target/folder"

Once the program runs, it will show pairs of similar images, in order
of how similar it judges them to be.

# Interpreting Distance Between Images
As a rule of thumb, "Distance between images" will be 0.0 for identical
images, 0 to 50 after a resize or conversion that changed a few pixels,
50 to 100 for barely noticeable differences.
and if distance is > 250 they are probably nothing alike.
Which means that when searching for duplicates you can ignore any after
the distance passes 100 or so.

The distance measure works well for resizes, minor edits, translations or rotations, and colour tweaks. However if a large change in colour has been made (such as converting an image to black and white) this
program will not notice that they are similar, since colour plays a large
role in judging similarity. Flipping an image or any other large transformations
will also cause the program to not recognize similarity.

# Efficiency

If the folder has a very large number of images, it may take a while
to search them all. It has been tested on upwards of 10K at a time
however and performance will scale approximately linearly unless you
search a truly massive number of files at once.

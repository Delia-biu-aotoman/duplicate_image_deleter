# Description

This displays all similar images in a folder and its subfolders.
It also shows information like which image is larger and their resolution
so you can decide whether to delete one, neither, or both of them.

# Performance

This is optimized to be as fast as possible and can detect all duplicates
in a collection of >40K images on a typical hard drive in under 200 seconds.
For a more reasonable collection of 1000 images, it will detect all duplicates
in 7 seconds.

After the first time it is run with a folder, it will cache some results,
which makes it roughly 10 times faster.

# Usage

```./find_matches.py "/path/to/target/folder"```

# Installation

This program was written and tested with python3 on Ubuntu, other platforms may not work.

Most requirements can be installed with

```
pip3 install -r requirements.txt
```

In addition, you must install the system python3 gtk library with:
```
sudo apt install python3-gi
```

The program uses a binary component to speed up searching, which can be compiled by running
```
make
```

The program additionally requires a CPU with AVX support. Any intel processor made after 2008 and any AMD processor post 2011 should support this.

# Interpreting Distance Between Images

As a rule of thumb, "Distance between images" will be 0.0 for identical
images, 0 to 50 after a resize or conversion that changed a few pixels,
50 to 100 for barely noticeable differences.
and if distance is > 250 they are probably nothing alike.
This means that when searching for duplicates you can ignore any after
the distance passes 100 or so.
By default the program will only list images at most 300 apart to improve performance.

The distance measure works well for resizes, minor edits, translations or rotations, and colour tweaks. However if a large change in colour has been made (such as converting an image to black and white) this
program will not notice that they are similar, since colour plays a large
role in judging similarity. Flipping an image or any other large transformations
will also cause the program to not recognize similarity.

# Efficiency

For most image collections, performance is approximately linear in how
many uncached images you have. When dealing with an extremely large
collection (Hundreds of thousands), the search code itself will become
dominant which runs in n-squared time.


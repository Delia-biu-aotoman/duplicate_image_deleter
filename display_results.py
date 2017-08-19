import gi
from PIL import Image
from math import ceil
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf
from io import BytesIO
import json
from os.path import join

def load_thumbnail(filename):
    img_orig = Image.open(filename)
    # Find the side requiring the greatest resize:

    size = (600, 600)
    x_size = size[0]
    y_size = size[1]
    x_resize_ratio = img_orig.size[0] / x_size
    y_resize_ratio = img_orig.size[1] / y_size

    if(x_resize_ratio > y_resize_ratio):
        y_size = ceil(y_size * (y_resize_ratio / x_resize_ratio))
    else:
        x_size = ceil(x_size * (x_resize_ratio / y_resize_ratio))

    img = img_orig.resize((x_size, y_size), Image.ANTIALIAS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(img, ((size[0]-x_size)//2, (size[1]-y_size)//2))

    buff = BytesIO()
    canvas.save(buff, 'ppm')
    contents = buff.getvalue()
    buff.close()
    loader = GdkPixbuf.PixbufLoader.new_with_type('pnm')
    loader.write(contents)
    pixbuf = loader.get_pixbuf()
    loader.close()
    stats = "Width: {}px\nHeight: {}px".format(img.size[0],img.size[1])
    return (pixbuf, stats)

def split_long_names(filename):
    split_len = 80
    parts = []
    while(len(filename) > 0):
        if(len(filename) > 80):
            parts.append(filename[:80])
            filename = filename[80:]
        else:
            parts.append(filename)
            break
    return "\n(Continued) ".join(parts)

class Handler:
    def __init__(self, folder, scores, builder):
        self.page_num = 0
        self.page_count = len(scores)
        self.scores = scores
        self.folder = folder
        self.builder = builder

        self.update_page()

    def update_page(self):
        score = self.scores[self.page_num][0]
        left_file = self.scores[self.page_num][1]
        right_file = self.scores[self.page_num][2]

        # update right
        image2 = self.builder.get_object("image2")
        path2 = join(self.folder, right_file)
        pixbuf2, stats2 = load_thumbnail(path2)
        image2.set_from_pixbuf(pixbuf2)

        stats2 = "Filename: %s\n%s\n" % (split_long_names(right_file), stats2)
        right_description = Gtk.TextBuffer()
        right_description.set_text(stats2)
        textview2 = self.builder.get_object("textview2")
        textview2.set_buffer(right_description)

        # update left
        image1 = self.builder.get_object("image1")
        path1 = join(self.folder, left_file)
        pixbuf1, stats1 = load_thumbnail(path1)
        image1.set_from_pixbuf(pixbuf1)

        stats1 = "Filename: %s\n%s\nDifference Score: %d\n" % (split_long_names(left_file), stats1, int(score))
        left_description = Gtk.TextBuffer()
        left_description.set_text(stats1)
        textview1 = self.builder.get_object("textview1")
        textview1.set_buffer(left_description)

    def onDeleteRight(self, *args):
        right_file = self.scores[self.page_num][2]
        temp = []
        for res in self.scores:
            if res[2] != right_file:
                temp.append(res)

        self.scores = temp
        self.page_count = len(self.scores)

        if(self.page_num >= self.page_count):
            self.page_num = 0
        self.update_page()

    def onDeleteLeft(self, *args):
        left_file = self.scores[self.page_num][1]
        temp = []
        for res in self.scores:
            if res[1] != left_file:
                temp.append(res)

        self.scores = temp
        self.page_count = len(self.scores)

        if(self.page_num >= self.page_count):
            self.page_num = 0
        self.update_page()

    def onDeleteWindow(self, *args):
        Gtk.main_quit(*args)

    def onButtonPressed(self, button):
        print("Hello World!")

    def onLeftClicked(self, *args):
        self.page_num = self.page_num-1
        if(self.page_num < 0):
            self.page_num = self.page_count - 1
        self.update_page()

    def onRightClicked(self, *args):
        self.page_num = self.page_num+1
        if(self.page_num >= self.page_count):
            self.page_num = 0
        self.update_page()

def display(folder, scores):
    builder = Gtk.Builder()
    builder.add_from_file("duplicate_deleter.glade")

    handler = Handler(folder, scores, builder)
    builder.connect_signals(handler)

    textview1 = builder.get_object("textview1")
    textview1.set_editable(False)
    textview2 = builder.get_object("textview2")
    textview2.set_editable(False)

    window = builder.get_object("window1")
    window.show_all()

    Gtk.main()

if __name__ == "__main__":
    with open("data.json", "r") as input:
        data = json.loads(input.read())
    folder = data["folder"]
    scores = data["scores"]
    display(folder, scores)

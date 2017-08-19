from PIL import Image
from math import ceil
from io import BytesIO
import json
from os.path import join, getsize

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf

def load_thumbnail(filename):
    img_orig = Image.open(filename)
    filesize = getsize(filename)
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
    stats = "Width: {} pixels\nHeight: {} pixels\nFile size: {} bytes".format(img_orig.size[0],img_orig.size[1], filesize)
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

class DialogExample(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "My Dialog", parent, 0,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.set_default_size(150, 100)

        label = Gtk.Label("Are you sure you want to delete this image? This cannot be undone.")

        box = self.get_content_area()
        box.add(label)
        self.show_all()

class Handler:
    def __init__(self, folder, scores, builder):
        self.page_num = 0
        self.page_count = len(scores)
        self.scores = scores
        self.folder = folder
        self.builder = builder
        adjustment = self.builder.get_object("adjustment1")
        adjustment.set_property("upper", self.page_count)

        self.update_page()

    def update_page(self):
        score = self.scores[self.page_num][0]

        description = Gtk.TextBuffer()
        description.set_text("Distance between images: %.2f" % (score))
        textview3 = self.builder.get_object("textview3")
        textview3.set_buffer(description)


        left_file = self.scores[self.page_num][1]
        right_file = self.scores[self.page_num][2]

        # update right
        image2 = self.builder.get_object("image2")
        path2 = join(self.folder, right_file)
        pixbuf2, stats2 = load_thumbnail(path2)
        image2.set_from_pixbuf(pixbuf2)

        stats2 = "%s\n%s\n" % (right_file, stats2)
        right_description = Gtk.TextBuffer()
        right_description.set_text(stats2)
        textview2 = self.builder.get_object("textview2")
        textview2.set_buffer(right_description)

        # update left
        image1 = self.builder.get_object("image1")
        path1 = join(self.folder, left_file)
        pixbuf1, stats1 = load_thumbnail(path1)
        image1.set_from_pixbuf(pixbuf1)

        stats1 = "%s\n%s\n" % (left_file, stats1)
        left_description = Gtk.TextBuffer()
        left_description.set_text(stats1)
        textview1 = self.builder.get_object("textview1")
        textview1.set_buffer(left_description)

    def page_changed(self, *args):
        adjustment = self.builder.get_object("adjustment1")
        self.page_num = int(adjustment.get_property("value")) -1
        self.update_page()

    def set_page_number(self, num):
        self.page_num = num
        if(self.page_num >= self.page_count):
            self.page_num = 0
        elif (self.page_num < 0):
            self.page_num = self.page_count - 1

        adjustment = self.builder.get_object("adjustment1")
        adjustment.set_property("value", self.page_num+1)
        self.update_page()

    def cancel_deletion(self):
        window = self.builder.get_object("window1")
        dialog = DialogExample(window)
        response = dialog.run()

        result = None
        if response == Gtk.ResponseType.OK:
            print("The OK button was clicked")
            result = False
        elif response == Gtk.ResponseType.CANCEL:
            print("The Cancel button was clicked")
            result = True

        dialog.destroy()

        return result

    def onDeleteRight(self, *args):
        if self.cancel_deletion():
            return

        right_file = self.scores[self.page_num][2]
        temp = []
        for res in self.scores:
            if res[2] != right_file:
                temp.append(res)

        self.scores = temp
        self.page_count = len(self.scores)

        self.set_page_number(self.page_num)

    def onDeleteLeft(self, *args):
        if self.cancel_deletion():
            return

        left_file = self.scores[self.page_num][1]
        temp = []
        for res in self.scores:
            if res[1] != left_file:
                temp.append(res)

        self.scores = temp
        self.page_count = len(self.scores)

        self.set_page_number(self.page_num)

    def onDeleteWindow(self, *args):
        Gtk.main_quit(*args)

    def onLeftClicked(self, *args):
        self.set_page_number(self.page_num-1)

    def onRightClicked(self, *args):
        self.set_page_number(self.page_num+1)

def display(folder, scores):
    builder = Gtk.Builder()
    builder.add_from_file("duplicate_deleter.glade")

    handler = Handler(folder, scores, builder)
    builder.connect_signals(handler)

    window = builder.get_object("window1")
    window.show_all()

    Gtk.main()

if __name__ == "__main__":
    with open("data.json", "r") as input:
        data = json.loads(input.read())
    folder = data["folder"]
    scores = data["scores"]
    display(folder, scores)

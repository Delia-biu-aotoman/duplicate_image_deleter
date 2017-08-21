from PIL import Image
from math import ceil
from io import BytesIO
import json
from os.path import join, getsize
import os
import time
import sys
from pprint import pprint
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

    stats = {
        "width": img_orig.size[0],
        "height": img_orig.size[1],
        "filesize": filesize
    }
    return (pixbuf, stats)

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
    def __init__(self, scores, builder, page_entry):
        self.page_entry = page_entry
        self.page_num = 0
        self.show_page_number()
        self.page_count = len(scores)
        self.scores = scores
        self.builder = builder
        #~ adjustment = self.builder.get_object("adjustment1")
        #~ adjustment.set_property("upper", self.page_count)

        self.update_page()

    def update_page(self):
        if(len(self.scores) == 0):
            description = Gtk.TextBuffer()
            description.set_text("No similar pairs of images found")
            textview3 = self.builder.get_object("textview3")
            textview3.set_buffer(description)
            return

        score = self.scores[self.page_num][0]

        description = Gtk.TextBuffer()
        description.set_text("Distance between images: %.2f" % (score))
        textview3 = self.builder.get_object("textview3")
        textview3.set_property("justification", Gtk.Justification.CENTER)
        textview3.set_buffer(description)


        left_file = self.scores[self.page_num][1]
        right_file = self.scores[self.page_num][2]

        try:
            # read right
            image2 = self.builder.get_object("image2")
            pixbuf2, stats2 = load_thumbnail(right_file)
            image2.set_from_pixbuf(pixbuf2)
        except FileNotFoundError as e:
            print("Expected right file is missing")
            print(e)
            # TODO: just remove right file.
            return

        try:
            # read left
            image1 = self.builder.get_object("image1")
            pixbuf1, stats1 = load_thumbnail(left_file)
            image1.set_from_pixbuf(pixbuf1)
        except FileNotFoundError as e:
            print("Expected left file is missing")
            print(e)
            # TODO: just remove left file.
            return

        # update right
        right_description = "%s\nWidth: %d\nHeight: %d\nFilesize: %d\n" % (
            right_file, stats2["width"], stats2["height"], stats2["filesize"])
        if(stats2["filesize"] > stats1["filesize"]):
            right_description = right_description + "(Larger)\n"

        right_buffer = Gtk.TextBuffer()
        right_buffer.set_text(right_description)
        textview2 = self.builder.get_object("textview2")
        textview2.set_buffer(right_buffer)

        # update left
        left_description = "%s\nWidth: %d\nHeight: %d\nFilesize: %d\n" % (
            left_file, stats1["width"], stats1["height"], stats1["filesize"])
        if(stats1["filesize"] > stats2["filesize"]):
            left_description = left_description + "(Larger)\n"

        left_buffer = Gtk.TextBuffer()
        left_buffer.set_text(left_description)
        textview1 = self.builder.get_object("textview1")
        textview1.set_buffer(left_buffer)

    def show_page_number(self):
        new_page_str = str(self.page_num + 1)
        self.page_entry.get_buffer().set_text(new_page_str, len(new_page_str))

    def set_page_number(self, num):
        self.page_num = num
        if(self.page_num >= self.page_count):
            self.page_num = 0
        elif (self.page_num < 0):
            self.page_num = self.page_count - 1

        self.update_page()

    def cancel_deletion(self):
        window = self.builder.get_object("window1")
        dialog = DialogExample(window)
        response = dialog.run()

        result = None
        if response == Gtk.ResponseType.OK:
            result = False
        elif response == Gtk.ResponseType.CANCEL:
            result = True

        dialog.destroy()

        return result

    def onDeleteRight(self, *args):
        if(len(self.scores) == 0):
            return
        #TODO: Disable navigation until this finishes to prevent races
        if self.cancel_deletion():
            return

        right_file = self.scores[self.page_num][2]
        temp = []
        for res in self.scores:
            if res[1] != right_file and res[2] != right_file:
                temp.append(res)

        self.scores = temp
        self.page_count = len(self.scores)

        self.set_page_number(self.page_num)
        self.show_page_number()
        try:
            os.remove(right_file)
        except FileNotFoundError as e:
            print(e)
            pass

    def onDeleteLeft(self, *args):
        if(len(self.scores) == 0):
            return
        #TODO: Disable navigation until this finishes to prevent races
        if self.cancel_deletion():
            return

        left_file = self.scores[self.page_num][1]
        temp = []
        for res in self.scores:
            if res[1] != left_file and res[2] != left_file:
                temp.append(res)

        self.scores = temp
        self.page_count = len(self.scores)

        self.set_page_number(self.page_num)
        self.show_page_number()
        try:
            os.remove(left_file)
        except FileNotFoundError as e:
            print(e)
            pass

    def onDeleteWindow(self, *args):
        Gtk.main_quit(*args)

    def onLeftClicked(self, *args):
        self.set_page_number(self.page_num-1)
        self.show_page_number()

    def onRightClicked(self, *args):
        self.set_page_number(self.page_num+1)
        self.show_page_number()

    def onIgnoreClicked(self, *args):
        pass

    def onDeleteBothClicked(self, *args):
        pass

    def page_num_edited(self, *args):
        page_num_str = self.page_entry.get_text()
        try:
            new_num = int(page_num_str) - 1
            if(new_num >= 0 and new_num < self.page_count):
                print('new num = ',new_num)
                self.page_num = new_num
                self.update_page()

            #~ if(self.page_num >= self.page_count):
                #~ self.page_num = self.page_count - 1
                #~ self.page_entry.set_text(str(self.page_count))
            #~ elif (self.page_num < 0):
                #~ self.page_num = 0
                #~ self.page_entry.set_text(str(1))
            #~ else:
                #~ self.update_page()
        except:
            pass

class MyEntry(Gtk.Entry, Gtk.Editable):
    """
    I wanted to make a text entry widget that only accepts numbers.
    A spinbox was close, but I did not want to have the extra +- buttons
    since they don't render right on a mac.
    Therefore, I created this entry with an overridden do_insert_text
    """

    def __init__(self):
        self.handler = None
        super(MyEntry, self).__init__()

    def do_insert_text(self, new_text, length, position):
        # Inspiration for function from here:
        # https://stackoverflow.com/questions/38815694/gtk-3-position-attribute-on-insert-text-signal-from-gtk-entry-is-always-0
        try:
            inserted_digit = int(new_text)
            self.get_buffer().insert_text(position, new_text, length)
            return position + length
        except ValueError:
            return position

def create_numeric_entry(builder):
    entry = MyEntry()
    entry.set_property("visible", True)
    entry.set_property("can_focus", True)

    grid = builder.get_object("grid1")
    grid.attach(entry, 3, 1, 1, 1)
    return entry

def display(scores):
    builder = Gtk.Builder()
    builder.add_from_file("duplicate_deleter.glade")

    page_entry = create_numeric_entry(builder)
    handler = Handler(scores, builder, page_entry)
    builder.connect_signals(handler)

    handler_id = page_entry.connect("changed", handler.page_num_edited)

    window = builder.get_object("window1")

    window.show_all()

    Gtk.main()

# -*- coding: utf-8 -*-
# *****************************COPYRIGHT*******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT*******************************
"""
This module contains Rose edit widgets for helping to configure STASH inputs.

Classes:
    StashSummaryDataPanelv1 - STASH summary GUI
    StashCodeChooserValueWidget - STASH code chooser array value widget.

"""


import os

import pygtk
pygtk.require('2.0')
import gtk

import rose.config_editor.plugin.um.widget.stash
import stash_parse


META_DIR = os.path.dirname(  # lib
              os.path.dirname(  # python
                 os.path.dirname(  # widget
                    os.path.dirname(os.path.abspath(__file__)))))

STASHMASTER_PATH = os.path.join(META_DIR, "etc", "stash",
                                "STASHmaster")
STASHMASTER_META_PATH = STASHMASTER_PATH
STASHMASTER_META_FILENAME = "STASHmaster-meta.conf"
STASH_PACKAGE_PATH = os.path.join(META_DIR, "etc", "stash",
                                  "package")

STASHMASTER_PARSERS_BY_PATH = {
    STASHMASTER_PATH: stash_parse.StashMasterParserv1(STASHMASTER_PATH)
}

class StashSummaryDataPanelv1(
      rose.config_editor.plugin.um.widget.stash.BaseStashSummaryDataPanelv1):

    """This is a class for displaying and editing STASH requests.

    It should be referenced via a:
    widget[rose-config-edit:sub-ns]=stash.StashSummaryDataPanelv1
    entry in the metadata. The default STASHmaster file used in the
    widget is the one in the metadata directory - supplying a path
    as an argument to the widget metadata will override it, e.g.:
    widget[rose-config-edit:sub-ns]=stash.StashSummaryDataPanelv1 /some/path/to/STASHmaster/files/

    For more information, see the base class within the Rose code.

    """

    STASHMASTER_PATH = STASHMASTER_PATH
    STASHMASTER_META_PATH = STASHMASTER_META_PATH
    STASH_PACKAGE_PATH = STASH_PACKAGE_PATH


    def get_stashmaster_lookup_dict(self):
        """Provide the necessary rose.config.ConfigNode object."""
        cached_parser = STASHMASTER_PARSERS_BY_PATH.get(
            self.stashmaster_directory_path)
        if cached_parser is not None:
            return cached_parser.get_lookup_dict()
        parser = stash_parse.StashMasterParserv1(
            self.stashmaster_directory_path)
        return parser.get_lookup_dict()


class StashCodeChooserValueWidgetv1(gtk.HBox):

    """This class generates a widget for entering one or more STASH codes."""

    ALLOWED_STASH_SECTIONS = ("0", "33", "34")
    DEFAULT_CODE = "2"
    TIP_ADD = "Add array element"
    TIP_DEL = "Delete array element"

    def __init__(self, value, metadata, set_value, hook, arg_str=None):
        super(StashCodeChooserValueWidgetv1, self).__init__(homogeneous=False,
                                                            spacing=0)
        self.value = value
        self.metadata = metadata
        self.set_value = set_value
        self.hook = hook
        if arg_str:
            self.stashmaster_directory_path = arg_str
        else:
            self.stashmaster_directory_path = STASHMASTER_PATH
        self.load_stash()
        self.max_length = metadata[rose.META_PROP_LENGTH]
        value_array = rose.variable.array_split(value)
        self.chooser_table = gtk.Table(rows=1,
                                       columns=1,
                                       homogeneous=True)
        self.chooser_table.connect('focus-in-event',
                                   self.hook.trigger_scroll)
        self.chooser_table.show()

        self.choosers = []
        for value_item in value_array:
            combo = self.get_chooser(value_item)
            self.choosers.append(combo)
        self.generate_buttons()
        self.populate_table()
        self.pack_start(self.button_box, expand=False, fill=False)
        self.pack_start(self.chooser_table, expand=True, fill=True)
        self.connect('focus-in-event',
                     lambda w, e: self.hook.get_focus(
                                                self.get_focus_chooser()))

    def load_stash(self):
        """Load STASHmaster record information and metadata."""
        self._stash_lookup = self.get_stashmaster_lookup_dict()
        self._stash_meta_lookup = (
            self.get_stashmaster_meta_lookup_dict())

    def get_stashmaster_lookup_dict(self):
        """Provide the necessary STASHmaster record lookup."""
        cached_parser = STASHMASTER_PARSERS_BY_PATH.get(
            self.stashmaster_directory_path)
        if cached_parser is not None:
            return cached_parser.get_lookup_dict()
        parser = stash_parse.StashMasterParserv1(
            self.stashmaster_directory_path)
        return parser.get_lookup_dict()

    def get_stashmaster_meta_lookup_dict(self):
        """Provide the metadata for STASHmaster records."""
        return stash_parse.get_stashmaster_meta_lookup_dict_v1(
            STASHMASTER_META_PATH, STASHMASTER_META_FILENAME)

    def get_focus_chooser(self):
        """Get either the last selected button or the last one."""
        return self.choosers[-1]

    def generate_buttons(self):
        """Create the add button."""
        add_image = gtk.image_new_from_stock(
            gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        add_image.show()
        self.add_button = gtk.Button()
        self.add_button.set_image(add_image)
        self.add_button.set_tooltip_text(self.TIP_ADD)
        self.add_button.connect("clicked",
                                lambda b: self.add_chooser())
        self.button_box = gtk.VBox()
        self.button_box.show()
        self.button_box.pack_start(self.add_button, expand=False, fill=False)

    def get_chooser(self, value_item):
        """Return a widget collection representing this STASH code choice."""
        return STASHCodeChooser(value_item, self._stash_lookup,
                                self._stash_meta_lookup, self.setter,
                                self.remove_chooser,
                                allowed_sections=self.ALLOWED_STASH_SECTIONS)

    def populate_table(self):
        """Populate a table with the array elements, dynamically."""
        focus = None
        table_widgets = self.choosers
        for child in self.chooser_table.get_children():
            if child.is_focus():
                focus = child
        if len(self.chooser_table.get_children()) < len(table_widgets):
            # Newly added widget, set focus to the end
            focus = self.choosers[-1]
        for child in self.chooser_table.get_children():
            self.chooser_table.remove(child)
        if (focus is None and self.chooser_table.is_focus()
            and len(self.choosers) > 0):
            focus = self.choosers[-1]
        num_fields = len(self.choosers)
        num_rows_now = num_fields
        self.chooser_table.resize(num_rows_now, 1)
        if (self.max_length.isdigit() and
            len(self.choosers) >= int(self.max_length)):
            self.add_button.hide()
        else:
            self.add_button.show()
        for i, widget in enumerate(table_widgets):
            row = i
            column = 0
            self.chooser_table.attach(widget,
                                      column, column + 1,
                                      row, row + 1,
                                      xoptions=gtk.FILL,
                                      yoptions=gtk.SHRINK)
            widget.set_remove_status((len(table_widgets) > 1))
        self.grab_focus = lambda : self.hook.get_focus(self.choosers[-1])
        self.check_resize()

    def add_chooser(self):
        """Add a new chooser widget to the array."""
        combo = self.get_chooser(self.DEFAULT_CODE)
        self.choosers.append(combo)
        self.populate_table()
        self.setter()

    def remove_chooser(self, chooser):
        """Remove a chooser widget."""
        self.choosers.remove(chooser)
        self.populate_table()
        self.setter()

    def setter(self, *args):
        """Update the value."""
        val_array = []
        for chooser in self.choosers:
            value = chooser.get_value()
            val_array.append(value)
        new_val = rose.variable.array_join(val_array)
        self.value = new_val
        self.set_value(new_val)
        self.value_array = rose.variable.array_split(self.value)
        return False


class STASHCodeChooser(gtk.HBox):

    """Represent a STASH code choice as a collection of GTK widgets.

    Arguments:
    value - a string representing a STASH code (section + item)
    stash_lookup - a nested dictionary representing STASHmaster data
    stash_meta_lookup - a nested dictionary representing metadata for
    STASHmaster data
    setter_func - a hook function to call with a new, user-set value
    remove_self_func - a hook function to call to remove this widget.

    Keyword Arguments:
    allowed_sections (default None) - a list of allowed STASH section
    strings to populate the section chooser. If None, the full list of
    STASHmaster sections in stash_lookup will be used.

    """

    FRAC_X_ALIGN = 0.9

    def __init__(self, value, stash_lookup, stash_meta_lookup, setter_func,
                 remove_self_func, allowed_sections=None):
        super(STASHCodeChooser, self).__init__(homogeneous=False)
        self.stash_lookup = stash_lookup
        self.stash_meta_lookup = stash_meta_lookup
        self.value = value
        self.setter_func = setter_func
        self.allowed_sections = allowed_sections
        request_item = str(int(value) % 1000)
        request_section = str(int(value) // 1000)
        self.error_pixbuf = self.render_icon(gtk.STOCK_DIALOG_WARNING,
                                             gtk.ICON_SIZE_MENU)
        self.combobox_section = self.get_combo_for_section(request_section)
        self.combobox_item = self.get_combo_for_item(
            request_section, request_item)
        self.remove_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        image.show()
        self.remove_button.set_image(image)
        self.remove_button.connect(
            "clicked", lambda b: remove_self_func(self))
        self.remove_button.show()
        self.pack_start(self.combobox_section, expand=False)
        self.pack_start(self.combobox_item, expand=False)
        self.pack_end(self.remove_button, expand=False)
        self.show()

    def get_combo_for_section(self, section_value):
        """Create a widget for the section choice in this array element."""
        combobox = gtk.ComboBox()
        liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        cell_error = gtk.CellRendererPixbuf()
        cell_section = gtk.CellRendererText()
        cell_section.xalign = self.FRAC_X_ALIGN
        combobox.pack_start(cell_error)
        combobox.add_attribute(cell_error, 'pixbuf', 0)
        combobox.pack_start(cell_section)
        combobox.add_attribute(cell_section, 'text', 2)

        if self.allowed_sections is None:
            section_choices = sorted(self.stash_lookup.keys(), key=int)
        else:
            section_choices = self.allowed_sections
        for section_num, section in enumerate(section_choices):
            title = self.stash_meta_lookup.get(
                stash_parse.StashMasterParserv1.SECT_OPT + "=" + section, {}
            ).get(rose.META_PROP_TITLE)
            if title is None:
                liststore.append(
                    [None, section, section])
            else:
                liststore.append(
                    [None, section, title])
        if section_value not in section_choices:
            liststore.append([self.error_pixbuf, section_value,
                              "Invalid: %s" % section_value])
        combobox.set_model(liststore)
        if section_value in section_choices:
            combobox.set_active(section_choices.index(section_value))
        else:
            combobox.set_active(section_num + 1)
        combobox.connect('changed', self.setter)
        combobox.connect('button-press-event',
                         lambda b: combobox.grab_focus())
        combobox.show()
        return combobox

    def get_combo_for_item(self, section_value, item_value):
        """Create a widget for the section choice in this array element."""
        combobox = gtk.ComboBox()
        liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        cell_error = gtk.CellRendererPixbuf()
        cell_item = gtk.CellRendererText()
        cell_item.xalign = self.FRAC_X_ALIGN
        combobox.pack_start(cell_error)
        combobox.add_attribute(cell_error, 'pixbuf', 0)
        combobox.pack_start(cell_item)
        combobox.add_attribute(cell_item, 'text', 2)

        item_choices = sorted(
            self.stash_lookup.get(section_value, {}).keys(), key=int)
        item_num = -1
        for item_num, item in enumerate(item_choices):
            name = self.stash_lookup.get(section_value, {}).get(
                item, {}).get(stash_parse.StashMasterParserv1.DESC_OPT)
            if name is None:
                liststore.append(
                    [None, item, item])
            else:
                liststore.append(
                    [None, item, name + " (" + item + ")"])
        if item_value not in item_choices:
            liststore.append([self.error_pixbuf, item_value,
                              "Invalid: %s" % item_value])
        combobox.set_model(liststore)
        if item_value in item_choices:
            combobox.set_active(item_choices.index(item_value))
        else:
            combobox.set_active(item_num + 1)
        name = self.stash_lookup.get(section_value, {}).get(
            item_value, {}).get(stash_parse.StashMasterParserv1.DESC_OPT)
        if name is not None:
            metadata = self.stash_meta_lookup.get(
                stash_parse.StashMasterParserv1.DESC_OPT + "=" + name, {})
            hover_text = ""
            for key, value in sorted(metadata.items()):
                hover_text += "%s: %s" % (key, value)
            if hover_text:
                combobox.set_tooltip_text(hover_text)
        combobox.connect('changed', self.setter)
        combobox.connect('button-press-event',
                         lambda b: combobox.grab_focus())
        combobox.show()
        return combobox

    def get_section_and_item(self):
        """Get the STASH section and item stored in the widgets."""
        section = self._get_combobox_value(self.combobox_section)
        item = self._get_combobox_value(self.combobox_item)
        return section, item

    def get_value(self):
        """Get the STASH code stored in this widget."""
        section, item = self.get_section_and_item()
        if section is None or item is None:
            return ""
        return (str(int(section)) + "%03d" % int(item)).lstrip("0")

    def set_remove_status(self, can_remove=False):
        """Set whether this set of widgets is removable."""
        self.remove_button.set_sensitive(can_remove)

    def setter(self, combobox):
        """Handle changes in settings and call the upstream hook."""
        section, item = self.get_section_and_item()
        if combobox == self.combobox_section:
            self.remove(self.combobox_item)
            self.combobox_item = self.get_combo_for_item(
                section, item)
            self.pack_start(self.combobox_item)
        self.setter_func(self.get_value())

    def _get_combobox_value(self, combobox):
        """Extract the active data represented in this combobox."""
        liststore = combobox.get_model()
        iter_ = combobox.get_active_iter()
        if iter_ is None:
            return None
        return liststore.get_value(iter_, 1)

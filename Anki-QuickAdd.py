#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import signal
import sys
import urllib.request

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QDesktopWidget
from PyQt5.QtWidgets import QLabel, QLineEdit


# Default AnkiConnect API functions
def request(action, **params):
    return {"action": action, "params": params, "version": 6}


def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode("utf-8")
    response = json.load(
        urllib.request.urlopen(
            urllib.request.Request("http://localhost:8765", requestJson)
        )
    )
    if len(response) != 2:
        raise Exception("response has an unexpected number of fields")
    if "error" not in response:
        raise Exception("response is missing required error field")
    if "result" not in response:
        raise Exception("response is missing required result field")
    if response["error"] is not None:
        raise Exception(response["error"])
    return response["result"]


# allow <Ctrl-c> from terminal to terminate the GUI
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Interface XML files
current_file_path = __file__
current_file_dir = os.path.dirname(current_file_path)
GUIui = os.path.join(current_file_dir, "AnkiQuickAdd_layout.ui")

# Build graphical interface constructed in XML
gui_window_object, gui_base_object = uic.loadUiType(GUIui)


class QuickaddGuiClass(gui_base_object, gui_window_object):
    """
    Class that constructs the PyQt graphical interface
    """

    def __init__(self):
        super(gui_base_object, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Anki QuickAdd")

        # Center GUI on screen
        qt_rectangle = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)

        # get information to populate dialog
        deck_list = invoke("deckNames")
        self.deck_comboBox.addItems(deck_list)
        model_names = invoke("modelNames")
        self.card_comboBox.addItems(model_names)

        # load fields for default card
        self.changed_card_comboBox()

        # if selected chromosome changes, create new graph for variants by position for chosen chromosome
        self.card_comboBox.currentTextChanged.connect(self.changed_card_comboBox)

        # on pressing add button, add to anki
        self.add_button.clicked.connect(self.add_fields_to_anki)

    def empty_qt_layout(self, qt_layout_name):
        while 1:
            layout_widget = qt_layout_name.takeAt(0)
            if not layout_widget:
                break
            layout_widget.widget().deleteLater()

    def changed_card_comboBox(self):
        self.empty_qt_layout(self.form_label_layout)

        card = self.card_comboBox.currentText()
        self.card_fields = invoke("modelFieldNames", modelName=card)
        self.card_fields_inputs = []
        for field in self.card_fields:
            self.form_label_layout.addWidget(QLabel(field))
            field_lineedit = QLineEdit()
            self.form_label_layout.addWidget(field_lineedit)
            self.card_fields_inputs.append(field_lineedit)

    def add_fields_to_anki(self):
        # create a dict of lineedits
        i = 0
        inputs_dict = {}
        for inputs in self.card_fields_inputs:
            inputs_dict[self.card_fields[i]] = inputs.text()
            i = i + 1

        # convert dict to json
        add_json = {
            "deckName": self.deck_comboBox.currentText(),
            "modelName": self.card_comboBox.currentText(),
            "fields": inputs_dict,
        }

        # submit json to Anki-Connect
        invoke("addNote", note=add_json)

        # close Anki QuickAdd on add
        QuickaddApp.quit()


if __name__ == "__main__":
    QuickaddApp = QApplication(sys.argv)
    QuickaddGui = QuickaddGuiClass()

    # show GUI
    QuickaddGui.show()

    # exit program on quitting the GUI
    sys.exit(QuickaddApp.exec_())

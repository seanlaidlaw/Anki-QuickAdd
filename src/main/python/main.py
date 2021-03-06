#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import platform
import pathlib
import signal
import sys
import urllib.request

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDesktopWidget, QMessageBox
from PyQt5.QtWidgets import QLabel, QLineEdit
from fbs_runtime.application_context.PyQt5 import ApplicationContext


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


# define error dialog
def throw_error_message(error_message):
    """
    Displays an error dialog with a message. Accepts one string
    as argument for the message to display.
    """
    print("Error: " + error_message)
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Critical)
    error_dialog.setWindowTitle("Error!")
    error_dialog.setText(error_message)
    error_dialog.setStandardButtons(QMessageBox.Ok)
    error_dialog.exec_()

# App context for fbs
appctxt = ApplicationContext()

# Build graphical interface constructed in XML
GUIui = appctxt.get_resource('AnkiQuickAdd_layout.ui')
gui_window_object, gui_base_object = uic.loadUiType(GUIui)


class QuickaddGuiClass(gui_base_object, gui_window_object):
    """
    Class that constructs the PyQt graphical interface
    """

    def __init__(self):
        super(gui_base_object, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Anki QuickAdd")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        # Center GUI on screen
        qt_rectangle = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)

        # determine where to store name of most recent deck/card
        home_dir = os.path.expanduser('~')
        if platform.system() == "Linux":
                quickadd_dir = home_dir + "/.anki-quickadd/"
        elif platform.system() == "Darwin":
                quickadd_dir = home_dir + "/Library/Caches/Anki-Quickadd/"
        elif platform.system() == "Windows":
                quickadd_dir = os.path.expandvars(r'%APPDATA%\Anki-Quickadd\\')

        # make data folder and parent folders if they don't exist
        pathlib.Path(quickadd_dir).mkdir(parents=True, exist_ok=True)

        self.quickadd_deck = os.path.join(quickadd_dir, "quickadd_deck.txt")
        self.quickadd_card = os.path.join(quickadd_dir, "quickadd_card.txt")


        # get information to populate dialog
        deck_list = invoke("deckNames")
        self.deck_comboBox.addItems(deck_list)
        model_names = invoke("modelNames")
        self.card_comboBox.addItems(model_names)

        # load last used deck name and card name as default
        if os.path.isfile(self.quickadd_deck):
            with open(self.quickadd_deck, "r") as myfile:
                last_deck = myfile.readline()
                index = self.deck_comboBox.findText(last_deck, Qt.MatchFixedString)
                if index >= 0:
                    self.deck_comboBox.setCurrentIndex(index)

        if os.path.isfile(self.quickadd_card):
            with open(self.quickadd_card, "r") as myfile:
                last_card = myfile.readline()
                index = self.card_comboBox.findText(last_card, Qt.MatchFixedString)
                if index >= 0:
                    self.card_comboBox.setCurrentIndex(index)

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
        tags_list = self.tags_lineedit.text()
        tags_list = tags_list.split(' ')
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
            "tags": tags_list
        }

        with open(self.quickadd_deck, "w") as myfile:
            myfile.write(self.deck_comboBox.currentText())
        with open(self.quickadd_card, "w") as myfile:
            myfile.write(self.card_comboBox.currentText())

        # submit json to Anki-Connect
        try:
            invoke("addNote", note=add_json)

            # close Anki QuickAdd on add
            QuickaddApp.quit()
        except Exception:
            throw_error_message(str(sys.exc_info()[1]))


if __name__ == "__main__":
    QuickaddApp = QApplication(sys.argv)
    QuickaddGui = QuickaddGuiClass()

    # show GUI
    QuickaddGui.show()

    # exit program on quitting the GUI
    # sys.exit(QuickaddApp.exec_())
    exit_code = appctxt.app.exec_()
    sys.exit(exit_code)

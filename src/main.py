import rosbag
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QAbstractScrollArea, QCheckBox, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QApplication
from dataclasses import dataclass
from typing import Tuple, List, Dict
import subprocess
import os

class CentralWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.tableWidget = QTableWidget(self)
        self.tableWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.tableHeaders = []
        self.clearTable()


        self.invertSelectionButton = QPushButton(self)
        self.invertSelectionButton.setText("Invert Selection")
        self.invertSelectionButton.clicked.connect(self.invertSelection)

        self.exportButton = QPushButton(self)
        self.exportButton.setText("Filter to new Rosbag")

        layout = QVBoxLayout(self)
        layout.addWidget(self.invertSelectionButton)
        layout.addWidget(self.exportButton)
        layout.addWidget(self.tableWidget)

        self.setLayout(layout)

    def setTableHeaders(self, headers):
        self.tableHeaders = headers

    def clearTable(self):
        self.tableWidget.clearContents()
        self.checkboxWidgets = []
        self.tableWidget.setHorizontalHeaderLabels(self.tableHeaders)

    def isSelected(self, index):
        return self.checkboxWidgets[index].isChecked()

    def setDisableCheckboxes(self, isDisabled):
        for checkboxWidget in self.checkboxWidgets:
            checkboxWidget.setDisabled(isDisabled)


    def setRow(self, row, fields):
        # Need to fix
        checkboxCellWidget = QWidget()
        checkbox = QCheckBox()
        self.checkboxWidgets.append(checkbox)
        layout = QHBoxLayout(checkboxCellWidget)
        layout.addWidget(checkbox)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        checkboxCellWidget.setLayout(layout)

        self.tableWidget.setCellWidget(row, 0, checkboxCellWidget)
        for index, field in enumerate(fields):
            self.tableWidget.setItem(row, 1 + index, QTableWidgetItem(field))

        self.tableWidget.resizeColumnsToContents()

    def invertSelection(self):
        for checkboxWidget in self.checkboxWidgets:
            checkboxWidget.setChecked(not checkboxWidget.isChecked())



class MainWindow(QtWidgets.QMainWindow):

    class DisplayMode:
        BY_TOPIC = 0
        BY_MESSAGE_TYPE = 1

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Rosbag Filter GUI")

        self.resize(640, 480)

        self.mainWidget = CentralWidget()
        self.setCentralWidget(self.mainWidget)


        self.fileMenu = self.menuBar().addMenu("File")
        self.loadBag = QtWidgets.QAction("Load Bagfile(s)", self)
        self.fileMenu.addAction(self.loadBag)

        self.displayMode = MainWindow.DisplayMode.BY_TOPIC

    def displayRosbags(self, rosbagList):
        self.rosbags = rosbagList

        if self.displayMode == MainWindow.DisplayMode.BY_TOPIC:

            self.mainWidget.setTableHeaders(("To Export", "Topic", "Message Type"))
            self.mainWidget.clearTable()

            for rosbag in self.rosbags:
                row = 0
                for messageType in rosbag.messageTypes:
                    for topic in rosbag.messageTypesToTopicsDict[messageType]:
                        self.view.mainWidget.setRow(row, (topic, messageType))
                        row += 1
                break # Temporary

        elif self.displayMode == MainWindow.DisplayMode.BY_MESSAGE_TYPE:

            for rosbag in self.rosbags:
                pass






    def promptForBagFiles(self):

        fileChooser = QFileDialog(self)
        fileChooser.setWindowTitle("Select Bag File(s)")
        fileChooser.setFileMode(QFileDialog.FileMode.ExistingFiles)
        fileChooser.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        fileChooser.setNameFilter("*.bag")

        if fileChooser.exec_():
            return fileChooser.selectedFiles()
        return []

    def promptForSaveLocation(self):

        fileChooser = QFileDialog(self)
        fileChooser.setWindowTitle("Select save location for new rosbag file")
        fileChooser.setFileMode(QFileDialog.FileMode.DirectoryOnly)
        fileChooser.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        fileChooser.setNameFilter("*.bag")

        if fileChooser.exec_():
            return fileChooser.selectedFiles()
        return ""

    def warning(self, title, msg):
        self._message(title, msg, QMessageBox.Icon.Warning, QMessageBox.StandardButton.Ok)

    def message(self, title, msg):
        self._message(title, msg, QMessageBox.Icon.Information, QMessageBox.StandardButton.Ok)

    def _message(self, title, msg, icon, buttons):
        messageBox = QMessageBox()
        messageBox.setIcon(icon)
        messageBox.setText(msg)
        messageBox.setWindowTitle(title)
        messageBox.setStandardButtons(buttons)
        messageBox.exec_()






class Controller:

    class State:

        WAITING_FOR_FILE = 0
        SELECTING_TOPICS = 1
        EXPORTING = 2


    def __init__(self):

        self.view = MainWindow()

        self.view.loadBag.triggered.connect(self.loadBag)

        self.view.mainWidget.exportButton.clicked.connect(self.export)

        self.__transition(Controller.State.WAITING_FOR_FILE)

    def __transition(self, state):

        if state == Controller.State.WAITING_FOR_FILE:
            self.view.menuBar().setDisabled(False)

            self.view.mainWidget.exportButton.setDisabled(True)
            self.view.mainWidget.invertSelectionButton.setDisabled(True)

            self.view.mainWidget.setDisableCheckboxes(True)

        elif state == Controller.State.SELECTING_TOPICS:
            self.view.menuBar().setDisabled(False)

            self.view.mainWidget.exportButton.setDisabled(False)
            self.view.mainWidget.invertSelectionButton.setDisabled(False)

            self.view.mainWidget.setDisableCheckboxes(False)

        elif state == Controller.State.EXPORTING:
            self.view.menuBar().setDisabled(True)

            self.view.mainWidget.exportButton.setDisabled(True)
            self.view.mainWidget.invertSelectionButton.setDisabled(True)

            self.view.mainWidget.setDisableCheckboxes(True)


    def run(self):

        self.view.show()

    def export(self):

        bagFileSavePath = self.view.promptForSaveLocation()

        if bagFileSavePath == "":
            self.view.warning("File Export Failed", "Need to select save locataion in order to export bag files")
            return None

        self.__transition(Controller.State.EXPORTING)

        exporting_topics = []
        for index, topic in enumerate(self.orderedTopics):
            if self.view.mainWidget.isSelected(index):
                exporting_topics.append(topic)

        bagFileSavePath = bagFileSavePath[0]

        command = self.generate_rosbag_filter_command(self.rosbags[0].filename, bagFileSavePath, exporting_topics)

        os.system(" ".join(command))

        self.view.message("Success", f"Rosbag exported successfully: {bagFileSavePath}")

        self.__transition(Controller.State.SELECTING_TOPICS)

    @classmethod
    def generate_rosbag_filter_command(cls, inputBagFile, outputBagFile, topics, flags=None) -> List[str]:
        filterArgs = " or ".join([f"topic == '{topic}'" for topic in topics])
        cmd = ["rosbag", "filter", inputBagFile, outputBagFile, f"\"{filterArgs}\""]
        return cmd

    def loadBag(self):

        bagFilePaths = self.view.promptForBagFiles()

        if len(bagFilePaths) < 1:
            self.view.warning("File Open Failed", "Invalid Bag File")
            return None


        self.rosbags = []

        for bagFilePath in bagFilePaths:
            bag = rosbag.Bag(bagFilePath)

            # Dictionary of topic -> topic information
            topicDict = bag.get_type_and_topic_info()[1]
            topics = [str(key) for key in topicDict.keys()]
            topics.sort()
            topics = tuple(topics)

            # Dictionary of message type -> topic name
            messageTypeDict : Dict[str, List[str]]= {}

            # Populating messageTypeDict
            for topic in topics:
                messageType = topicDict[topic].msg_type

                # If this is the first topic that we have found to be publishing this type of message
                if messageType not in messageTypeDict.keys():
                    messageTypeDict[messageType] = []

                messageTypeDict[messageType].append(topic)

            messageTypes = [str(key) for key in messageTypeDict.keys()]
            messageTypes.sort()
            messageTypes = tuple(messageTypes)

            self.rosbags.append(RosbagData(bagFilePath, topics, messageTypes, messageTypeDict))

        bag = self.rosbags[0]
        self.view.mainWidget.tableWidget.setRowCount(len(bag.topics))
        self.view.mainWidget.tableWidget.setColumnCount(3)
        self.view.mainWidget.setTableHeaders(("To Export", "Topic", "Message Type"))

        row = 0
        self.view.mainWidget.clearTable()
        self.orderedTopics = []
        for messageType in bag.messageTypes:
            for topic in bag.messageTypesToTopicsDict[messageType]:
                self.view.mainWidget.setRow(row, topic, messageType)
                self.orderedTopics.append(topic)
                row += 1

        self.__transition(Controller.State.SELECTING_TOPICS)


@dataclass
class RosbagData:
    filename: str
    topics: Tuple[str, ...]
    messageTypes: Tuple[str, ...]
    messageTypesToTopicsDict: Dict[str, List[str]]
    exporting: bool = False

    def setExporting(self, willExport):
        self.exporting = willExport






if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("Rosbag Filter GUI")

    ctrl = Controller()

    ctrl.run()
    exit(app.exec_())






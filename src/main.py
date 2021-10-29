import rosbag
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QAbstractScrollArea, QCheckBox, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QRadioButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QApplication
from dataclasses import dataclass
from typing import Tuple, List, Dict
import subprocess
from datetime import datetime
import os

class CentralWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.tableWidget = QTableWidget(self)
        self.tableWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.clearTable()

        self.invertSelectionButton = QPushButton(self)
        self.invertSelectionButton.setText("Invert Selection")
        self.invertSelectionButton.clicked.connect(self.invertSelection)

        self.exportButton = QPushButton(self)
        self.exportButton.setText("Filter to new Rosbag")

        self.displayOptions = QWidget()

        self.displayByTopic = True
        self.byTopicRadioButton = QRadioButton("By Topic")
        self.byMessageTypeRadioButton = QRadioButton("By Message Type")

        self.byTopicRadioButton.setChecked(True)
        self.byTopicRadioButton.toggled.connect(self.onByTopicToggle)
        self.byMessageTypeRadioButton.toggled.connect(self.onByMessageTypeToggle)

        displayOptionsLayout = QHBoxLayout()
        displayOptionsLayout.addWidget(self.byTopicRadioButton)
        displayOptionsLayout.addWidget(self.byMessageTypeRadioButton)
        self.displayOptions.setLayout(displayOptionsLayout)

        layout = QVBoxLayout(self)
        layout.addWidget(self.invertSelectionButton)
        layout.addWidget(self.exportButton)
        layout.addWidget(self.displayOptions)
        layout.addWidget(self.tableWidget)

        self.setLayout(layout)


    def clearTable(self):
        self.tableWidget.clear()
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(0)
        self.checkboxWidgets = {}
        self.tableHeaders = []

    def initializeTable(self, rowCount, colCount, headers):
        self.tableHeaders = headers
        self.tableWidget.setRowCount(rowCount)
        self.tableWidget.setColumnCount(colCount)
        self.tableWidget.setHorizontalHeaderLabels(self.tableHeaders)

    def setDisableCheckboxes(self, isDisabled):
        for checkboxWidget in self.checkboxWidgets.keys():
            checkboxWidget.setDisabled(isDisabled)

    def getSelectedTopics(self):

        topics = []
        for checkboxWidget in self.checkboxWidgets.keys():

            if not checkboxWidget.isChecked():
                continue

            if self.displayByTopic:
                topics.append(self.checkboxWidgets[checkboxWidget])
            else:
                messageType = self.checkboxWidgets[checkboxWidget]
                topics.extend(self.messageTypeToTopicsDict[messageType])

        return topics


    def setRow(self, row, checkbox, fields):
        checkboxCellWidget = QWidget()
        layout = QHBoxLayout(checkboxCellWidget)
        layout.addWidget(checkbox)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        checkboxCellWidget.setLayout(layout)

        self.tableWidget.setCellWidget(row, 0, checkboxCellWidget)
        for index, field in enumerate(fields):
            self.tableWidget.setItem(row, 1 + index, QTableWidgetItem(field))

        self.tableWidget.resizeColumnsToContents()

    def invertSelection(self):
        for checkboxWidget in self.checkboxWidgets.keys():
            checkboxWidget.setChecked(not checkboxWidget.isChecked())

    def onByTopicToggle(self):
        radioButton = self.sender()
        if radioButton.isChecked():
            self.displayByTopic = True
            self.updateDisplay()

    def onByMessageTypeToggle(self):
        radioButton = self.sender()
        if radioButton.isChecked():
            self.displayByTopic = False
            self.updateDisplay()

    def updateDisplay(self):

        if self.displayByTopic:

            self.clearTable()
            self.initializeTable(len(self.topics), 3, ("To Export", "Topic", "Message Type"))

            row = 0

            messageTypesSorted = list(self.messageTypes)
            messageTypesSorted.sort()

            for messageType in messageTypesSorted:

                # Getting the topics of this type of message
                topicsOfTypeSorted = list(self.messageTypeToTopicsDict[messageType])
                topicsOfTypeSorted.sort()

                for topic in topicsOfTypeSorted:
                    checkbox = QCheckBox()
                    self.checkboxWidgets[checkbox] = topic
                    self.setRow(row, checkbox, (topic, messageType))
                    row += 1

        else:

            self.clearTable()
            self.initializeTable(len(self.messageTypes), 3, ("To Export", "Message Type", "Topics"))

            row = 0

            messageTypesSorted = list(self.messageTypes)
            messageTypesSorted.sort()

            for messageType in messageTypesSorted:

                topicsOfTypeSorted = list(self.messageTypeToTopicsDict[messageType])
                topicsOfTypeSorted.sort()

                topicsOfTypeString = ",".join(topicsOfTypeSorted)

                checkbox = QCheckBox()
                self.checkboxWidgets[checkbox] = messageType

                self.setRow(row, checkbox, (messageType, topicsOfTypeString))
                row += 1


    def displayRosbags(self, topics, messageTypes, messageTypeToTopicsDict):

        self.topics = topics
        self.messageTypes = messageTypes
        self.messageTypeToTopicsDict = messageTypeToTopicsDict

        self.updateDisplay()




class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Rosbag Filter GUI")

        self.resize(640, 480)

        self.mainWidget = CentralWidget()
        self.setCentralWidget(self.mainWidget)


        self.fileMenu = self.menuBar().addMenu("File")
        self.loadBag = QtWidgets.QAction("Load Bagfile(s)", self)
        self.fileMenu.addAction(self.loadBag)


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

            self.view.mainWidget.byTopicRadioButton.setDisabled(True)
            self.view.mainWidget.byMessageTypeRadioButton.setDisabled(True)

            self.view.mainWidget.setDisableCheckboxes(True)

        elif state == Controller.State.SELECTING_TOPICS:
            self.view.menuBar().setDisabled(False)

            self.view.mainWidget.exportButton.setDisabled(False)
            self.view.mainWidget.invertSelectionButton.setDisabled(False)

            self.view.mainWidget.byTopicRadioButton.setDisabled(False)
            self.view.mainWidget.byMessageTypeRadioButton.setDisabled(False)

            self.view.mainWidget.setDisableCheckboxes(False)

        elif state == Controller.State.EXPORTING:
            self.view.menuBar().setDisabled(True)

            self.view.mainWidget.exportButton.setDisabled(True)
            self.view.mainWidget.invertSelectionButton.setDisabled(True)

            self.view.mainWidget.byTopicRadioButton.setDisabled(True)
            self.view.mainWidget.byMessageTypeRadioButton.setDisabled(True)

            self.view.mainWidget.setDisableCheckboxes(True)


    def run(self):

        self.view.show()

    def export(self):

        exporting_topics = self.view.mainWidget.getSelectedTopics()

        if len(exporting_topics) < 1:
            self.view.warning("File Export Failed", "No Topics were selected to export")
            return None

        bagFileSavePathList = self.view.promptForSaveLocation()

        if len(bagFileSavePathList) != 1:
            self.view.warning("File Export Failed", "Can only select one directory to save to")
            return None

        bagFileSavePath = bagFileSavePathList[0]

        if bagFileSavePath == "":
            self.view.warning("File Export Failed", "Need to select save locataion in order to export bag files")
            return None

        self.__transition(Controller.State.EXPORTING)


        for rosbag in self.rosbags:
            filename = "".join(os.path.basename(rosbag.filename).split(".")[:-1]) + "_filtered_" + datetime.now().strftime("%Y_%m_%d-%I:%M:%S_%p") + ".bag"
            bagFileSavePathIncludingFile = os.path.join(bagFileSavePath, filename)
            command = self.generate_rosbag_filter_command(rosbag.filename, bagFileSavePathIncludingFile, exporting_topics)
            commandStr = " ".join(command)
            print(commandStr)
            os.system(commandStr)

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
        self.allTopics = set()
        allMessageTypes = set()
        allMessageTypesToTopicsDict = dict()

        for bagFilePath in bagFilePaths:
            bag = rosbag.Bag(bagFilePath)

            # Dictionary of topic -> topic information
            topicDict = bag.get_type_and_topic_info()[1]
            topics = [str(key) for key in topicDict.keys()]
            topics.sort()
            topics = tuple(topics)

            self.allTopics.update(topics)

            # Dictionary of message type -> topic name
            messageTypeDict : Dict[str, List[str]]= {}

            # Populating messageTypeDict
            for topic in topics:
                messageType = topicDict[topic].msg_type

                if messageType not in allMessageTypesToTopicsDict.keys():
                    allMessageTypesToTopicsDict[messageType] = set()

                allMessageTypesToTopicsDict[messageType].add(topic)


                # If this is the first topic that we have found to be publishing this type of message
                if messageType not in messageTypeDict.keys():
                    messageTypeDict[messageType] = []

                messageTypeDict[messageType].append(topic)

            messageTypes = [str(key) for key in messageTypeDict.keys()]
            messageTypes.sort()
            messageTypes = tuple(messageTypes)

            allMessageTypes.update(messageTypes)

            self.rosbags.append(RosbagData(bagFilePath, topics, messageTypes, messageTypeDict))

        self.view.mainWidget.displayRosbags(self.allTopics, allMessageTypes, allMessageTypesToTopicsDict)

        """
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
        """

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






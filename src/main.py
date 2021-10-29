import rosbag
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QAbstractScrollArea, QCheckBox, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QRadioButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QApplication
from dataclasses import dataclass
from typing import Tuple, List, Dict, Set
from datetime import datetime
import os

class CentralWidget(QWidget):
    """
    PyQt5 Widget that has some buttons and a table to view ROS Topics/Message Types.
    """

    def __init__(self, parent=None):
        """
        Initializes CentralWidget, creates: QTableWidget to show Topics/Message Types, 
        A button to invert current selection of topics/messages, a button to export the data,
        and two radio buttons that determine the display mode that the table shows. These two
        modes are either by topic or by message type.
        """
        super().__init__(parent=parent)

        self.tableWidget = QTableWidget(self)
        # Allows table to be resized to fit the largest text
        self.tableWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        # Initializes table by clearing it
        self.clearTable()

        # Making the button that inverts the selection
        self.invertSelectionButton = QPushButton(self)
        self.invertSelectionButton.setText("Invert Selection")
        self.invertSelectionButton.clicked.connect(self.invertSelection)

        # Making the button the exports the data (event is linked up in Controller class)
        self.exportButton = QPushButton(self)
        self.exportButton.setText("Filter to new Rosbag")

        # Creating parent widget to hold the two radio buttons
        self.displayOptions = QWidget()

        # Creating the two radio buttons
        self.byTopicRadioButton = QRadioButton("By Topic")
        self.byMessageTypeRadioButton = QRadioButton("By Message Type")

        # When True, display rosbag in a table by topic
        # When False, display rosbag in a table by message type
        self.displayByTopic = True
        self.byTopicRadioButton.setChecked(self.displayByTopic)
        self.byMessageTypeRadioButton.setChecked(not self.displayByTopic)

        # Linking up button events
        self.byTopicRadioButton.toggled.connect(self.onByTopicToggle)
        self.byMessageTypeRadioButton.toggled.connect(self.onByMessageTypeToggle)

        # Laying out buttons horizontally within parent widget
        displayOptionsLayout = QHBoxLayout()
        displayOptionsLayout.addWidget(self.byTopicRadioButton)
        displayOptionsLayout.addWidget(self.byMessageTypeRadioButton)
        self.displayOptions.setLayout(displayOptionsLayout)

        # Creating layout for CentralWidget
        layout = QVBoxLayout(self)
        layout.addWidget(self.invertSelectionButton)
        layout.addWidget(self.exportButton)
        layout.addWidget(self.displayOptions)
        layout.addWidget(self.tableWidget)

        # Applying the created layout
        self.setLayout(layout)


    def clearTable(self):
        """
        Clears the current table by setting rowCount and ColCount to 0. 
        Also clears the dictionary keeping track of checkboxes
        """
        self.tableWidget.clear()
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(0)

        # Dictionary storing mapping checkboxes to their respective topic/message type
        self.checkboxWidgets: Dict[QCheckBox, str] = {}


    def initializeTable(self, rowCount, colCount, headers):
        """
        Sets the size of the table, and the headers
        """
        self.tableWidget.setRowCount(rowCount)
        self.tableWidget.setColumnCount(colCount)
        self.tableWidget.setHorizontalHeaderLabels(headers)

    def setDisableCheckboxes(self, isDisabled):
        """
        Disables/Enables all checkboxes based on the input parameter
        """
        for checkboxWidget in self.checkboxWidgets.keys():
            checkboxWidget.setDisabled(isDisabled)

    def getSelectedTopics(self):
        """
        Returns a list of strings of all of the currently selected topics based on
        the checkboxes
        """

        # All the the selected topics will be put into this list
        topics = []

        # Iterating through each checkbox in the table
        for checkboxWidget in self.checkboxWidgets.keys():

            # Skip if not checked
            if not checkboxWidget.isChecked():
                continue

            # If the table's primary key is topic, then the checkboxWidgets Dict is Checkbox -> Topic string
            if self.displayByTopic:
                topics.append(self.checkboxWidgets[checkboxWidget])
            # Else, the checkboxWidgets Dict is Checkbox -> Message type
            else:
                messageType = self.checkboxWidgets[checkboxWidget]

                # Lookup the topics corresponding to this message type
                topics.extend(self.messageTypeToTopicsDict[messageType])

        return topics


    def setRow(self, row, checkbox, fields):
        """
        Adds a row to the table with the corresponding checkbox in each row to allow each row to
        effectively be selected
        """

        # Centering the checkbox
        checkboxCellWidget = QWidget()
        layout = QHBoxLayout(checkboxCellWidget)
        layout.addWidget(checkbox)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        checkboxCellWidget.setLayout(layout)


        # Set the first column in this row to be the checkbox
        self.tableWidget.setCellWidget(row, 0, checkboxCellWidget)

        # Set the remaining columns in this row to be the provided fields
        for index, field in enumerate(fields):
            self.tableWidget.setItem(row, 1 + index, QTableWidgetItem(field))

        # Resize the table to make sure text fits within the columns
        self.tableWidget.resizeColumnsToContents()

    def invertSelection(self):
        """
        Inverts the current selection of checkboxes in the table
        """
        for checkboxWidget in self.checkboxWidgets.keys():
            checkboxWidget.setChecked(not checkboxWidget.isChecked())

    def onByTopicToggle(self):
        """
        Callback function for when the "By Topic" radio button gets toggled
        """
        radioButton = self.sender()

        # Only want to update when the button is checked
        if radioButton.isChecked():
            self.displayByTopic = True
            self.updateDisplay()

    def onByMessageTypeToggle(self):
        """
        Callback function for when the "By Message Type" radio button gets toggled
        """
        radioButton = self.sender()

        # Only want to update when the button is checked
        if radioButton.isChecked():
            self.displayByTopic = False
            self.updateDisplay()

    def updateDisplay(self):
        """
        Updates the table display, either to be "By Topic" or "By Message Type"
        """

        if self.displayByTopic:

            self.clearTable()
            self.initializeTable(len(self.topics), 3, ("To Export", "Topic", "Message Type"))

            row = 0

            # Getting sorted message types
            messageTypesSorted = list(self.messageTypes)
            messageTypesSorted.sort()

            for messageType in messageTypesSorted:

                # Getting the topics of this type of message
                topicsOfTypeSorted = list(self.messageTypeToTopicsDict[messageType])
                topicsOfTypeSorted.sort()

                # For each topic that this message type corresponds to
                for topic in topicsOfTypeSorted:

                    # Setting up checkbox so we can lookup what topic it corresponds to later on
                    checkbox = QCheckBox()
                    self.checkboxWidgets[checkbox] = topic
                    self.setRow(row, checkbox, (topic, messageType))
                    row += 1

        else:

            self.clearTable()
            self.initializeTable(len(self.messageTypes), 3, ("To Export", "Message Type", "Topics"))

            row = 0

            # Getting sorted message types
            messageTypesSorted = list(self.messageTypes)
            messageTypesSorted.sort()

            for messageType in messageTypesSorted:

                # Getting the topics of this type of message
                topicsOfTypeSorted = list(self.messageTypeToTopicsDict[messageType])
                topicsOfTypeSorted.sort()

                # Combining all topics of this message type into one string
                topicsOfTypeString = ", ".join(topicsOfTypeSorted)

                # Setting up checkbox so we can lookup what message type it corresponds to later on
                checkbox = QCheckBox()
                self.checkboxWidgets[checkbox] = messageType

                self.setRow(row, checkbox, (messageType, topicsOfTypeString))
                row += 1


    def displayRosbags(self, topics, messageTypes, messageTypeToTopicsDict):
        """
        Sets the view's internal state to know what topics, message types there are to display,
        and then displays them
        """

        self.topics = topics
        self.messageTypes = messageTypes
        self.messageTypeToTopicsDict = messageTypeToTopicsDict

        self.updateDisplay()




class MainWindow(QMainWindow):
    """
    Main window in this application
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Rosbag Filter GUI")
        self.resize(640, 480)

        self.mainWidget = CentralWidget()
        self.setCentralWidget(self.mainWidget)

        # Setting up load file menu
        self.fileMenu = self.menuBar().addMenu("File")
        self.loadBag = QtWidgets.QAction("Load Bagfile(s)", self)
        self.fileMenu.addAction(self.loadBag)


    def promptForBagFiles(self):
        """
        Helper function that prompts for existing rosbag files
        """

        fileChooser = QFileDialog(self)
        fileChooser.setWindowTitle("Select Bag File(s)")
        fileChooser.setFileMode(QFileDialog.FileMode.ExistingFiles)
        fileChooser.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        fileChooser.setNameFilter("*.bag")

        if fileChooser.exec_():
            return fileChooser.selectedFiles()
        return []

    def promptForSaveLocation(self):
        """
        Helper function that prompts for a directory to save files in
        """

        fileChooser = QFileDialog(self)
        fileChooser.setWindowTitle("Select save location for new rosbag file")
        fileChooser.setFileMode(QFileDialog.FileMode.DirectoryOnly)
        fileChooser.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        fileChooser.setNameFilter("*.bag")

        if fileChooser.exec_():
            return fileChooser.selectedFiles()
        return []

    def warning(self, title, msg):
        """
        Helper function that displays a warning message on screen
        """
        self._message(title, msg, QMessageBox.Icon.Warning, QMessageBox.StandardButton.Ok)

    def message(self, title, msg):
        """
        Helper function that displays a message on screen
        """
        self._message(title, msg, QMessageBox.Icon.Information, QMessageBox.StandardButton.Ok)

    def _message(self, title, msg, icon, buttons):
        """
        Helper function used to create a QMessageBox
        """
        messageBox = QMessageBox()
        messageBox.setIcon(icon)
        messageBox.setText(msg)
        messageBox.setWindowTitle(title)
        messageBox.setStandardButtons(buttons)
        messageBox.exec_()






class Controller:
    """
    Main controller behind this application. Part of a MVC design, except the Model is basically the 
    rosbag file(s). This controller parses the bag files and sends the topic/message type information
    to the view, and handles exporting.
    """

    class State:
        """
        Internal state to handle disabling UI elements when they should not be used
        """
        WAITING_FOR_FILE = 0
        SELECTING_TOPICS = 1
        EXPORTING = 2


    def __init__(self):

        self.view = MainWindow()

        # Connecting callback for when the load button is pressed
        self.view.loadBag.triggered.connect(self.loadBag)
        # Connecting callback for when the export button is pressed
        self.view.mainWidget.exportButton.clicked.connect(self.export)

        # Transition states to be waiting for a file(s)
        self.__transition(Controller.State.WAITING_FOR_FILE)

    def __transition(self, state):
        """
        Internal method used to transition to a new state, that handles enabling/disabling
        UI elements in the view
        """

        if state == Controller.State.WAITING_FOR_FILE:
            # Only allow the user to select a file from the menu bar
            self.view.menuBar().setDisabled(False)

            # Disable everything else
            self.view.mainWidget.exportButton.setDisabled(True)
            self.view.mainWidget.invertSelectionButton.setDisabled(True)

            self.view.mainWidget.byTopicRadioButton.setDisabled(True)
            self.view.mainWidget.byMessageTypeRadioButton.setDisabled(True)

            self.view.mainWidget.setDisableCheckboxes(True)

        elif state == Controller.State.SELECTING_TOPICS:
            # Enable everything after a file is loaded and the user is selecting topics
            self.view.menuBar().setDisabled(False)

            self.view.mainWidget.exportButton.setDisabled(False)
            self.view.mainWidget.invertSelectionButton.setDisabled(False)

            self.view.mainWidget.byTopicRadioButton.setDisabled(False)
            self.view.mainWidget.byMessageTypeRadioButton.setDisabled(False)

            self.view.mainWidget.setDisableCheckboxes(False)

        elif state == Controller.State.EXPORTING:
            # Disable everything while exporting
            self.view.menuBar().setDisabled(True)

            self.view.mainWidget.exportButton.setDisabled(True)
            self.view.mainWidget.invertSelectionButton.setDisabled(True)

            self.view.mainWidget.byTopicRadioButton.setDisabled(True)
            self.view.mainWidget.byMessageTypeRadioButton.setDisabled(True)

            self.view.mainWidget.setDisableCheckboxes(True)


    def run(self):
        """
        Entry point
        """
        self.view.show()

    def export(self):
        """
        Exports the rosbag files with their filtered topics
        """

        # Gets the topics to save from the view based on user selection
        exporting_topics = self.view.mainWidget.getSelectedTopics()

        # If the user selected no topics, lets not waste time and export empty rosbag files
        if len(exporting_topics) < 1:
            self.view.warning("File Export Failed", "No Topics were selected to export")
            return None

        # Get save directory
        bagFileSavePathList = self.view.promptForSaveLocation()

        # If the user selected more than one directory (should never happen), don't proceed with exporting
        if len(bagFileSavePathList) != 1:
            self.view.warning("File Export Failed", "Can only select one directory to save to")
            return None

        # The save location method returns a list of files/directories, so just get the 1st and only one
        bagFileSavePath = bagFileSavePathList[0]

        # If the path is empty, we cannot save there
        if bagFileSavePath == "":
            self.view.warning("File Export Failed", "Need to select save locataion in order to export bag files")
            return None

        # Transition to exporting state so that the user cannot break anything with the UI
        self.__transition(Controller.State.EXPORTING)


        # Iterate through rosbags and export them
        for rosbag in self.rosbags:

            # Gets the filename (without the path) of the rosbag file, removes the file extension, and appends a suffix to indicate that it has been filtered
            filename = "".join(os.path.basename(rosbag.filename).split(".")[:-1]) + "_filtered_" + datetime.now().strftime("%Y_%m_%d-%I:%M:%S_%p") + ".bag"
            bagFileSavePathIncludingFile = os.path.join(bagFileSavePath, filename)

            # Generate command to execute
            command = self.generate_rosbag_filter_command(rosbag.filename, bagFileSavePathIncludingFile, exporting_topics)
            commandStr = " ".join(command)

            # Print the command we are running incase the user wants to copy it
            print(commandStr)

            # Run's command
            os.system(commandStr)

        self.view.message("Success", f"Rosbag exported successfully: {bagFileSavePath}")


        # Transition back to selecting topics state to let the user use the UI again
        self.__transition(Controller.State.SELECTING_TOPICS)

    @classmethod
    def generate_rosbag_filter_command(cls, inputBagFile, outputBagFile, topics) -> List[str]:
        """
        Creates a command from input variables in the format required for command line tool
        """
        filterArgs = " or ".join([f"topic == '{topic}'" for topic in topics])
        cmd = ["rosbag", "filter", inputBagFile, outputBagFile, f"\"{filterArgs}\""]
        return cmd

    def loadBag(self):
        """
        Callback for the load files menu option in the view. Loads a rosbag file(s)
        """

        # Gets the file paths for all files to open
        bagFilePaths = self.view.promptForBagFiles()

        # If no files we returned, return early
        if len(bagFilePaths) < 1:
            self.view.warning("File Open Failed", "Invalid Bag File")
            return None

        # Keeps track of all individual files, and their topics, message types
        self.rosbags: List[RosbagData] = []
        # Keeps track of every single topic we find in all selected rosbag files
        self.allTopics: Set[str] = set()
        # Keeps track of every single message type we find in all selected rosbag files
        allMessageTypes: Set[str] = set()
        # Keeps track of a map between message type and every single topic that corresponds to that message type
        allMessageTypesToTopicsDict: Dict[str, Set[str]] = dict()

        # Iterating through each selected rosbag file
        for bagFilePath in bagFilePaths:

            # Parse file
            bag = rosbag.Bag(bagFilePath)

            # Dictionary of topic -> topic information
            topicDict = bag.get_type_and_topic_info()[1]
            topics = [str(key) for key in topicDict.keys()]
            topics.sort()
            topics = tuple(topics)

            # Adds all topics in "topics" to the set "alltopics"
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

            # Get sorted messageTypes as tuple
            messageTypes = [str(key) for key in messageTypeDict.keys()]
            messageTypes.sort()
            messageTypes = tuple(messageTypes)

            allMessageTypes.update(messageTypes)

            # Store rosbag 
            self.rosbags.append(RosbagData(bagFilePath, topics, messageTypes, messageTypeDict))

        # Display rosbag in view
        self.view.mainWidget.displayRosbags(self.allTopics, allMessageTypes, allMessageTypesToTopicsDict)

        # Transition to allow the user to now select topics
        self.__transition(Controller.State.SELECTING_TOPICS)

@dataclass
class RosbagData:
    filename: str
    topics: Tuple[str, ...]
    messageTypes: Tuple[str, ...]
    messageTypesToTopicsDict: Dict[str, List[str]]
    exporting: bool = False



if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("Rosbag Filter GUI")

    ctrl = Controller()

    ctrl.run()
    exit(app.exec_())






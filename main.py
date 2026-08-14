# import
import sys
import os

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QDateEdit
)
from PyQt5.QtSql import QSqlDatabase, QSqlQuery

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Folder that holds the .qss files, relative to this script
STYLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")


def load_stylesheet(filename: str) -> str:
    """Read a .qss file from the styles/ folder and return its contents as a string."""
    path = os.path.join(STYLE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: stylesheet '{path}' not found, using no styling.")
        return ""


# Main Class
class ActivityTracker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Activity Tracker")
        self.resize(800, 600)

        # self.setup_database()
        self.initUI()
        # self.load_activities()

    def initUI(self):
        self.date_box = QDateEdit()
        self.date_box.setDate(QDate.currentDate())

        self.activity_name = QLineEdit()
        self.activity_name.setPlaceholderText("Enter the Name of the Activity")
        self.activity_date = QLineEdit()
        self.activity_date.setPlaceholderText("Enter the Activity Date")

        self.submit_btn = QPushButton("Submit")
        self.add_btn = QPushButton("Add")
        self.delete_btn = QPushButton("Delete")
        self.clear_btn = QPushButton("Clear")
        self.dark_mode = QCheckBox("Dark Mode")

        # object names let the QSS target specific buttons (see delete_btn / clear_btn rules)
        self.delete_btn.setObjectName("delete_btn")
        self.clear_btn.setObjectName("clear_btn")

        self.dark_mode.stateChanged.connect(self.toggle_dark_mode)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)

        # Design Layout
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Activity:"))
        input_layout.addWidget(self.activity_name)
        input_layout.addWidget(QLabel("Date:"))
        input_layout.addWidget(self.date_box)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.dark_mode)

        left_layout = QVBoxLayout()
        left_layout.addLayout(input_layout)
        left_layout.addLayout(button_layout)

        self.master_layout = QHBoxLayout()
        self.master_layout.addLayout(left_layout, 2)
        self.master_layout.addWidget(self.canvas, 1)

        self.setLayout(self.master_layout)

    def toggle_dark_mode(self, state):
        sheet = "dark.qss" if state == Qt.Checked else "light.qss"
        self.setStyleSheet(load_stylesheet(sheet))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet("light.qss"))
    window = ActivityTracker()
    window.show()
    sys.exit(app.exec_())
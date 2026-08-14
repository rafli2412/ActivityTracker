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

        self.setup_database()
        self.initUI()
        self.load_activities()

    def setup_database(self):
        """Create/connect to a SQLite file next to this script and make sure the table exists."""
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "activities.db")

        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName(db_path)

        if not self.db.open():
            QMessageBox.critical(self, "Database Error", "Could not open the database.")
            sys.exit(1)

        query = QSqlQuery()
        query.exec_(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL
            )
            """
        )

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

        self.add_btn.clicked.connect(self.add_activity)
        self.delete_btn.clicked.connect(self.delete_activity)
        self.clear_btn.clicked.connect(self.clear_activities)
        self.dark_mode.stateChanged.connect(self.toggle_dark_mode)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Activity", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnHidden(0, True)  # hide the id column
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

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
        left_layout.addWidget(self.table)

        self.setLayout(left_layout)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def add_activity(self):
        name = self.activity_name.text().strip()
        date = self.date_box.date().toString("yyyy-MM-dd")

        if not name:
            QMessageBox.warning(self, "Missing Info", "Please enter an activity name.")
            return

        query = QSqlQuery()
        query.prepare("INSERT INTO activities (name, date) VALUES (?, ?)")
        query.addBindValue(name)
        query.addBindValue(date)
        query.exec_()

        self.activity_name.clear()
        self.load_activities()

    def delete_activity(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "No Selection", "Please select a row to delete.")
            return

        activity_id = self.table.item(selected, 0).text()
        query = QSqlQuery()
        query.prepare("DELETE FROM activities WHERE id = ?")
        query.addBindValue(activity_id)
        query.exec_()

        self.load_activities()

    def clear_activities(self):
        confirm = QMessageBox.question(
            self, "Confirm Clear", "Delete ALL activities?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            query = QSqlQuery()
            query.exec_("DELETE FROM activities")
            self.load_activities()

    def toggle_dark_mode(self, state):
        sheet = "dark.qss" if state == Qt.Checked else "light.qss"
        self.setStyleSheet(load_stylesheet(sheet))

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------
    def load_activities(self):
        query = QSqlQuery("SELECT id, name, date FROM activities ORDER BY date")

        self.table.setRowCount(0)

        row = 0
        while query.next():
            self.table.insertRow(row)
            id_ = query.value(0)
            name = query.value(1)
            date = query.value(2)

            self.table.setItem(row, 0, QTableWidgetItem(str(id_)))
            self.table.setItem(row, 1, QTableWidgetItem(str(name)))
            self.table.setItem(row, 2, QTableWidgetItem(str(date)))

            row += 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet("light.qss"))
    window = ActivityTracker()
    window.show()
    sys.exit(app.exec_())
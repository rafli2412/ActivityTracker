import sys
import os

from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QDateEdit
)
from PyQt5 import QtGui, QtCore

import google_backend as gbackend
import local_backend as lbackend

# Folder that holds the .css files, relative to this script
STYLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")


def load_stylesheet(filename: str) -> str:
    """Read a .css file from the styles/ folder and return its contents as a string."""
    path = os.path.join(STYLE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: stylesheet '{path}' not found, using no styling.")
        return ""

def set_app_icon(filename: str, length: int, width: int):
    app_icon = QtGui.QIcon()
    if length != width:
        print("Icon must be square!")
        return
    
    app_icon.addFile(filename, QtCore.QSize(length, width))
    
    return app_icon

# ----------------------------------------------------------------------
# Background thread so the blocking OAuth call doesn't freeze the UI
# ----------------------------------------------------------------------
class GoogleLoginThread(QThread):
    success = pyqtSignal(object)   # emits the Credentials object
    failure = pyqtSignal(str)      # emits an error message

    def run(self):
        try:
            creds = gbackend.login_with_browser()
            self.success.emit(creds)
        except Exception as exc:
            self.failure.emit(str(exc))


# ----------------------------------------------------------------------
# Login screen shown when there's no valid saved session.
# Signing in is optional -- "Continue without signing in" uses local storage.
# ----------------------------------------------------------------------
class LoginWindow(QWidget):
    def __init__(self, on_success, on_skip):
        super().__init__()
        self.on_success = on_success
        self.on_skip = on_skip
        self.login_thread = None

        self.setWindowTitle("Sign in - Activity Tracker")
        self.resize(380, 220)

        self.status_label = QLabel(
            "Sign in with your Google account to save your activities "
            "to a Google Sheet, or continue without signing in to keep "
            "them on this device."
        )
        self.status_label.setWordWrap(True)

        self.login_btn = QPushButton("Sign in with Google")
        self.login_btn.clicked.connect(self.start_login)

        self.skip_btn = QPushButton("Continue without signing in")
        self.skip_btn.setObjectName("clear_btn")
        self.skip_btn.clicked.connect(self.on_skip)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.skip_btn)
        layout.addStretch()
        self.setLayout(layout)

    def start_login(self):
        self.login_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.status_label.setText("Opening your browser to sign in with Google...")

        self.login_thread = GoogleLoginThread()
        self.login_thread.success.connect(self.handle_success)
        self.login_thread.failure.connect(self.handle_failure)
        self.login_thread.start()

    def handle_success(self, creds):
        self.on_success(creds)

    def handle_failure(self, message):
        self.login_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.status_label.setText(
            "Sign in with your Google account to save your activities "
            "to a Google Sheet, or continue without signing in to keep "
            "them on this device."
        )
        QMessageBox.critical(self, "Sign-in Failed", message)


# ----------------------------------------------------------------------
# Main Class
# ----------------------------------------------------------------------
class ActivityTracker(QWidget):
    def __init__(self, creds, on_logout):
        super().__init__()
        self.creds = creds
        self.on_logout = on_logout
        self.spreadsheet_id = None
        self.mode = "google" if creds else "local"
        self.google_login_thread = None

        self.setWindowTitle("Activity Tracker")
        self.resize(800, 600)

        self.initUI()

        if self.mode == "google":
            if not self.connect_to_sheet():
                # Google is unreachable/misconfigured -- fall back to local
                # storage instead of leaving the window broken.
                self.mode = "local"
                self.creds = None
                self.status_label.setText(
                    "Couldn't reach Google Sheets -- using local storage instead."
                )
                self.account_btn.setText("Sign in with Google")
        else:
            try:
                lbackend.ensure_ready()
            except Exception as exc:
                QMessageBox.critical(self, "Local Storage Error", f"Could not open local storage:\n{exc}")

        self.load_activities()

    # ------------------------------------------------------------------
    # Google Sheets connection
    # ------------------------------------------------------------------
    def connect_to_sheet(self):
        try:
            self.spreadsheet_id = gbackend.get_or_create_spreadsheet(self.creds)
            return True
        except Exception as exc:
            QMessageBox.critical(
                self, "Google Sheets Error",
                f"Could not connect to Google Sheets:\n{exc}"
            )
            return False

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
        self.account_btn = QPushButton("Sign out" if self.mode == "google" else "Sign in with Google")
        self.dark_mode = QCheckBox("Dark Mode")

        # object names let the css target specific buttons (see delete_btn / clear_btn rules)
        self.delete_btn.setObjectName("delete_btn")
        self.clear_btn.setObjectName("clear_btn")
        self.account_btn.setObjectName("clear_btn")

        self.add_btn.clicked.connect(self.add_activity)
        self.delete_btn.clicked.connect(self.delete_activity)
        self.clear_btn.clicked.connect(self.clear_activities)
        self.account_btn.clicked.connect(self.handle_account_action)
        self.dark_mode.stateChanged.connect(self.toggle_dark_mode)

        self.status_label = QLabel(
            "Connected to Google Sheets" if self.mode == "google" else "Using local storage (offline)"
        )

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Activity", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnHidden(0, True)  # hide the id column
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        # Design Layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()
        top_layout.addWidget(self.account_btn)

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
        left_layout.addLayout(top_layout)
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

        try:
            if self.mode == "google":
                gbackend.append_activity(self.creds, self.spreadsheet_id, name, date)
            else:
                lbackend.append_activity(name, date)
        except Exception as exc:
            QMessageBox.critical(self, "Storage Error", f"Could not save activity:\n{exc}")
            return

        self.activity_name.clear()
        self.load_activities()

    def delete_activity(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "No Selection", "Please select a row to delete.")
            return

        activity_id = self.table.item(selected, 0).text()

        try:
            if self.mode == "google":
                gbackend.delete_activity_by_id(self.creds, self.spreadsheet_id, activity_id)
            else:
                lbackend.delete_activity_by_id(int(activity_id))
        except Exception as exc:
            QMessageBox.critical(self, "Storage Error", f"Could not delete activity:\n{exc}")
            return

        self.load_activities()

    def clear_activities(self):
        confirm = QMessageBox.question(
            self, "Confirm Clear", "Delete ALL activities?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            if self.mode == "google":
                gbackend.clear_all_activities(self.creds, self.spreadsheet_id)
            else:
                lbackend.clear_all_activities()
        except Exception as exc:
            QMessageBox.critical(self, "Storage Error", f"Could not clear activities:\n{exc}")
            return

        self.load_activities()

    # ------------------------------------------------------------------
    # Account: sign out (Google mode) or sign in (local mode)
    # ------------------------------------------------------------------
    def handle_account_action(self):
        if self.mode == "google":
            self.handle_logout()
        else:
            self.start_google_signin()

    def handle_logout(self):
        confirm = QMessageBox.question(
            self, "Sign Out", "Sign out of Google? You'll need to sign in again next time.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            gbackend.logout()
            self.close()
            self.on_logout()

    def start_google_signin(self):
        self.account_btn.setEnabled(False)
        self.status_label.setText("Opening your browser to sign in with Google...")

        self.google_login_thread = GoogleLoginThread()
        self.google_login_thread.success.connect(self.handle_google_signin_success)
        self.google_login_thread.failure.connect(self.handle_google_signin_failure)
        self.google_login_thread.start()

    def handle_google_signin_success(self, creds):
        self.creds = creds
        self.mode = "google"

        if not self.connect_to_sheet():
            # Couldn't reach Sheets -- stay on local storage.
            self.mode = "local"
            self.creds = None
            self.account_btn.setEnabled(True)
            self.status_label.setText("Using local storage (offline)")
            return

        self.account_btn.setText("Sign out")
        self.account_btn.setEnabled(True)
        self.status_label.setText("Connected to Google Sheets")
        self.load_activities()
        QMessageBox.information(
            self, "Signed In",
            "You're signed in. Note: activities already saved locally were "
            "not automatically copied to Google Sheets."
        )

    def handle_google_signin_failure(self, message):
        self.account_btn.setEnabled(True)
        self.status_label.setText("Using local storage (offline)")
        QMessageBox.critical(self, "Sign-in Failed", message)

    def toggle_dark_mode(self, state):
        sheet = "dark.css" if state == Qt.Checked else "light.css"
        self.setStyleSheet(load_stylesheet(sheet))

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------
    def load_activities(self):
        try:
            if self.mode == "google":
                rows = gbackend.read_activities(self.creds, self.spreadsheet_id)
            else:
                rows = lbackend.read_activities()
        except Exception as exc:
            QMessageBox.critical(self, "Storage Error", f"Could not load activities:\n{exc}")
            return

        self.table.setRowCount(0)

        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            for col_index in range(3):
                value = row[col_index] if col_index < len(row) else ""
                self.table.setItem(row_index, col_index, QTableWidgetItem(str(value)))


# ----------------------------------------------------------------------
# App startup: decide whether to show the login screen or go straight in
# ----------------------------------------------------------------------
class AppController:
    def __init__(self):
        self.login_window = None
        self.main_window = None

    def start(self):
        creds = gbackend.load_saved_credentials()
        if creds:
            self.show_main(creds)
        else:
            self.show_login()

    def show_login(self):
        self.login_window = LoginWindow(on_success=self.show_main, on_skip=self.show_main_offline)
        self.login_window.show()

    def show_main_offline(self):
        self.show_main(None)

    def show_main(self, creds):
        if self.login_window:
            self.login_window.close()
            self.login_window = None

        self.main_window = ActivityTracker(creds, on_logout=self.show_login)
        self.main_window.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet("light.css"))
    app.setWindowIcon(set_app_icon("assets/icon.png", 16, 16))

    controller = AppController()
    controller.start()

    sys.exit(app.exec_())
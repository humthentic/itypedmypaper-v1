import ctypes
from datetime import datetime
import json
import os
from PyQt5.QtCore import Qt, QByteArray, QEventLoop, QSettings, QThread, QTimer, QUrl, QSize
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget
import sys
import zlib

from global_variables import HUMTHENTICATION_SERVER_DOMAIN
from submit_functions import read_file_content
from ui_classes import KeystrokeWorker, LoginWindow
from written_variables import COMPANY_NAME, LOGGED_IN, MAIN_MESSAGE, NO_GUARANTEE, NOW_HUMTHENTICATING, SELECT_A_FILE, SELECT_VALID_FILE, SOFTWARE_NAME, STOPPING_ACTIVITY, UI_RESET

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.keystroke_thread = None
        self.keystroke_worker = None
        self.file_list_loaded = False
        self.settings = QSettings(COMPANY_NAME, SOFTWARE_NAME)
        self.login_window = None
        self.network_manager = QNetworkAccessManager(self)
        self.work_location = "local"
        self.tokens_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tokens')
        self.tokens_file = os.path.join(self.tokens_dir, 'auth_tokens.json')
        os.makedirs(self.tokens_dir, exist_ok=True)
        self.initUI()
        self.update_ui_based_on_login()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)

        # Add logo at the top
        logo_label = QLabel(self)
        logo_pixmap = QIcon("assets/logo.png").pixmap(QSize(536, 146))  # Adjust size as needed
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        # Add stretch to push content toward middle
        layout.addStretch()

        # Create and style the status label
        self.status_label = QLabel(MAIN_MESSAGE, self)
        font = self.status_label.font()
        font.setPointSize(14)
        self.status_label.setFont(font)
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)

        # Style the Start button
        self.start_button = QPushButton("Start Humthenticating", self)
        self.start_button.setIcon(QIcon("assets/play-button.png"))
        self.start_button.setIconSize(QSize(24, 24))
        self.start_button.clicked.connect(self.start_recording)
        self.start_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_button.setEnabled(False)
        self.start_button.setMinimumHeight(50)
        self.start_button.setFont(font)

        # Style the End button
        self.end_button = QPushButton("Stop Humthenticating", self)
        self.end_button.setIcon(QIcon("assets/stop-button.png"))
        self.end_button.setIconSize(QSize(24, 24))
        self.end_button.clicked.connect(self.end_recording)
        self.end_button.setEnabled(False)
        self.end_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.end_button.setMinimumHeight(50)
        self.end_button.setFont(font)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.end_button)
        layout.addLayout(button_layout)

        # Style the login button
        self.login_button = QPushButton("Sign In for Submitted Works", self)
        self.login_button.clicked.connect(self.handle_login_logout)
        self.login_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.login_button.setMinimumHeight(50)
        self.login_button.setFont(font)
        layout.addWidget(self.login_button)

        # Add stretch to push content toward middle
        layout.addStretch()

        # Style the bottom label with smaller font
        bottom_label = QLabel(NO_GUARANTEE, self)
        bottom_label.setAlignment(Qt.AlignCenter)
        small_font = bottom_label.font()
        small_font.setPointSize(8)
        bottom_label.setFont(small_font)
        bottom_label.setWordWrap(True)
        layout.addWidget(bottom_label)

        self.setStyleSheet("""
            QWidget {
                background-color: #004477;
            }
            QPushButton {
                padding: 10px;
                border-radius: 5px;
                background-color: #f0f0f0;
                border: 2px solid #c0c0c0;
                color: black;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                background-color: #d0d0d0;
                border: 2px solid #b0b0b0;
            }
            QLabel {
                padding: 10px;
                background-color: transparent;
                color: white;
            }
        """)

        self.setLayout(layout)
        self.setWindowTitle(f"{SOFTWARE_NAME} by {COMPANY_NAME}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.showMaximized()
        icon = QIcon("assets/favicon.ico")
        self.setWindowIcon(icon)
        if sys.platform == "win32":
            myappid = 'humthentic.humthenticate.windows.0.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    def update_ui_based_on_login(self):
        tokens = self.read_tokens()
        if tokens.get('user_token') and tokens.get('session_token'):
            self.update_ui_logged_in()
        else:
            self.update_ui_logged_out()

    def read_tokens(self):
        try:
            if os.path.exists(self.tokens_file):
                with open(self.tokens_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def write_tokens(self, user_token=None, session_token=None):
        # Only write if at least one token is provided
        if user_token is not None or session_token is not None:
            tokens = {
                'user_token': user_token,
                'session_token': session_token
            }
            with open(self.tokens_file, 'w') as f:
                json.dump(tokens, f)

    def update_ui_logged_in(self):
        self.login_button.setText("Sign Out")
        self.status_label.setText(LOGGED_IN)
        self.start_button.setEnabled(True)

    def update_ui_logged_out(self):
        self.login_button.setText("Sign In and Start Typing")
        self.status_label.setText(MAIN_MESSAGE)
        self.start_button.setEnabled(False)

    def handle_login_logout(self):
        tokens = self.read_tokens()
        if tokens.get('user_token') and tokens.get('session_token'):
            self.logout()
        else:
            self.open_login_window()

    def open_login_window(self):
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.on_login_successful)
        self.login_window.show()

    def on_login_successful(self):
        self.update_ui_based_on_login()
        QMessageBox.information(self, "Signed In", "You have been successfully signed in.")

    def send_to_endpoint(self, file_path, csv_path):
        url = f"{HUMTHENTICATION_SERVER_DOMAIN}/api/humthenticate_that"
        request = QNetworkRequest(QUrl(url))
        reply = None  # Initialize reply to None
        
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        if not os.path.exists(csv_path):
            return f"CSV file not found: {csv_path}"
        
        try:
            work_content = read_file_content(file_path)
            
            with open(csv_path, 'r') as csv_file:
                keystrokes_content = [json.loads(line.strip()) for line in csv_file if line.strip()]
            
            data = {
                "work": work_content,
                "keystrokes": keystrokes_content,
                "work_tag": "desktop"
            }
            
            compressed_data = zlib.compress(json.dumps(data).encode('utf-8'))
            
            request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/octet-stream')
            request.setRawHeader(b"Content-Encoding", b"deflate")
            
            tokens = self.read_tokens()
            user_token = tokens.get('user_token')
            if user_token:
                request.setRawHeader(b"Cookie", f"user_token={user_token}".encode())
            
            reply = self.network_manager.post(request, QByteArray(compressed_data))
            
            # Wait for the request to finish
            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            loop.exec_()
            
            if reply.error() == QNetworkReply.NoError:
                response_data = reply.readAll().data().decode('utf-8')
                json_response = json.loads(response_data)
                if 'message' in json_response:
                    return json_response['message']
                else:
                    return f"Unexpected response format. Response received: {json_response}"
            else:
                return f"Error communicating with the server: {reply.errorString()}"
        
        except json.JSONDecodeError as json_err:
            return f"Invalid response from server. Raw response: {response_data[:100]}..."
        except Exception as e:
            return f"Unexpected error: {str(e)}"
        finally:
            if reply is not None:  # Only call deleteLater if reply exists
                reply.deleteLater()

    def logout(self):
        # Clear the tokens file by writing an empty dictionary
        with open(self.tokens_file, 'w') as f:
            json.dump({}, f)
        self.update_ui_logged_out()
        QMessageBox.information(self, "Logged Out", "You have been successfully logged out.")

    def start_recording(self):
        self.start_button.setEnabled(False)
        self.end_button.setEnabled(True)
        self.status_label.setText(NOW_HUMTHENTICATING)
        self.keystroke_worker = KeystrokeWorker()
        self.keystroke_thread = QThread()
        self.keystroke_worker.moveToThread(self.keystroke_thread)
        self.keystroke_thread.started.connect(self.keystroke_worker.start_recording)
        self.keystroke_worker.finished.connect(self.keystroke_thread.quit)
        self.keystroke_worker.error.connect(self.handle_error)        
        self.keystroke_thread.start()

    def end_recording(self):
        self.end_button.setEnabled(False)
        self.status_label.setText(STOPPING_ACTIVITY)
        self.spinner_label = QLabel(self)
        loading_wait = QMovie("assets/loading_spinner.gif")
        self.spinner_label.setMovie(loading_wait)
        loading_wait.start()
        self.layout().addWidget(self.spinner_label, alignment=Qt.AlignCenter)
        QApplication.processEvents()
        if self.keystroke_worker:
            self.keystroke_worker.stop_recording()
        if self.keystroke_thread:
            self.keystroke_thread.quit()
            self.keystroke_thread.wait()
        QTimer.singleShot(1000, self.post_recording_cleanup)

    def post_recording_cleanup(self):
        if hasattr(self, 'spinner_label') and self.spinner_label is not None:
            self.spinner_label.movie().stop()
            self.layout().removeWidget(self.spinner_label)
            self.spinner_label.deleteLater()
            self.spinner_label = None
        self.status_label.setText(SELECT_A_FILE)
        QApplication.processEvents()
        QTimer.singleShot(100, self.select_file)

    def select_file(self):
        valid_extension_selected = False
        while not valid_extension_selected:
            file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
            if file_path:
                if file_path.endswith(('.docx', '.doc', '.pages', '.odt', '.txt')):
                    valid_extension_selected = True
                else:
                    QMessageBox.warning(self, "Invalid File Type", SELECT_VALID_FILE)
        if file_path:
            self.process_file(file_path)
        else:
            self.reset_ui("File selected. Processing...")

    def process_file(self, file_path):
        try:
            self.confirm_send(file_path)
        except Exception as e:
            self.handle_error(str(e))

    def confirm_send(self, file_path):
        reply = QMessageBox.question(self, "Confirmation", 
                                     "Do you want to send the file to the iTypedMyPaper server?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            if os.path.exists(f'{file_name}.csv'):
                os.rename(f'{file_name}.csv', f'{file_name}_before_{int(datetime.now().timestamp())}.csv')
            os.rename('keystrokes.csv', f'{file_name}.csv')
            csv_path = f'{file_name}.csv'
            message = self.send_to_endpoint(file_path, csv_path)
        else:
            message = "Your Humthentication data has been saved locally."
        self.show_result_dialog("Humthentication Data Saved", message)
        csv_path = f'{os.path.splitext(os.path.basename(file_path))[0]}.csv'
        if os.path.exists(csv_path):
            os.remove(csv_path)
        self.show_final_message('')

    def show_final_message(self, message):
        self.status_label.setText(message)
        self.reset_ui(message)

    def reset_ui(self, message):
        message += UI_RESET
        self.status_label.setText(message)
        self.start_button.setEnabled(True)
        self.end_button.setEnabled(False)

    def handle_error(self, error_message):
        QMessageBox.critical(self, "Error", f"An error occurred: {error_message}")
        self.reset_ui(error_message)

    def show_result_dialog(self, title, result):
        result_dialog = QMessageBox(self)
        result_dialog.setWindowTitle(title)
        result_dialog.setText(result)
        result_dialog.setIcon(QMessageBox.Information)
        result_dialog.exec_()
    
    def verify_authentication(self):
        tokens = self.read_tokens()
        user_token = tokens.get('user_token')
        if user_token:
            url = QUrl(f"{HUMTHENTICATION_SERVER_DOMAIN}/api/verify_user")
            request = QNetworkRequest(url)
            request.setRawHeader(b"Cookie", f"user_token={user_token}".encode())
            
            loop = QEventLoop()
            reply = self.network_manager.get(request)
            reply.finished.connect(loop.quit)
            loop.exec_()
            
            should_clear_tokens = False
            if reply.error() == QNetworkReply.NoError:
                response_data = reply.readAll().data().decode()
                if response_data != "Killer login":
                    should_clear_tokens = True
            else:
                should_clear_tokens = True
            
            if should_clear_tokens:
                self.write_tokens()
                self.open_login_window()
            
            reply.deleteLater()
        else:
            self.open_login_window()

def main():
    if sys.platform == "win32":
        myappid = 'humthentic.humthenticate.windows.0.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/favicon.ico"))
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

import json
from pynput.keyboard import Listener
from PyQt5.QtCore import pyqtSignal, QUrl, QByteArray, QJsonDocument, QObject
from PyQt5.QtGui import QIcon
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QTextEdit, QPushButton, QVBoxLayout
import os

from global_variables import HUMTHENTICATION_SERVER_DOMAIN
from key_functions import on_press, on_release
from written_variables import SIGN_IN_HEADING

class KeystrokeWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.listener = None
    
    def start_recording(self):
        self.is_recording = True
        def on_press_wrapper(key):
            if self.is_recording:
                on_press(key)
            return self.is_recording
        def on_release_wrapper(key):
            if self.is_recording:
                on_release(key)
            return self.is_recording
        try:
            with Listener(on_press=on_press_wrapper, on_release=on_release_wrapper) as self.listener:
                self.listener.join()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.is_recording = False
            self.finished.emit()
    
    def stop_recording(self):
        self.is_recording = False
        if self.listener:
            self.listener.stop()

class LoginWindow(QWidget):
    login_successful = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self.onRequestFinished)
        self.tokens_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tokens')
        self.tokens_file = os.path.join(self.tokens_dir, 'auth_tokens.json')
        self.is_login_request = False
        self.login_successful.connect(self.close)
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setWindowTitle(SIGN_IN_HEADING)
        icon = QIcon("assets/favicon.ico")
        self.setWindowIcon(icon)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.layout.addWidget(self.status_text)

        if self.check_saved_cookie():
            self.show_logged_in_ui()
        else:
            self.show_login_ui()

        self.show()

    def check_saved_cookie(self):
        try:
            if os.path.exists(self.tokens_file):
                with open(self.tokens_file, 'r') as f:
                    tokens = json.load(f)
                    return tokens.get('user_token') and tokens.get('session_token')
        except Exception:
            pass
        return False

    def show_login_ui(self):
        self.clear_layout()

        self.username_label = QLabel("Your Email:")
        self.username_input = QLineEdit()
        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_input)

        self.password_label = QLabel("Your Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_input)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.login)
        self.layout.addWidget(self.login_button)

        self.layout.addWidget(self.status_text)

    def show_logged_in_ui(self):
        self.clear_layout()

        welcome_label = QLabel("Welcome! You are logged in.")
        self.layout.addWidget(welcome_label)

        logout_button = QPushButton("Log Out")
        logout_button.clicked.connect(self.logout)
        self.layout.addWidget(logout_button)

        self.layout.addWidget(self.status_text)

    def clear_layout(self):
        for i in reversed(range(self.layout.count())): 
            widget = self.layout.itemAt(i).widget()
            if widget is not None and widget is not self.status_text:
                widget.setParent(None)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        url = QUrl(f"{HUMTHENTICATION_SERVER_DOMAIN}/api/login")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        data = json.dumps({"username": username, "password": password, "work_tag": "desktop_access"})
        self.is_login_request = True
        self.network_manager.post(request, QByteArray(data.encode()))
        self.log_message(f"Sending login request to {url.toString()}")

    def logout(self):
        if os.path.exists(self.tokens_file):
            try:
                with open(self.tokens_file, 'w') as f:
                    json.dump({}, f)
            except Exception as e:
                self.log_message(f"Error clearing tokens: {str(e)}")
        self.log_message("Logged out successfully")
        self.show_login_ui()

    def onRequestFinished(self, reply):
        if self.is_login_request:
            self.handleLoginResponse(reply)
        else:
            self.handleAuthenticatedResponse(reply)
        reply.deleteLater()

    def handleLoginResponse(self, reply):
        self.is_login_request = False
        if reply.error() == QNetworkReply.NoError:
            response_data = reply.readAll().data()
            self.log_message(f"Received login response: {response_data.decode()}")
            json_doc = QJsonDocument.fromJson(response_data)
            json_obj = json_doc.object()

            if "message" in json_obj and json_obj["message"] == "Login successful":
                self.handleSuccessfulLogin(reply, json_obj)
            else:
                self.log_message("Login Failed: Invalid username or password")
                QMessageBox.warning(self, "Login Failed", "Invalid username or password")
        else:
            error_message = f"Network error during login: {reply.errorString()}"
            self.log_message(error_message)
            QMessageBox.critical(self, "Error", error_message)

    def handleSuccessfulLogin(self, reply, json_obj):
        # Convert QJsonValue to Python string
        session_token = json_obj["session_token"].toString()
        user_token = None

        cookies = reply.header(QNetworkRequest.SetCookieHeader)
        for cookie in cookies:
            if cookie.name() == b"user_token":
                user_token = str(cookie.value(), 'utf-8')
                break

        # Save tokens to file
        tokens = {
            'user_token': user_token,
            'session_token': session_token
        }
        os.makedirs(self.tokens_dir, exist_ok=True)
        with open(self.tokens_file, 'w') as f:
            json.dump(tokens, f)

        self.log_message("Login Successful")
        self.login_successful.emit()

    def handleAuthenticatedResponse(self, reply):
        if reply.error() == QNetworkReply.NoError:
            self.log_message("Authenticated request successful")
            response_data = reply.readAll().data().decode()
            self.log_message(f"Response from authenticated endpoint: {response_data}")
        else:
            self.log_message(f"Authenticated request failed: {reply.errorString()}")

    def log_message(self, message):
        if self.status_text is not None:
            self.status_text.append(message)

    def closeEvent(self, event):
        self.network_manager.finished.disconnect()
        super().closeEvent(event)

from PyQt6 import QtWidgets
from sim import Ui_Form
from tcp_client import TcpClient
from tcp_server import TcpServer

class Widget(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.setupUi(self)
        self.tcp_client = TcpClient(self)
        self.tcp_server = TcpServer(self)
        self.pushButton_change.clicked.connect(self.on_change)
        self.pushButton_recv_clear.clicked.connect(self.on_recv_clear)
        self.pushButton_send_clear.clicked.connect(self.on_send_clear)

    def on_change(self):
        cur_index = self.stackedWidget.currentIndex()
        if cur_index == 0:
            self.pushButton_change.setText('tcp server')
        else:
            self.pushButton_change.setText('tcp client')
        self.stackedWidget.setCurrentIndex(1 - cur_index)
        self.textEdit_recv.clear()
        self.textEdit_send.clear()

    def on_send_clear(self):
        self.textEdit_send.clear()

    def on_recv_clear(self):
        self.textEdit_recv.clear()

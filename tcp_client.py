from PyQt6 import QtCore, QtWidgets
import struct
from PyQt6.QtNetwork import QTcpSocket

class TcpClient():
    def __init__(self, widget):
        self.widget = widget
        self.widget.tableWidget_property.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.widget.tableWidget_property.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.widget.tableWidget_station.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.widget.tableWidget_station.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.widget.tableWidget_train.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.widget.tableWidget_train.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.widget.pushButton_connect.clicked.connect(self.on_connect)
        self.widget.pushButton_send.clicked.connect(self.on_send)
        self.tcp_socket = QTcpSocket()
        self.tcp_socket.readyRead.connect(self.on_read)

    def on_read(self):
        self.widget.textEdit_recv.setText(self.tcp_socket.readAll().data().hex().upper())

    def on_connect(self):
        if self.widget.pushButton_connect.text() == '連接':
            self.tcp_socket.connectToHost(self.widget.lineEdit_ip.text(), int(self.widget.lineEdit_port.text()))
            if self.tcp_socket.waitForConnected(2500) == False:
                msg = self.tcp_socket.errorString()
                QtWidgets.QMessageBox.critical(self, "error", msg)
            else:
                self.widget.pushButton_connect.setText('斷開連接')
        else:
            self.tcp_socket.disconnectFromHost()
            self.widget.pushButton_connect.setText('連接')

    def on_send(self):
        if self.widget.tabWidget_func.currentIndex() == 0:
            self.opm_operate()
        else:
            self.status_operate()

    def opm_operate(self):
        out = QtCore.QByteArray()
        out.append(7, b'\x00')
        out.append(1, b'\x10')
        out.append(5, b'\x00')
        property = ''
        for row in range(4):
            item = self.widget.tableWidget_property.item(row, 1)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                property += '1'
            else:
                property += '0'
        item = self.widget.tableWidget_property.item(4, 1)
        if item.checkState() == QtCore.Qt.CheckState.Checked:
            property = '1' + '00000000000' + property[::-1]
        else:
            property = '0' + '00000000000' + property[::-1]
        out.append(struct.pack('>H', int(property, base=2)))
        time = QtCore.QDateTime.fromString(self.widget.dateTimeEdit_start.text(), "MM/dd/yyyy HH:mm:ss")
        out.append(struct.pack('>I', time.toSecsSinceEpoch()))
        time = QtCore.QDateTime.fromString(self.widget.dateTimeEdit_end.text(), "MM/dd/yyyy HH:mm:ss")
        out.append(struct.pack('>I', time.toSecsSinceEpoch()))

        out.append(self.widget.textEdit.toPlainText().encode('utf-16-be'))
        if out.size() > 2071:
            out.truncate(2071)
        else:
            out.append(2071 - out.size(), b'\x00')

        for row in range(self.widget.tableWidget_station.rowCount()):
            temp = '000000000000'
            for col in range(self.widget.tableWidget_station.columnCount()):
                item = self.widget.tableWidget_station.item(row, col)
                if item.checkState() == QtCore.Qt.CheckState.Checked:
                    temp += '1'
                else:
                    temp += '0'
            out.append(struct.pack('>H', int(temp, base=2)))
        out.append(6 * 2, b'\x00')
        for row in range(self.widget.tableWidget_train.rowCount()):
            for col in range(self.widget.tableWidget_train.columnCount()):
                item = self.widget.tableWidget_train.item(row, col)
                out.append(struct.pack('>H', int(item.text())))

        cur_index = self.widget.stackedWidget.currentIndex()
        if cur_index == 0:
            self.widget.textEdit_send.append(out.data().hex().upper())
        self.tcp_socket.write(out)

    def status_operate(self):
        out = QtCore.QByteArray()
        out.append(struct.pack('>H', self.widget.spinBox_sn.value()))
        out.append(b'\x00\x00\x00\x06\x06\x04')
        out.append(struct.pack('>H', self.widget.spinBox_sp.value()))
        out.append(struct.pack('>H', self.widget.spinBox_nr.value()))
        cur_index = self.widget.stackedWidget.currentIndex()
        if cur_index == 0:
            self.widget.textEdit_send.append(out.data().hex().upper())
        self.widget.tcp_socket.write(out)
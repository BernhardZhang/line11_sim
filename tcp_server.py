from PyQt6.QtCore import QObject
from PyQt6.QtNetwork import QHostAddress, QTcpServer
from PyQt6 import QtWidgets, QtCore
from datetime import datetime, timedelta
import struct
import random

class TcpServer(QtCore.QObject):
    def __init__(self, widget):
        super().__init__(widget)
        settings = QtCore.QSettings("config.ini", QtCore.QSettings.Format.IniFormat)
        self.tcp_server = QTcpServer()
        self.tcp_server.listen(QHostAddress(QHostAddress.SpecialAddress.AnyIPv4), int(settings.value("server_port", 0)))
        self.tcp_server.newConnection.connect(self.on_connect)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(1000 * 60)
        self.timer_send = QtCore.QTimer()
        self.timer_send.timeout.connect(self.on_send_timer)
        self.widget = widget
        self.widget.spinBox.valueChanged.connect(self.on_parse)
        self.cols = 4
        self.number_of_train_services = int(settings.value("number_of_train_services", 0))
        self.widget.spinBox_interval.valueChanged.connect(self.on_interval_change)
        self.widget.pushButton_end.setEnabled(False)
        self.widget.pushButton_start.clicked.connect(self.on_start)
        self.widget.pushButton_end.clicked.connect(self.on_end)
        self.client_socket = None
        settings.beginGroup('platforms')
        self.platform_dict = {}
        keys = settings.childKeys()
        for key in keys:
            key_int = int(key)
            value = settings.value(key)
            self.platform_dict[key_int] = value
        settings.endGroup()
        self.create_table_widget()

    def on_start(self):
        self.timer_send.start(1000 * self.widget.spinBox_interval.value())
        self.widget.pushButton_start.setEnabled(False)
        self.widget.pushButton_end.setEnabled(True)

    def on_end(self):
        self.timer.stop()
        self.timer_send.stop()
        self.widget.pushButton_start.setEnabled(True)
        self.widget.pushButton_end.setEnabled(False)

    def on_interval_change(self):
        self.timer.stop()
        self.timer.setInterval(1000 * self.widget.spinBox_interval.value())
        self.timer.start()

    def on_send_timer(self):
        out = QtCore.QByteArray()
        out.append(7, b'\x00')
        out.append(struct.pack('<H', 3))
        out.append(struct.pack('<H', len(self.platform_dict)))

        for i in range(self.widget.tableWidget.rowCount()):
            for j in range(0, self.widget.tableWidget.columnCount(), self.cols):
                out.append(struct.pack('<H', int(self.widget.tableWidget.item(i, j + 1).text())))
                out.append(struct.pack('B', int(self.widget.tableWidget.item(i, j + 2).text())))
                out.append(struct.pack('<H', self.number_of_train_services))
                table_widget = self.widget.tableWidget.cellWidget(i, j + 3)
                if table_widget == None:
                    break
                for k in range(table_widget.rowCount()):
                    train_group_num = table_widget.item(k, 0).text()
                    out.append(struct.pack('B', len(train_group_num)))
                    out.append(train_group_num.encode('ascii'))
                    train_num = table_widget.item(k, 1).text()
                    out.append(struct.pack('B', len(train_num)))
                    out.append(train_num.encode('ascii'))
                    out.append(struct.pack('B', int(table_widget.item(k, 2).text())))
                    arrival_delta = int(table_widget.item(k, 3).text())
                    departure_delta = int(table_widget.item(k, 4).text())

                    def append_time(out, current_time, delta_seconds):
                        new_time = current_time + timedelta(seconds=delta_seconds)
                        year = new_time.year
                        month = new_time.month
                        day = new_time.day
                        hour = new_time.hour
                        minute = new_time.minute
                        second = new_time.second

                        out.append(struct.pack('<H', year))
                        out.append(struct.pack('B', month))
                        out.append(struct.pack('B', day))
                        out.append(struct.pack('B', hour))
                        out.append(struct.pack('B', minute))
                        out.append(struct.pack('B', second))

                    current_time = datetime.now()
                    append_time(out, current_time, arrival_delta * 60)
                    append_time(out, current_time, departure_delta * 60)

                    out.append(struct.pack('<H', int(table_widget.item(k, 5).text())))
                    out.append(struct.pack('B', int(table_widget.item(k, 6).text())))
                    out.append(struct.pack('B', int(table_widget.item(k, 7).text())))
                    out.append(1, b'\x00')
                    out.append(struct.pack('B', int(table_widget.item(k, 8).text())))
                    out.append(struct.pack('<H', int(table_widget.item(k, 9).text())))
                    out.append(struct.pack('B', int(table_widget.item(k, 10).text())))
                    out.append(1, b'\x00')

        out.append(2, b'\x00')
        data_len = len(out) - 9
        out.replace(4, 2, struct.pack('<H', data_len))
        cur_index = self.widget.stackedWidget.currentIndex()
        if cur_index == 1:
            self.widget.textEdit_send.append(out.data().hex().upper())
        if self.client_socket:
            self.client_socket.write(out)

    def on_connect(self):
        client_socket = self.tcp_server.nextPendingConnection()
        client_socket.disconnected.connect(self.on_disconnect)
        client_address = client_socket.peerAddress().toString()
        client_port = client_socket.peerPort()
        self.widget.textEdit_recv.append("connect from {}:{}".format(client_address, client_port))
        self.client_socket = client_socket


    def on_disconnect(self):
        self.timer.stop()
        self.timer_send.stop()
        client_socket = self.sender()
        client_socket.deleteLater()
        client_address = client_socket.peerAddress().toString()
        client_port = client_socket.peerPort()
        self.widget.textEdit_recv.append("disconnect from {}:{}".format(client_address, client_port))

    def create_table_widget(self):
        per_line = self.widget.spinBox.value()
        stations = len(self.platform_dict)
        self.widget.tableWidget.setRowCount((stations - 1) // per_line + 1)
        self.widget.tableWidget.setColumnCount(4 * per_line)

        settings = QtCore.QSettings("config.ini", QtCore.QSettings.Format.IniFormat)
        destinations_upward = settings.value("destinations_upward", defaultValue=[])
        destinations_downward = settings.value("destinations_downward", defaultValue=[])

        for i in range(len(self.platform_dict)):
            table_widget = QtWidgets.QTableWidget()
            table_widget.setColumnCount(11)
            table_widget.setRowCount(self.number_of_train_services)
            table_widget.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem('車組號'))
            table_widget.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem('車次號'))
            table_widget.setHorizontalHeaderItem(2, QtWidgets.QTableWidgetItem('停車類型'))
            table_widget.setHorizontalHeaderItem(3, QtWidgets.QTableWidgetItem('計劃到站時間'))
            table_widget.setHorizontalHeaderItem(4, QtWidgets.QTableWidgetItem('計劃離站時間'))
            table_widget.setHorizontalHeaderItem(5, QtWidgets.QTableWidgetItem('終到站'))
            table_widget.setHorizontalHeaderItem(6, QtWidgets.QTableWidgetItem('當前狀態'))
            table_widget.setHorizontalHeaderItem(7, QtWidgets.QTableWidgetItem('是否扣車'))
            table_widget.setHorizontalHeaderItem(8, QtWidgets.QTableWidgetItem('大站快車標志'))
            table_widget.setHorizontalHeaderItem(9, QtWidgets.QTableWidgetItem('下一停車站站碼'))
            table_widget.setHorizontalHeaderItem(10, QtWidgets.QTableWidgetItem('清客標志'))

            for l in range(self.number_of_train_services):
                table_widget.setVerticalHeaderItem(l, QtWidgets.QTableWidgetItem('第{}列車'.format(l + 1)))
                table_widget.setItem(l, 0, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(1, 55)))))
                table_widget.setItem(l, 1, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(1, 100)))))
                table_widget.setItem(l, 3, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(1, 10)))))
                table_widget.setItem(l, 4, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(1, 10)))))
                dst = destinations_downward if i % 2 == 0 else destinations_upward
                rand = random.randint(1, len(dst))
                table_widget.setItem(l, 5, QtWidgets.QTableWidgetItem(dst[rand - 1]))
                table_widget.setItem(l, 2, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(0, 1)))))
                table_widget.setItem(l, 6, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(0, 2)))))
                table_widget.setItem(l, 7, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(0, 1)))))
                table_widget.setItem(l, 8, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(0, 1)))))
                table_widget.setItem(l, 9, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(1, 31)))))
                table_widget.setItem(l, 10, QtWidgets.QTableWidgetItem(QtWidgets.QTableWidgetItem(str(random.randint(0, 1)))))
            table_widget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
            table_widget.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

            m = i % per_line + 1
            n = i // per_line
            self.widget.tableWidget.setHorizontalHeaderItem((m - 1) * self.cols, QtWidgets.QTableWidgetItem('站臺'))
            self.widget.tableWidget.setHorizontalHeaderItem((m - 1) * self.cols + 1, QtWidgets.QTableWidgetItem('車站編號'))
            self.widget.tableWidget.setHorizontalHeaderItem((m - 1) * self.cols + 2, QtWidgets.QTableWidgetItem('站臺編號'))
            self.widget.tableWidget.setHorizontalHeaderItem((m - 1) * self.cols + 3, QtWidgets.QTableWidgetItem('列車信息'))
            self.widget.tableWidget.setItem(n, (m - 1) * self.cols, QtWidgets.QTableWidgetItem(self.platform_dict[i + 1]))
            k = (i + 1) // 2
            station_id = k if (i + 1) % 2 == 0 else k + 1
            platform_id = 2 if (i + 1) % 2 == 0 else 1
            self.widget.tableWidget.setItem(n, (m - 1) * self.cols + 1, QtWidgets.QTableWidgetItem(str(station_id)))
            self.widget.tableWidget.setItem(n, (m - 1) * self.cols + 2, QtWidgets.QTableWidgetItem(str(platform_id)))
            self.widget.tableWidget.setCellWidget(n, (m - 1) * self.cols + 3, table_widget)
        for i in range(per_line * self.cols):
            if i % self.cols == 1 or i % self.cols == 2:
                self.widget.tableWidget.setColumnWidth(i, 55)
            elif i % self.cols == 0:
                self.widget.tableWidget.setColumnWidth(i, 85)
            else:
                self.widget.tableWidget.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.widget.tableWidget.verticalHeader().setDefaultSectionSize(192)
        self.widget.tableWidget.setVerticalHeaderLabels([])

    def on_parse(self):
        self.widget.tableWidget.clear()
        self.create_table_widget()


    def on_timer(self):
        def set_time(table_widget):
            if table_widget == None:
                return
            row_cnt = table_widget.rowCount()
            for k in range(row_cnt):
                cur = int(table_widget.item(k, 3).text())
                if cur == 0:
                    cur = random.randint(1, 10)
                else:
                    cur = cur - 1
                item = QtWidgets.QTableWidgetItem(str(cur))
                table_widget.setItem(k, 3, item)
        for i in range(self.widget.tableWidget.rowCount()):
            for j in range(3, self.widget.tableWidget.columnCount(), self.cols):
                table_widget1 = self.widget.tableWidget.cellWidget(i, j)
                table_widget2 = self.widget.tableWidget.cellWidget(i, j + 1)
                set_time(table_widget1)
                set_time(table_widget2)
import sys
import serial
import serial.tools.list_ports
import time
import re
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from collections import deque
import os
import zipfile

class SensorData:
    def __init__(self, index, rom_code, temperature, sensor_type="DS18B20"):
        self.index = index
        self.rom_code = rom_code
        self.temperature = temperature
        self.timestamp = datetime.now()
        self.history = deque(maxlen=100)
        self.TL = 25.0
        self.TH = 30.0
        self.resolution = 12
        self.sensor_type = sensor_type

class SensorConfigDialog(QDialog):
    def __init__(self, sensors, parent=None):
        super().__init__(parent)
        self.sensors = sensors
        self.parent_window = parent
        self.config_widgets = {}
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Настройка датчиков")
        self.setGeometry(200, 200, 900, 600)
        main_layout = QVBoxLayout(self)
        columns_layout = QHBoxLayout()

        ds18b20_widget = QWidget()
        ds18b20_layout = QVBoxLayout(ds18b20_widget)
        ds18b20_layout.setContentsMargins(0, 0, 0, 0)
        
        ds18b20_label = QLabel("DS18B20")
        ds18b20_label.setStyleSheet("font-weight: bold; color: green;")
        ds18b20_layout.addWidget(ds18b20_label)
        
        ds18b20_scroll = QScrollArea()
        ds18b20_scroll_widget = QWidget()
        ds18b20_scroll_layout = QVBoxLayout(ds18b20_scroll_widget)
        
        ds18b20_sensors = [(code, s) for code, s in self.sensors.items() if s.sensor_type == "DS18B20"]
        for rom_code, sensor in ds18b20_sensors:
            group_box = QGroupBox(f"ROM: {rom_code}")
            group_layout = QVBoxLayout(group_box)
            tl_layout = QHBoxLayout()
            tl_layout.addWidget(QLabel("TL (°C):"))
            tl_spin = QDoubleSpinBox()
            tl_spin.setRange(-55, 125)
            tl_spin.setDecimals(1)
            tl_spin.setSingleStep(0.5)
            tl_spin.setValue(sensor.TL)
            tl_spin.valueChanged.connect(lambda v, rc=rom_code: self.update_tl(rc, v))
            tl_layout.addWidget(tl_spin)
            group_layout.addLayout(tl_layout)
            th_layout = QHBoxLayout()
            th_layout.addWidget(QLabel("TH (°C):"))
            th_spin = QDoubleSpinBox()
            th_spin.setRange(-55, 125)
            th_spin.setDecimals(1)
            th_spin.setSingleStep(0.5)
            th_spin.setValue(sensor.TH)
            th_spin.valueChanged.connect(lambda v, rc=rom_code: self.update_th(rc, v))
            th_layout.addWidget(th_spin)
            group_layout.addLayout(th_layout)
            res_layout = QHBoxLayout()
            res_layout.addWidget(QLabel("Разрядность (бит):"))
            res_combo = QComboBox()
            res_combo.addItems(['9', '10', '11', '12'])
            res_combo.setCurrentText(str(sensor.resolution))
            res_combo.currentTextChanged.connect(lambda v, rc=rom_code: self.update_resolution(rc, int(v)))
            res_layout.addWidget(res_combo)
            group_layout.addLayout(res_layout)
            self.config_widgets[rom_code] = {
                'tl_spin': tl_spin,
                'th_spin': th_spin,
                'res_combo': res_combo,
                'type': 'DS18B20'
            }
            ds18b20_scroll_layout.addWidget(group_box)
        ds18b20_scroll_layout.addStretch()
        ds18b20_scroll.setWidget(ds18b20_scroll_widget)
        ds18b20_layout.addWidget(ds18b20_scroll)
        ds18b20_apply_all_btn = QPushButton("Применить настройки ко всем DS18B20")
        ds18b20_apply_all_btn.clicked.connect(self.apply_all_ds18b20)
        ds18b20_layout.addWidget(ds18b20_apply_all_btn)
        columns_layout.addWidget(ds18b20_widget)
        lm75a_widget = QWidget()
        lm75a_layout = QVBoxLayout(lm75a_widget)
        lm75a_layout.setContentsMargins(0, 0, 0, 0)
        lm75a_label = QLabel("LM75A")
        lm75a_label.setStyleSheet("font-weight: bold; color: blue;")
        lm75a_layout.addWidget(lm75a_label)
        lm75a_scroll = QScrollArea()
        lm75a_scroll_widget = QWidget()
        lm75a_scroll_layout = QVBoxLayout(lm75a_scroll_widget)
        lm75a_sensors = [(code, s) for code, s in self.sensors.items() if s.sensor_type == "LM75A"]
        for address, sensor in lm75a_sensors:
            group_box = QGroupBox(f"адрес: 0x{address}")
            group_layout = QVBoxLayout(group_box)
            tos_layout = QHBoxLayout()
            tos_layout.addWidget(QLabel("Tos (°C):"))
            tos_spin = QDoubleSpinBox()
            tos_spin.setRange(-55, 125)
            tos_spin.setDecimals(1)
            tos_spin.setSingleStep(0.5)
            tos_spin.setValue(sensor.TL)
            tos_spin.valueChanged.connect(lambda v, addr=address: self.update_tl(addr, v))
            tos_layout.addWidget(tos_spin)
            group_layout.addLayout(tos_layout)
            thyst_layout = QHBoxLayout()
            thyst_layout.addWidget(QLabel("Thyst (°C):"))
            thyst_spin = QDoubleSpinBox()
            thyst_spin.setRange(-55, 125)
            thyst_spin.setDecimals(1)
            thyst_spin.setSingleStep(0.5)
            thyst_spin.setValue(sensor.TH)
            thyst_spin.valueChanged.connect(lambda v, addr=address: self.update_th(addr, v))
            thyst_layout.addWidget(thyst_spin)
            group_layout.addLayout(thyst_layout)
            self.config_widgets[address] = {
                'tos_spin': tos_spin,
                'thyst_spin': thyst_spin,
                'type': 'LM75A'
            }
            lm75a_scroll_layout.addWidget(group_box)
        lm75a_scroll_layout.addStretch()
        lm75a_scroll.setWidget(lm75a_scroll_widget)
        lm75a_layout.addWidget(lm75a_scroll)
        lm75a_apply_all_btn = QPushButton("Применить настройки ко всем LM75A")
        lm75a_apply_all_btn.clicked.connect(self.apply_all_lm75a)
        lm75a_layout.addWidget(lm75a_apply_all_btn)
        columns_layout.addWidget(lm75a_widget)
        main_layout.addLayout(columns_layout, 1)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.apply_and_accept)
        main_layout.addWidget(button_box)
    
    def apply_and_accept(self):
        for code, widget in self.config_widgets.items():
            if code in self.sensors:
                if widget['type'] == 'DS18B20':
                    tl_value = widget['tl_spin'].value()
                    th_value = widget['th_spin'].value()
                    res_value = int(widget['res_combo'].currentText())
                    self.sensors[code].TL = tl_value
                    self.sensors[code].TH = th_value
                    self.sensors[code].resolution = res_value
                    if self.parent_window and hasattr(self.parent_window, 'send_ds18b20_config'):
                        self.parent_window.send_ds18b20_config(code, tl_value, th_value, res_value)
                elif widget['type'] == 'LM75A':
                    tos_value = widget['tos_spin'].value()
                    thyst_value = widget['thyst_spin'].value()
                    self.sensors[code].TL = tos_value
                    self.sensors[code].TH = thyst_value
                    if self.parent_window and hasattr(self.parent_window, 'send_lm75a_config'):
                        self.parent_window.send_lm75a_config(code, tos_value, thyst_value)
        self.accept()

    def apply_all_ds18b20(self):
        first_ds18b20 = None
        for code, widget in self.config_widgets.items():
            if widget['type'] == 'DS18B20':
                first_ds18b20 = code
                break
        if first_ds18b20:
            tl_value = self.config_widgets[first_ds18b20]['tl_spin'].value()
            th_value = self.config_widgets[first_ds18b20]['th_spin'].value()
            res_value = int(self.config_widgets[first_ds18b20]['res_combo'].currentText())
            for code, widget in self.config_widgets.items():
                if widget['type'] == 'DS18B20':
                    widget['tl_spin'].setValue(tl_value)
                    widget['th_spin'].setValue(th_value)
                    widget['res_combo'].setCurrentText(str(res_value))
        
    def apply_all_lm75a(self):
        first_lm75a = None
        for code, widget in self.config_widgets.items():
            if widget['type'] == 'LM75A':
                first_lm75a = code
                break
        if first_lm75a:
            tos_value = self.config_widgets[first_lm75a]['tos_spin'].value()
            thyst_value = self.config_widgets[first_lm75a]['thyst_spin'].value()
            for code, widget in self.config_widgets.items():
                if widget['type'] == 'LM75A':
                    widget['tos_spin'].setValue(tos_value)
                    widget['thyst_spin'].setValue(thyst_value)
        
    def update_tl(self, rom_code, value):
        if rom_code in self.sensors:
            self.sensors[rom_code].TL = value
            
    def update_th(self, rom_code, value):
        if rom_code in self.sensors:
            self.sensors[rom_code].TH = value
            
    def update_resolution(self, rom_code, value):
        if rom_code in self.sensors:
            self.sensors[rom_code].resolution = value

class SerialWorker(QThread):
    data_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.running = False
        self.port_name = ""
        self.baudrate = 9600
        
    def connect_to_port(self, port_name, baudrate=9600):
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            self.port_name = port_name
            self.baudrate = baudrate
            self.connection_status.emit(True)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Ошибка подключения: {str(e)}")
            self.connection_status.emit(False)
            return False
    
    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.running = False
        self.connection_status.emit(False)
    
    def run(self):
        self.running = True
        buffer = ""
        while self.running:
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting:
                        data = self.serial_port.read(self.serial_port.in_waiting)
                        if data:
                            decoded_data = data.decode('utf-8', errors='ignore')
                            buffer += decoded_data
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                line = line.strip('\r')
                                if line.strip():
                                    self.data_received.emit(line.strip())
                    else:
                        time.sleep(0.01)
                except Exception as e:
                    self.error_occurred.emit(f"Ошибка чтения: {str(e)}")
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

    def send_command(self, command):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write((command + '\r\n').encode())
                return True
            except Exception as e:
                self.error_occurred.emit(f"Ошибка отправки: {str(e)}")
                return False
        return False
    
    def set_ds18b20_config(self, rom_code, tl, th, resolution):
        command = f"set_ds18b20,{rom_code},{tl:.1f},{th:.1f},{resolution}"
        return self.send_command(command)
    
    def set_lm75a_config(self, address, tos, thyst):
        command = f"set_lm75a,{address:02X},{tos:.1f},{thyst:.1f}"
        return self.send_command(command)
    
    def request_sensor_configs(self):
        return self.send_command("get_configs")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_worker = SerialWorker()
        self.sensors = {}
        self.ds18b20_measurements = deque(maxlen=20)
        self.lm75a_measurements = deque(maxlen=20)
        self.log_file = "temperature_log.txt"
        self.archive_num = 1
        self.sensor_config_dialog = None
        self.init_ui()
        self.setup_connections()
        self.init_log_file()
    
    def send_ds18b20_config(self, rom_code, tl, th, resolution):
        if self.serial_worker and self.serial_worker.running:
            command = f"set_ds18b20,{rom_code},{tl:.1f},{th:.1f},{resolution}"
            self.serial_worker.send_command(command)
            self.add_log(f"Отправлена настройка DS18B20 (ROM: {rom_code}): TL={tl}, TH={th}, разрядность={resolution}")
    
    def send_lm75a_config(self, address, tos, thyst):
        if self.serial_worker and self.serial_worker.running:
            if isinstance(address, str):
                addr_str = address.replace('0x', '')
                addr = int(addr_str, 16)
            else:
                addr = address
            command = f"set_lm75a,{addr:02X},{tos:.1f},{thyst:.1f}"
            self.serial_worker.send_command(command)
            self.add_log(f"Отправлена настройка LM75A (адрес: 0x{addr:02X}): Tos={tos}, Thyst={thyst}")
    
    def request_sensor_configs(self):
        if self.serial_worker and self.serial_worker.running:
            self.serial_worker.send_command("get_configs")
    
    def open_sensor_config(self):
        if not self.sensors:
            QMessageBox.warning(self, "Нет датчиков", "Нет подключенных датчиков для настройки")
            return
        self.request_sensor_configs()
        QApplication.processEvents()
        self.sensor_config_dialog = SensorConfigDialog(self.sensors, self)
        if self.sensor_config_dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Применение настроек", "Настройки отправлены на контроллер")

    def init_log_file(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"{'Timestamp':<20} {'Sensor Type':<12} {'Sensor ID':<25} {'Temperature':<13} {'TL/Tos':<9} {'TH/Thyst':<8} {'Resolution':<10}\n")
                f.write("-" * 103 + "\n")
                
    def check_and_archive(self):
        if os.path.exists(self.log_file):
            file_size = os.path.getsize(self.log_file)
            if file_size > (1024 * 10):
                archive_name = f"temperature_log_{self.archive_num}.zip"
                with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(self.log_file, os.path.basename(self.log_file))
                    self.archive_num+=1;
                os.remove(self.log_file)
                self.init_log_file()
                self.add_log(f"Лог заархивирован: {archive_name}")
                
    def save_to_log(self, measurement):
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{measurement['timestamp'].strftime('%Y-%m-%d %H:%M:%S'):<20} "
                   f"{measurement['sensor_type']:<12} "
                   f"{measurement['sensor_id']:<24} "
                   f"{measurement['temperature']:>6.2f}       "
                   f"{measurement['TL']:>6.1f}    "
                   f"{measurement['TH']:>6.1f}      "
                   f"{measurement['resolution']:<12}\n")
        self.check_and_archive()
        
    def init_ui(self):
        self.setWindowTitle("Мониторинг температуры")
        self.setGeometry(100, 100, 1600, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        connection_group = QGroupBox()
        connection_layout = QVBoxLayout(connection_group)
        
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        control_layout.addWidget(QLabel("COM порт:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        self.refresh_ports_btn = QPushButton("Обновить")
        self.refresh_ports_btn.clicked.connect(self.refresh_ports_list)
        control_layout.addWidget(self.port_combo)
        control_layout.addWidget(self.refresh_ports_btn)
        
        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.clicked.connect(self.toggle_connection)
        control_layout.addWidget(self.connect_btn)
        
        self.config_sensors_btn = QPushButton("Настройка датчиков")
        self.config_sensors_btn.clicked.connect(self.open_sensor_config)
        control_layout.addWidget(self.config_sensors_btn)
        
        control_layout.addStretch()
        connection_layout.addWidget(control_panel)
        
        self.status_label = QLabel("Отключено")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumHeight(30)
        self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; font-size: 14pt; background-color: #FFEEEE; border: 2px solid red; border-radius: 5px; }")
        connection_layout.addWidget(self.status_label)
        
        main_layout.addWidget(connection_group)
        
        tables_layout = QHBoxLayout()
        
        ds18b20_container = QWidget()
        ds18b20_container_layout = QVBoxLayout(ds18b20_container)
        ds18b20_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ds18b20_group = QGroupBox("DS18B20 (0)")
        ds18b20_layout = QVBoxLayout(self.ds18b20_group)
        self.ds18b20_table = QTableWidget()
        self.ds18b20_table.setColumnCount(6)
        self.ds18b20_table.setHorizontalHeaderLabels(["Время", "ROM", "Температура (°C)", "TL (°C)", "TH (°C)", "Разрядность"])
        header = self.ds18b20_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        ds18b20_layout.addWidget(self.ds18b20_table)
        ds18b20_container_layout.addWidget(self.ds18b20_group)
        
        tables_layout.addWidget(ds18b20_container)
        
        lm75a_container = QWidget()
        lm75a_container_layout = QVBoxLayout(lm75a_container)
        lm75a_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lm75a_group = QGroupBox("LM75A (0)")
        lm75a_layout = QVBoxLayout(self.lm75a_group)
        self.lm75a_table = QTableWidget()
        self.lm75a_table.setColumnCount(5)
        self.lm75a_table.setHorizontalHeaderLabels(["Время", "Адрес", "Температура (°C)", "Tos (°C)", "Thyst (°C)"])
        header = self.lm75a_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        lm75a_layout.addWidget(self.lm75a_table)
        lm75a_container_layout.addWidget(self.lm75a_group)
        
        tables_layout.addWidget(lm75a_container)
        
        main_layout.addLayout(tables_layout, 1)
        
        log_group = QGroupBox("Лог событий")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.refresh_ports_list()
        
    def refresh_ports_list(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}")
        
        if self.port_combo.count() == 0:
            self.port_combo.addItem("Порты не найдены")
        
    def setup_connections(self):
        self.serial_worker.data_received.connect(self.process_serial_data)
        self.serial_worker.connection_status.connect(self.on_connection_status)
        
    def toggle_connection(self):
        if self.serial_worker.running:
            self.serial_worker.disconnect()
            self.serial_worker.wait()
            self.connect_btn.setText("Подключиться")
            self.status_label.setText("Отключено")
            self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; font-size: 14pt; background-color: #FFEEEE; border: 2px solid red; border-radius: 5px; }")
        else:
            self.connect_to_selected_port()
                    
    def connect_to_selected_port(self):
        if self.port_combo.currentText() == "Порты не найдены":
            QMessageBox.warning(self, "Ошибка", "Нет доступных COM портов")
            return
        port_text = self.port_combo.currentText()
        port_name = port_text.split(" - ")[0]
        if self.serial_worker.connect_to_port(port_name, 9600):
            self.serial_worker.start()
        else:
            self.status_label.setText("Ошибка подключения")
            self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; font-size: 14pt; background-color: #FFEEEE; border: 2px solid red; border-radius: 5px; }")
            
    def on_connection_status(self, connected):
        if connected:
            self.status_label.setText(f"Подключено к {self.serial_worker.port_name}")
            self.status_label.setStyleSheet("QLabel { color: green; font-weight: bold; font-size: 14pt; background-color: #EEFFEE; border: 2px solid green; border-radius: 5px; }")
            self.connect_btn.setText("Отключиться")
            self.add_log(f"Подключено к {self.serial_worker.port_name}")
            self.request_sensor_configs()
        else:
            self.status_label.setText("Отключено")
            self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; font-size: 14pt; background-color: #FFEEEE; border: 2px solid red; border-radius: 5px; }")
            self.connect_btn.setText("Подключиться")
            self.add_log(f"Отключено от {self.serial_worker.port_name}")
            
    def process_serial_data(self, data):
        if "DS18B20_CONFIG" in data:
            parts = data.split(',')
            if len(parts) >= 5:
                rom_code = parts[1]
                tl = float(parts[2])
                th = float(parts[3])
                resolution = int(parts[4])
                if rom_code in self.sensors:
                    self.sensors[rom_code].TL = tl
                    self.sensors[rom_code].TH = th
                    self.sensors[rom_code].resolution = resolution
                    self.add_log(f"Получены настройки DS18B20 (ROM: {rom_code}): TL={tl}, TH={th}, разрядность={resolution}")
            return
        
        elif "LM75A_CONFIG" in data:
            parts = data.split(',')
            if len(parts) >= 4:
                address = parts[1]
                tos = float(parts[2])
                thyst = float(parts[3])
                if address in self.sensors:
                    self.sensors[address].TL = tos
                    self.sensors[address].TH = thyst
                    self.add_log(f"Получены настройки LM75A (адрес: 0x{address}): Tos={tos}, Thyst={thyst}")
            return
        
        elif "CONFIG_OK" in data:
            self.add_log("Настройки датчика применены успешно")
            return
        
        elif "CONFIG_ERROR" in data:
            self.add_log("Ошибка применения настроек датчика")
            return
        self.parse_sensor_data(data)
    
    def parse_sensor_data(self, data):
        if "DS18B20 Sensors count:" in data:
            match = re.search(r'DS18B20 Sensors count:\s*(\d+)', data)
            if match:
                count = int(match.group(1))
                self.update_ds18b20_group_title()
            return
        
        if "LM75A Sensor:" in data:
            if "Not found" in data:
                self.add_log("Отключен LM75A")
            else:
                match = re.search(r'Address 0x([0-9A-F]{2}):\s+([\d\.-]+)\s+C', data)
                if match:
                    address = match.group(1)
                    temperature = float(match.group(2))
                    self.add_lm75a_sensor(address, temperature)
            return
            
        match = re.search(r'DS18B20 Sensor\s+(\d+)\s+\(([0-9A-F]+)\):\s+([\d\.-]+)\s+C', data)
        if match:
            index = int(match.group(1))
            rom_code = match.group(2)
            temperature = float(match.group(3))
            self.add_ds18b20_sensor(index, rom_code, temperature)
            return
        
        if "=== TEMPERATURE REPORT ===" in data:
            self.add_log("Получен отчет о температуре")
            return
            
        if "Sensor connected:" in data:
            match = re.search(r'Sensor connected:\s*([0-9A-F]+)', data)
            if match:
                rom_code = match.group(1)
                self.add_log(f"Подключен DS18B20 (ROM: {rom_code})")
            return
            
        if "Sensor disconnected:" in data:
            match = re.search(r'Sensor disconnected:\s*([0-9A-F]+)', data)
            if match:
                rom_code = match.group(1)
                if rom_code in self.sensors:
                    del self.sensors[rom_code]
                    self.add_log(f"Отключен DS18B20 (ROM: {rom_code})")
                    self.update_ds18b20_group_title()
                    self.update_lm75a_group_title()
            return
            
    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def add_ds18b20_sensor(self, index, rom_code, temperature):
        timestamp = datetime.now()
        sensor_id = f"{rom_code}"
        if rom_code not in self.sensors:
            self.sensors[rom_code] = SensorData(index, rom_code, temperature, "DS18B20")
            self.add_log(f"Подключен DS18B20 (ROM: {rom_code})")
            self.update_ds18b20_group_title()
        else:
            self.sensors[rom_code].temperature = temperature
            self.sensors[rom_code].timestamp = timestamp
            self.sensors[rom_code].history.append((timestamp, temperature))
        sensor = self.sensors[rom_code]
        self.add_ds18b20_measurement(sensor_id, temperature, timestamp, sensor, rom_code)
        
    def add_lm75a_sensor(self, address, temperature):
        timestamp = datetime.now()
        addr_str = f"{int(address, 16):02X}" if isinstance(address, str) and len(address) <= 2 else str(address)
        sensor_id = f"0x{addr_str}"
        if address not in self.sensors:
            self.sensors[address] = SensorData(0, address, temperature, "LM75A")
            self.update_lm75a_group_title()
            self.add_log(f"Подключен LM75A (адрес: 0x{address})")
        else:
            self.sensors[address].temperature = temperature
            self.sensors[address].timestamp = timestamp
            self.sensors[address].history.append((timestamp, temperature))
        sensor = self.sensors[address]
        self.add_lm75a_measurement(sensor_id, temperature, timestamp, sensor, f"0x{address}")
        
    def update_ds18b20_group_title(self):
        count = sum(1 for s in self.sensors.values() if s.sensor_type == "DS18B20")
        self.ds18b20_group.setTitle(f"DS18B20 (подключено: {count})")
        
    def update_lm75a_group_title(self):
        count = sum(1 for s in self.sensors.values() if s.sensor_type == "LM75A")
        self.lm75a_group.setTitle(f"LM75A (подключено: {count})")
        
    def format_temperature(self, temp):
        sign = '+' if temp >= 0 else '-'
        abs_temp = abs(temp)
        integer_part = int(abs_temp)
        fractional_part = int(round((abs_temp - integer_part) * 100))
        if fractional_part >= 100:
            fractional_part = 99
        return f"{sign}{integer_part:02d}.{fractional_part:02d}"
        
    def add_ds18b20_measurement(self, sensor_id, temperature, timestamp, sensor, display_id):
        measurement = {
            'sensor_id': sensor_id,
            'sensor_type': "DS18B20",
            'display_id': display_id,
            'temperature': temperature,
            'timestamp': timestamp,
            'TL': sensor.TL,
            'TH': sensor.TH,
            'resolution': sensor.resolution
        }
        self.save_to_log(measurement)
        self.ds18b20_measurements.append(measurement)
        self.update_ds18b20_table()
        
    def add_lm75a_measurement(self, sensor_id, temperature, timestamp, sensor, display_id):
        measurement = {
            'sensor_id': sensor_id,
            'sensor_type': "LM75A",
            'display_id': display_id,
            'temperature': temperature,
            'timestamp': timestamp,
            'TL': sensor.TL,
            'TH': sensor.TH,
            'resolution': 0
        }
        self.save_to_log(measurement)
        self.lm75a_measurements.append(measurement)
        self.update_lm75a_table()
        
    def update_ds18b20_table(self):
        self.ds18b20_table.setRowCount(len(self.ds18b20_measurements))
        measurements_list = list(self.ds18b20_measurements)
        for i, measurement in enumerate(reversed(measurements_list)):
            time_item = QTableWidgetItem(measurement['timestamp'].strftime("%H:%M:%S"))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.ds18b20_table.setItem(i, 0, time_item)
            id_item = QTableWidgetItem(measurement['display_id'])
            id_item.setTextAlignment(Qt.AlignCenter)
            self.ds18b20_table.setItem(i, 1, id_item)
            temp_color = QColor(255, 0, 0) if measurement['temperature'] > measurement['TH'] or measurement['temperature'] < measurement['TL'] else QColor(0, 128, 0)
            temp_item = QTableWidgetItem(self.format_temperature(measurement['temperature']))
            temp_item.setForeground(temp_color)
            temp_item.setTextAlignment(Qt.AlignCenter)
            self.ds18b20_table.setItem(i, 2, temp_item)
            tl_item = QTableWidgetItem(self.format_temperature(measurement['TL']))
            tl_item.setTextAlignment(Qt.AlignCenter)
            self.ds18b20_table.setItem(i, 3, tl_item)
            th_item = QTableWidgetItem(self.format_temperature(measurement['TH']))
            th_item.setTextAlignment(Qt.AlignCenter)
            self.ds18b20_table.setItem(i, 4, th_item)
            res_item = QTableWidgetItem(str(measurement['resolution']))
            res_item.setTextAlignment(Qt.AlignCenter)
            self.ds18b20_table.setItem(i, 5, res_item)
        self.ds18b20_table.scrollToTop()
        
    def update_lm75a_table(self):
        self.lm75a_table.setRowCount(len(self.lm75a_measurements))
        measurements_list = list(self.lm75a_measurements)
        
        for i, measurement in enumerate(reversed(measurements_list)):
            time_item = QTableWidgetItem(measurement['timestamp'].strftime("%H:%M:%S"))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.lm75a_table.setItem(i, 0, time_item)
            id_item = QTableWidgetItem(measurement['display_id'])
            id_item.setTextAlignment(Qt.AlignCenter)
            self.lm75a_table.setItem(i, 1, id_item)
            temp_color = QColor(255, 0, 0) if measurement['temperature'] > measurement['TH'] or measurement['temperature'] < measurement['TL'] else QColor(0, 128, 0)
            temp_item = QTableWidgetItem(self.format_temperature(measurement['temperature']))
            temp_item.setForeground(temp_color)
            temp_item.setTextAlignment(Qt.AlignCenter)
            self.lm75a_table.setItem(i, 2, temp_item)
            tos_item = QTableWidgetItem(self.format_temperature(measurement['TL']))
            tos_item.setTextAlignment(Qt.AlignCenter)
            self.lm75a_table.setItem(i, 3, tos_item)
            thyst_item = QTableWidgetItem(self.format_temperature(measurement['TH']))
            thyst_item.setTextAlignment(Qt.AlignCenter)
            self.lm75a_table.setItem(i, 4, thyst_item)
        self.lm75a_table.scrollToTop()
        
    def open_sensor_config(self):
        if not self.sensors:
            QMessageBox.warning(self, "Нет датчиков", "Нет подключенных датчиков для настройки")
            return
            
        self.sensor_config_dialog = SensorConfigDialog(self.sensors, self)
        if self.sensor_config_dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Применение настроек", "Настройки применены к датчикам")
            
    def closeEvent(self, event):
        if self.serial_worker.running:
            self.serial_worker.disconnect()
            self.serial_worker.wait()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

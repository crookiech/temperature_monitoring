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
        # Временные хранилища для настроек до нажатия OK
        self.temp_tl = {}
        self.temp_th = {}
        self.temp_resolution = {}
        self.init_ui()
        # Инициализируем временные значения текущими настройками датчиков
        for code, sensor in self.sensors.items():
            self.temp_tl[code] = sensor.TL
            self.temp_th[code] = sensor.TH
            if sensor.sensor_type == "DS18B20":
                self.temp_resolution[code] = sensor.resolution

    def init_ui(self):
        self.setWindowTitle("Настройка датчиков")
        self.setGeometry(200, 200, 900, 600)
        main_layout = QVBoxLayout(self)
        columns_layout = QHBoxLayout()

        # Добавляем информационную метку вверху
        info_label = QLabel("Здесь отображаются актуальные настройки датчиков")
        info_label.setStyleSheet("color: gray;")
        main_layout.addWidget(info_label)
        
        columns_layout = QHBoxLayout()

        # DS18B20 column
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
            # Точность зависит от разрядности
            initial_res = sensor.resolution
            tl_spin.setDecimals(self._get_decimals_from_resolution(initial_res))
            tl_spin.setSingleStep(0.1)
            tl_spin.setValue(sensor.TL)
            # Сохраняем изменения во временное хранилище
            tl_spin.valueChanged.connect(lambda v, rc=rom_code: self.update_temp_tl(rc, v))
            tl_layout.addWidget(tl_spin)
            group_layout.addLayout(tl_layout)

            th_layout = QHBoxLayout()
            th_layout.addWidget(QLabel("TH (°C):"))
            th_spin = QDoubleSpinBox()
            th_spin.setRange(-55, 125)
            th_spin.setDecimals(self._get_decimals_from_resolution(initial_res))
            th_spin.setSingleStep(0.1)
            th_spin.setValue(sensor.TH)
            th_spin.valueChanged.connect(lambda v, rc=rom_code: self.update_temp_th(rc, v))
            th_layout.addWidget(th_spin)
            group_layout.addLayout(th_layout)

            res_layout = QHBoxLayout()
            res_layout.addWidget(QLabel("Разрядность (бит):"))
            res_combo = QComboBox()
            res_combo.addItems(['9', '10', '11', '12'])
            res_combo.setCurrentText(str(sensor.resolution))
            # При изменении разрядности обновляем точность полей TL и TH
            res_combo.currentTextChanged.connect(lambda v, rc=rom_code: self.update_temp_resolution_and_precision(rc, int(v)))
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

        ds18b20_apply_all_btn = QPushButton("Применить настройки ко всем DS18B20\n(относительно первого датчика)")
        ds18b20_apply_all_btn.clicked.connect(self.apply_all_ds18b20)
        ds18b20_layout.addWidget(ds18b20_apply_all_btn)

        columns_layout.addWidget(ds18b20_widget)

        # LM75A column
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
            tos_spin.setDecimals(2)
            tos_spin.setSingleStep(0.1)
            tos_spin.setValue(sensor.TL)
            tos_spin.valueChanged.connect(lambda v, addr=address: self.update_temp_tl(addr, v))
            tos_layout.addWidget(tos_spin)
            group_layout.addLayout(tos_layout)

            thyst_layout = QHBoxLayout()
            thyst_layout.addWidget(QLabel("Thyst (°C):"))
            thyst_spin = QDoubleSpinBox()
            thyst_spin.setRange(-55, 125)
            thyst_spin.setDecimals(2)
            thyst_spin.setSingleStep(0.1)
            thyst_spin.setValue(sensor.TH)
            thyst_spin.valueChanged.connect(lambda v, addr=address: self.update_temp_th(addr, v))
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

        lm75a_apply_all_btn = QPushButton("Применить настройки ко всем LM75A\n(относительно первого датчика)")
        lm75a_apply_all_btn.clicked.connect(self.apply_all_lm75a)
        lm75a_layout.addWidget(lm75a_apply_all_btn)

        columns_layout.addWidget(lm75a_widget)
        main_layout.addLayout(columns_layout, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.apply_and_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _get_decimals_from_resolution(self, resolution):
        """Возвращает количество знаков после запятой в зависимости от разрядности."""
        if resolution == 9:
            return 1
        elif resolution == 10:
            return 2
        elif resolution == 11:
            return 3
        else:  # 12 бит
            return 4

    def _set_spinbox_precision(self, spinbox, resolution):
        """Устанавливает точность и шаг для spinbox в зависимости от разрядности."""
        decimals = self._get_decimals_from_resolution(resolution)
        spinbox.setDecimals(decimals)
        spinbox.setSingleStep(0.1)

    def update_temp_tl(self, code, value):
        """Обновляет временное значение TL."""
        self.temp_tl[code] = value

    def update_temp_th(self, code, value):
        """Обновляет временное значение TH."""
        self.temp_th[code] = value

    def update_temp_resolution(self, code, value):
        """Обновляет временное значение разрядности."""
        self.temp_resolution[code] = value

    def update_temp_resolution_and_precision(self, code, new_resolution):
        self.update_temp_resolution(code, new_resolution)
        if code in self.config_widgets and self.config_widgets[code]['type'] == 'DS18B20':
            widget = self.config_widgets[code]
            self._set_spinbox_precision(widget['tl_spin'], new_resolution)
            self._set_spinbox_precision(widget['th_spin'], new_resolution)

    def apply_and_accept(self):
        """Применяет все настройки к датчикам и отправляет на контроллер."""
        for code, widget in self.config_widgets.items():
            if code in self.sensors:
                if widget['type'] == 'DS18B20':
                    tl_value = self.temp_tl.get(code, self.sensors[code].TL)
                    th_value = self.temp_th.get(code, self.sensors[code].TH)
                    res_value = self.temp_resolution.get(code, self.sensors[code].resolution)
                    
                    # Обновляем датчик
                    self.sensors[code].TL = tl_value
                    self.sensors[code].TH = th_value
                    self.sensors[code].resolution = res_value
                    
                    # Отправляем на контроллер
                    if self.parent_window and hasattr(self.parent_window, 'send_ds18b20_config'):
                        self.parent_window.send_ds18b20_config(code, tl_value, th_value, res_value)
                        
                elif widget['type'] == 'LM75A':
                    tos_value = self.temp_tl.get(code, self.sensors[code].TL)
                    thyst_value = self.temp_th.get(code, self.sensors[code].TH)
                    
                    # Обновляем датчик
                    self.sensors[code].TL = tos_value
                    self.sensors[code].TH = thyst_value
                    
                    # Отправляем на контроллер
                    if self.parent_window and hasattr(self.parent_window, 'send_lm75a_config'):
                        self.parent_window.send_lm75a_config(code, tos_value, thyst_value)
        
        # Обновляем таблицы в главном окне
        if self.parent_window:
            self.parent_window.update_ds18b20_table()
            self.parent_window.update_lm75a_table()
        
        self.accept()

    def apply_all_ds18b20(self):
        first_ds18b20 = None
        for code, widget in self.config_widgets.items():
            if widget['type'] == 'DS18B20':
                first_ds18b20 = code
                break
        if first_ds18b20:
            tl_value = self.temp_tl.get(first_ds18b20, self.sensors[first_ds18b20].TL)
            th_value = self.temp_th.get(first_ds18b20, self.sensors[first_ds18b20].TH)
            res_value = self.temp_resolution.get(first_ds18b20, self.sensors[first_ds18b20].resolution)
            
            for code, widget in self.config_widgets.items():
                if widget['type'] == 'DS18B20':
                    # Обновляем временные значения
                    self.temp_tl[code] = tl_value
                    self.temp_th[code] = th_value
                    self.temp_resolution[code] = res_value
                    
                    # Обновляем виджеты
                    widget['tl_spin'].setValue(tl_value)
                    widget['th_spin'].setValue(th_value)
                    widget['res_combo'].setCurrentText(str(res_value))
                    
                    # Обновляем точность полей
                    self._set_spinbox_precision(widget['tl_spin'], res_value)
                    self._set_spinbox_precision(widget['th_spin'], res_value)

    def apply_all_lm75a(self):
        first_lm75a = None
        for code, widget in self.config_widgets.items():
            if widget['type'] == 'LM75A':
                first_lm75a = code
                break
        if first_lm75a:
            tos_value = self.temp_tl.get(first_lm75a, self.sensors[first_lm75a].TL)
            thyst_value = self.temp_th.get(first_lm75a, self.sensors[first_lm75a].TH)
            
            for code, widget in self.config_widgets.items():
                if widget['type'] == 'LM75A':
                    # Обновляем временные значения
                    self.temp_tl[code] = tos_value
                    self.temp_th[code] = thyst_value
                    
                    # Обновляем виджеты
                    widget['tos_spin'].setValue(tos_value)
                    widget['thyst_spin'].setValue(thyst_value)

    def reject(self):
        super().reject()


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

    def get_configs(self):
        return self.send_command("get_configs")

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

    def set_ds18b20_config(self, sensor_index, tl_str, th_str, resolution):
        command = f"set_ds {sensor_index},{tl_str},{th_str},{resolution}"
        return self.send_command(command)

    def set_lm75a_config(self, tos, thyst):
        command = f"set_lm75a {tos:.2f},{thyst:.2f}"
        return self.send_command(command)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_worker = SerialWorker()
        self.sensors = {}
        self.ds18b20_sensor_list = []
        self.ds18b20_measurements = deque(maxlen=21)
        self.lm75a_measurements = deque(maxlen=21)
        self.log_file = "temperature_log.txt"
        self.sensor_config_dialog = None
        self.logging_enabled = False
        
        # Хранилища для последних данных
        self.latest_ds18b20_data = {}  # rom_code -> latest temperature data
        self.latest_lm75a_data = {}    # address -> latest temperature data
        
        # Таймер для обновления таблицы (каждые 5 секунд)
        self.table_update_timer = QTimer()
        self.table_update_timer.timeout.connect(self.update_tables_from_latest_data)
        self.table_update_timer.setInterval(5000)  # 5 секунд
        
        # Таймер для логов (каждые 0.5 секунды)
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.save_current_state_to_log)
        self.log_timer.setInterval(500)  # 0.5 секунды

        self.pending_configs = {}
        self.config_request_pending = False

        self.init_ui()
        self.setup_connections()
        self.init_log_file()

    def update_tables_from_latest_data(self):
            
        # Обновляем DS18B20
        for rom_code, data in self.latest_ds18b20_data.items():
            if rom_code in self.sensors:
                sensor = self.sensors[rom_code]
                self.add_ds18b20_measurement(rom_code, data['temperature'], data['timestamp'], sensor, data['index'])
        
        # Обновляем LM75A
        for address, data in self.latest_lm75a_data.items():
            if address in self.sensors:
                sensor = self.sensors[address]
                self.add_lm75a_measurement(address, data['temperature'], data['timestamp'], sensor)

    def clear_all_data(self):
        """Очищает все данные и таблицы"""
        # Очищаем хранилища данных
        self.sensors.clear()
        self.ds18b20_sensor_list.clear()
        self.ds18b20_measurements.clear()
        self.lm75a_measurements.clear()
        self.latest_ds18b20_data.clear()
        self.latest_lm75a_data.clear()
        
        # Очищаем таблицы
        self.ds18b20_table.setRowCount(0)
        self.lm75a_table.setRowCount(0)
        
        # Обновляем заголовки групп
        self.ds18b20_group.setTitle("DS18B20 (0)")
        self.lm75a_group.setTitle("LM75A (0)")

    def send_ds18b20_config(self, rom_code, tl, th, resolution):
        if self.serial_worker and self.serial_worker.running:
            # Находим индекс датчика по ROM коду
            sensor_index = None
            for idx, sensor in enumerate(self.ds18b20_sensor_list):
                if sensor == rom_code:
                    sensor_index = idx
                    break
            
            if sensor_index is not None:
                # Форматируем TL и TH с правильной точностью в зависимости от разрядности
                if resolution == 9:
                    tl_str = f"{tl:.1f}"
                    th_str = f"{th:.1f}"
                elif resolution == 10:
                    tl_str = f"{tl:.2f}"
                    th_str = f"{th:.2f}"
                elif resolution == 11:
                    tl_str = f"{tl:.3f}"
                    th_str = f"{th:.3f}"
                else:  # 12 бит
                    tl_str = f"{tl:.4f}"
                    th_str = f"{th:.4f}"
                
                self.serial_worker.set_ds18b20_config(sensor_index, tl_str, th_str, resolution)
                self.add_log(f"Отправлена настройка DS18B20 (ROM: {rom_code}): TL={tl_str}, TH={th_str}, разрядность={resolution}")
            else:
                self.add_log(f"Ошибка: DS18B20 с ROM {rom_code} не найден")

    def send_lm75a_config(self, address, tos, thyst):
        if self.serial_worker and self.serial_worker.running:
            self.serial_worker.set_lm75a_config(tos, thyst)
            self.add_log(f"Отправлена настройка LM75A: Tos={tos}, Thyst={thyst}")

    def open_sensor_config(self):
        if not self.sensors:
            QMessageBox.warning(self, "Нет датчиков", "Нет подключенных датчиков для настройки")
            return
        self.sensor_config_dialog = SensorConfigDialog(self.sensors, self)
        if self.sensor_config_dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Применение настроек", "Настройки отправлены на контроллер")
            # Обновляем таблицы после применения настроек
            self.update_ds18b20_table()
            self.update_lm75a_table()

    def toggle_logging(self):
        """Включает/выключает запись логов и обновление таблиц."""
        if not self.serial_worker.running:
            QMessageBox.warning(self, "Нет подключения", "Сначала подключитесь к устройству")
            return
            
        self.logging_enabled = not self.logging_enabled
        if self.logging_enabled:
            self.logging_btn.setText("Остановить запись логов")
            # Запускаем оба таймера
            self.log_timer.start()  # Таймер для записи в файл (0.5 сек)
            # self.table_update_timer.start()  # Таймер для обновления таблицы (5 сек)
            self.add_log("Запись логов включена (частота: 0.5 сек)")
            # self.add_log("Обновление таблицы: каждые 5 сек")
        else:
            self.logging_btn.setText("Начать запись логов")
            # Останавливаем оба таймера
            self.log_timer.stop()
            
            self.add_log("Запись логов остановлена")

    def save_current_state_to_log(self):
        """Сохраняет текущее состояние всех датчиков в лог (вызывается каждые 0.5 секунды)"""
        if not self.logging_enabled:
            return
        
        if not self.sensors:
            return
        
        # Берем текущее время
        current_time = datetime.now()
        timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Формируем строку данных
        data_parts = [timestamp_str]
        
        # Добавляем все датчики в фиксированном порядке
        for sensor in self.sensors.values():
            if sensor.sensor_type == "DS18B20":
                formatted_temp = self._format_temperature_for_log(sensor.temperature, sensor.resolution)
                data_parts.append(f"{sensor.rom_code}:{formatted_temp}")
            elif sensor.sensor_type == "LM75A":
                formatted_temp = f"{sensor.temperature:>6.2f}"
                data_parts.append(f"0x{sensor.rom_code}:{formatted_temp}")
        
        data_line = "  ".join(data_parts) + "\n"
        
        # Читаем существующий файл
        existing_lines = []
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # Проверяем, не дублируется ли последняя запись
        if existing_lines and existing_lines[0] == data_line:
            return  # Данные не изменились - не пишем
        
        # Записываем новую строку в начало
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(data_line)
            f.writelines(existing_lines)
        
        self.check_and_archive()

    def init_log_file(self):
        """Создает пустой файл лога, если он не существует."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                pass  # Создаем пустой файл без заголовка

    def get_next_archive_number(self):
        import re
        max_num = 0
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for filename in os.listdir(script_dir):
            match = re.match(r'temperature_log_(\d+)\.zip', filename)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        return max_num + 1

    def check_and_archive(self):
        if os.path.exists(self.log_file):
            file_size = os.path.getsize(self.log_file)
            if file_size > (1024 * 10):
                next_num = self.get_next_archive_number()
                archive_name = f"temperature_log_{next_num}.zip"
                with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(self.log_file, os.path.basename(self.log_file))
                os.remove(self.log_file)
                self.init_log_file()
                self.add_log(f"Лог заархивирован: {archive_name}")

    def _format_temperature_for_log(self, temp, resolution):
        """Форматирует температуру для лога с нужной точностью в зависимости от разрядности."""
        if resolution == 9:
            return f"{temp:>6.1f}"
        elif resolution == 10:
            return f"{temp:>6.2f}"
        elif resolution == 11:
            return f"{temp:>6.3f}"
        else:  # 12 бит
            return f"{temp:>6.4f}"

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

        # Кнопка управления записью логов
        self.logging_btn = QPushButton("Начать запись логов")
        self.logging_btn.clicked.connect(self.toggle_logging)
        control_layout.addWidget(self.logging_btn)

        control_layout.addStretch()
        connection_layout.addWidget(control_panel)

        self.status_label = QLabel("Отключено")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumHeight(30)
        self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; font-size: 14pt; background-color: #FFEEEE; border: 2px solid red; border-radius: 5px; }")
        connection_layout.addWidget(self.status_label)

        main_layout.addWidget(connection_group)

        tables_layout = QHBoxLayout()

        # DS18B20 table
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

        # LM75A table
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
            # Отключаемся
            self.serial_worker.disconnect()
            self.serial_worker.wait()
            self.connect_btn.setText("Подключиться")
            self.status_label.setText("Отключено")
            self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; font-size: 14pt; background-color: #FFEEEE; border: 2px solid red; border-radius: 5px; }")
            self.table_update_timer.stop()
            # Останавливаем запись логов, если она была включена
            if self.logging_enabled:
                self.logging_enabled = False
                self.logging_btn.setText("Начать запись логов")
                self.log_timer.stop()
                self.add_log("Запись логов остановлена из-за отключения")
            
        else:
            # Подключаемся
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

            QTimer.singleShot(1000, self.request_sensor_configs)
            self.table_update_timer.start()  # Таймер для обновления таблицы (5 сек)
            self.add_log("Обновление таблицы: каждые 5 сек")
        else:
            self.status_label.setText("Отключено")
            self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; font-size: 14pt; background-color: #FFEEEE; border: 2px solid red; border-radius: 5px; }")
            self.connect_btn.setText("Подключиться")
            self.add_log(f"Отключено от {self.serial_worker.port_name}")

    def request_sensor_configs(self):
        if self.serial_worker and self.serial_worker.running:
            self.config_request_pending = True
            self.serial_worker.get_configs()

    def process_serial_data(self, data):
        if not self.serial_worker.running:
            return  # Игнорируем данные, если нет подключения
            
        if "DS18B20_CONFIG" in data:
            match = re.search(r'DS18B20_CONFIG,([0-9A-F]+),([\d\.-]+),([\d\.-]+),(\d+)', data)
            if match:
                rom_code = match.group(1)
                tl = float(match.group(2))
                th = float(match.group(3))
                resolution = int(match.group(4))
                
                if rom_code in self.sensors:
                    self.sensors[rom_code].TL = tl
                    self.sensors[rom_code].TH = th
                    self.sensors[rom_code].resolution = resolution
                    self.add_log(f"Получены настройки DS18B20 (ROM: {rom_code}): TL={tl}, TH={th}, разрядность={resolution}")
                
                self.update_ds18b20_table()
            return
        
        # Обработка конфигураций LM75A
        if "LM75A_CONFIG" in data:
            match = re.search(r'LM75A_CONFIG,([0-9A-F]+),([\d\.-]+),([\d\.-]+)', data)
            if match:
                address = match.group(1)
                tos = float(match.group(2))
                thyst = float(match.group(3))
                
                if address in self.sensors:
                    self.sensors[address].TL = tos
                    self.sensors[address].TH = thyst
                    self.add_log(f"Получены настройки LM75A (адрес: 0x{address}): Tos={tos}, Thyst={thyst}")
                
                self.update_lm75a_table()
            return
        # Обработка данных о температуре DS18B20
        match = re.search(r'DS18B20 Sensor\s+(\d+)\s+\(([0-9A-F]+)\):\s+([\d\.-]+)\s+C', data)
        if match:
            index = int(match.group(1))
            rom_code = match.group(2)
            temperature = float(match.group(3))
            # Сохраняем последние данные для отложенного обновления таблицы
            self.latest_ds18b20_data[rom_code] = {
                'temperature': temperature,
                'timestamp': datetime.now(),
                'index': index
            }
            # Обновляем датчик в реальном времени для логирования
            self.add_ds18b20_sensor(index, rom_code, temperature)
            return

        # Обработка данных LM75A
        if "LM75A Sensor" in data:
            if "Not found" in data:
                self.add_log("LM75A отключен")
            else:
                match = re.search(r'Address 0x([0-9A-F]{2}):\s+([\d\.-]+)\s+C', data)
                if match:
                    address = match.group(1)
                    temperature = float(match.group(2))
                    # Сохраняем последние данные для отложенного обновления таблицы
                    self.latest_lm75a_data[address] = {
                        'temperature': temperature,
                        'timestamp': datetime.now()
                    }
                    # Обновляем датчик в реальном времени для логирования
                    self.add_lm75a_sensor(address, temperature)
            return

        # Обработка подключения датчика
        if "Sensor connected:" in data:
            match = re.search(r'Sensor connected:\s*([0-9A-F]+)', data)
            if match:
                rom_code = match.group(1)
                self.add_log(f"Подключен DS18B20 (ROM: {rom_code})")
                # Обновим список датчиков при следующем опросе
            return

        # Обработка отключения датчика
        if "Sensor disconnected:" in data:
            match = re.search(r'Sensor disconnected:\s*([0-9A-F]+)', data)
            if match:
                rom_code = match.group(1)
                if rom_code in self.sensors:
                    # Удаляем из списка индексов
                    if rom_code in self.ds18b20_sensor_list:
                        self.ds18b20_sensor_list.remove(rom_code)
                    del self.sensors[rom_code]
                    # Удаляем из хранилища последних данных
                    if rom_code in self.latest_ds18b20_data:
                        del self.latest_ds18b20_data[rom_code]
                    self.add_log(f"Отключен DS18B20 (ROM: {rom_code})")
                    self.update_ds18b20_group_title()
            return

        # Обработка количества датчиков
        if "Sensor count:" in data:
            match = re.search(r'Sensor count:\s*(\d+)', data)
            if match:
                count = int(match.group(1))
                self.update_ds18b20_group_title()
            return

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_ds18b20_sensor(self, index, rom_code, temperature):
        timestamp = datetime.now()

        # Обновляем список индексов
        if rom_code not in self.ds18b20_sensor_list:
            # Вставляем на правильную позицию
            while len(self.ds18b20_sensor_list) <= index:
                self.ds18b20_sensor_list.append(None)
            self.ds18b20_sensor_list[index] = rom_code

        if rom_code not in self.sensors:
            self.sensors[rom_code] = SensorData(index, rom_code, temperature, "DS18B20")
            self.add_log(f"Подключен DS18B20 (ROM: {rom_code})")
            self.update_ds18b20_group_title()
        else:
            self.sensors[rom_code].temperature = temperature
            self.sensors[rom_code].timestamp = timestamp
            self.sensors[rom_code].history.append((timestamp, temperature))

    def add_lm75a_sensor(self, address, temperature):
        timestamp = datetime.now()

        if address not in self.sensors:
            self.sensors[address] = SensorData(0, address, temperature, "LM75A")
            self.update_lm75a_group_title()
            self.add_log(f"Подключен LM75A (адрес: 0x{address})")
        else:
            self.sensors[address].temperature = temperature
            self.sensors[address].timestamp = timestamp
            self.sensors[address].history.append((timestamp, temperature))

    def update_ds18b20_group_title(self):
        count = sum(1 for s in self.sensors.values() if s.sensor_type == "DS18B20")
        self.ds18b20_group.setTitle(f"DS18B20 (подключено: {count})")

    def update_lm75a_group_title(self):
        count = sum(1 for s in self.sensors.values() if s.sensor_type == "LM75A")
        self.lm75a_group.setTitle(f"LM75A (подключено: {count})")

    def _format_temperature_by_resolution(self, temp, resolution):
        """Форматирует температуру с нужной точностью в зависимости от разрядности, сохраняя знак."""
        if resolution == 9:
            return f"{temp:+.1f}"
        elif resolution == 10:
            return f"{temp:+.2f}"
        elif resolution == 11:
            return f"{temp:+.3f}"
        else:  # 12 бит
            return f"{temp:+.4f}"

    def add_ds18b20_measurement(self, sensor_id, temperature, timestamp, sensor, index):
        measurement = {
            'sensor_id': sensor_id,
            'sensor_type': "DS18B20",
            'display_id': sensor_id,
            'temperature': temperature,
            'timestamp': timestamp,
            'TL': sensor.TL,
            'TH': sensor.TH,
            'resolution': sensor.resolution,
            'index': index
        }
        self.ds18b20_measurements.append(measurement)
        self.update_ds18b20_table()

    def add_lm75a_measurement(self, sensor_id, temperature, timestamp, sensor):
        measurement = {
            'sensor_id': sensor_id,
            'sensor_type': "LM75A",
            'display_id': f"0x{sensor_id}",
            'temperature': temperature,
            'timestamp': timestamp,
            'TL': sensor.TL,
            'TH': sensor.TH,
            'resolution': 0
        }
        self.lm75a_measurements.append(measurement)
        self.update_lm75a_table()

    def update_ds18b20_table(self):
        self.ds18b20_table.setRowCount(len(self.ds18b20_measurements))
        measurements_list = list(self.ds18b20_measurements)

        for i, measurement in enumerate(reversed(measurements_list)):
            # Проверяем выход за границы
            is_out_of_range = measurement['temperature'] > measurement['TH'] or measurement['temperature'] < measurement['TL']
            
            # Создаем все элементы строки
            time_item = QTableWidgetItem(measurement['timestamp'].strftime("%H:%M:%S"))
            time_item.setTextAlignment(Qt.AlignCenter)
            
            id_item = QTableWidgetItem(measurement['display_id'])
            id_item.setTextAlignment(Qt.AlignCenter)
            
            # Используем форматирование с учётом разрядности
            temp_text = self._format_temperature_by_resolution(measurement['temperature'], measurement['resolution'])
            temp_item = QTableWidgetItem(temp_text)
            temp_item.setTextAlignment(Qt.AlignCenter)
            
            # TL и TH тоже форматируем с той же точностью
            tl_text = self._format_temperature_by_resolution(measurement['TL'], measurement['resolution'])
            tl_item = QTableWidgetItem(tl_text)
            tl_item.setTextAlignment(Qt.AlignCenter)
            
            th_text = self._format_temperature_by_resolution(measurement['TH'], measurement['resolution'])
            th_item = QTableWidgetItem(th_text)
            th_item.setTextAlignment(Qt.AlignCenter)
            
            res_item = QTableWidgetItem(str(measurement['resolution']))
            res_item.setTextAlignment(Qt.AlignCenter)
            
            if is_out_of_range:
                brush = QBrush(QColor(255, 200, 200))
                time_item.setBackground(brush)
                id_item.setBackground(brush)
                temp_item.setBackground(brush)
                tl_item.setBackground(brush)
                th_item.setBackground(brush)
                res_item.setBackground(brush)
                
                time_item.setForeground(QColor(0, 0, 0))
                id_item.setForeground(QColor(0, 0, 0))
                temp_item.setForeground(QColor(0, 0, 0))
                tl_item.setForeground(QColor(0, 0, 0))
                th_item.setForeground(QColor(0, 0, 0))
                res_item.setForeground(QColor(0, 0, 0))
            else:
                brush = QBrush(QColor(198, 255, 194))
                time_item.setBackground(brush)
                id_item.setBackground(brush)
                temp_item.setBackground(brush)
                tl_item.setBackground(brush)
                th_item.setBackground(brush)
                res_item.setBackground(brush)
                
                time_item.setForeground(QColor(0, 0, 0))
                id_item.setForeground(QColor(0, 0, 0))
                temp_item.setForeground(QColor(0, 0, 0))
                tl_item.setForeground(QColor(0, 0, 0))
                th_item.setForeground(QColor(0, 0, 0))
                res_item.setForeground(QColor(0, 0, 0))
            
            # Устанавливаем элементы в таблицу
            self.ds18b20_table.setItem(i, 0, time_item)
            self.ds18b20_table.setItem(i, 1, id_item)
            self.ds18b20_table.setItem(i, 2, temp_item)
            self.ds18b20_table.setItem(i, 3, tl_item)
            self.ds18b20_table.setItem(i, 4, th_item)
            self.ds18b20_table.setItem(i, 5, res_item)

        self.ds18b20_table.scrollToTop()

    def update_lm75a_table(self):
        self.lm75a_table.setRowCount(len(self.lm75a_measurements))
        measurements_list = list(self.lm75a_measurements)

        for i, measurement in enumerate(reversed(measurements_list)):
            # Проверяем выход за границы
            is_out_of_range = measurement['temperature'] > measurement['TH'] or measurement['temperature'] < measurement['TL']
            
            time_item = QTableWidgetItem(measurement['timestamp'].strftime("%H:%M:%S"))
            time_item.setTextAlignment(Qt.AlignCenter)
            
            id_item = QTableWidgetItem(measurement['display_id'])
            id_item.setTextAlignment(Qt.AlignCenter)
            
            temp_item = QTableWidgetItem(f"{measurement['temperature']:+.2f}")
            temp_item.setTextAlignment(Qt.AlignCenter)
            
            tos_item = QTableWidgetItem(f"{measurement['TL']:+.2f}")
            tos_item.setTextAlignment(Qt.AlignCenter)
            
            thyst_item = QTableWidgetItem(f"{measurement['TH']:+.2f}")
            thyst_item.setTextAlignment(Qt.AlignCenter)
            
            if is_out_of_range:
                brush = QBrush(QColor(255, 200, 200))
                time_item.setBackground(brush)
                id_item.setBackground(brush)
                temp_item.setBackground(brush)
                tos_item.setBackground(brush)
                thyst_item.setBackground(brush)
                
                time_item.setForeground(QColor(0, 0, 0))
                id_item.setForeground(QColor(0, 0, 0))
                temp_item.setForeground(QColor(0, 0, 0))
                tos_item.setForeground(QColor(0, 0, 0))
                thyst_item.setForeground(QColor(0, 0, 0))
            else:
                brush = QBrush(QColor(198, 255, 194))
                time_item.setBackground(brush)
                id_item.setBackground(brush)
                temp_item.setBackground(brush)
                tos_item.setBackground(brush)
                thyst_item.setBackground(brush)
                
                time_item.setForeground(QColor(0, 0, 0))
                id_item.setForeground(QColor(0, 0, 0))
                temp_item.setForeground(QColor(0, 0, 0))
                tos_item.setForeground(QColor(0, 0, 0))
                thyst_item.setForeground(QColor(0, 0, 0))
            
            self.lm75a_table.setItem(i, 0, time_item)
            self.lm75a_table.setItem(i, 1, id_item)
            self.lm75a_table.setItem(i, 2, temp_item)
            self.lm75a_table.setItem(i, 3, tos_item)
            self.lm75a_table.setItem(i, 4, thyst_item)

        self.lm75a_table.scrollToTop()

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
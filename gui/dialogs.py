import re
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLineEdit, QTextEdit, QLabel, QFormLayout,
                               QFileDialog, QMessageBox,
                               QCheckBox, QScrollArea, QWidget)
from PySide6.QtGui import QFont

class SettingsDialog(QDialog):
    def __init__(self, parent, settings_data):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Настройки WireGuard")
        self.setMinimumWidth(450)
        
        layout = QFormLayout()
        self.fields = {}
        
        config = [
            ("PrivateKey", "private_key", True),
            ("Address", "address", False),
            ("DNS", "dns", False),
            ("MTU", "mtu", False),
            ("PublicKey (Peer)", "public_key", True),
            ("Endpoint", "endpoint", False),
            ("Keepalive", "keepalive", False)
        ]
        
        if settings_data:
            values = {
                "private_key": settings_data[2] or "",
                "address": settings_data[3] or "10.7.0.18/32",
                "dns": settings_data[4] or "1.1.1.1",
                "mtu": settings_data[5] or "1420",
                "public_key": settings_data[6] or "",
                "endpoint": settings_data[7] or "",
                "keepalive": settings_data[8] or "21"
            }
        else:
            values = {}
        
        for label, key, is_multiline in config:
            if is_multiline:
                inp = QTextEdit()
                inp.setMaximumHeight(80)
                inp.setPlainText(values.get(key, ""))
            else:
                inp = QLineEdit()
                inp.setText(values.get(key, ""))
            self.fields[key] = inp
            layout.addRow(label, inp)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("💾 Сохранить")
        btn_save.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("❌ Отмена")
        btn_cancel.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 10px; }")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)
        
        self.setLayout(layout)

    def get_settings(self):
        return (
            self.fields["private_key"].toPlainText().strip() if isinstance(self.fields["private_key"], QTextEdit) else self.fields["private_key"].text().strip(),
            self.fields["address"].text().strip(),
            self.fields["dns"].text().strip(),
            self.fields["mtu"].text().strip(),
            self.fields["public_key"].toPlainText().strip() if isinstance(self.fields["public_key"], QTextEdit) else self.fields["public_key"].text().strip(),
            self.fields["endpoint"].text().strip(),
            self.fields["keepalive"].text().strip()
        )


class IPListDialog(QDialog):
    def __init__(self, parent, data=None):
        super().__init__(parent)
        self.data = data
        self.setWindowTitle("➕ Добавить" if not data else "✏️ Редактировать")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        self.name_input = QLineEdit()
        self.ips_input = QTextEdit()
        self.ips_input.setMaximumHeight(200)
        self.ips_input.setPlaceholderText("Пример:\n3.162.38.0/24, 3.174.18.0/24\n8.6.112.0/24")
        
        if data:
            self.name_input.setText(data[1])
            self.ips_input.setText(data[2])
        
        layout.addWidget(QLabel("Название списка (например, discord):"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("IP адреса / подсети (через запятую, пробел или новую строку):"))
        layout.addWidget(self.ips_input)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("✅ Сохранить")
        btn_save.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("❌ Отмена")
        btn_cancel.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 10px; }")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название списка")
            return
        self.accept()
    
    def get_data(self):
        name = self.name_input.text().strip()
        ips_raw = self.ips_input.toPlainText()
        ips = ", ".join([ip.strip() for ip in re.split(r'[,\n\s]+', ips_raw) if ip.strip()])
        return (name, ips)


class ImportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("📥 Импорт конфига WireGuard")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        self.config_text = QTextEdit()
        self.config_text.setPlaceholderText("Вставьте содержимое .conf файла сюда или используйте кнопку загрузки")
        self.config_text.setFont(QFont("Consolas", 10))
        
        btn_load_file = QPushButton("📂 Загрузить из файла .conf")
        btn_load_file.clicked.connect(self.load_file)
        
        btn_parse = QPushButton("✅ Распарсить")
        btn_parse.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("❌ Отмена")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_load_file)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_parse)
        btn_layout.addWidget(btn_cancel)
        
        layout.addWidget(QLabel("Содержимое конфига:"))
        layout.addWidget(self.config_text)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "",
                                                    "WireGuard Config (*.conf);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.config_text.setText(f.read())
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл: {e}")
    
    def get_config_text(self):
        return self.config_text.toPlainText()


class ProfileNameDialog(QDialog):
    def __init__(self, parent, title="Название профиля", default_name=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setText(default_name)
        self.name_input.setPlaceholderText("Например: Work VPN, Home VPN")
        self.name_input.setMinimumHeight(40)
        
        btn_layout = QHBoxLayout()
        
        if title == "Новый профиль":
            btn_ok = QPushButton("✅ Создать профиль")
        elif "Импорт" in title:
            btn_ok = QPushButton("✅ Импортировать")
        else:
            btn_ok = QPushButton("✅ Сохранить")
            
        btn_ok.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }")
        btn_ok.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("❌ Отмена")
        btn_cancel.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 10px; }")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        
        layout.addWidget(QLabel("Введите название профиля:"))
        layout.addWidget(self.name_input)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def get_name(self):
        return self.name_input.text().strip()


class SelectIPListsDialog(QDialog):
    """Диалог выбора IP списков для добавления к профилю"""
    def __init__(self, parent, available_lists):
        super().__init__(parent)
        self.setWindowTitle("📋 Выбрать IP списки")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # ИСПРАВЛЕНО: Храним list_id в отдельном словаре
        self.checkbox_ids = {}
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Доступные IP списки (отметьте для добавления):"))
        
        # Список с чекбоксами
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        for list_id, name, ips in available_lists:
            cb = QCheckBox(f"📄 {name}")
            # ИСПРАВЛЕНО: Используем свойство для хранения ID
            cb.setProperty("list_id", list_id)
            cb.setToolTip(ips[:100] + "..." if len(ips) > 100 else ips)
            self.checkbox_ids[list_id] = cb
            scroll_layout.addWidget(cb)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("✅ Добавить выбранные")
        btn_add.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }")
        btn_add.clicked.connect(self.accept)
        btn_cancel = QPushButton("❌ Отмена")
        btn_cancel.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 10px; }")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def get_selected_ids(self):
        # ИСПРАВЛЕНО: Получаем ID через свойство
        selected = []
        for list_id, cb in self.checkbox_ids.items():
            if cb.isChecked():
                selected.append(list_id)
        return selected
# gui/parser_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QCheckBox, QComboBox, QSpinBox, QProgressBar,
    QTextEdit, QScrollArea, QFormLayout, QMessageBox, QFileDialog,
    QInputDialog, QTabWidget, QDialog, QDialogButtonBox, QLineEdit,
    QListWidget, QListWidgetItem, QRadioButton, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from domainmapper_api import dm_api


class PreviewDialog(QDialog):
    def __init__(self, parent, ips, list_name):
        super().__init__(parent)
        self.setWindowTitle(f"👁️ Предпросмотр: {list_name}")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout()
        info_label = QLabel(f"Найдено IP-адресов: {len(ips)}")
        info_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(info_label)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 9))
        if len(ips) > 0:
            self.preview_text.setText(', '.join(ips[:100]))
        else:
            self.preview_text.setText('\n'.join(ips[:500]))
        layout.addWidget(self.preview_text)
        if len(ips) > 100:
            more_label = QLabel(f"... и ещё {len(ips) - 100} IP-адресов")
            more_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(more_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.setLayout(layout)


class CustomServiceDialog(QDialog):
    """Диалог добавления/редактирования сервиса"""
    def __init__(self, parent, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle("➕ Добавить сервис" if not edit_data else "✏️ Редактировать сервис")
        self.setMinimumWidth(500)
        layout = QVBoxLayout()
        
        # Название сервиса
        layout.addWidget(QLabel("Название сервиса:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: MyService")
        if edit_data:
            self.name_input.setText(edit_data[0])
        layout.addWidget(self.name_input)
        
        # Выбор типа источника
        layout.addWidget(QLabel("Тип источника:"))
        self.radio_url = QRadioButton("📥 URL файла")
        self.radio_url.setChecked(True)
        layout.addWidget(self.radio_url)
        self.radio_file = QRadioButton("📁 Локальный файл")
        layout.addWidget(self.radio_file)
        self.radio_manual = QRadioButton("✍️ Ввести домены вручную")
        layout.addWidget(self.radio_manual)
        
        # Поле для URL/пути
        layout.addWidget(QLabel("Источник:"))
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("https://... или C:\\path\\to\\file.txt")
        if edit_data and edit_data[2] != 'manual':
            self.source_input.setText(edit_data[1])
            if edit_data[2] == 'url':
                self.radio_url.setChecked(True)
            else:
                self.radio_file.setChecked(True)
        layout.addWidget(self.source_input)
        
        # Поле для ручного ввода (многострочное) - создаётся ОДИН РАЗ
        self.manual_input = QTextEdit()
        self.manual_input.setMaximumHeight(150)
        self.manual_input.setPlaceholderText("domain1.com\ndomain2.com")
        if edit_data and edit_data[2] == 'manual':
            self.manual_input.setPlainText(edit_data[1])
            self.radio_manual.setChecked(True)
            self.source_input.setVisible(False)
            self.manual_input.setVisible(True)
        else:
            self.manual_input.setVisible(False)
        layout.addWidget(self.manual_input)
        
        # Подключение сигналов
        self.radio_url.toggled.connect(self.on_source_changed)
        self.radio_file.toggled.connect(self.on_source_changed)
        self.radio_manual.toggled.connect(self.on_source_changed)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("✅ Сохранить")
        btn_ok.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("❌ Отмена")
        btn_cancel.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 10px; }")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def on_source_changed(self):
        """Просто показывает/скрывает поля, не создаёт новые"""
        if self.radio_manual.isChecked():
            self.source_input.setVisible(False)
            self.manual_input.setVisible(True)
        else:
            self.source_input.setVisible(True)
            self.manual_input.setVisible(False)

    def get_service_data(self):
        """Возвращает name, source, source_type"""
        name = self.name_input.text().strip()
        if self.radio_manual.isChecked():
            source = self.manual_input.toPlainText().strip()
            source_type = 'manual'
        else:
            source = self.source_input.text().strip()
            source_type = 'url' if self.radio_url.isChecked() else 'file'
        return name, source, source_type


class DNSSettingsDialog(QDialog):
    """Диалог управления DNS серверами"""
    def __init__(self, parent, dns_db, local_mode=False):
        super().__init__(parent)
        self.local_mode = local_mode
        self.setWindowTitle("⚙️ Управление DNS серверами")
        self.setMinimumSize(600, 500)
        self.dns_db = dns_db.copy()
        layout = QVBoxLayout()
        info_label = QLabel("📝 Формат: Имя: IP1 IP2 IP3\nПример: MyDNS: 8.8.8.8 8.8.4.4")
        info_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }")
        layout.addWidget(info_label)
        self.dns_list = QListWidget()
        self.dns_list.itemDoubleClicked.connect(self.edit_dns)
        self.dns_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dns_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(QLabel("Список DNS серверов:"))
        layout.addWidget(self.dns_list)
        self.refresh_dns_list()
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Добавить")
        add_btn.clicked.connect(self.add_dns)
        del_btn = QPushButton("🗑️ Удалить")
        del_btn.clicked.connect(self.delete_dns)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        dialog_btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog_btns.accepted.connect(self.accept)
        dialog_btns.rejected.connect(self.reject)
        layout.addWidget(dialog_btns)
        self.setLayout(layout)

    def show_context_menu(self, pos):
        item = self.dns_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        edit_action = menu.addAction("✏️ Редактировать")
        del_action = menu.addAction("🗑️ Удалить")
        action = menu.exec(self.dns_list.mapToGlobal(pos))
        if action == edit_action:
            self.edit_dns(item)
        elif action == del_action:
            self.delete_dns()

    def refresh_dns_list(self):
        self.dns_list.clear()
        for name, servers in sorted(self.dns_db.items()):
            item = QListWidgetItem(f"🌐 {name}: {', '.join(servers)}")
            item.setData(Qt.UserRole, name)
            self.dns_list.addItem(item)

    def add_dns(self):
        if not self.local_mode:
            QMessageBox.warning(self, "Внимание", "Добавление DNS доступно только в локальном режиме")
            return
        name, ok = QInputDialog.getText(self, "Добавить DNS", "Введите имя DNS сервера:")
        if not ok or not name.strip():
            return
        if name.strip() in self.dns_db:
            QMessageBox.warning(self, "Ошибка", "DNS с таким именем уже существует!")
            return
        servers, ok = QInputDialog.getText(self, "Добавить DNS", "Введите IP адреса через пробел:")
        if not ok or not servers.strip():
            return
        server_list = servers.strip().split()
        import re
        ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        for ip in server_list:
            if not ip_pattern.match(ip):
                QMessageBox.warning(self, "Ошибка", f"Неверный формат IP: {ip}")
                return
        self.dns_db[name.strip()] = server_list
        self.refresh_dns_list()

    def edit_dns(self, item):
        if not self.local_mode:
            QMessageBox.warning(self, "Внимание", "Редактирование DNS доступно только в локальном режиме")
            return
        name = item.data(Qt.UserRole)
        servers, ok = QInputDialog.getText(self, "Редактировать DNS", "Введите IP адреса:", text=' '.join(self.dns_db.get(name, [])))
        if not ok or not servers.strip():
            return
        server_list = servers.strip().split()
        import re
        ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        for ip in server_list:
            if not ip_pattern.match(ip):
                QMessageBox.warning(self, "Ошибка", f"Неверный формат IP: {ip}")
                return
        del self.dns_db[name]
        self.dns_db[name] = server_list
        self.refresh_dns_list()

    def delete_dns(self):
        if not self.local_mode:
            QMessageBox.warning(self, "Внимание", "Удаление DNS доступно только в локальном режиме")
            return
        selected = self.dns_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите DNS для удаления")
            return
        name = selected.data(Qt.UserRole)
        confirm = QMessageBox.question(self, "Подтверждение", f"Удалить DNS '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            del self.dns_db[name]
            self.refresh_dns_list()

    def get_dns_db(self):
        return self.dns_db


class ServiceManagementDialog(QDialog):
    """Диалог управления кастомными сервисами"""
    def __init__(self, parent, custom_services, local_mode=False):
        super().__init__(parent)
        self.local_mode = local_mode
        self.custom_services = custom_services.copy()
        self.setWindowTitle("⚙️ Управление сервисами")
        self.setMinimumSize(600, 500)
        layout = QVBoxLayout()
        self.service_list = QListWidget()
        self.service_list.itemDoubleClicked.connect(self.edit_service)
        self.service_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.service_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(QLabel("Кастомные сервисы:"))
        layout.addWidget(self.service_list)
        self.refresh_list()
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Добавить")
        add_btn.clicked.connect(self.add_service)
        edit_btn = QPushButton("✏️ Редактировать")
        edit_btn.clicked.connect(self.edit_selected)
        del_btn = QPushButton("🗑️ Удалить")
        del_btn.clicked.connect(self.delete_service)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        dialog_btns = QDialogButtonBox(QDialogButtonBox.Ok)
        dialog_btns.accepted.connect(self.accept)
        layout.addWidget(dialog_btns)
        self.setLayout(layout)

    def show_context_menu(self, pos):
        item = self.service_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        edit_action = menu.addAction("✏️ Редактировать")
        del_action = menu.addAction("🗑️ Удалить")
        action = menu.exec(self.service_list.mapToGlobal(pos))
        if action == edit_action:
            self.edit_service(item)
        elif action == del_action:
            self.delete_service()

    def refresh_list(self):
        self.service_list.clear()
        for name, data in sorted(self.custom_services.items()):
            source_type = data.get('type', 'url')
            prefix = "📝" if source_type == 'manual' else ("📁" if source_type == 'file' else "🌐")
            item = QListWidgetItem(f"{prefix} {name} ({source_type})")
            item.setData(Qt.UserRole, name)
            self.service_list.addItem(item)

    def add_service(self):
        if not self.local_mode:
            QMessageBox.warning(self, "Внимание", "Добавление сервисов доступно только в локальном режиме")
            return
        dialog = CustomServiceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, source, source_type = dialog.get_service_data()
            if name and source:
                self.custom_services[name] = {'source': source, 'type': source_type}
                self.refresh_list()

    def edit_selected(self):
        if not self.local_mode:
            QMessageBox.warning(self, "Внимание", "Редактирование доступно только в локальном режиме")
            return
        selected = self.service_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите сервис")
            return
        self.edit_service(selected)

    def edit_service(self, item):
        if not self.local_mode:
            QMessageBox.warning(self, "Внимание", "Редактирование доступно только в локальном режиме")
            return
        name = item.data(Qt.UserRole)
        data = self.custom_services.get(name, {})
        dialog = CustomServiceDialog(self, edit_data=(name, data.get('source', ''), data.get('type', 'url')))
        if dialog.exec() == QDialog.Accepted:
            new_name, source, source_type = dialog.get_service_data()
            if new_name and source:
                if name != new_name:
                    del self.custom_services[name]
                self.custom_services[new_name] = {'source': source, 'type': source_type}
                self.refresh_list()

    def delete_service(self):
        if not self.local_mode:
            QMessageBox.warning(self, "Внимание", "Удаление доступно только в локальном режиме")
            return
        selected = self.service_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите сервис")
            return
        name = selected.data(Qt.UserRole)
        confirm = QMessageBox.question(self, "Подтверждение", f"Удалить сервис '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            del self.custom_services[name]
            self.refresh_list()

    def get_services(self):
        return self.custom_services


class DataLoaderWorker(QThread):
    services_loaded = Signal(list)
    dns_loaded = Signal(dict)
    error = Signal(str)

    def __init__(self, load_type: str, use_local: bool = False):
        super().__init__()
        self.load_type = load_type
        self.use_local = use_local

    def run(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            from database import Database
            db = Database()
            try:
                if self.load_type == 'services':
                    if self.use_local:
                        from main import load_urls_from_file
                        data = loop.run_until_complete(load_urls_from_file())
                    else:
                        from main import load_urls_with_retry
                        data = loop.run_until_complete(load_urls_with_retry(
                            "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platformdb"
                        ))
                    if data:
                        db.save_platforms_to_cache(data)
                        dm_api.set_services_cache(list(data.keys()))
                        dm_api.set_urls_cache(data)
                        from main import cleanup_http_client
                        loop.run_until_complete(cleanup_http_client())
                        self.services_loaded.emit(list(data.keys()))
                    else:
                        self.error.emit("Не удалось загрузить сервисы")
                elif self.load_type == 'dns':
                    if self.use_local:
                        from main import load_dns_from_file
                        data = loop.run_until_complete(load_dns_from_file())
                    else:
                        from main import load_dns_with_retry
                        data = loop.run_until_complete(load_dns_with_retry(
                            "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/dnsdb"
                        ))
                    if data:
                        db.save_dns_to_cache(data)
                        dm_api.set_dns_cache(data)
                        from main import cleanup_http_client
                        loop.run_until_complete(cleanup_http_client())
                        self.dns_loaded.emit(data)
                    else:
                        self.error.emit("Не удалось загрузить DNS")
            finally:
                loop.close()
        except Exception as e:
            self.error.emit(str(e))


class ParserWorker(QThread):
    progress_signal = Signal(str, int)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, services, dns_servers, dns_mode, exclude_cf, rate_limit,
                 subnet, output_format, format_settings, services_list,
                 custom_services: Optional[Dict[str, Dict[str, str]]] = None,
                 use_local: bool = False):
        super().__init__()
        self.services = services
        self.dns_servers = dns_servers
        self.dns_mode = dns_mode
        self.exclude_cf = exclude_cf
        self.rate_limit = rate_limit
        self.subnet = subnet
        self.output_format = output_format
        self.format_settings = format_settings
        self.services_list = services_list
        self.custom_services = custom_services or {}
        self.use_local = use_local

    def run(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            from database import Database
            db = Database()
            self.progress_signal.emit("Загрузка платформ...", 5)
            urls = db.get_platforms_from_cache() if self.use_local else None
            if not urls:
                if self.use_local:
                    from main import load_urls_from_file
                    urls = loop.run_until_complete(load_urls_from_file())
                else:
                    from main import load_urls_with_retry
                    urls = loop.run_until_complete(load_urls_with_retry(
                        "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platformdb"
                    ))
                if urls and self.use_local:
                    db.save_platforms_to_cache(urls)
            if not urls:
                self.error_signal.emit("Не удалось загрузить платформы")
                return
            self.progress_signal.emit("Загрузка DNS...", 15)
            dns_db = db.get_dns_from_cache() if self.use_local else None
            if not dns_db:
                if self.use_local:
                    from main import load_dns_from_file
                    dns_db = loop.run_until_complete(load_dns_from_file())
                else:
                    from main import load_dns_with_retry
                    dns_db = loop.run_until_complete(load_dns_with_retry(
                        "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/dnsdb"
                    ))
                if dns_db and self.use_local:
                    db.save_dns_to_cache(dns_db)
            if not dns_db:
                self.error_signal.emit("Не удалось загрузить DNS")
                return
            dm_api.set_urls_cache(urls)
            dm_api.set_dns_cache(dns_db)
            selected_dns = list(dns_db.keys()) if self.dns_mode == 'all' else self.dns_servers
            result = loop.run_until_complete(
                dm_api.parse_services(
                    services=self.services,
                    dns_servers=selected_dns,
                    urls=urls,
                    dns_db=dns_db,
                    exclude_cloudflare=self.exclude_cf,
                    rate_limit=self.rate_limit,
                    subnet=self.subnet,
                    output_format=self.output_format,
                    format_settings=self.format_settings,
                    on_progress=self._progress_callback,
                    custom_services=self.custom_services,
                    use_local=self.use_local
                )
            )
            if result.get('error'):
                self.error_signal.emit(result['error'])
            else:
                self.finished_signal.emit(result)
        except Exception as e:
            import traceback
            self.error_signal.emit(f"{str(e)}\n{traceback.format_exc()}")
        finally:
            if loop:
                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    loop.close()
                except:
                    pass

    def _progress_callback(self, message: str, percent: int):
        self.progress_signal.emit(message, percent)


class ParserTab(QWidget):
    save_to_database_signal = Signal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.data_loader = None
        self.dns_loader = None
        self.current_results = []
        self.current_list_name = ""
        self.custom_services: Dict[str, Dict[str, str]] = {}
        self.dns_db_cache: Dict[str, List[str]] = {}
        self.init_ui()
        QTimer.singleShot(500, self.load_data_background)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        self.inner_tabs = QTabWidget()
        
        # === Вкладка 1: Парсинг ===
        self.tab_parsing = QWidget()
        parsing_layout = QVBoxLayout(self.tab_parsing)
        top_layout = QHBoxLayout()
        services_group = QGroupBox("📡 Сервисы")
        services_layout = QVBoxLayout()
        self.services_scroll = QScrollArea()
        self.services_scroll.setWidgetResizable(True)
        self.services_scroll.setMinimumHeight(150)
        services_widget = QWidget()
        self.services_checkboxes_layout = QVBoxLayout(services_widget)
        self.service_checkboxes = {}
        self.services_scroll.setWidget(services_widget)
        services_layout.addWidget(self.services_scroll)
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("✅ Все")
        select_all_btn.setMaximumWidth(50)
        select_all_btn.clicked.connect(self.select_all_services)
        deselect_all_btn = QPushButton("❌ Снять")
        deselect_all_btn.setMaximumWidth(50)
        deselect_all_btn.clicked.connect(self.deselect_all_services)
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setMaximumWidth(70)
        refresh_btn.clicked.connect(self.load_services)
        add_btn = QPushButton("➕ Добавить")
        add_btn.setMaximumWidth(70)
        add_btn.clicked.connect(self.add_custom_service)
        manage_btn = QPushButton("⚙️")
        manage_btn.setMaximumWidth(40)
        manage_btn.setToolTip("Управление сервисами")
        manage_btn.clicked.connect(self.manage_services)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(manage_btn)
        btn_layout.addStretch()
        services_layout.addLayout(btn_layout)
        services_group.setLayout(services_layout)
        top_layout.addWidget(services_group, stretch=1)
        parsing_layout.addLayout(top_layout)
        action_layout = QHBoxLayout()
        self.start_btn = QPushButton("🚀 Запустить")
        self.start_btn.clicked.connect(self.start_parsing)
        self.start_btn.setMinimumHeight(30)
        self.start_btn.setEnabled(False)
        self.preview_btn = QPushButton("👁️ Предпросмотр")
        self.preview_btn.clicked.connect(self.show_preview)
        self.preview_btn.setMinimumHeight(30)
        self.preview_btn.setEnabled(False)
        self.save_btn = QPushButton("💾 В базу")
        self.save_btn.clicked.connect(self.save_to_db)
        self.save_btn.setMinimumHeight(30)
        self.save_btn.setEnabled(False)
        self.export_btn = QPushButton("📤 В файл")
        self.export_btn.clicked.connect(self.export_to_file)
        self.export_btn.setMinimumHeight(30)
        self.export_btn.setEnabled(False)
        action_layout.addWidget(self.start_btn)
        action_layout.addWidget(self.preview_btn)
        action_layout.addWidget(self.save_btn)
        action_layout.addWidget(self.export_btn)
        parsing_layout.addLayout(action_layout)
        self.inner_tabs.addTab(self.tab_parsing, "📡 Парсинг")
        
        # === Вкладка 2: Настройки ===
        self.tab_settings = QWidget()
        settings_layout = QVBoxLayout(self.tab_settings)
        mode_group = QGroupBox("🌐 Режим DomainMapper")
        mode_layout = QVBoxLayout()
        self.local_mode_check = QCheckBox("Локальный режим (файлы проекта DM)")
        self.local_mode_check.setToolTip("Использует dnsdb, platformdb и файлы из папки platforms")
        self.local_mode_check.stateChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.local_mode_check)
        mode_info = QLabel("ℹ️ В локальном режиме можно добавлять/редактировать свои сервисы и DNS")
        mode_info.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        mode_layout.addWidget(mode_info)
        mode_group.setLayout(mode_layout)
        settings_layout.addWidget(mode_group)
        dns_group = QGroupBox("🌐 DNS")
        dns_form = QFormLayout()
        self.dns_mode_combo = QComboBox()
        self.dns_mode_combo.addItems(["Все DNS", "Выбрать"])
        self.dns_mode_combo.currentTextChanged.connect(self.on_dns_mode_changed)
        dns_form.addRow("Режим:", self.dns_mode_combo)
        self.dns_list_widget = QWidget()
        self.dns_list_layout = QVBoxLayout(self.dns_list_widget)
        self.dns_scroll_area = QScrollArea()
        self.dns_scroll_area.setWidget(self.dns_list_widget)
        self.dns_scroll_area.setWidgetResizable(True)
        self.dns_scroll_area.setMaximumHeight(200)
        self.dns_scroll_area.setVisible(False)
        self.dns_checkboxes = {}
        dns_form.addRow("Серверы:", self.dns_scroll_area)
        manage_dns_btn = QPushButton("⚙️ Управление DNS...")
        manage_dns_btn.clicked.connect(self.manage_dns)
        dns_form.addRow("", manage_dns_btn)
        dns_group.setLayout(dns_form)
        settings_layout.addWidget(dns_group)
        format_group = QGroupBox("💾 Формат")
        format_form = QFormLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["wireguard", "cidr", "ip", "unix", "win", "mikrotik", "ovpn", "keenetic"])
        self.format_combo.setCurrentText("wireguard")
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_form.addRow("Формат:", self.format_combo)
        self.rate_limit_spin = QSpinBox()
        self.rate_limit_spin.setRange(10, 200)
        self.rate_limit_spin.setValue(50)
        format_form.addRow("Rate limit:", self.rate_limit_spin)
        self.exclude_cf_check = QCheckBox("Исключить Cloudflare")
        format_form.addRow("", self.exclude_cf_check)
        self.subnet_combo = QComboBox()
        self.subnet_combo.addItems(['32', '24', '16', 'mix'])
        self.subnet_combo.setCurrentText('mix')
        format_form.addRow("CIDR:", self.subnet_combo)
        self.format_settings_widget = QWidget()
        self.format_settings_layout = QFormLayout()
        self.format_settings_layout.setContentsMargins(0, 0, 0, 0)
        self.gateway_label = QLabel("Шлюз:")
        self.gateway_input = QLineEdit()
        self.ken_label = QLabel("Keenetic:")
        self.ken_gateway_input = QLineEdit()
        self.mk_label = QLabel("Mikrotik list:")
        self.mk_listname_input = QLineEdit()
        self.mk_comment_check = QCheckBox("comment")
        self.format_settings_layout.addRow(self.gateway_label, self.gateway_input)
        self.format_settings_layout.addRow(self.ken_label, self.ken_gateway_input)
        self.format_settings_layout.addRow(self.mk_label, self.mk_listname_input)
        self.format_settings_layout.addRow("", self.mk_comment_check)
        self.format_settings_widget.setLayout(self.format_settings_layout)
        format_form.addRow("", self.format_settings_widget)
        format_group.setLayout(format_form)
        settings_layout.addWidget(format_group)
        settings_layout.addStretch()
        self.inner_tabs.addTab(self.tab_settings, "⚙️ Настройки")
        
        # === Вкладка 3: Лог ===
        self.tab_log = QWidget()
        log_layout = QVBoxLayout(self.tab_log)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        clear_log_btn = QPushButton("🗑️ Очистить")
        clear_log_btn.setMaximumWidth(150)
        clear_log_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_log_btn, alignment=Qt.AlignRight)
        self.inner_tabs.addTab(self.tab_log, "📋 Лог")
        main_layout.addWidget(self.inner_tabs)
        status_group = QGroupBox("📊 Статус")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        status_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(20)
        status_layout.addWidget(self.progress_bar)
        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.stats_label.setFont(QFont("Consolas", 9))
        status_layout.addWidget(self.stats_label)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        self.on_format_changed("wireguard")
        self.load_dm_mode()

    def load_dm_mode(self):
        from database import Database
        db = Database()
        mode = db.get_setting('dm_mode', 'network')
        self.local_mode_check.setChecked(mode == 'local')

    def on_mode_changed(self, state):
        from database import Database
        db = Database()
        try:
            mode = 'local' if self.local_mode_check.isChecked() else 'network'
            db.set_setting('dm_mode', mode)
            self.log_message(f"✅ Режим: {mode}")
            
            if mode == 'network':
                # При переключении в сетевой режим - очищаем кэш
                db.clear_platforms_cache()
                db.clear_dns_cache()
                # Очищаем кастомные сервисы из UI (но не из БД!)
                self.custom_services = {}
                self.dns_db_cache = {}
            
            # Полная перезагрузка UI
            self.clear_services_ui(full_clear=True)
            self.load_data_background()
        except Exception as e:
            self.log_message(f"❌ Ошибка смены режима: {e}")
        finally:
            db.close()

    def clear_services_ui(self, full_clear=False):
        """Очищает UI сервисов"""
        for i in reversed(range(self.services_checkboxes_layout.count())):
            widget = self.services_checkboxes_layout.itemAt(i).widget()
            if widget and isinstance(widget, QCheckBox):
                is_custom = widget.property('custom')
                # Если full_clear=True - удаляем всё, иначе только системные
                if full_clear or not is_custom:
                    widget.deleteLater()
        
        if full_clear:
            self.service_checkboxes = {}
        else:
            self.service_checkboxes = {k: v for k, v in self.service_checkboxes.items() 
                                       if v.property('custom')}

    def load_data_background(self):
        use_local = self.local_mode_check.isChecked()
        mode_str = "локальный" if use_local else "сетевой"
        self.log_message(f"🔄 Загрузка ({mode_str})...")
        
        self.data_loader = DataLoaderWorker('services', use_local=use_local)
        self.data_loader.services_loaded.connect(self.on_services_loaded)
        self.data_loader.error.connect(self.on_data_load_error)
        self.data_loader.start()
        
        self.dns_loader = DataLoaderWorker('dns', use_local=use_local)
        self.dns_loader.dns_loaded.connect(self.on_dns_loaded)
        self.dns_loader.error.connect(self.on_data_load_error)
        self.dns_loader.start()
        
        # Загружаем кастомные сервисы ТОЛЬКО в локальном режиме
        if use_local:
            self.load_custom_services_from_db()
            self.load_custom_dns_from_db()

    def load_custom_services_from_db(self):
        from database import Database
        db = Database()
        self.custom_services = db.get_all_custom_services()
        for name, data in self.custom_services.items():
            self.add_custom_service_to_ui(name, data)
        if self.custom_services:
            self.log_message(f"✅ Своих сервисов: {len(self.custom_services)}")

    def add_custom_service_to_ui(self, name, data):
        source_type = data.get('type', 'url')
        prefix = "📝" if source_type == 'manual' else ("📁" if source_type == 'file' else "🌐")
        cb = QCheckBox(f"{prefix} {name}")
        cb.setProperty('custom', True)
        cb.setChecked(False)
        self.services_checkboxes_layout.addWidget(cb)
        self.service_checkboxes[name] = cb

    def load_custom_dns_from_db(self):
        from database import Database
        db = Database()
        custom_dns = db.get_all_custom_dns()
        for name, servers in custom_dns.items():
            self.dns_db_cache[name] = servers
        if custom_dns:
            self.log_message(f"✅ Своих DNS: {len(custom_dns)}")

    def load_services(self):
        use_local = self.local_mode_check.isChecked()
        self.log_message(f"🔄 Обновление...")
        self.clear_services_ui()
        self.data_loader = DataLoaderWorker('services', use_local=use_local)
        self.data_loader.services_loaded.connect(self.on_services_loaded)
        self.data_loader.error.connect(self.on_data_load_error)
        self.data_loader.start()

    def load_dns_combo(self):
        if self.dns_list_layout:
            while self.dns_list_layout.count():
                item = self.dns_list_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        self.dns_checkboxes = {}
        for name in sorted(self.dns_db_cache.keys()):
            cb = QCheckBox(f"{name}")
            cb.setChecked(True)
            self.dns_list_layout.addWidget(cb)
            self.dns_checkboxes[name] = cb

    def on_dns_mode_changed(self, mode):
        self.dns_scroll_area.setVisible(mode == "Выбрать")

    def on_format_changed(self, fmt):
        self.gateway_label.setVisible(fmt in ['win', 'unix'])
        self.gateway_input.setVisible(fmt in ['win', 'unix'])
        self.ken_label.setVisible(fmt == 'keenetic')
        self.ken_gateway_input.setVisible(fmt == 'keenetic')
        self.mk_label.setVisible(fmt == 'mikrotik')
        self.mk_listname_input.setVisible(fmt == 'mikrotik')
        self.mk_comment_check.setVisible(fmt == 'mikrotik')

    def manage_dns(self):
        use_local = self.local_mode_check.isChecked()
        if not use_local:
            QMessageBox.warning(self, "Внимание", "Управление DNS доступно только в локальном режиме")
            return
        dialog = DNSSettingsDialog(self, self.dns_db_cache, local_mode=use_local)
        if dialog.exec() == QDialog.Accepted:
            self.dns_db_cache = dialog.get_dns_db()
            dm_api.set_dns_cache(self.dns_db_cache)
            from database import Database
            db = Database()
            try:
                db.cursor.execute("DELETE FROM custom_dns")
                db.conn.commit()
                for name, servers in self.dns_db_cache.items():
                    db.save_custom_dns(name, servers)
                self.load_dns_combo()
                self.log_message("✅ DNS сохранены")
            except Exception as e:
                self.log_message(f"❌ Ошибка сохранения DNS: {e}")
            finally:
                db.close()

    def manage_services(self):
        use_local = self.local_mode_check.isChecked()
        if not use_local:
            QMessageBox.warning(self, "Внимание", "Управление сервисами доступно только в локальном режиме")
            return
        dialog = ServiceManagementDialog(self, self.custom_services, local_mode=use_local)
        if dialog.exec() == QDialog.Accepted:
            self.custom_services = dialog.get_services()
            from database import Database
            db = Database()
            try:
                db.cursor.execute("DELETE FROM custom_services")
                db.conn.commit()
                for name, data in self.custom_services.items():
                    db.save_custom_service(name, data.get('source', ''), data.get('type', 'url'))
                self.clear_services_ui()
                for name, data in self.custom_services.items():
                    self.add_custom_service_to_ui(name, data)
                self.log_message("✅ Сервисы сохранены")
            except Exception as e:
                self.log_message(f"❌ Ошибка сохранения сервисов: {e}")
            finally:
                db.close()

    def add_custom_service(self):
        use_local = self.local_mode_check.isChecked()
        if not use_local:
            QMessageBox.warning(self, "Внимание", "Добавление сервисов доступно только в локальном режиме")
            return
        dialog = CustomServiceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, source, source_type = dialog.get_service_data()
            if not name or not source:
                QMessageBox.warning(self, "Ошибка", "Заполните поля")
                return
            from database import Database
            db = Database()
            db.save_custom_service(name, source, source_type)
            self.custom_services[name] = {'source': source, 'type': source_type}
            self.add_custom_service_to_ui(name, self.custom_services[name])
            self.log_message(f"✅ Добавлен: {name}")

    def on_services_loaded(self, services: list):
        for service in sorted(services):
            if service not in self.service_checkboxes:
                cb = QCheckBox(service)
                cb.setChecked(False)
                self.services_checkboxes_layout.addWidget(cb)
                self.service_checkboxes[service] = cb
        self.start_btn.setEnabled(True)
        self.log_message(f"✅ Сервисов: {len(services)}")
        self.status_label.setText("Готов")

    def on_dns_loaded(self, dns: dict):
        self.dns_db_cache = dns
        self.load_dns_combo()
        self.log_message(f"✅ DNS: {len(dns)}")

    def on_data_load_error(self, error: str):
        self.log_message(f"⚠️ Ошибка: {error}")

    def select_all_services(self):
        for cb in self.service_checkboxes.values():
            cb.setChecked(True)

    def deselect_all_services(self):
        for cb in self.service_checkboxes.values():
            cb.setChecked(False)

    def start_parsing(self):
        selected_services = [name for name, cb in self.service_checkboxes.items() if cb.isChecked()]
        if not selected_services:
            QMessageBox.warning(self, "Внимание", "Выберите сервисы!")
            return
        dns_mode = "all" if self.dns_mode_combo.currentText() == "Все DNS" else "specific"
        dns_servers = [name for name, cb in self.dns_checkboxes.items() if cb.isChecked()] if dns_mode == "specific" else []
        format_settings = {
            'gateway': self.gateway_input.text().strip(),
            'keenetic': self.ken_gateway_input.text().strip(),
            'mk_listname': self.mk_listname_input.text().strip(),
            'mk_comment': 'on' if self.mk_comment_check.isChecked() else 'off'
        }
        self.start_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_message(f"🚀 Запуск: {', '.join(selected_services)}")
        use_local = self.local_mode_check.isChecked()
        self.worker = ParserWorker(
            services=selected_services,
            dns_servers=dns_servers,
            dns_mode=dns_mode,
            exclude_cf=self.exclude_cf_check.isChecked(),
            rate_limit=self.rate_limit_spin.value(),
            subnet=self.subnet_combo.currentText(),
            output_format=self.format_combo.currentText(),
            format_settings=format_settings,
            services_list=selected_services,
            custom_services=self.custom_services,
            use_local=use_local
        )
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_parsing_finished)
        self.worker.error_signal.connect(self.on_parsing_error)
        self.worker.start()

    def update_progress(self, message: str, percent: int):
        self.status_label.setText(message)
        self.progress_bar.setValue(percent)
        self.log_message(f"→ {message}")

    def on_parsing_finished(self, result: dict):
        self.start_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        if result.get('success'):
            self.current_results = result['ips']
            self.current_list_name = f"parsed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.preview_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            stats = result['stats']
            self.stats_label.setText(f"📊 IP: {result['total_ips']} | Доменов: {stats['total_domains_processed']}")
            self.log_message(f"✅ Готово! IP: {result['total_ips']}")
        else:
            self.log_message(f"❌ Ошибка: {result.get('error', 'Неизвестная')}")

    def on_parsing_error(self, error: str):
        self.start_btn.setEnabled(True)
        self.log_message(f"❌ Ошибка: {error}")
        QMessageBox.critical(self, "Ошибка", f"Ошибка:\n{error}")

    def show_preview(self):
        if not self.current_results:
            return
        dialog = PreviewDialog(self, self.current_results, self.current_list_name)
        dialog.exec()

    def save_to_db(self):
        if not self.current_results:
            return
        list_name, ok = QInputDialog.getText(self, "Сохранение", "Название:", text=self.current_list_name)
        if ok and list_name:
            self.save_to_database_signal.emit(self.current_results, list_name)
            self.log_message(f"💾 Сохранено: {list_name}")

    def export_to_file(self):
        if not self.current_results:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if self.format_combo.currentText() == 'wireguard':
                        f.write(', '.join(self.current_results))
                    else:
                        f.write('\n'.join(self.current_results))
                self.log_message(f"📤 Экспорт: {file_path}")
                QMessageBox.information(self, "Успех", f"Сохранено {len(self.current_results)} IP")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось: {e}")

    def clear_log(self):
        self.log_text.clear()
        self.log_message("🗑️ Лог очищен")

    def log_message(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
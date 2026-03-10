# gui/main_window.py
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                QTableWidget, QTableWidgetItem, QPushButton,
                                QLabel, QHeaderView, QTabWidget, QSplitter,
                                QMenu, QToolBar, QListWidget, QListWidgetItem,
                                QFileDialog, QMessageBox, QTextEdit, QDialog,
                                QApplication, QComboBox, QCheckBox, QScrollArea, QGroupBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from database import Database
from dialogs import SettingsDialog, IPListDialog, ImportDialog, ProfileNameDialog, SelectIPListsDialog
from parser_tab import ParserTab
import json


class IPFormatConverterDialog(QDialog):
    """Диалог импорта сервисов с выбором"""
    def __init__(self, parent, import_data):
        super().__init__(parent)
        self.import_data = import_data
        self.selected_services = []
        self.setWindowTitle("📥 Импорт сервисов")
        self.setMinimumSize(600, 500)
        layout = QVBoxLayout()
        
        # Информация
        info_label = QLabel("Выберите сервисы для импорта:")
        info_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(info_label)
        
        # Кнопки выбора
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("✅ Выбрать все")
        select_all_btn.setMaximumWidth(120)
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("❌ Снять выбор")
        deselect_all_btn.setMaximumWidth(120)
        deselect_all_btn.clicked.connect(self.deselect_all)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Список с чекбоксами
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.checkbox_layout = QVBoxLayout(self.scroll_widget)
        self.checkboxes = {}
        
        for name, data in import_data.get('services', {}).items():
            source_type = data.get('type', 'url')
            cb = QCheckBox(f"{name} ({source_type})")
            cb.setProperty('name', name)
            cb.setProperty('data', data)
            self.checkboxes[name] = cb
            self.checkbox_layout.addWidget(cb)
        
        self.checkbox_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)
        
        # Кнопки
        dialog_btns = QHBoxLayout()
        btn_import = QPushButton("📥 Импортировать")
        btn_import.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }")
        btn_import.clicked.connect(self.accept)
        btn_cancel = QPushButton("❌ Отмена")
        btn_cancel.clicked.connect(self.reject)
        dialog_btns.addWidget(btn_import)
        dialog_btns.addWidget(btn_cancel)
        layout.addLayout(dialog_btns)
        
        self.setLayout(layout)

    def select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def deselect_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def get_selected_services(self):
        selected = {}
        for name, cb in self.checkboxes.items():
            if cb.isChecked():
                selected[name] = cb.property('data')
        return selected


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.current_profile_id = None
        self.current_profile_name = ""
        self.setWindowTitle("🔐 WireGuard Config Manager Pro")
        self.setMinimumSize(1200, 800)
        self.init_ui()
        self.load_profiles()
        self.load_global_ip_lists()
        active = self.db.get_active_profile()
        if active:
            self.load_profile(active[0])
        else:
            self.statusBar().showMessage("Создайте новый профиль или выберите существующий")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === ЛЕВАЯ ПАНЕЛЬ ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_header = QLabel("📁 Профили")
        left_header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        left_layout.addWidget(left_header)
        self.profile_list = QListWidget()
        self.profile_list.itemClicked.connect(self.on_profile_selected)
        self.profile_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.profile_list.customContextMenuRequested.connect(self.show_profile_context_menu)
        left_layout.addWidget(self.profile_list)
        btn_new_profile = QPushButton("➕ Новый профиль")
        btn_new_profile.setStyleSheet("QPushButton { padding: 10px; font-weight: bold; }")
        btn_new_profile.clicked.connect(self.create_new_profile)
        left_layout.addWidget(btn_new_profile)
        
        # === ПРАВАЯ ПАНЕЛЬ ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_title = QLabel("Нет выбранного профиля")
        self.profile_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        right_layout.addWidget(self.profile_title)
        self.tabs = QTabWidget()
        
        # === Вкладка 1: База данных IP ===
        self.tab_global_ips = QWidget()
        global_ip_layout = QVBoxLayout(self.tab_global_ips)
        global_ip_toolbar = QHBoxLayout()
        self.btn_add_global_ip = QPushButton("➕ Создать список")
        self.btn_add_global_ip.clicked.connect(self.add_global_ip_list)
        self.btn_edit_global_ip = QPushButton("✏️ Редактировать")
        self.btn_edit_global_ip.clicked.connect(self.edit_global_ip_list)
        self.btn_del_global_ip = QPushButton("🗑️ Удалить")
        self.btn_del_global_ip.clicked.connect(self.delete_global_ip_list)
        self.btn_import_json = QPushButton("📥 Импорт JSON")
        self.btn_import_json.clicked.connect(self.import_ip_from_json)
        
        # === ВЫПАДАЮЩИЙ СПИСОК КОНВЕРТЕРА ===
        self.converter_combo = QComboBox()
        self.converter_combo.addItem("🔄 Конвертер форматов...")
        self.converter_combo.addItems(["wireguard", "cidr", "ip", "unix", "win", "mikrotik", "ovpn", "keenetic"])
        self.converter_combo.setCurrentIndex(0)
        self.converter_combo.setMaximumWidth(200)
        self.converter_combo.currentIndexChanged.connect(self.on_converter_selected)
        
        global_ip_toolbar.addWidget(self.btn_add_global_ip)
        global_ip_toolbar.addWidget(self.btn_edit_global_ip)
        global_ip_toolbar.addWidget(self.btn_del_global_ip)
        global_ip_toolbar.addStretch()
        global_ip_toolbar.addWidget(QLabel("Конвертер:"))
        global_ip_toolbar.addWidget(self.converter_combo)
        global_ip_toolbar.addWidget(self.btn_import_json)
        global_ip_layout.addLayout(global_ip_toolbar)
        
        self.global_ip_table = QTableWidget()
        self.global_ip_table.setColumnCount(3)
        self.global_ip_table.setHorizontalHeaderLabels(["Название", "IP Адреса", "Создан"])
        self.global_ip_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.global_ip_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.global_ip_table.setEditTriggers(QTableWidget.NoEditTriggers)
        global_ip_layout.addWidget(self.global_ip_table)
        
        # === Вкладка 2: IP списки профиля ===
        self.tab_profile_ips = QWidget()
        profile_ip_layout = QVBoxLayout(self.tab_profile_ips)
        profile_ip_toolbar = QHBoxLayout()
        self.btn_add_to_profile = QPushButton("➕ Добавить из базы")
        self.btn_add_to_profile.clicked.connect(self.add_ip_list_to_profile)
        self.btn_remove_from_profile = QPushButton("➖ Удалить из профиля")
        self.btn_remove_from_profile.clicked.connect(self.remove_ip_list_from_profile)
        profile_ip_toolbar.addWidget(self.btn_add_to_profile)
        profile_ip_toolbar.addWidget(self.btn_remove_from_profile)
        profile_ip_toolbar.addStretch()
        profile_ip_layout.addLayout(profile_ip_toolbar)
        self.profile_ip_table = QTableWidget()
        self.profile_ip_table.setColumnCount(3)
        self.profile_ip_table.setHorizontalHeaderLabels(["ID", "Название", "IP Адреса"])
        self.profile_ip_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.profile_ip_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.profile_ip_table.setEditTriggers(QTableWidget.NoEditTriggers)
        profile_ip_layout.addWidget(self.profile_ip_table)
        
        # === Вкладка 3: Настройки и Предпросмотр (ОБЪЕДИНЕНЫ) ===
        self.tab_settings_preview = QWidget()
        sp_layout = QVBoxLayout(self.tab_settings_preview)
        settings_group = QGroupBox("⚙️ Настройки WireGuard")
        settings_layout = QVBoxLayout()
        self.settings_display = QTextEdit()
        self.settings_display.setReadOnly(True)
        self.settings_display.setMaximumHeight(200)
        settings_layout.addWidget(self.settings_display)
        self.btn_edit_settings = QPushButton("✏️ Редактировать настройки")
        self.btn_edit_settings.setMaximumWidth(200)
        self.btn_edit_settings.clicked.connect(self.edit_wg_settings)
        settings_layout.addWidget(self.btn_edit_settings)
        settings_group.setLayout(settings_layout)
        sp_layout.addWidget(settings_group)
        preview_group = QGroupBox("👁️ Предпросмотр конфига")
        preview_layout = QVBoxLayout()
        preview_toolbar = QHBoxLayout()
        self.btn_generate = QPushButton("🔄 Сгенерировать")
        self.btn_generate.clicked.connect(self.generate_config)
        self.btn_export = QPushButton("💾 Экспорт")
        self.btn_export.clicked.connect(self.export_config)
        self.btn_copy = QPushButton("📋 Копировать")
        self.btn_copy.clicked.connect(self.copy_config)
        preview_toolbar.addWidget(self.btn_generate)
        preview_toolbar.addWidget(self.btn_export)
        preview_toolbar.addWidget(self.btn_copy)
        preview_toolbar.addStretch()
        preview_layout.addLayout(preview_toolbar)
        self.config_preview = QTextEdit()
        self.config_preview.setReadOnly(True)
        self.config_preview.setFont(QFont("Consolas", 10))
        preview_layout.addWidget(self.config_preview)
        preview_group.setLayout(preview_layout)
        sp_layout.addWidget(preview_group)
        
        # === Вкладка 4: История ===
        self.tab_history = QWidget()
        history_layout = QVBoxLayout(self.tab_history)
        history_toolbar = QHBoxLayout()
        self.btn_clear_history = QPushButton("🗑️ Очистить историю")
        self.btn_clear_history.clicked.connect(self.clear_history)
        history_toolbar.addWidget(self.btn_clear_history)
        history_toolbar.addStretch()
        history_layout.addLayout(history_toolbar)
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        
        # === Вкладка 5: Парсинг IP ===
        self.parser_tab = ParserTab()
        self.parser_tab.save_to_database_signal.connect(self.save_parsed_ips_to_db)
        
        # Добавляем вкладки
        self.tabs.addTab(self.tab_global_ips, "🗄️ База данных")
        self.tabs.addTab(self.tab_profile_ips, "📋 IP профиля")
        self.tabs.addTab(self.tab_settings_preview, "⚙️ Настройки")
        self.tabs.addTab(self.tab_history, "📜 История")
        self.tabs.addTab(self.parser_tab, "📡 Парсинг IP")
        
        right_layout.addWidget(self.tabs)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)
        
        # Тулбар
        toolbar = QToolBar("Главная")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        profile_menu = QMenu("📁 Профиль", self)
        import_action = QAction("📥 Импорт .conf", self)
        import_action.triggered.connect(self.import_config)
        profile_menu.addAction(import_action)
        export_action = QAction("📤 Экспорт .conf", self)
        export_action.triggered.connect(self.export_config)
        profile_menu.addAction(export_action)
        toolbar.addAction(profile_menu.menuAction())
        toolbar.addSeparator()
        toolbar.addAction(QAction("🔄 Генерировать", self, triggered=self.generate_config))

    def on_converter_selected(self, index):
        """Обработка выбора формата в конвертере"""
        if index == 0:
            return  # Первый элемент - заголовок
        
        fmt = self.converter_combo.currentText()
        selected = self.global_ip_table.selectedItems()
        
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите IP списки для конвертации")
            self.converter_combo.setCurrentIndex(0)
            return
        
        # Получаем уникальные строки
        rows = set(item.row() for item in selected)
        
        confirm = QMessageBox.question(
            self, "Подтверждение",
            f"Конвертировать {len(rows)} списков в формат {fmt}?\n\n"
            "⚠️ Это перезапишет IP адреса в базе данных!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            count = 0
            for row in rows:
                list_id = self.global_ip_table.item(row, 0).data(Qt.UserRole)
                ips_str = self.global_ip_table.item(row, 1).text()
                ips = [ip.strip() for ip in ips_str.split(',') if ip.strip()]
                
                # Конвертируем
                converted = self.apply_format(ips, fmt)
                converted_str = ', '.join(converted) if fmt == 'wireguard' else '\n'.join(converted)
                
                # Обновляем в БД
                self.db.update_ip_list(list_id, self.global_ip_table.item(row, 0).text(), converted_str)
                count += 1
            
            self.load_global_ip_lists()
            QMessageBox.information(self, "Успех", f"Конвертировано {count} списков в формат {fmt}")
        
        # Сбрасываем выбор на заголовок
        self.converter_combo.setCurrentIndex(0)

    def apply_format(self, ips, fmt):
        """Применяет форматирование к IP адресам"""
        if fmt == 'wireguard':
            return [ip if '/' in ip else f"{ip}/32" for ip in ips]
        elif fmt == 'cidr':
            return [ip if '/' in ip else f"{ip}/32" for ip in ips]
        elif fmt == 'ip':
            return [ip.split('/')[0] for ip in ips]
        elif fmt == 'win':
            return [f"route add {ip.split('/')[0]} mask 255.255.255.0 0.0.0.0" for ip in ips]
        elif fmt == 'unix':
            return [f"ip route {ip} 0.0.0.0" for ip in ips]
        elif fmt == 'mikrotik':
            return [f'/ip/firewall/address-list add list=DM_List address={ip}' for ip in ips]
        elif fmt == 'ovpn':
            return [f'push "route {ip.split("/")[0]} 255.255.255.0"' for ip in ips]
        elif fmt == 'keenetic':
            return [f"ip route {ip} 0.0.0.0 auto" for ip in ips]
        return ips

    def load_profiles(self):
        self.profile_list.clear()
        profiles = self.db.get_all_profiles()
        for p in profiles:
            item = QListWidgetItem(f"📄 {p[1]}")
            item.setData(Qt.UserRole, p[0])
            if p[4] == 1:
                item.setBackground(Qt.lightGray)
            self.profile_list.addItem(item)

    def on_profile_selected(self, item):
        profile_id = item.data(Qt.UserRole)
        self.load_profile(profile_id)

    def load_profile(self, profile_id):
        self.current_profile_id = profile_id
        profiles = self.db.get_all_profiles()
        for p in profiles:
            if p[0] == profile_id:
                self.current_profile_name = p[1]
                break
        self.profile_title.setText(f"📄 {self.current_profile_name}")
        self.db.set_active_profile(profile_id)
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.data(Qt.UserRole) == profile_id:
                item.setBackground(Qt.lightGray)
            else:
                item.setBackground(Qt.white)
        self.load_profile_ip_lists()
        self.load_wg_settings()
        self.load_history()
        self.config_preview.clear()
        self.statusBar().showMessage(f"Профиль '{self.current_profile_name}' загружен")

    def create_new_profile(self):
        dialog = ProfileNameDialog(self, "Новый профиль")
        if dialog.exec() == QDialog.Accepted:
            name = dialog.get_name()
            if name:
                profile_id = self.db.create_profile(name)
                if profile_id:
                    self.load_profiles()
                    self.load_profile(profile_id)
                else:
                    QMessageBox.warning(self, "Ошибка", "Профиль с таким именем уже существует")

    def show_profile_context_menu(self, pos):
        item = self.profile_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("Переименовать")
        delete_action = menu.addAction("Удалить")
        action = menu.exec(self.profile_list.mapToGlobal(pos))
        if action == rename_action:
            self.rename_profile(item)
        elif action == delete_action:
            self.delete_profile(item)

    def rename_profile(self, item):
        profile_id = item.data(Qt.UserRole)
        dialog = ProfileNameDialog(self, "Переименовать профиль", self.current_profile_name)
        if dialog.exec() == QDialog.Accepted:
            new_name = dialog.get_name()
            if new_name:
                if self.db.rename_profile(profile_id, new_name):
                    self.load_profiles()
                    self.current_profile_name = new_name
                    self.profile_title.setText(f"📄 {new_name}")
                else:
                    QMessageBox.warning(self, "Ошибка", "Имя уже занято")

    def delete_profile(self, item):
        profile_id = item.data(Qt.UserRole)
        confirm = QMessageBox.question(self, "Подтверждение",
                                       f"Удалить профиль '{item.text()}'?\nВсе данные будут потеряны.",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.db.delete_profile(profile_id)
            self.current_profile_id = None
            self.current_profile_name = ""
            self.profile_title.setText("Нет выбранного профиля")
            self.profile_ip_table.setRowCount(0)
            self.settings_display.clear()
            self.config_preview.clear()
            self.history_list.clear()
            self.load_profiles()
            self.statusBar().showMessage("Профиль удален")

    def load_global_ip_lists(self):
        self.global_ip_table.setRowCount(0)
        lists = self.db.get_all_ip_lists()
        for row in lists:
            pos = self.global_ip_table.rowCount()
            self.global_ip_table.insertRow(pos)
            self.global_ip_table.setItem(pos, 0, QTableWidgetItem(row[1]))
            self.global_ip_table.setItem(pos, 1, QTableWidgetItem(row[2]))
            date_str = row[3][:19].replace('T', ' ') if row[3] else ""
            self.global_ip_table.setItem(pos, 2, QTableWidgetItem(date_str))
            self.global_ip_table.item(pos, 0).setData(Qt.UserRole, row[0])

    def get_selected_global_ip_list_ids(self):
        """Получает ID выбранных строк"""
        selected = self.global_ip_table.selectedItems()
        if not selected:
            return []
        rows = set(item.row() for item in selected)
        ids = []
        for row in rows:
            item = self.global_ip_table.item(row, 0)
            if item:
                ids.append(item.data(Qt.UserRole))
        return ids

    def add_global_ip_list(self):
        dialog = IPListDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, ips = dialog.get_data()
            list_id = self.db.create_ip_list(name, ips)
            if list_id:
                self.load_global_ip_lists()
                self.statusBar().showMessage(f"Список '{name}' создан")
            else:
                QMessageBox.warning(self, "Ошибка", "Список с таким именем уже существует")

    def edit_global_ip_list(self):
        list_id = self.get_selected_global_ip_list_ids()
        if not list_id:
            return
        data = self.db.get_ip_list(list_id[0])
        if data:
            dialog = IPListDialog(self, data)
            if dialog.exec() == QDialog.Accepted:
                name, ips = dialog.get_data()
                self.db.update_ip_list(list_id[0], name, ips)
                self.load_global_ip_lists()
                if self.current_profile_id:
                    self.load_profile_ip_lists()

    def delete_global_ip_list(self):
        list_ids = self.get_selected_global_ip_list_ids()
        if not list_ids:
            return
        confirm = QMessageBox.question(self, "Подтверждение",
                                       f"Удалить {len(list_ids)} IP списков?\nОни будут удалены из всех профилей!",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            for list_id in list_ids:
                self.db.delete_ip_list(list_id)
            self.load_global_ip_lists()
            if self.current_profile_id:
                self.load_profile_ip_lists()

    def import_ip_from_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Импорт IP списков из JSON", "",
                                                    "JSON Files (*.json);;All Files (*)")
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                QMessageBox.warning(self, "Ошибка", "JSON должен содержать объект с названиями списков и IP")
                return
            
            # Показываем диалог выбора сервисов
            dialog = IPFormatConverterDialog(self, {'services': data})
            if dialog.exec() == QDialog.Accepted:
                selected = dialog.get_selected_services()
                count = 0
                for name, ips in selected.items():
                    if isinstance(ips, list):
                        ips_str = ", ".join(ips)
                    else:
                        ips_str = str(ips)
                    if self.db.create_ip_list(name, ips_str):
                        count += 1
                self.load_global_ip_lists()
                self.statusBar().showMessage(f"Импортировано {count} списков IP из JSON")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось импортировать JSON: {e}")

    def export_ip_to_json(self):
        """Экспорт выбранных IP списков в JSON"""
        selected_ids = self.get_selected_global_ip_list_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Внимание", "Выберите IP списки для экспорта")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт IP списков в JSON", "",
                                                    "JSON Files (*.json);;All Files (*)")
        if file_path:
            try:
                export_data = {}
                for list_id in selected_ids:
                    row = self.db.get_ip_list(list_id)
                    if row:
                        ips_list = [ip.strip() for ip in row[2].split(',') if ip.strip()]
                        export_data[row[1]] = ips_list
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                self.statusBar().showMessage(f"Экспортировано {len(export_data)} списков в {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось экспортировать: {e}")

    def load_profile_ip_lists(self):
        self.profile_ip_table.setRowCount(0)
        if not self.current_profile_id:
            return
        lists = self.db.get_profile_ip_lists(self.current_profile_id)
        for row in lists:
            pos = self.profile_ip_table.rowCount()
            self.profile_ip_table.insertRow(pos)
            self.profile_ip_table.setItem(pos, 0, QTableWidgetItem(str(row[0])))
            self.profile_ip_table.setItem(pos, 1, QTableWidgetItem(row[1]))
            self.profile_ip_table.setItem(pos, 2, QTableWidgetItem(row[2]))

    def add_ip_list_to_profile(self):
        if not self.current_profile_id:
            QMessageBox.warning(self, "Внимание", "Выберите профиль")
            return
        available = self.db.get_available_ip_lists_for_profile(self.current_profile_id)
        if not available:
            QMessageBox.information(self, "Инфо", "Нет доступных IP списков для добавления")
            return
        dialog = SelectIPListsDialog(self, available)
        if dialog.exec() == QDialog.Accepted:
            selected_ids = dialog.get_selected_ids()
            count = 0
            for list_id in selected_ids:
                if self.db.add_ip_list_to_profile(self.current_profile_id, list_id):
                    count += 1
            self.load_profile_ip_lists()
            self.statusBar().showMessage(f"Добавлено {count} списков к профилю")

    def remove_ip_list_from_profile(self):
        if not self.current_profile_id:
            return
        selected = self.profile_ip_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите список для удаления")
            return
        list_id = int(selected[0].text())
        confirm = QMessageBox.question(self, "Подтверждение",
                                       "Удалить этот список из профиля?\nСам список останется в базе.",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.db.remove_ip_list_from_profile(self.current_profile_id, list_id)
            self.load_profile_ip_lists()

    def load_wg_settings(self):
        if not self.current_profile_id:
            self.settings_display.clear()
            return
        settings = self.db.get_wg_settings(self.current_profile_id)
        if settings:
            text = f"""Address: {settings[3] or 'N/A'}
DNS: {settings[4] or 'N/A'}
MTU: {settings[5] or 'N/A'}
Endpoint: {settings[7] or 'N/A'}
Keepalive: {settings[8] or 'N/A'}
PrivateKey: {'***' if settings[2] else 'Не задан'}
PublicKey: {'***' if settings[6] else 'Не задан'}
"""
            self.settings_display.setText(text)

    def edit_wg_settings(self):
        if not self.current_profile_id:
            QMessageBox.warning(self, "Внимание", "Выберите профиль")
            return
        settings = self.db.get_wg_settings(self.current_profile_id)
        dialog = SettingsDialog(self, settings)
        if dialog.exec() == QDialog.Accepted:
            new_settings = dialog.get_settings()
            self.db.save_wg_settings(self.current_profile_id, new_settings)
            self.load_wg_settings()
            self.statusBar().showMessage("Настройки сохранены")

    def import_config(self):
        dialog = ImportDialog(self)
        if dialog.exec() == QDialog.Accepted:
            config_text = dialog.get_config_text()
            if not config_text.strip():
                QMessageBox.warning(self, "Внимание", "Конфиг пуст")
                return
            profile_name = self.extract_profile_name_from_config(config_text)
            name_dialog = ProfileNameDialog(self, "📥 Импорт профиля", profile_name)
            if name_dialog.exec() == QDialog.Accepted:
                profile_name = name_dialog.get_name()
                if not profile_name:
                    QMessageBox.warning(self, "Ошибка", "Введите название профиля")
                    return
                profile_id = self.db.create_profile(profile_name)
                if profile_id:
                    if self.parse_and_import_config(config_text, profile_id):
                        self.load_profiles()
                        self.load_profile(profile_id)
                        self.statusBar().showMessage("Конфиг успешно импортирован")
                    else:
                        self.db.delete_profile(profile_id)
                        self.load_profiles()
                else:
                    QMessageBox.warning(self, "Ошибка", "Профиль с таким именем уже существует")

    def extract_profile_name_from_config(self, config_text):
        try:
            for line in config_text.split('\n'):
                line = line.strip()
                if line.lower().startswith('endpoint'):
                    if '=' in line:
                        endpoint = line.split('=', 1)[1].strip()
                        name = endpoint.split(':')[0]
                        if name:
                            return f"Imported_{name.replace('.', '_')}"
        except:
            pass
        return "Imported_Config"

    def parse_and_import_config(self, config_text, profile_id):
        try:
            interface_section = {}
            peer_section = {}
            current_section = None
            for line in config_text.split('\n'):
                line = line.strip()
                if line.startswith('['):
                    current_section = line.strip('[]').lower()
                    continue
                if '=' in line and current_section:
                    key, value = line.split('=', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if current_section == 'interface':
                        interface_section[key] = value
                    elif current_section == 'peer':
                        peer_section[key] = value
            settings = (
                interface_section.get('privatekey', ''),
                interface_section.get('address', '10.7.0.18/32'),
                interface_section.get('dns', '1.1.1.1'),
                interface_section.get('mtu', '1420'),
                peer_section.get('publickey', ''),
                peer_section.get('endpoint', ''),
                peer_section.get('persistentkeepalive', '21')
            )
            self.db.save_wg_settings(profile_id, settings)
            allowed_ips = peer_section.get('allowedips', '')
            if allowed_ips:
                ips_list = [ip.strip() for ip in allowed_ips.split(',') if ip.strip()]
                if ips_list:
                    self.db.create_ip_list("Imported", ", ".join(ips_list))
                    all_lists = self.db.get_all_ip_lists()
                    for lst in all_lists:
                        if lst[1] == "Imported":
                            self.db.add_ip_list_to_profile(profile_id, lst[0])
                            break
            return True
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось распарсить конфиг: {e}")
            return False

    def generate_config(self):
        if not self.current_profile_id:
            QMessageBox.warning(self, "Внимание", "Выберите профиль")
            return
        lists = self.db.get_profile_ip_lists(self.current_profile_id)
        if not lists:
            QMessageBox.warning(self, "Внимание", "Нет IP списков для генерации")
            return
        all_ips = []
        for row in lists:
            ips = [ip.strip() for ip in row[2].split(',') if ip.strip()]
            all_ips.extend(ips)
        allowed_ips_str = ", ".join(all_ips)
        settings = self.db.get_wg_settings(self.current_profile_id)
        if not settings:
            QMessageBox.critical(self, "Ошибка", "Нет настроек WireGuard")
            return
        config = f"""[Interface]
PrivateKey = {settings[2]}
Address = {settings[3]}
DNS = {settings[4]}
MTU = {settings[5]}

[Peer]
PublicKey = {settings[6]}
AllowedIPs = {allowed_ips_str}
Endpoint = {settings[7]}
PersistentKeepalive = {settings[8]}
"""
        self.config_preview.setText(config)
        self.tabs.setCurrentIndex(2)
        self.statusBar().showMessage("Конфиг сгенерирован")

    def export_config(self):
        if not self.current_profile_id:
            QMessageBox.warning(self, "Внимание", "Выберите профиль")
            return
        lists = self.db.get_profile_ip_lists(self.current_profile_id)
        if not lists:
            QMessageBox.warning(self, "Внимание", "Нет IP списков")
            return
        all_ips = []
        for row in lists:
            ips = [ip.strip() for ip in row[2].split(',') if ip.strip()]
            all_ips.extend(ips)
        settings = self.db.get_wg_settings(self.current_profile_id)
        config = f"""[Interface]
PrivateKey = {settings[2]}
Address = {settings[3]}
DNS = {settings[4]}
MTU = {settings[5]}

[Peer]
PublicKey = {settings[6]}
AllowedIPs = {", ".join(all_ips)}
Endpoint = {settings[7]}
PersistentKeepalive = {settings[8]}
"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить конфиг",
                                                    f"{self.current_profile_name}.conf",
                                                    "WireGuard Config (*.conf);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(config)
                self.statusBar().showMessage(f"Конфиг сохранен: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def copy_config(self):
        config = self.config_preview.toPlainText()
        if config:
            QApplication.clipboard().setText(config)
            self.statusBar().showMessage("Конфиг скопирован в буфер")
        else:
            QMessageBox.information(self, "Инфо", "Сначала сгенерируйте конфиг")

    def load_history(self):
        self.history_list.clear()
        if not self.current_profile_id:
            return
        history = self.db.get_history(self.current_profile_id)
        for action, timestamp in history:
            self.history_list.addItem(f"[{timestamp}] {action}")

    def clear_history(self):
        if not self.current_profile_id:
            QMessageBox.warning(self, "Внимание", "Выберите профиль")
            return
        confirm = QMessageBox.question(self, "Подтверждение",
                                       "Очистить историю этого профиля?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.db.clear_history(self.current_profile_id)
            self.load_history()
            self.statusBar().showMessage("История очищена")

    def save_parsed_ips_to_db(self, ips: list, list_name: str):
        try:
            existing = self.db.get_ip_list_by_name(list_name)
            if existing:
                reply = QMessageBox.question(
                    self, "Список существует",
                    f"Список '{list_name}' уже существует. Заменить?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
                self.db.delete_ip_list_by_name(list_name)
            ips_str = ", ".join(ips)
            self.db.create_ip_list(list_name, ips_str)
            QMessageBox.information(
                self, "Успех",
                f"Сохранено {len(ips)} IP-адресов в список '{list_name}'"
            )
            self.load_global_ip_lists()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить в БД: {e}")

    def closeEvent(self, event):
        self.db.close()
        event.accept()
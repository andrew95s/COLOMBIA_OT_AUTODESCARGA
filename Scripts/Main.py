# -*- coding: utf-8 -*-
import os
import io
import sys
import codecs
import signal
import psutil
import sqlite3
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, 
                               QTextEdit, QComboBox, QDialog, QLineEdit, QMessageBox, QTabWidget, 
                               QTableWidget, QTableWidgetItem, QHBoxLayout)
from PySide6.QtCore import Qt, QRunnable, QThreadPool, Signal, QObject, Slot, QMetaObject
from PySide6.QtGui import QTextCursor, QColor, QPalette, QFont

def find_project_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(current_dir, 'Scripts')) and \
           os.path.exists(os.path.join(current_dir, 'db')) and \
           os.path.exists(os.path.join(current_dir, 'credentials.txt')):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            raise FileNotFoundError("No se pudo encontrar la carpeta raíz del proyecto")
        current_dir = parent_dir

PROJECT_ROOT = find_project_root()

class ConsoleRedirect(QObject):
    write_signal = Signal(str)

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.write_signal.connect(self.write_to_widget)
        self.buffer = io.StringIO()

    def write(self, text):
        try:
            decoded_text = text.encode('utf-8').decode('utf-8')
        except UnicodeEncodeError:
            decoded_text = text.encode('utf-8', errors='replace').decode('utf-8')
        self.buffer.write(decoded_text)
        if '\n' in decoded_text:
            self.flush()

    def flush(self):
        self.write_signal.emit(self.buffer.getvalue())
        self.buffer.truncate(0)
        self.buffer.seek(0)

    def write_to_widget(self, text):
        cursor = self.text_widget.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.text_widget.setTextCursor(cursor)
    
    def detach(self):
        return None

class WorkerSignals(QObject):
    finished = Signal(str)
    error = Signal(str)

class ScriptRunner(QRunnable):
    def __init__(self, script_path, console_redirect):
        super().__init__()
        self.script_path = script_path
        self.signals = WorkerSignals()
        self.process = None
        self.console_redirect = console_redirect

    def run(self):
        try:
            self.process = subprocess.Popen([sys.executable, self.script_path], 
                                            stdout=subprocess.PIPE, 
                                            stderr=subprocess.PIPE, 
                                            bufsize=1, 
                                            universal_newlines=True,
                                            encoding='utf-8',
                                            errors='replace')
            
            while True:
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    break
                if output:
                    self.console_redirect.write(output)
            
            rc = self.process.poll()
            if rc != 0:
                error = self.process.stderr.read()
                self.signals.error.emit(f"Error en el script (código {rc}): {error}")
        except Exception as e:
            self.signals.error.emit(str(e))

    def kill(self):
        if self.process:
            parent = psutil.Process(self.process.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()

class CredentialsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Credenciales de Acceso -Correos Hotmail/Outlook")
        self.setGeometry(200, 200, 300, 150)

        layout = QVBoxLayout()

        self.email_label = QLabel("Correo:")
        self.email_input = QLineEdit()
        layout.addWidget(self.email_label)
        layout.addWidget(self.email_input)

        self.password_label = QLabel("Contraseña:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        self.update_button = QPushButton("Actualizar Datos")
        self.update_button.clicked.connect(self.update_credentials)
        layout.addWidget(self.update_button)

        self.setLayout(layout)

    def update_credentials(self):
        email = self.email_input.text()
        password = self.password_input.text()

        if email and password:
            credentials_path = os.path.join(PROJECT_ROOT, "credentials.txt")
            with open(credentials_path, "w") as f:
                f.write(f"Email: {email}\nPassword: {password}")
            QMessageBox.information(self, "Éxito", "Credenciales actualizadas correctamente.")
        else:
            QMessageBox.warning(self, "Error", "Por favor, ingrese correo y contraseña.")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("COLOMBIA OT's AUTODESCARGA  By Andres Felipe Osorio --- andres.osorio@igac.gov.co --- osorio.ucaldas@hormail.com")
        self.setGeometry(100, 100, 900, 700)

        self.set_dark_theme()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3A3A3A;
                background: #2D2D2D;
            }
            QTabBar::tab {
                background: #1E1E1E;
                color: #FFFFFF;
                padding: 10px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background: #0D47A1;
            }
        """)
        
        # Pestaña 1: Controles originales
        self.tab1 = QWidget()
        self.tab1_layout = QVBoxLayout(self.tab1)
        
        self.cargar_lista_btn = self.create_button("Cargar Lista Municipios")
        self.cargar_lista_btn.clicked.connect(self.cargar_lista_municipios)
        self.tab1_layout.addWidget(self.cargar_lista_btn)

        self.inicializar_proceso_btn = self.create_button("Inicializar Proceso", "#005200") 
        self.inicializar_proceso_btn.clicked.connect(self.inicializar_proceso)
        self.tab1_layout.addWidget(self.inicializar_proceso_btn)

        self.numero_label = QLabel("Seleccione la cantidad de consultas en paralelo (Ventanas)")
        self.numero_label.setStyleSheet("color: #FFFFFF; font-size: 14px;")
        self.tab1_layout.addWidget(self.numero_label)

        self.numero_combo = QComboBox()
        self.numero_combo.addItems([str(i) for i in range(1, 16)])
        self.numero_combo.setCurrentText("4")
        self.numero_combo.currentTextChanged.connect(self.guardar_numero)
        self.numero_combo.setStyleSheet("""
            QComboBox {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid #555555;
                padding: 5px;
                min-width: 6em;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: #555555;
                border-left-style: solid;
            }
        """)
        self.tab1_layout.addWidget(self.numero_combo)

        self.credenciales_btn = self.create_button("Credenciales de Acceso Hotmail/Outlook")
        self.credenciales_btn.clicked.connect(self.abrir_credenciales)
        self.tab1_layout.addWidget(self.credenciales_btn)

        self.console_output = QTextEdit(self)
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #00FF00;
                border: 1px solid #3A3A3A;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }
        """)
        self.tab1_layout.addWidget(self.console_output)

        self.clear_console_btn = self.create_button("Limpiar Consola")
        self.clear_console_btn.clicked.connect(self.clear_console)
        self.tab1_layout.addWidget(self.clear_console_btn)

        self.console_redirect = ConsoleRedirect(self.console_output)
        sys.stdout = self.console_redirect
        sys.stderr = self.console_redirect

        self.kill_process_btn = self.create_button("Detener Proceso", "#6B0000")
        self.kill_process_btn.clicked.connect(self.kill_process)
        self.tab1_layout.addWidget(self.kill_process_btn)
        self.current_runner = None

        # Pestaña 2: Visualización de datos
        self.tab2 = QWidget()
        self.tab2_layout = QVBoxLayout(self.tab2)
        
        self.table_layout = QHBoxLayout()
        self.pending_table = QTableWidget()
        self.deleted_table = QTableWidget()
        self.setup_table(self.pending_table, "Descargas Pendientes", QColor(0, 200, 0))
        self.setup_table(self.deleted_table, "Descargas Finalizadas", QColor(200, 0, 0))
        self.table_layout.addWidget(self.pending_table)
        self.table_layout.addWidget(self.deleted_table)
        self.tab2_layout.addLayout(self.table_layout)
        
        self.clear_db_btn = self.create_button("Limpiar Base de Datos")
        self.clear_db_btn.clicked.connect(self.clear_database)
        self.tab2_layout.addWidget(self.clear_db_btn)
        
        self.tab_widget.addTab(self.tab1, "Controles")
        self.tab_widget.addTab(self.tab2, "Visualización de Datos")
        
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.addWidget(self.tab_widget)
        
        self.load_data()

        self.threadpool = QThreadPool()

        print("GUI inicializada correctamente.")
        print(f"Carpeta raíz del proyecto: {PROJECT_ROOT}")

    def create_button(self, text, color="#0D47A1"):
        button = QPushButton(text)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color)};
            }}
        """)
        return button

    def lighten_color(self, color):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        return f"#{min(255, r + 20):02x}{min(255, g + 20):02x}{min(255, b + 20):02x}"

    def darken_color(self, color):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        return f"#{max(0, r - 20):02x}{max(0, g - 20):02x}{max(0, b - 20):02x}"
    
    def set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(dark_palette)

    def setup_table(self, table, title, color):
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Municipio", "Objetivo Descargas", "Total Descargados"])
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #2D2D2D;
                color: #FFFFFF;
                gridline-color: #3A3A3A;
            }}
            QHeaderView::section {{
                background-color: {color.name()};
                color: #FFFFFF;
                padding: 5px;
                border: 1px solid #3A3A3A;
            }}
            QTableWidget::item {{
                border: 1px solid #3A3A3A;
            }}
        """)
        table.setHorizontalHeaderItem(0, QTableWidgetItem(title))
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

    def get_db_path(self):
        db_path = os.path.join(PROJECT_ROOT, "db", "Consultas.db")
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"No se encontró la base de datos en {db_path}")
        return db_path

    def load_data(self):
        try:
            db_path = self.get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT municipio, objetivo_descargas, total_descargados FROM municipios_tab_replica")
            self.populate_table(self.pending_table, cursor.fetchall())

            cursor.execute("SELECT municipio, objetivo_descargas, total_descargados FROM municipios_tab_borrados")
            self.populate_table(self.deleted_table, cursor.fetchall())

            conn.close()
        except FileNotFoundError as e:
            QMessageBox.warning(self, "Error", str(e))
        except sqlite3.OperationalError as e:
            QMessageBox.warning(self, "Error", f"Error al acceder a las tablas: {str(e)}")

    def populate_table(self, table, data):
        table.setRowCount(len(data))
        for row, record in enumerate(data):
            for col, value in enumerate(record):
                item = QTableWidgetItem(str(value))
                table.setItem(row, col, item)

    def clear_database(self):
        reply = QMessageBox.warning(self, "Advertencia", 
                                    "¿Está seguro de que desea eliminar toda la información de las bases de datos?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                db_path = self.get_db_path()
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                cursor.execute("DELETE FROM municipios_tab_replica")
                cursor.execute("DELETE FROM municipios_tab_borrados")
                conn.commit()
                conn.close()

                QMessageBox.information(self, "Éxito", "Las bases de datos han sido limpiadas exitosamente.")
                self.load_data()
            except FileNotFoundError as e:
                QMessageBox.warning(self, "Error", str(e))
            except sqlite3.OperationalError as e:
                QMessageBox.warning(self, "Error", f"Error al limpiar las tablas: {str(e)}")

    def cargar_lista_municipios(self):
        script_path = os.path.join(PROJECT_ROOT, "Scripts", "consulta_db.py")
        print(f"Ejecutando script: {script_path}")
        self.ejecutar_script(script_path)

    def inicializar_proceso(self):
        script_path = os.path.join(PROJECT_ROOT, "Scripts", "Script_OT.py")
        self.ejecutar_script(script_path)

    def ejecutar_script(self, script_path):
        if os.path.exists(script_path):
            self.current_runner = ScriptRunner(script_path, self.console_redirect)
            self.current_runner.signals.finished.connect(self.on_script_finished)
            self.current_runner.signals.error.connect(self.on_script_error)
            self.threadpool.start(self.current_runner)
        else:
            QMessageBox.warning(self, "Error", f"No se encontró el archivo {script_path}")

    def kill_process(self):
        if self.current_runner and self.current_runner.process:
            self.current_runner.kill()
            print("Proceso detenido.")
            self.console_output.append("Proceso detenido por el usuario.")
        else:
            print("No hay proceso en ejecución para detener.")
            self.console_output.append("No hay proceso en ejecución para detener.")

    @Slot(str)
    def on_script_finished(self, output):
        self.load_data()

    @Slot(str)
    def on_script_error(self, error_msg):
        self.console_redirect.write(f"Error: {error_msg}\n")
        QMessageBox.critical(self, "Error", f"Error al ejecutar el script: {error_msg}")

    def guardar_numero(self, numero):
        numero_path = os.path.join(PROJECT_ROOT, "workers_ventanas.txt")
        with open(numero_path, "w") as f:
            f.write(numero)
        print(f"Número {numero} guardado en {numero_path}")

    def abrir_credenciales(self):
        dialog = CredentialsDialog(self)
        if hasattr(dialog, 'exec'):
            dialog.exec()
        else:
            dialog.exec_()

    def clear_console(self):
        self.console_output.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
        window.show()
        print("Aplicación iniciada. Esperando interacción del usuario...")
        print(f"Carpeta raíz del proyecto: {PROJECT_ROOT}")
        sys.exit(app.exec())
    except Exception as e:
        QMessageBox.critical(None, "Error crítico", f"Error al iniciar la aplicación: {str(e)}")
        sys.exit(1)
# -*- coding: utf-8 -*-
import pandas as pd
import sqlite3
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import os

# Función para obtener la ruta de la base de datos
def get_db_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    db_dir = os.path.join(parent_dir, 'db')
    return os.path.join(db_dir, 'Consultas.db')

# Función para limpiar la tabla
def limpiar_tabla(conn, cursor):
    cursor.execute("DELETE FROM municipios_tab")
    conn.commit()

# Función para insertar datos en la tabla
def insertar_datos(conn, cursor, datos):
    cursor.executemany("INSERT INTO municipios_tab (municipio) VALUES (?)", datos)
    conn.commit()

# Función para listar los municipios guardados
def listar_municipios(cursor):
    cursor.execute("SELECT municipio FROM municipios_tab")
    municipios = cursor.fetchall()
    print("\nMunicipios guardados en la base de datos:")
    for i, (municipio,) in enumerate(municipios, 1):
        print(f"{i}. {municipio}")

# Función principal
def main():
    # Crear una ventana Tkinter oculta
    Tk().withdraw()

    # Solicitar al usuario que seleccione el archivo Excel
    excel_path = askopenfilename(title="Selecciona el archivo Excel", filetypes=[("Excel files", "*.xlsx *.xls")])

    if not excel_path:
        print("No se seleccionó ningún archivo.")
        return

    # Leer el archivo Excel
    df = pd.read_excel(excel_path)

    # Obtener los valores de la primera columna
    municipios = df.iloc[:, 0].tolist()

    # Obtener la ruta de la base de datos
    db_path = get_db_path()

    # Conectar a la base de datos SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Limpiar la tabla
    limpiar_tabla(conn, cursor)

    # Insertar los nuevos datos
    datos = [(municipio,) for municipio in municipios]
    insertar_datos(conn, cursor, datos)

    print(f"Se han guardado {len(municipios)} municipios en la base de datos.")

    # Listar los municipios guardados
    listar_municipios(cursor)

    # Cerrar la conexión
    conn.close()

if __name__ == "__main__":
    main()
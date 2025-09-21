# conexion_mysql.py
import mysql.connector

# Crear conexión
def conexion():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="password",
            database="inventario"
        )
        if conn.is_connected():
            print("Conexión exitosa a la base de datos")
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar: {err}")
        return None

# Cerrar conexión
def cerrar_conexion(conn):
    if conn and conn.is_connected():
        conn.close()
        print("Conexión cerrada.")

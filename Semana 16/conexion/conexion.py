# clase de conexion a BD sin sqlalchemy 
import mysql.connector
from mysql.connector import Error

# conexion a la base de datos

def conexion():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="inventario"
    )

# cerrar conexion a la base de datos
def cerrar_conexion(conn):
    if conn.is_connected():
        conn.close()
        print("Conexion a la base de datos cerrada.")

# probar conexion a la base de datos

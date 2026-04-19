from fastapi import FastAPI
import sqlite3
import os
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "personas.db")

class Persona(BaseModel):
    nombre: str
    edad:int
    correo:str

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def crear_tabla():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            edad INTEGER NOT NULL,                    
            correo TEXT NOT NULL                         
        )
    """)
    conn.commit()
    conn.close()

crear_tabla()
            
@app.get("/")
def inicio():
    return {"mensaje": "API de personas funcionando"}

@app.get("/personas")
def obtener_personas():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nombre, edad, correo FROM personas")
    personas = cursor.fetchall()
    conn.close()

    return [dict(persona) for persona in personas]
    
@app.post("/personas")
def crear_persona(persona: Persona):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO personas (nombre, edad, correo) VALUES (?, ?, ?)",
        (persona.nombre, persona.edad, persona.correo)
    )
    conn.commit()
    conn.close()

    return {"mensaje": "Persona creada correctamente"}

@app.put("/personas/{id}")
def editar_persona(id: int, persona: Persona):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM personas WHERE id = ?", (id,))
    if not cursor.fetchone():
        conn.close()
        return {"error": "Persona no encontrada"}

    cursor.execute(
        "UPDATE personas SET nombre = ?, edad = ?, correo = ? WHERE id = ?",
        (persona.nombre, persona.edad, persona.correo, id)
    )
    conn.commit()
    conn.close()

    return {"mensaje": "Persona actualizada correctamente"}



@app.delete("/personas/{id}")
def eliminar_persona(id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM personas WHERE id = ?", (id,))
    if not cursor.fetchone():
        conn.close()
        return {"error": "Persona no encontrada"}
    
    cursor.execute("DELETE FROM personas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return {"mensaje": "Persona eliminada correctamente"}
@app.get("/debug-db")
def debug_db():
    return {"db_patch": DB_PATH}
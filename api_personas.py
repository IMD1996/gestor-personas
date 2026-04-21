from fastapi import FastAPI
import psycopg2
import os
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

class UsuarioRegistro(BaseModel):
    nombre: str
    email: str
    password: str

class UsuarioLogin(BaseModel):
    email: str
    password: str

class Persona(BaseModel):
    nombre: str
    edad: int
    correo: str

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def crear_tabla():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personas(
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            edad INTEGER NOT NULL,
            correo TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

crear_tabla()

@app.post("/registro")
def registrar_usuario(usuario: UsuarioRegistro):
    if not usuario.nombre.strip() or not usuario.email.strip() or not usuario.password.strip():
        return {"error": "Todos los campos son obligatorios"}

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (usuario.email,))
    usuario_existente = cursor.fetchone()

    if usuario_existente:
        cursor.close()
        conn.close()
        return {"error": "El correo ya está registrado"}

    password_hash = pwd_context.hash(usuario.password)

    cursor.execute(
        "INSERT INTO usuarios (nombre, email, password) VALUES (%s, %s, %s)",
        (usuario.nombre, usuario.email, password_hash)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Usuario registrado correctamente"}

@app.post("/login")
def login(usuario: UsuarioLogin):
    if not usuario.email.strip() or not usuario.password.strip():
        return {"error": "Email y contraseña son obligatorios"}

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (usuario.email,))
    usuario_db = cursor.fetchone()

    cursor.close()
    conn.close()

    if not usuario_db:
        return {"error": "Usuario no encontrado"}

    if not pwd_context.verify(usuario.password, usuario_db[3]):
        return {"error": "Contraseña incorrecta"}

    return {
        "mensaje": "Login correcto",
        "usuario": {
            "id": usuario_db[0],
            "nombre": usuario_db[1],
            "email": usuario_db[2]
        }
    }
            
@app.get("/")
def inicio():
    return {"mensaje": "API de personas funcionando"}

@app.get("/personas")
def obtener_personas():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nombre, edad, correo FROM personas")
    personas = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": p[0],
            "nombre": p[1],
            "edad": p[2],
            "correo": p[3]
        }
        for p in personas
    ]
    
@app.post("/personas")
def crear_persona(persona: Persona):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO personas (nombre, edad, correo) VALUES (%s, %s, %s)",
        (persona.nombre, persona.edad, persona.correo)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Persona creada correctamente"}

@app.put("/personas/{id}")
def editar_persona(id: int, persona: Persona):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM personas WHERE id = %s", (id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return {"error": "Persona no encontrada"}

    cursor.execute(
        "UPDATE personas SET nombre = %s, edad = %s, correo = %s WHERE id = %s",
        (persona.nombre, persona.edad, persona.correo, id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Persona actualizada correctamente"}


@app.delete("/personas/{id}")
def eliminar_persona(id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM personas WHERE id = %s", (id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return {"error": "Persona no encontrada"}
    
    cursor.execute("DELETE FROM personas WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Persona eliminada correctamente"}
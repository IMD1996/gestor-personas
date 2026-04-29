from fastapi import HTTPException, status
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Header
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


SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


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

@app.post("/registro", status_code=201)
def registrar_usuario(usuario: UsuarioRegistro):
    if not usuario.nombre.strip() or not usuario.email.strip() or not usuario.password.strip():
        raise HTTPException(status_code=400, detail="Todos los campos son obligatorios")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (usuario.email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    password_hash = pwd_context.hash(usuario.password)

    try:
        cursor.execute(
            "INSERT INTO usuarios (nombre, email, password) VALUES (%s, %s, %s)",
            (usuario.nombre, usuario.email, password_hash)
        )
        conn.commit()
    except Exception as e:
        print("ERROR EN REGISTRO:", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

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

    access_token = crear_token(
    data={"sub": usuario_db[2]},
    expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    refresh_token = crear_token(
    data={"sub": usuario_db[2], "type": "refresh"},
    expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

    return {
    "mensaje": "Login correcto",
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer",
    "usuario": {
        "id": usuario_db[0],
        "nombre": usuario_db[1],
        "email": usuario_db[2]
    }
}

class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/refresh")
def refresh_token(data: RefreshRequest):
    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")

        email = payload.get("sub")

        if not email:
            raise HTTPException(status_code=401, detail="Token inválido")

        nuevo_access_token = crear_token(
            data={"sub": email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            "access_token": nuevo_access_token,
            "token_type": "bearer"
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

def crear_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")

    try:
        esquema, token = authorization.split()

        if esquema.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Formato inválido")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")

        return {"email": email}

    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado o inválido")

@app.get("/")
def inicio():
    return {"mensaje": "API de personas funcionando"}

@app.get("/personas")
def obtener_personas(authorization: str = Header(None)):
    

    verificar_token(authorization)

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
def crear_persona(persona: Persona, authorization: str = Header(None)):
    
    
    
    verificar_token(authorization)

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
def editar_persona(id: int, persona: Persona, authorization: str = Header(None)):

    
    
    verificar_token(authorization)

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
def eliminar_persona(id: int, authorization: str = Header(None)):

    
    
    verificar_token(authorization)

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
import hashlib
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from domain.entidades import (
    Usuario,
    Tarea,
    Postulacion,
    Mensaje,
    Notificacion,
    Resena,
    RolParticipacion,
)
from application.interfaces import (
    IValidadorCredenciales,
    IUsuarioRepository,
    ITareaRepository,
    IPostulacionRepository,
    IMensajeRepository,
    INotificacionRepository,
    IResenaRepository,
    ISilencioRepository,
)


class ValidadorCredencialesSHA256(IValidadorCredenciales):
    def hashear(self, password_plano: str) -> str:
        return hashlib.sha256(password_plano.encode("utf-8")).hexdigest()

    def verificar(self, password_plano: str, password_hash: str) -> bool:
        return self.hashear(password_plano) == password_hash


def inicializar_bd(db_path: str = "database.db") -> None:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Usuarios (
            Id TEXT PRIMARY KEY,
            Nombre TEXT NOT NULL,
            Correo TEXT UNIQUE NOT NULL,
            PasswordHash TEXT NOT NULL,
            Carrera TEXT NOT NULL,
            Contacto TEXT NOT NULL DEFAULT '',
            Habilidades TEXT NOT NULL,
            Bio TEXT NOT NULL,
            Activo INTEGER NOT NULL DEFAULT 0,
            CodigoVerificacion TEXT
        )
        """
    )

    try:
        c.execute("ALTER TABLE Usuarios ADD COLUMN Contacto TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Tareas (
            Id TEXT PRIMARY KEY,
            CreadorId TEXT NOT NULL,
            Titulo TEXT NOT NULL,
            Descripcion TEXT NOT NULL,
            Requisitos TEXT NOT NULL,
            FechaLimite TEXT NOT NULL,
            Categoria TEXT NOT NULL,
            Estado TEXT NOT NULL,
            FechaPublicacion TEXT NOT NULL,
            FOREIGN KEY (CreadorId) REFERENCES Usuarios(Id)
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Participaciones (
            Id TEXT PRIMARY KEY,
            UsuarioId TEXT NOT NULL,
            TareaId TEXT NOT NULL,
            Rol TEXT NOT NULL,
            Estado TEXT NOT NULL,
            MensajePropuesta TEXT NOT NULL,
            FOREIGN KEY (UsuarioId) REFERENCES Usuarios(Id),
            FOREIGN KEY (TareaId) REFERENCES Tareas(Id)
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Mensajes (
            Id TEXT PRIMARY KEY,
            TareaId TEXT NOT NULL,
            EmisorId TEXT NOT NULL,
            Contenido TEXT NOT NULL,
            FechaEnvio TEXT NOT NULL,
            FOREIGN KEY (TareaId) REFERENCES Tareas(Id),
            FOREIGN KEY (EmisorId) REFERENCES Usuarios(Id)
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Notificaciones (
            Id TEXT PRIMARY KEY,
            UsuarioId TEXT NOT NULL,
            OrigenUsuarioId TEXT,
            Titulo TEXT NOT NULL,
            Mensaje TEXT NOT NULL,
            Leida INTEGER NOT NULL DEFAULT 0,
            Fecha TEXT NOT NULL,
            FOREIGN KEY (UsuarioId) REFERENCES Usuarios(Id)
        )
        """
    )

    try:
        c.execute("ALTER TABLE Notificaciones ADD COLUMN OrigenUsuarioId TEXT")
    except sqlite3.OperationalError:
        pass

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS Resenas (
            Id TEXT PRIMARY KEY,
            TareaId TEXT NOT NULL,
            AutorId TEXT NOT NULL,
            ReceptorId TEXT NOT NULL,
            Calificacion INTEGER NOT NULL,
            Comentario TEXT NOT NULL,
            Fecha TEXT NOT NULL,
            FOREIGN KEY (TareaId) REFERENCES Tareas(Id),
            FOREIGN KEY (AutorId) REFERENCES Usuarios(Id),
            FOREIGN KEY (ReceptorId) REFERENCES Usuarios(Id)
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS UsuariosSilenciados (
            Id TEXT PRIMARY KEY,
            UsuarioId TEXT NOT NULL,
            SilenciadoId TEXT NOT NULL,
            Fecha TEXT NOT NULL,
            UNIQUE(UsuarioId, SilenciadoId),
            FOREIGN KEY (UsuarioId) REFERENCES Usuarios(Id),
            FOREIGN KEY (SilenciadoId) REFERENCES Usuarios(Id)
        )
        """
    )

    conn.commit()
    conn.close()


def sembrar_datos_iniciales(db_path: str = "database.db") -> None:
    validador = ValidadorCredencialesSHA256()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    usuarios_base = [
        (
            "00000000-0000-0000-0000-000000000001",
            "Administrador FIF",
            "admin@fiflancers.mx",
            validador.hashear("Admin123!"),
            "Administración Plataforma - FIF UAQ",
            "admin@fiflancers.mx",
            "Gestión, Arquitectura de Software, Python",
            "Cuenta administrativa de FIFLancers.",
            1,
            None,
        ),
        (
            "123e4567-e89b-12d3-a456-426614174000",
            "Ana Estudiante",
            "ana@uaq.mx",
            validador.hashear("Ana123!"),
            "Ingeniería de Software - FIF UAQ",
            "ana@uaq.mx | Discord: anasofia_dev",
            "Python, FastAPI, Clean Architecture, SQLite, Git",
            "Busco colaboradores para proyectos de desarrollo web y arquitectura.",
            1,
            None,
        ),
        (
            "223e4567-e89b-12d3-a456-426614174000",
            "Carlos Mendoza",
            "carlos@uaq.mx",
            validador.hashear("Carlos123!"),
            "Ingeniería en Computación - FIF UAQ",
            "carlos@uaq.mx | Tel: 442-123-4567",
            "Frontend, HTML, CSS, JavaScript, Redes",
            "Desarrollador web apasionado por interfaces limpias y sistemas distribuidos.",
            1,
            None,
        ),
        (
            "323e4567-e89b-12d3-a456-426614174000",
            "Valeria López",
            "valeria@uaq.mx",
            validador.hashear("Valeria123!"),
            "Ingeniería de Software - FIF UAQ",
            "valeria@uaq.mx | GitHub: @valelopez",
            "Python, SQLite, JavaScript, HTML, CSS",
            "Me interesa colaborar en aplicaciones web completas y bases de datos.",
            1,
            None,
        ),
    ]

    c.executemany(
        "INSERT OR IGNORE INTO Usuarios VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        usuarios_base,
    )

    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    tareas_base = [
        (
            "333e4567-e89b-12d3-a456-426614174001",
            "123e4567-e89b-12d3-a456-426614174000",
            "Desarrollo de API REST en Python",
            "Necesito apoyo para implementar rutas y pruebas unitarias en Python para un proyecto escolar.",
            "Python 3.10+, FastAPI, manejo básico de JSON y Git.",
            (ahora + timedelta(days=7)).isoformat(),
            "Desarrollo Web",
            "Abierta",
            ahora.isoformat(),
        ),
        (
            "333e4567-e89b-12d3-a456-426614174002",
            "223e4567-e89b-12d3-a456-426614174000",
            "Diseño de Base de Datos Relacional en SQLite",
            "Busco compañero que domine normalización y consultas SQL para optimizar un sistema escolar.",
            "SQL estándar, modelado Entidad-Relación (3FN) y manejo de índices.",
            (ahora + timedelta(days=5)).isoformat(),
            "Bases de Datos",
            "Abierta",
            ahora.isoformat(),
        ),
    ]

    c.executemany(
        "INSERT OR IGNORE INTO Tareas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        tareas_base,
    )

    participaciones_base = [
        (
            "444e4567-e89b-12d3-a456-426614174001",
            "123e4567-e89b-12d3-a456-426614174000",
            "333e4567-e89b-12d3-a456-426614174001",
            RolParticipacion.CREADOR.value,
            "Aceptada",
            "Creador de la tarea",
        ),
        (
            "444e4567-e89b-12d3-a456-426614174002",
            "223e4567-e89b-12d3-a456-426614174000",
            "333e4567-e89b-12d3-a456-426614174002",
            RolParticipacion.CREADOR.value,
            "Aceptada",
            "Creador de la tarea",
        ),
    ]

    c.executemany(
        "INSERT OR IGNORE INTO Participaciones VALUES (?, ?, ?, ?, ?, ?)",
        participaciones_base,
    )

    conn.commit()
    conn.close()


class UsuarioRepositorySQLite(IUsuarioRepository):
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path

    def _mapear(self, row) -> Usuario:
        contacto = row[5] if row[5] else row[2]
        return Usuario(
            id=uuid.UUID(row[0]),
            nombre=row[1],
            correo=row[2],
            password_hash=row[3],
            carrera=row[4],
            contacto=contacto,
            habilidades=row[6],
            bio=row[7],
            activo=bool(row[8]),
            codigo_verificacion=row[9],
        )

    def guardar(self, usuario: Usuario) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO Usuarios VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(usuario.id),
                usuario.nombre,
                usuario.correo,
                usuario.password_hash,
                usuario.carrera,
                usuario.contacto,
                usuario.habilidades,
                usuario.bio,
                1 if usuario.activo else 0,
                usuario.codigo_verificacion,
            ),
        )
        conn.commit()
        conn.close()

    def actualizar(self, usuario: Usuario) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            UPDATE Usuarios
            SET Nombre=?, Carrera=?, Contacto=?, Habilidades=?, Bio=?, Activo=?, CodigoVerificacion=?
            WHERE Id=?
            """,
            (
                usuario.nombre,
                usuario.carrera,
                usuario.contacto,
                usuario.habilidades,
                usuario.bio,
                1 if usuario.activo else 0,
                usuario.codigo_verificacion,
                str(usuario.id),
            ),
        )
        conn.commit()
        conn.close()

    def obtener_por_id(self, id: uuid.UUID) -> Optional[Usuario]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            SELECT Id, Nombre, Correo, PasswordHash, Carrera, Contacto, Habilidades, Bio, Activo, CodigoVerificacion
            FROM Usuarios WHERE Id=?
            """,
            (str(id),),
        )
        row = c.fetchone()
        conn.close()
        return self._mapear(row) if row else None

    def obtener_por_correo(self, correo: str) -> Optional[Usuario]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            SELECT Id, Nombre, Correo, PasswordHash, Carrera, Contacto, Habilidades, Bio, Activo, CodigoVerificacion
            FROM Usuarios WHERE Correo=?
            """,
            (correo.strip().lower(),),
        )
        row = c.fetchone()
        conn.close()
        return self._mapear(row) if row else None

    def listar_todos(self) -> List[Usuario]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            SELECT Id, Nombre, Correo, PasswordHash, Carrera, Contacto, Habilidades, Bio, Activo, CodigoVerificacion
            FROM Usuarios WHERE Activo=1
            """
        )
        rows = c.fetchall()
        conn.close()
        return [self._mapear(r) for r in rows]


class TareaRepositorySQLite(ITareaRepository):
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path

    def guardar(self, tarea: Tarea) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO Tareas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(tarea.id),
                str(tarea.creador_id),
                tarea.titulo,
                tarea.descripcion,
                tarea.requisitos,
                tarea.fecha_limite.isoformat(),
                tarea.categoria,
                tarea.estado,
                tarea.fecha_publicacion.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def actualizar_estado(self, tarea_id: uuid.UUID, nuevo_estado: str) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "UPDATE Tareas SET Estado=? WHERE Id=?",
            (nuevo_estado, str(tarea_id)),
        )
        conn.commit()
        conn.close()

    def obtener_por_id(self, id: uuid.UUID) -> Optional[Tarea]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, CreadorId, Titulo, Descripcion, Requisitos, FechaLimite, Categoria, Estado, FechaPublicacion FROM Tareas WHERE Id=?",
            (str(id),),
        )
        row = c.fetchone()
        conn.close()
        if row:
            return Tarea(
                id=uuid.UUID(row[0]),
                creador_id=uuid.UUID(row[1]),
                titulo=row[2],
                descripcion=row[3],
                requisitos=row[4],
                fecha_limite=datetime.fromisoformat(row[5]),
                categoria=row[6],
                estado=row[7],
                fecha_publicacion=datetime.fromisoformat(row[8]),
                validar_fecha_futura=False,
            )
        return None

    def listar_todas(self) -> List[Tarea]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, CreadorId, Titulo, Descripcion, Requisitos, FechaLimite, Categoria, Estado, FechaPublicacion FROM Tareas ORDER BY FechaPublicacion DESC"
        )
        rows = c.fetchall()
        conn.close()
        return [
            Tarea(
                id=uuid.UUID(r[0]),
                creador_id=uuid.UUID(r[1]),
                titulo=r[2],
                descripcion=r[3],
                requisitos=r[4],
                fecha_limite=datetime.fromisoformat(r[5]),
                categoria=r[6],
                estado=r[7],
                fecha_publicacion=datetime.fromisoformat(r[8]),
                validar_fecha_futura=False,
            )
            for r in rows
        ]


class PostulacionRepositorySQLite(IPostulacionRepository):
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path

    def guardar(self, postulacion: Postulacion) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO Participaciones VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(postulacion.id),
                str(postulacion.usuario_id),
                str(postulacion.tarea_id),
                postulacion.rol.value,
                postulacion.estado,
                postulacion.mensaje_propuesta,
            ),
        )
        conn.commit()
        conn.close()

    def actualizar_estado(self, postulacion_id: uuid.UUID, nuevo_estado: str) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "UPDATE Participaciones SET Estado=? WHERE Id=?",
            (nuevo_estado, str(postulacion_id)),
        )
        conn.commit()
        conn.close()

    def obtener_por_id(self, postulacion_id: uuid.UUID) -> Optional[Postulacion]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, UsuarioId, TareaId, Rol, Estado, MensajePropuesta FROM Participaciones WHERE Id=?",
            (str(postulacion_id),),
        )
        row = c.fetchone()
        conn.close()
        if row:
            return Postulacion(
                id=uuid.UUID(row[0]),
                usuario_id=uuid.UUID(row[1]),
                tarea_id=uuid.UUID(row[2]),
                rol=RolParticipacion(row[3]),
                estado=row[4],
                mensaje_propuesta=row[5],
            )
        return None

    def obtener_por_tarea(self, tarea_id: uuid.UUID) -> List[Postulacion]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, UsuarioId, TareaId, Rol, Estado, MensajePropuesta FROM Participaciones WHERE TareaId=?",
            (str(tarea_id),),
        )
        rows = c.fetchall()
        conn.close()
        return [
            Postulacion(
                id=uuid.UUID(r[0]),
                usuario_id=uuid.UUID(r[1]),
                tarea_id=uuid.UUID(r[2]),
                rol=RolParticipacion(r[3]),
                estado=r[4],
                mensaje_propuesta=r[5],
            )
            for r in rows
        ]

    def obtener_por_usuario_y_tarea(
        self, usuario_id: uuid.UUID, tarea_id: uuid.UUID
    ) -> Optional[Postulacion]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, UsuarioId, TareaId, Rol, Estado, MensajePropuesta FROM Participaciones WHERE UsuarioId=? AND TareaId=?",
            (str(usuario_id), str(tarea_id)),
        )
        row = c.fetchone()
        conn.close()
        if row:
            return Postulacion(
                id=uuid.UUID(row[0]),
                usuario_id=uuid.UUID(row[1]),
                tarea_id=uuid.UUID(row[2]),
                rol=RolParticipacion(row[3]),
                estado=row[4],
                mensaje_propuesta=row[5],
            )
        return None


class MensajeRepositorySQLite(IMensajeRepository):
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path

    def guardar(self, mensaje: Mensaje) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO Mensajes VALUES (?, ?, ?, ?, ?)",
            (
                str(mensaje.id),
                str(mensaje.tarea_id),
                str(mensaje.emisor_id),
                mensaje.contenido,
                mensaje.fecha_envio.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def obtener_por_id(self, mensaje_id: uuid.UUID) -> Optional[Mensaje]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, TareaId, EmisorId, Contenido, FechaEnvio FROM Mensajes WHERE Id=?",
            (str(mensaje_id),),
        )
        row = c.fetchone()
        conn.close()
        if row:
            return Mensaje(
                id=uuid.UUID(row[0]),
                tarea_id=uuid.UUID(row[1]),
                emisor_id=uuid.UUID(row[2]),
                contenido=row[3],
                fecha_envio=datetime.fromisoformat(row[4]),
            )
        return None

    def eliminar(self, mensaje_id: uuid.UUID) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM Mensajes WHERE Id=?", (str(mensaje_id),))
        conn.commit()
        conn.close()

    def listar_por_tarea(self, tarea_id: uuid.UUID) -> List[Mensaje]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, TareaId, EmisorId, Contenido, FechaEnvio FROM Mensajes WHERE TareaId=? ORDER BY FechaEnvio ASC",
            (str(tarea_id),),
        )
        rows = c.fetchall()
        conn.close()
        return [
            Mensaje(
                id=uuid.UUID(r[0]),
                tarea_id=uuid.UUID(r[1]),
                emisor_id=uuid.UUID(r[2]),
                contenido=r[3],
                fecha_envio=datetime.fromisoformat(r[4]),
            )
            for r in rows
        ]


class NotificacionRepositorySQLite(INotificacionRepository):
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path

    def guardar(self, notificacion: Notificacion) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO Notificaciones VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(notificacion.id),
                str(notificacion.usuario_id),
                str(notificacion.origen_usuario_id) if notificacion.origen_usuario_id else None,
                notificacion.titulo,
                notificacion.mensaje,
                1 if notificacion.leida else 0,
                notificacion.fecha.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def listar_por_usuario(self, usuario_id: uuid.UUID) -> List[Notificacion]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """
            SELECT Id, UsuarioId, OrigenUsuarioId, Titulo, Mensaje, Leida, Fecha
            FROM Notificaciones WHERE UsuarioId=? ORDER BY Fecha DESC LIMIT 30
            """,
            (str(usuario_id),),
        )
        rows = c.fetchall()
        conn.close()
        return [
            Notificacion(
                id=uuid.UUID(r[0]),
                usuario_id=uuid.UUID(r[1]),
                origen_usuario_id=uuid.UUID(r[2]) if r[2] else None,
                titulo=r[3],
                mensaje=r[4],
                leida=bool(r[5]),
                fecha=datetime.fromisoformat(r[6]),
            )
            for r in rows
        ]

    def marcar_todas_leidas(self, usuario_id: uuid.UUID) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "UPDATE Notificaciones SET Leida=1 WHERE UsuarioId=?",
            (str(usuario_id),),
        )
        conn.commit()
        conn.close()

    def eliminar(self, notificacion_id: uuid.UUID, usuario_id: uuid.UUID) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "DELETE FROM Notificaciones WHERE Id=? AND UsuarioId=?",
            (str(notificacion_id), str(usuario_id)),
        )
        conn.commit()
        conn.close()

    def vaciar_por_usuario(self, usuario_id: uuid.UUID) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM Notificaciones WHERE UsuarioId=?", (str(usuario_id),))
        conn.commit()
        conn.close()


class ResenaRepositorySQLite(IResenaRepository):
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path

    def guardar(self, resena: Resena) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO Resenas VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(resena.id),
                str(resena.tarea_id),
                str(resena.autor_id),
                str(resena.receptor_id),
                resena.calificacion,
                resena.comentario,
                resena.fecha.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def obtener_por_tarea_y_autor(
        self, tarea_id: uuid.UUID, autor_id: uuid.UUID
    ) -> Optional[Resena]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, TareaId, AutorId, ReceptorId, Calificacion, Comentario, Fecha FROM Resenas WHERE TareaId=? AND AutorId=?",
            (str(tarea_id), str(autor_id)),
        )
        row = c.fetchone()
        conn.close()
        if row:
            return Resena(
                id=uuid.UUID(row[0]),
                tarea_id=uuid.UUID(row[1]),
                autor_id=uuid.UUID(row[2]),
                receptor_id=uuid.UUID(row[3]),
                calificacion=row[4],
                comentario=row[5],
                fecha=datetime.fromisoformat(row[6]),
            )
        return None

    def listar_por_receptor(self, receptor_id: uuid.UUID) -> List[Resena]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, TareaId, AutorId, ReceptorId, Calificacion, Comentario, Fecha FROM Resenas WHERE ReceptorId=? ORDER BY Fecha DESC",
            (str(receptor_id),),
        )
        rows = c.fetchall()
        conn.close()
        return [
            Resena(
                id=uuid.UUID(r[0]),
                tarea_id=uuid.UUID(r[1]),
                autor_id=uuid.UUID(r[2]),
                receptor_id=uuid.UUID(r[3]),
                calificacion=r[4],
                comentario=r[5],
                fecha=datetime.fromisoformat(r[6]),
            )
            for r in rows
        ]

    def listar_por_tarea(self, tarea_id: uuid.UUID) -> List[Resena]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT Id, TareaId, AutorId, ReceptorId, Calificacion, Comentario, Fecha FROM Resenas WHERE TareaId=? ORDER BY Fecha ASC",
            (str(tarea_id),),
        )
        rows = c.fetchall()
        conn.close()
        return [
            Resena(
                id=uuid.UUID(r[0]),
                tarea_id=uuid.UUID(r[1]),
                autor_id=uuid.UUID(r[2]),
                receptor_id=uuid.UUID(r[3]),
                calificacion=r[4],
                comentario=r[5],
                fecha=datetime.fromisoformat(r[6]),
            )
            for r in rows
        ]


class SilencioRepositorySQLite(ISilencioRepository):
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path

    def silenciar(self, usuario_id: uuid.UUID, silenciado_id: uuid.UUID) -> None:
        if usuario_id == silenciado_id:
            raise ValueError("No puedes silenciarte a ti mismo.")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        ahora = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        c.execute(
            "INSERT OR IGNORE INTO UsuariosSilenciados VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), str(usuario_id), str(silenciado_id), ahora),
        )
        conn.commit()
        conn.close()

    def quitar_silencio(self, usuario_id: uuid.UUID, silenciado_id: uuid.UUID) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "DELETE FROM UsuariosSilenciados WHERE UsuarioId=? AND SilenciadoId=?",
            (str(usuario_id), str(silenciado_id)),
        )
        conn.commit()
        conn.close()

    def esta_silenciado(self, usuario_id: uuid.UUID, origen_id: uuid.UUID) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT 1 FROM UsuariosSilenciados WHERE UsuarioId=? AND SilenciadoId=?",
            (str(usuario_id), str(origen_id)),
        )
        existe = c.fetchone() is not None
        conn.close()
        return existe

    def listar_silenciados_ids(self, usuario_id: uuid.UUID) -> List[uuid.UUID]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT SilenciadoId FROM UsuariosSilenciados WHERE UsuarioId=?",
            (str(usuario_id),),
        )
        rows = c.fetchall()
        conn.close()
        return [uuid.UUID(r[0]) for r in rows]
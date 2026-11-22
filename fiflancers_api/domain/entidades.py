import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RolParticipacion(Enum):
    CREADOR = "Creador"
    PRESTADOR = "Prestador"


class Usuario:
    """Protege BR-01 / RN-01: Identidad, credenciales, contacto y estado activo."""

    def __init__(
        self,
        id: uuid.UUID,
        nombre: str,
        correo: str,
        password_hash: str,
        carrera: str = "Estudiante FIF - UAQ",
        contacto: str = "",
        habilidades: str = "Python, HTML/CSS, SQL",
        bio: str = "Disponible para colaborar en proyectos académicos y desarrollo.",
        activo: bool = False,
        codigo_verificacion: Optional[str] = None,
    ):
        if not id:
            raise ValueError("El ID del usuario es obligatorio.")
        if not nombre or not nombre.strip():
            raise ValueError("El nombre de usuario es obligatorio.")
        if not correo or "@" not in correo or "." not in correo:
            raise ValueError("El correo electrónico no tiene un formato válido.")
        if not password_hash:
            raise ValueError("La contraseña cifrada es obligatoria.")

        self.id = id
        self.nombre = nombre.strip()
        self.correo = correo.strip().lower()
        self.password_hash = password_hash
        self.carrera = carrera.strip() if carrera else "Estudiante FIF - UAQ"
        self.contacto = contacto.strip() if contacto and contacto.strip() else self.correo
        self.habilidades = habilidades.strip() if habilidades else ""
        self.bio = bio.strip() if bio else ""
        self.activo = activo
        self.codigo_verificacion = codigo_verificacion


class Tarea:
    """Protege BR-02 / UC-04 / UC-14: Título, descripción, requisitos, fecha límite y ciclo de estados."""

    ESTADOS_VALIDOS = ("Abierta", "Asignada", "Finalizada")

    def __init__(
        self,
        creador_id: uuid.UUID,
        titulo: str,
        descripcion: str,
        requisitos: str,
        fecha_limite: datetime,
        categoria: str = "Desarrollo Web",
        id: Optional[uuid.UUID] = None,
        estado: str = "Abierta",
        fecha_publicacion: Optional[datetime] = None,
        validar_fecha_futura: bool = True,
    ):
        if not creador_id:
            raise ValueError("El creador de la tarea es obligatorio.")
        if not titulo or not titulo.strip():
            raise ValueError("BR-02: El título de la tarea es obligatorio.")
        if not descripcion or not descripcion.strip():
            raise ValueError("BR-02: La descripción de la tarea es obligatoria.")
        if not requisitos or not requisitos.strip():
            raise ValueError("BR-02: Los requisitos de la tarea son obligatorios.")
        if not fecha_limite:
            raise ValueError("BR-02: La fecha límite es obligatoria.")

        fl_naive = (
            fecha_limite.replace(tzinfo=None)
            if fecha_limite.tzinfo
            else fecha_limite
        )
        ahora_naive = datetime.now(timezone.utc).replace(tzinfo=None)

        if validar_fecha_futura and fl_naive <= ahora_naive:
            raise ValueError(
                "UC-04: La fecha límite ingresada debe ser mayor a la fecha y hora actual."
            )

        if estado not in self.ESTADOS_VALIDOS:
            raise ValueError(f"Estado de tarea inválido: {estado}")

        self.id = id or uuid.uuid4()
        self.creador_id = creador_id
        self.titulo = titulo.strip()
        self.descripcion = descripcion.strip()
        self.requisitos = requisitos.strip()
        self.fecha_limite = fl_naive
        self.categoria = categoria.strip() if categoria else "General"
        self.estado = estado
        self.fecha_publicacion = fecha_publicacion or ahora_naive


class Postulacion:
    """Protege BR-03 / BR-04: Solicitud de un prestador para realizar una tarea."""

    def __init__(
        self,
        usuario_id: uuid.UUID,
        tarea_id: uuid.UUID,
        rol: RolParticipacion,
        estado: str = "Pendiente",
        mensaje_propuesta: str = "",
        id: Optional[uuid.UUID] = None,
    ):
        if not usuario_id or not tarea_id:
            raise ValueError("El usuario y la tarea son obligatorios.")
        if rol not in (RolParticipacion.CREADOR, RolParticipacion.PRESTADOR):
            raise ValueError("Rol inválido en la postulación.")

        self.id = id or uuid.uuid4()
        self.usuario_id = usuario_id
        self.tarea_id = tarea_id
        self.rol = rol
        self.estado = estado
        self.mensaje_propuesta = mensaje_propuesta.strip()


class Mensaje:
    """Chat privado habilitado entre Creador y Prestador asignado."""

    def __init__(
        self,
        tarea_id: uuid.UUID,
        emisor_id: uuid.UUID,
        contenido: str,
        id: Optional[uuid.UUID] = None,
        fecha_envio: Optional[datetime] = None,
    ):
        if not tarea_id or not emisor_id:
            raise ValueError("La tarea y el emisor son obligatorios.")
        if not contenido or not contenido.strip():
            raise ValueError("El mensaje no puede estar vacío.")

        self.id = id or uuid.uuid4()
        self.tarea_id = tarea_id
        self.emisor_id = emisor_id
        self.contenido = contenido.strip()
        self.fecha_envio = fecha_envio or datetime.now(timezone.utc).replace(tzinfo=None)


class Notificacion:
    """Entidad de dominio para eventos del ciclo de vida."""

    def __init__(
        self,
        usuario_id: uuid.UUID,
        titulo: str,
        mensaje: str,
        leida: bool = False,
        id: Optional[uuid.UUID] = None,
        fecha: Optional[datetime] = None,
        origen_usuario_id: Optional[uuid.UUID] = None,
    ):
        if not usuario_id or not mensaje.strip():
            raise ValueError("Usuario y mensaje de notificación obligatorios.")
        self.id = id or uuid.uuid4()
        self.usuario_id = usuario_id
        self.origen_usuario_id = origen_usuario_id
        self.titulo = titulo.strip()
        self.mensaje = mensaje.strip()
        self.leida = leida
        self.fecha = fecha or datetime.now(timezone.utc).replace(tzinfo=None)


class Resena:
    """Protege BR-05 / RN-05 / UC-15: Calificación y retroalimentación tras finalizar una tarea."""

    def __init__(
        self,
        tarea_id: uuid.UUID,
        autor_id: uuid.UUID,
        receptor_id: uuid.UUID,
        calificacion: int,
        comentario: str,
        id: Optional[uuid.UUID] = None,
        fecha: Optional[datetime] = None,
    ):
        if not tarea_id or not autor_id or not receptor_id:
            raise ValueError("La tarea, el autor y el receptor son obligatorios.")
        if autor_id == receptor_id:
            raise ValueError("No puedes calificarte a ti mismo.")
        if not isinstance(calificacion, int) or calificacion < 1 or calificacion > 5:
            raise ValueError("La calificación debe ser un número entero entre 1 y 5.")
        if not comentario or not comentario.strip():
            raise ValueError("El comentario de la reseña no puede estar vacío.")

        self.id = id or uuid.uuid4()
        self.tarea_id = tarea_id
        self.autor_id = autor_id
        self.receptor_id = receptor_id
        self.calificacion = calificacion
        self.comentario = comentario.strip()
        self.fecha = fecha or datetime.now(timezone.utc).replace(tzinfo=None)
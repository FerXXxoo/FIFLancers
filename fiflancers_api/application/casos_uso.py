import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
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
    IUsuarioRepository,
    ITareaRepository,
    IPostulacionRepository,
    IMensajeRepository,
    INotificacionRepository,
    IResenaRepository,
    IValidadorCredenciales,
)


class RegistrarUsuario:
    """UC-01 / BR-01: Registro de usuario con contraseña cifrada y verificación."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        validador: IValidadorCredenciales,
    ):
        self.usuarios = usuarios_repo
        self.validador = validador

    def ejecutar(
        self,
        nombre: str,
        correo: str,
        password: str,
        carrera: str,
        habilidades: str,
        bio: str,
    ) -> Usuario:
        if not nombre or not nombre.strip() or not correo or not correo.strip():
            raise ValueError("Todos los campos del registro son obligatorios.")
        if len(password.strip()) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")
        if not carrera.strip() or not habilidades.strip() or not bio.strip():
            raise ValueError("Debes completar tu carrera, habilidades y descripción.")

        existente = self.usuarios.obtener_por_correo(correo)
        if existente:
            raise ValueError("Ya existe una cuenta registrada con ese correo.")

        codigo = str(random.randint(100000, 999999))
        usuario = Usuario(
            id=uuid.uuid4(),
            nombre=nombre,
            correo=correo,
            password_hash=self.validador.hashear(password),
            carrera=carrera,
            habilidades=habilidades,
            bio=bio,
            activo=False,
            codigo_verificacion=codigo,
        )
        self.usuarios.guardar(usuario)
        return usuario


class VerificarCorreo:
    """Activa la cuenta del usuario (BR-01)."""

    def __init__(self, usuarios_repo: IUsuarioRepository):
        self.usuarios = usuarios_repo

    def ejecutar(self, correo: str, codigo: str) -> Usuario:
        if not correo.strip() or not codigo.strip():
            raise ValueError("Debes ingresar el correo y el código de verificación.")

        usuario = self.usuarios.obtener_por_correo(correo)
        if not usuario:
            raise ValueError("No se encontró ninguna cuenta con ese correo.")
        if usuario.activo:
            return usuario
        if usuario.codigo_verificacion != codigo.strip():
            raise ValueError("El código de verificación es incorrecto.")

        usuario.activo = True
        usuario.codigo_verificacion = None
        self.usuarios.actualizar(usuario)
        return usuario


class IniciarSesion:
    """AutenticarUsuario / RN-01."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        validador: IValidadorCredenciales,
    ):
        self.usuarios = usuarios_repo
        self.validador = validador

    def ejecutar(self, correo: str, password: str) -> Usuario:
        if not correo.strip() or not password.strip():
            raise ValueError("Ingresa tu correo y contraseña.")

        usuario = self.usuarios.obtener_por_correo(correo)
        if not usuario or not self.validador.verificar(password, usuario.password_hash):
            raise ValueError("Correo o contraseña incorrectos.")

        if not usuario.activo:
            raise ValueError(
                "BR-01: Tu correo aún no está verificado. Activa tu cuenta primero."
            )

        return usuario


class CrearTarea:
    """UC-04 / BR-01 / BR-02: Publicar tarea con requisitos y fecha límite futura en estado Abierta."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        tareas_repo: ITareaRepository,
        postulaciones_repo: IPostulacionRepository,
    ):
        self.usuarios = usuarios_repo
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo

    def ejecutar(
        self,
        creador_id: uuid.UUID,
        titulo: str,
        descripcion: str,
        requisitos: str,
        fecha_limite_str: str,
        categoria: str,
    ) -> Tarea:
        usuario = self.usuarios.obtener_por_id(creador_id)
        if not usuario or not usuario.activo:
            raise ValueError("BR-01: Solo usuarios registrados y activos pueden publicar tareas.")

        if not fecha_limite_str or not fecha_limite_str.strip():
            raise ValueError("BR-02: La fecha límite es obligatoria.")

        try:
            fecha_limite = datetime.fromisoformat(fecha_limite_str)
        except ValueError:
            raise ValueError("El formato de la fecha límite no es válido.")

        tarea = Tarea(
            creador_id=creador_id,
            titulo=titulo,
            descripcion=descripcion,
            requisitos=requisitos,
            fecha_limite=fecha_limite,
            categoria=categoria,
            estado="Abierta",
            validar_fecha_futura=True,
        )
        self.tareas.guardar(tarea)

        participacion_creador = Postulacion(
            usuario_id=creador_id,
            tarea_id=tarea.id,
            rol=RolParticipacion.CREADOR,
            estado="Aceptada",
            mensaje_propuesta="Creador de la tarea",
        )
        self.postulaciones.guardar(participacion_creador)
        return tarea


class PostularseATarea:
    """BR-01 / BR-03 / RN-02 / RN-04: Evita duplicados, tareas cerradas o fechas vencidas."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        tareas_repo: ITareaRepository,
        postulaciones_repo: IPostulacionRepository,
        notificaciones_repo: INotificacionRepository,
    ):
        self.usuarios = usuarios_repo
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.notificaciones = notificaciones_repo

    def ejecutar(
        self, usuario_id: uuid.UUID, tarea_id: uuid.UUID, mensaje_propuesta: str
    ) -> Postulacion:
        if not mensaje_propuesta or not mensaje_propuesta.strip():
            raise ValueError("Debes escribir un mensaje de propuesta para postularte.")

        usuario = self.usuarios.obtener_por_id(usuario_id)
        if not usuario or not usuario.activo:
            raise ValueError("BR-01: Usuario inválido o cuenta no verificada.")

        tarea = self.tareas.obtener_por_id(tarea_id)
        if not tarea:
            raise ValueError("La tarea no existe.")

        if tarea.creador_id == usuario_id:
            raise ValueError("No puedes postularte a tu propia tarea.")

        # RN-04: Una vez asignada o finalizada, deja de aceptar postulaciones
        if tarea.estado != "Abierta":
            raise ValueError(
                f"RN-04: Esta tarea está '{tarea.estado}' y ya no acepta nuevas postulaciones."
            )

        # Regla de dominio: no aceptar postulaciones después de la fecha límite
        ahora_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        if tarea.fecha_limite <= ahora_naive:
            raise ValueError("La fecha límite de esta tarea ya venció.")

        # BR-03 / RN-02: Un prestador no puede postularse más de una vez a la misma tarea
        previa = self.postulaciones.obtener_por_usuario_y_tarea(usuario_id, tarea_id)
        if previa:
            raise ValueError("BR-03: Ya te has postulado anteriormente a esta tarea.")

        postulacion = Postulacion(
            usuario_id=usuario_id,
            tarea_id=tarea_id,
            rol=RolParticipacion.PRESTADOR,
            estado="Pendiente",
            mensaje_propuesta=mensaje_propuesta,
        )
        self.postulaciones.guardar(postulacion)

        self.notificaciones.guardar(
            Notificacion(
                usuario_id=tarea.creador_id,
                titulo="Nueva postulación recibida",
                mensaje=f"{usuario.nombre} se ha postulado a tu tarea '{tarea.titulo}'.",
            )
        )
        return postulacion


class ObtenerPostulacionesTarea:
    """Privacidad: Solo el creador de la tarea puede consultar los perfiles de los postulantes."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        tareas_repo: ITareaRepository,
        postulaciones_repo: IPostulacionRepository,
        resenas_repo: IResenaRepository,
    ):
        self.usuarios = usuarios_repo
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.resenas = resenas_repo

    def ejecutar(
        self, solicitante_id: uuid.UUID, tarea_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        tarea = self.tareas.obtener_por_id(tarea_id)
        if not tarea:
            raise ValueError("La tarea no existe.")

        if tarea.creador_id != solicitante_id:
            raise ValueError(
                "Acceso denegado: solo el creador de la tarea puede ver los postulantes."
            )

        postulaciones = self.postulaciones.obtener_por_tarea(tarea_id)
        resultado = []
        for p in postulaciones:
            if p.rol == RolParticipacion.PRESTADOR:
                postulante = self.usuarios.obtener_por_id(p.usuario_id)
                if postulante:
                    resenas_recibidas = self.resenas.listar_por_receptor(postulante.id)
                    promedio = (
                        round(
                            sum(r.calificacion for r in resenas_recibidas)
                            / len(resenas_recibidas),
                            1,
                        )
                        if resenas_recibidas
                        else None
                    )
                    resultado.append(
                        {
                            "participacion_id": str(p.id),
                            "estado": p.estado,
                            "mensaje_propuesta": p.mensaje_propuesta,
                            "postulante": {
                                "id": str(postulante.id),
                                "nombre": postulante.nombre,
                                "correo": postulante.correo,
                                "carrera": postulante.carrera,
                                "habilidades": postulante.habilidades,
                                "bio": postulante.bio,
                                "promedio_calificacion": promedio,
                                "total_resenas": len(resenas_recibidas),
                            },
                        }
                    )
        return resultado


class SeleccionarPrestador:
    """BR-04 / RN-03 / RN-04 / AsignarTarea: Solo el creador asigna 1 prestador y cierra postulaciones."""

    def __init__(
        self,
        tareas_repo: ITareaRepository,
        postulaciones_repo: IPostulacionRepository,
        notificaciones_repo: INotificacionRepository,
    ):
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.notificaciones = notificaciones_repo

    def ejecutar(
        self, creador_id: uuid.UUID, postulacion_id: uuid.UUID, accion: str
    ) -> Postulacion:
        postulacion = self.postulaciones.obtener_por_id(postulacion_id)
        if not postulacion:
            raise ValueError("Postulación no encontrada.")

        tarea = self.tareas.obtener_por_id(postulacion.tarea_id)
        if not tarea:
            raise ValueError("Tarea no encontrada.")

        # BR-04: Solamente el creador de una tarea puede seleccionar al prestador
        if tarea.creador_id != creador_id:
            raise ValueError(
                "BR-04: Solamente el creador de la tarea puede seleccionar al prestador."
            )

        if accion not in ("Aceptada", "Rechazada"):
            raise ValueError("Acción inválida. Debe ser 'Aceptada' o 'Rechazada'.")

        if accion == "Aceptada":
            # RN-03: Una tarea solo puede ser asignada a un prestador
            if tarea.estado != "Abierta":
                raise ValueError(
                    "RN-03: Esta tarea ya fue asignada a un prestador o está finalizada."
                )

            todas = self.postulaciones.obtener_por_tarea(tarea.id)
            for p in todas:
                if p.rol == RolParticipacion.PRESTADOR:
                    if p.id == postulacion.id:
                        self.postulaciones.actualizar_estado(p.id, "Aceptada")
                    elif p.estado == "Pendiente":
                        # RN-04: Al asignar la tarea, rechaza automáticamente las demás pendientes
                        self.postulaciones.actualizar_estado(p.id, "Rechazada")

            self.tareas.actualizar_estado(tarea.id, "Asignada")
            postulacion.estado = "Aceptada"

            self.notificaciones.guardar(
                Notificacion(
                    usuario_id=postulacion.usuario_id,
                    titulo="¡Fuiste seleccionado para una tarea!",
                    mensaje=f"Has sido asignado a '{tarea.titulo}'. Ya puedes abrir el chat privado.",
                )
            )
        else:
            self.postulaciones.actualizar_estado(postulacion.id, "Rechazada")
            postulacion.estado = "Rechazada"

        return postulacion


class FinalizarTarea:
    """UC-14: El creador marca una tarea Asignada como Finalizada y notifica al prestador."""

    def __init__(
        self,
        tareas_repo: ITareaRepository,
        postulaciones_repo: IPostulacionRepository,
        notificaciones_repo: INotificacionRepository,
    ):
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.notificaciones = notificaciones_repo

    def ejecutar(self, creador_id: uuid.UUID, tarea_id: uuid.UUID) -> Tarea:
        tarea = self.tareas.obtener_por_id(tarea_id)
        if not tarea:
            raise ValueError("La tarea no existe.")

        if tarea.creador_id != creador_id:
            raise ValueError("UC-14: Solo el creador original puede finalizar esta tarea.")

        if tarea.estado != "Asignada":
            raise ValueError(
                "UC-14: Solo se pueden finalizar tareas que estén en estado 'Asignada'."
            )

        self.tareas.actualizar_estado(tarea.id, "Finalizada")
        tarea.estado = "Finalizada"

        postulaciones = self.postulaciones.obtener_por_tarea(tarea.id)
        aceptado = next(
            (
                p
                for p in postulaciones
                if p.rol == RolParticipacion.PRESTADOR and p.estado == "Aceptada"
            ),
            None,
        )
        if aceptado:
            self.notificaciones.guardar(
                Notificacion(
                    usuario_id=aceptado.usuario_id,
                    titulo="Tarea marcada como Finalizada",
                    mensaje=f"El creador finalizó '{tarea.titulo}'. Ya puedes dejar tu reseña.",
                )
            )

        return tarea


class CrearResena:
    """BR-05 / RN-05 / UC-15: Reseña mutua exclusiva entre participantes de una tarea Finalizada."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        tareas_repo: ITareaRepository,
        postulaciones_repo: IPostulacionRepository,
        resenas_repo: IResenaRepository,
        notificaciones_repo: INotificacionRepository,
    ):
        self.usuarios = usuarios_repo
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.resenas = resenas_repo
        self.notificaciones = notificaciones_repo

    def ejecutar(
        self,
        autor_id: uuid.UUID,
        tarea_id: uuid.UUID,
        calificacion: int,
        comentario: str,
    ) -> Resena:
        autor = self.usuarios.obtener_por_id(autor_id)
        if not autor or not autor.activo:
            raise ValueError("BR-01: Usuario no autenticado o inactivo.")

        tarea = self.tareas.obtener_por_id(tarea_id)
        if not tarea:
            raise ValueError("La tarea no existe.")

        # BR-05: Una tarea debe estar finalizada antes de generar una reseña
        if tarea.estado != "Finalizada":
            raise ValueError(
                "BR-05: La tarea debe estar 'Finalizada' antes de poder publicar una reseña."
            )

        postulaciones = self.postulaciones.obtener_por_tarea(tarea.id)
        prestador_aceptado = next(
            (
                p
                for p in postulaciones
                if p.rol == RolParticipacion.PRESTADOR and p.estado == "Aceptada"
            ),
            None,
        )
        if not prestador_aceptado:
            raise ValueError("No existe un prestador asignado en esta tarea.")

        # RN-05: Solo los usuarios que participaron en la tarea pueden realizar reseña
        if autor_id == tarea.creador_id:
            receptor_id = prestador_aceptado.usuario_id
        elif autor_id == prestador_aceptado.usuario_id:
            receptor_id = tarea.creador_id
        else:
            raise ValueError(
                "RN-05: Solo el creador y el prestador asignado pueden dejar reseña en esta tarea."
            )

        # UC-15 Paso 4: Verificar que no exista reseña previa del autor para esta tarea
        previa = self.resenas.obtener_por_tarea_y_autor(tarea.id, autor_id)
        if previa:
            raise ValueError("UC-15: Ya has registrado una reseña para esta tarea.")

        resena = Resena(
            tarea_id=tarea.id,
            autor_id=autor_id,
            receptor_id=receptor_id,
            calificacion=calificacion,
            comentario=comentario,
        )
        self.resenas.guardar(resena)

        self.notificaciones.guardar(
            Notificacion(
                usuario_id=receptor_id,
                titulo="Nueva reseña recibida",
                mensaje=f"{autor.nombre} te calificó con {calificacion}/5 en '{tarea.titulo}'.",
            )
        )
        return resena


class GestionarChat:
    """Chat privado entre el creador y el prestador seleccionado."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        tareas_repo: ITareaRepository,
        postulaciones_repo: IPostulacionRepository,
        mensajes_repo: IMensajeRepository,
    ):
        self.usuarios = usuarios_repo
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.mensajes = mensajes_repo

    def _validar_acceso_chat(self, usuario_id: uuid.UUID, tarea_id: uuid.UUID) -> None:
        tarea = self.tareas.obtener_por_id(tarea_id)
        if not tarea:
            raise ValueError("La tarea no existe.")

        postulaciones = self.postulaciones.obtener_por_tarea(tarea_id)
        aceptados = [
            p
            for p in postulaciones
            if p.rol == RolParticipacion.PRESTADOR and p.estado == "Aceptada"
        ]

        if not aceptados:
            raise ValueError(
                "El chat se habilitará cuando el creador asigne a un prestador."
            )

        ids_permitidos = {tarea.creador_id} | {p.usuario_id for p in aceptados}
        if usuario_id not in ids_permitidos:
            raise ValueError("No tienes permiso para acceder al chat de esta tarea.")

    def enviar_mensaje(
        self, usuario_id: uuid.UUID, tarea_id: uuid.UUID, contenido: str
    ) -> Dict[str, Any]:
        self._validar_acceso_chat(usuario_id, tarea_id)
        emisor = self.usuarios.obtener_por_id(usuario_id)
        if not emisor:
            raise ValueError("Emisor no encontrado.")

        mensaje = Mensaje(tarea_id=tarea_id, emisor_id=usuario_id, contenido=contenido)
        self.mensajes.guardar(mensaje)
        return {
            "id": str(mensaje.id),
            "emisor_id": str(mensaje.emisor_id),
            "emisor_nombre": emisor.nombre,
            "contenido": mensaje.contenido,
            "fecha_envio": mensaje.fecha_envio.isoformat(),
        }

    def listar_mensajes(
        self, usuario_id: uuid.UUID, tarea_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        self._validar_acceso_chat(usuario_id, tarea_id)
        mensajes = self.mensajes.listar_por_tarea(tarea_id)
        salida = []
        for m in mensajes:
            emisor = self.usuarios.obtener_por_id(m.emisor_id)
            salida.append(
                {
                    "id": str(m.id),
                    "emisor_id": str(m.emisor_id),
                    "emisor_nombre": emisor.nombre if emisor else "Usuario",
                    "contenido": m.contenido,
                    "fecha_envio": m.fecha_envio.isoformat(),
                }
            )
        return salida
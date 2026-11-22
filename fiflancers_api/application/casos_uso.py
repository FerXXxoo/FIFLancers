import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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
    ISilencioRepository,
    IValidadorCredenciales,
)


class RegistrarUsuario:
    """UC-01 / BR-01: Registro directo con cuenta activa, notificación simulada y validación de correo."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        validador: IValidadorCredenciales,
        notificaciones_repo: Optional[INotificacionRepository] = None,
    ):
        self.usuarios = usuarios_repo
        self.validador = validador
        self.notificaciones = notificaciones_repo

    def ejecutar(
        self,
        nombre: str,
        correo: str,
        password: str,
        carrera: str,
        habilidades: str,
        bio: str,
        contacto: str = "",
    ) -> Dict[str, Any]:
        if not nombre or not nombre.strip() or not correo or not correo.strip():
            raise ValueError("Todos los campos del registro son obligatorios.")
        if len(password.strip()) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")
        if not carrera.strip() or not habilidades.strip() or not bio.strip():
            raise ValueError("Debes completar tu carrera, habilidades y descripción.")

        correo_limpio = correo.strip().lower()
        existente = self.usuarios.obtener_por_correo(correo_limpio)
        if existente:
            raise ValueError("Ese correo ya está registrado en la base de datos.")

        codigo_simulado = str(random.randint(100000, 999999))
        usuario = Usuario(
            id=uuid.uuid4(),
            nombre=nombre,
            correo=correo_limpio,
            password_hash=self.validador.hashear(password),
            carrera=carrera,
            contacto=contacto.strip() or correo_limpio,
            habilidades=habilidades,
            bio=bio,
            activo=True,
            codigo_verificacion=None,
        )
        self.usuarios.guardar(usuario)

        if self.notificaciones:
            self.notificaciones.guardar(
                Notificacion(
                    usuario_id=usuario.id,
                    titulo="Código de verificación (simulado)",
                    mensaje=f"Bienvenido a FIFLancers. Tu código de referencia simulado es: {codigo_simulado}",
                )
            )

        return {
            "usuario": usuario,
            "codigo_simulado": codigo_simulado,
        }


class VerificarCorreo:
    """Mantiene compatibilidad si alguna petición invoca verificación, activando la cuenta."""

    def __init__(self, usuarios_repo: IUsuarioRepository):
        self.usuarios = usuarios_repo

    def ejecutar(self, correo: str, codigo: str = "") -> Usuario:
        if not correo or not correo.strip():
            raise ValueError("Debes ingresar el correo.")

        usuario = self.usuarios.obtener_por_correo(correo.strip().lower())
        if not usuario:
            raise ValueError("No se encontró ninguna cuenta con ese correo.")

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
            usuario.activo = True
            self.usuarios.actualizar(usuario)

        return usuario


class ActualizarPerfil:
    """Permite al usuario editar su nombre, carrera, contacto, habilidades y descripción."""

    def __init__(self, usuarios_repo: IUsuarioRepository):
        self.usuarios = usuarios_repo

    def ejecutar(
        self,
        usuario_id: uuid.UUID,
        nombre: str,
        carrera: str,
        contacto: str,
        habilidades: str,
        bio: str,
    ) -> Usuario:
        usuario = self.usuarios.obtener_por_id(usuario_id)
        if not usuario:
            raise ValueError("Usuario no encontrado.")

        if not nombre.strip() or not carrera.strip() or not contacto.strip():
            raise ValueError("Nombre, carrera y medio de contacto son obligatorios.")

        usuario.nombre = nombre.strip()
        usuario.carrera = carrera.strip()
        usuario.contacto = contacto.strip()
        usuario.habilidades = habilidades.strip()
        usuario.bio = bio.strip()
        usuario.activo = True
        self.usuarios.actualizar(usuario)
        return usuario


class ObtenerPerfilesRecomendados:
    """Recomienda perfiles con habilidades o carrera afines, excluyendo silenciados."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        resenas_repo: IResenaRepository,
        silencios_repo: Optional[ISilencioRepository] = None,
    ):
        self.usuarios = usuarios_repo
        self.resenas = resenas_repo
        self.silencios = silencios_repo

    def ejecutar(self, usuario_id: uuid.UUID) -> List[Dict[str, Any]]:
        yo = self.usuarios.obtener_por_id(usuario_id)
        if not yo:
            return []

        silenciados = (
            set(self.silencios.listar_silenciados_ids(usuario_id))
            if self.silencios
            else set()
        )
        mis_tags = {
            t.strip().lower() for t in yo.habilidades.split(",") if t.strip()
        }
        mi_carrera = yo.carrera.strip().lower()

        candidatos = []
        for u in self.usuarios.listar_todos():
            if u.id == usuario_id or u.id in silenciados or u.correo == "admin@fiflancers.mx":
                continue

            sus_tags_raw = [t.strip() for t in u.habilidades.split(",") if t.strip()]
            sus_tags_low = {t.lower(): t for t in sus_tags_raw}
            comunes = [sus_tags_low[k] for k in mis_tags.intersection(sus_tags_low.keys())]
            misma_carrera = u.carrera.strip().lower() == mi_carrera

            puntaje = len(comunes) * 2 + (1 if misma_carrera else 0)
            if comunes:
                motivo = f"Intereses en común: {', '.join(comunes[:3])}"
            elif misma_carrera:
                motivo = f"Misma carrera: {u.carrera}"
            else:
                motivo = f"Activo en {u.carrera}"

            resenas_u = self.resenas.listar_por_receptor(u.id)
            promedio = (
                round(sum(r.calificacion for r in resenas_u) / len(resenas_u), 1)
                if resenas_u
                else 0
            )

            candidatos.append(
                {
                    "id": str(u.id),
                    "nombre": u.nombre,
                    "carrera": u.carrera,
                    "contacto": u.contacto,
                    "habilidades": u.habilidades,
                    "motivo": motivo,
                    "puntaje": puntaje,
                    "promedio_calificacion": promedio,
                }
            )

        candidatos.sort(
            key=lambda x: (x["puntaje"], x["promedio_calificacion"]), reverse=True
        )
        return candidatos[:4]


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
        if not usuario:
            raise ValueError("Solo usuarios registrados pueden publicar tareas.")

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
        silencios_repo: Optional[ISilencioRepository] = None,
    ):
        self.usuarios = usuarios_repo
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.notificaciones = notificaciones_repo
        self.silencios = silencios_repo

    def ejecutar(
        self, usuario_id: uuid.UUID, tarea_id: uuid.UUID, mensaje_propuesta: str
    ) -> Postulacion:
        if not mensaje_propuesta or not mensaje_propuesta.strip():
            raise ValueError("Debes escribir un mensaje de propuesta para postularte.")

        usuario = self.usuarios.obtener_por_id(usuario_id)
        if not usuario:
            raise ValueError("Usuario inválido.")

        tarea = self.tareas.obtener_por_id(tarea_id)
        if not tarea:
            raise ValueError("La tarea no existe.")

        if tarea.creador_id == usuario_id:
            raise ValueError("No puedes postularte a tu propia tarea.")

        if tarea.estado != "Abierta":
            raise ValueError(
                f"RN-04: Esta tarea está '{tarea.estado}' y ya no acepta nuevas postulaciones."
            )

        ahora_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        if tarea.fecha_limite <= ahora_naive:
            raise ValueError("La fecha límite de esta tarea ya venció.")

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

        silenciado = (
            self.silencios.esta_silenciado(tarea.creador_id, usuario_id)
            if self.silencios
            else False
        )
        if not silenciado:
            self.notificaciones.guardar(
                Notificacion(
                    usuario_id=tarea.creador_id,
                    origen_usuario_id=usuario_id,
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
                                "contacto": postulante.contacto,
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
        silencios_repo: Optional[ISilencioRepository] = None,
    ):
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.notificaciones = notificaciones_repo
        self.silencios = silencios_repo

    def ejecutar(
        self, creador_id: uuid.UUID, postulacion_id: uuid.UUID, accion: str
    ) -> Postulacion:
        postulacion = self.postulaciones.obtener_por_id(postulacion_id)
        if not postulacion:
            raise ValueError("Postulación no encontrada.")

        tarea = self.tareas.obtener_por_id(postulacion.tarea_id)
        if not tarea:
            raise ValueError("Tarea no encontrada.")

        if tarea.creador_id != creador_id:
            raise ValueError(
                "BR-04: Solamente el creador de la tarea puede seleccionar al prestador."
            )

        if accion not in ("Aceptada", "Rechazada"):
            raise ValueError("Acción inválida. Debe ser 'Aceptada' o 'Rechazada'.")

        if accion == "Aceptada":
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
                        self.postulaciones.actualizar_estado(p.id, "Rechazada")

            self.tareas.actualizar_estado(tarea.id, "Asignada")
            postulacion.estado = "Aceptada"

            silenciado = (
                self.silencios.esta_silenciado(postulacion.usuario_id, creador_id)
                if self.silencios
                else False
            )
            if not silenciado:
                self.notificaciones.guardar(
                    Notificacion(
                        usuario_id=postulacion.usuario_id,
                        origen_usuario_id=creador_id,
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
        silencios_repo: Optional[ISilencioRepository] = None,
    ):
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.notificaciones = notificaciones_repo
        self.silencios = silencios_repo

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
            silenciado = (
                self.silencios.esta_silenciado(aceptado.usuario_id, creador_id)
                if self.silencios
                else False
            )
            if not silenciado:
                self.notificaciones.guardar(
                    Notificacion(
                        usuario_id=aceptado.usuario_id,
                        origen_usuario_id=creador_id,
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
        silencios_repo: Optional[ISilencioRepository] = None,
    ):
        self.usuarios = usuarios_repo
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.resenas = resenas_repo
        self.notificaciones = notificaciones_repo
        self.silencios = silencios_repo

    def ejecutar(
        self,
        autor_id: uuid.UUID,
        tarea_id: uuid.UUID,
        calificacion: int,
        comentario: str,
    ) -> Resena:
        autor = self.usuarios.obtener_por_id(autor_id)
        if not autor:
            raise ValueError("Usuario no autenticado.")

        tarea = self.tareas.obtener_por_id(tarea_id)
        if not tarea:
            raise ValueError("La tarea no existe.")

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

        if autor_id == tarea.creador_id:
            receptor_id = prestador_aceptado.usuario_id
        elif autor_id == prestador_aceptado.usuario_id:
            receptor_id = tarea.creador_id
        else:
            raise ValueError(
                "RN-05: Solo el creador y el prestador asignado pueden dejar reseña en esta tarea."
            )

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

        silenciado = (
            self.silencios.esta_silenciado(receptor_id, autor_id)
            if self.silencios
            else False
        )
        if not silenciado:
            self.notificaciones.guardar(
                Notificacion(
                    usuario_id=receptor_id,
                    origen_usuario_id=autor_id,
                    titulo="Nueva reseña recibida",
                    mensaje=f"{autor.nombre} te calificó con {calificacion}/5 en '{tarea.titulo}'.",
                )
            )
        return resena


class GestionarChat:
    """Chat privado entre el creador y el prestador seleccionado, con hora y borrado."""

    def __init__(
        self,
        usuarios_repo: IUsuarioRepository,
        tareas_repo: ITareaRepository,
        postulaciones_repo: IPostulacionRepository,
        mensajes_repo: IMensajeRepository,
        notificaciones_repo: Optional[INotificacionRepository] = None,
        silencios_repo: Optional[ISilencioRepository] = None,
    ):
        self.usuarios = usuarios_repo
        self.tareas = tareas_repo
        self.postulaciones = postulaciones_repo
        self.mensajes = mensajes_repo
        self.notificaciones = notificaciones_repo
        self.silencios = silencios_repo

    def _validar_acceso_chat(self, usuario_id: uuid.UUID, tarea_id: uuid.UUID):
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

        return tarea, aceptados[0].usuario_id

    def enviar_mensaje(
        self, usuario_id: uuid.UUID, tarea_id: uuid.UUID, contenido: str
    ) -> Dict[str, Any]:
        tarea, prestador_id = self._validar_acceso_chat(usuario_id, tarea_id)
        emisor = self.usuarios.obtener_por_id(usuario_id)
        if not emisor:
            raise ValueError("Emisor no encontrado.")

        mensaje = Mensaje(tarea_id=tarea_id, emisor_id=usuario_id, contenido=contenido)
        self.mensajes.guardar(mensaje)

        receptor_id = prestador_id if usuario_id == tarea.creador_id else tarea.creador_id
        if self.notificaciones:
            silenciado = (
                self.silencios.esta_silenciado(receptor_id, usuario_id)
                if self.silencios
                else False
            )
            if not silenciado:
                self.notificaciones.guardar(
                    Notificacion(
                        usuario_id=receptor_id,
                        origen_usuario_id=usuario_id,
                        titulo="Nuevo mensaje en chat",
                        mensaje=f"{emisor.nombre} te envió un mensaje en '{tarea.titulo}'.",
                    )
                )

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

    def eliminar_mensaje(
        self, usuario_id: uuid.UUID, tarea_id: uuid.UUID, mensaje_id: uuid.UUID
    ) -> None:
        self._validar_acceso_chat(usuario_id, tarea_id)
        mensaje = self.mensajes.obtener_por_id(mensaje_id)
        if not mensaje or mensaje.tarea_id != tarea_id:
            raise ValueError("El mensaje no existe en este chat.")
        if mensaje.emisor_id != usuario_id:
            raise ValueError("Solo puedes eliminar tus propios mensajes.")
        self.mensajes.eliminar(mensaje_id)


class GestionarNotificaciones:
    """Administra bandeja de notificaciones y silencio de usuarios."""

    def __init__(
        self,
        notificaciones_repo: INotificacionRepository,
        silencios_repo: ISilencioRepository,
        usuarios_repo: IUsuarioRepository,
    ):
        self.notificaciones = notificaciones_repo
        self.silencios = silencios_repo
        self.usuarios = usuarios_repo

    def listar(self, usuario_id: uuid.UUID) -> List[Dict[str, Any]]:
        silenciados = set(self.silencios.listar_silenciados_ids(usuario_id))
        notifs = self.notificaciones.listar_por_usuario(usuario_id)
        salida = []
        for n in notifs:
            if n.origen_usuario_id and n.origen_usuario_id in silenciados:
                continue
            origen = (
                self.usuarios.obtener_por_id(n.origen_usuario_id)
                if n.origen_usuario_id
                else None
            )
            salida.append(
                {
                    "id": str(n.id),
                    "origen_usuario_id": str(n.origen_usuario_id) if n.origen_usuario_id else None,
                    "origen_nombre": origen.nombre if origen else None,
                    "titulo": n.titulo,
                    "mensaje": n.mensaje,
                    "leida": n.leida,
                    "fecha": n.fecha.isoformat(),
                }
            )
        return salida

    def eliminar(self, usuario_id: uuid.UUID, notificacion_id: uuid.UUID) -> None:
        self.notificaciones.eliminar(notificacion_id, usuario_id)

    def vaciar(self, usuario_id: uuid.UUID) -> None:
        self.notificaciones.vaciar_por_usuario(usuario_id)

    def silenciar_usuario(self, usuario_id: uuid.UUID, silenciado_id: uuid.UUID) -> None:
        self.silencios.silenciar(usuario_id, silenciado_id)

    def quitar_silencio(self, usuario_id: uuid.UUID, silenciado_id: uuid.UUID) -> None:
        self.silencios.quitar_silencio(usuario_id, silenciado_id)

    def listar_silenciados(self, usuario_id: uuid.UUID) -> List[Dict[str, Any]]:
        ids = self.silencios.listar_silenciados_ids(usuario_id)
        salida = []
        for sid in ids:
            u = self.usuarios.obtener_por_id(sid)
            if u:
                salida.append(
                    {
                        "id": str(u.id),
                        "nombre": u.nombre,
                        "carrera": u.carrera,
                    }
                )
        return salida
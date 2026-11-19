from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid

from domain.entidades import RolParticipacion
from infrastructure.sqlite_adapters import (
    inicializar_bd,
    sembrar_datos_iniciales,
    ValidadorCredencialesSHA256,
    UsuarioRepositorySQLite,
    TareaRepositorySQLite,
    PostulacionRepositorySQLite,
    MensajeRepositorySQLite,
    NotificacionRepositorySQLite,
    ResenaRepositorySQLite,
)
from application.casos_uso import (
    RegistrarUsuario,
    VerificarCorreo,
    IniciarSesion,
    CrearTarea,
    PostularseATarea,
    ObtenerPostulacionesTarea,
    SeleccionarPrestador,
    FinalizarTarea,
    CrearResena,
    GestionarChat,
)

app = FastAPI(title="FIFLancers API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

inicializar_bd()
sembrar_datos_iniciales()

validador = ValidadorCredencialesSHA256()
usuarios_repo = UsuarioRepositorySQLite()
tareas_repo = TareaRepositorySQLite()
postulaciones_repo = PostulacionRepositorySQLite()
mensajes_repo = MensajeRepositorySQLite()
notificaciones_repo = NotificacionRepositorySQLite()
resenas_repo = ResenaRepositorySQLite()

registrar_usuario_uc = RegistrarUsuario(usuarios_repo, validador)
verificar_correo_uc = VerificarCorreo(usuarios_repo)
iniciar_sesion_uc = IniciarSesion(usuarios_repo, validador)
crear_tarea_uc = CrearTarea(usuarios_repo, tareas_repo, postulaciones_repo)
postularse_tarea_uc = PostularseATarea(
    usuarios_repo, tareas_repo, postulaciones_repo, notificaciones_repo
)
obtener_postulaciones_uc = ObtenerPostulacionesTarea(
    usuarios_repo, tareas_repo, postulaciones_repo, resenas_repo
)
seleccionar_prestador_uc = SeleccionarPrestador(
    tareas_repo, postulaciones_repo, notificaciones_repo
)
finalizar_tarea_uc = FinalizarTarea(
    tareas_repo, postulaciones_repo, notificaciones_repo
)
crear_resena_uc = CrearResena(
    usuarios_repo, tareas_repo, postulaciones_repo, resenas_repo, notificaciones_repo
)
gestionar_chat_uc = GestionarChat(
    usuarios_repo, tareas_repo, postulaciones_repo, mensajes_repo
)


def parsear_uuid(valor: str) -> uuid.UUID:
    try:
        return uuid.UUID(valor)
    except Exception:
        raise ValueError("Identificador con formato inválido.")


class RegistroRequest(BaseModel):
    nombre: str
    correo: str
    password: str
    carrera: str
    habilidades: str
    bio: str


class VerificarCorreoRequest(BaseModel):
    correo: str
    codigo: str


class LoginRequest(BaseModel):
    correo: str
    password: str


class TareaRequest(BaseModel):
    creador_id: str
    titulo: str
    descripcion: str
    requisitos: str
    fecha_limite: str
    categoria: str


class PostularRequest(BaseModel):
    usuario_id: str
    mensaje_propuesta: str


class SeleccionarPrestadorRequest(BaseModel):
    creador_id: str
    accion: str  # "Aceptada" o "Rechazada"


class FinalizarTareaRequest(BaseModel):
    creador_id: str


class ResenaRequest(BaseModel):
    autor_id: str
    calificacion: int
    comentario: str


class MensajeChatRequest(BaseModel):
    usuario_id: str
    contenido: str


@app.post("/api/auth/registro")
def api_registro(req: RegistroRequest):
    try:
        usuario = registrar_usuario_uc.ejecutar(
            nombre=req.nombre,
            correo=req.correo,
            password=req.password,
            carrera=req.carrera,
            habilidades=req.habilidades,
            bio=req.bio,
        )
        print(
            f"[VERIFICACIÓN CORREO] Código para {usuario.correo}: {usuario.codigo_verificacion}"
        )
        return {
            "mensaje": "Registro exitoso. Ingresa el código para verificar tu correo.",
            "correo": usuario.correo,
            "codigo_verificacion_demo": usuario.codigo_verificacion,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/verificar")
def api_verificar_correo(req: VerificarCorreoRequest):
    try:
        usuario = verificar_correo_uc.ejecutar(correo=req.correo, codigo=req.codigo)
        return {
            "mensaje": "Correo verificado correctamente. Ya puedes iniciar sesión.",
            "usuario_id": str(usuario.id),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
def api_login(req: LoginRequest):
    try:
        usuario = iniciar_sesion_uc.ejecutar(correo=req.correo, password=req.password)
        resenas = resenas_repo.listar_por_receptor(usuario.id)
        promedio = (
            round(sum(r.calificacion for r in resenas) / len(resenas), 1)
            if resenas
            else 0
        )
        return {
            "mensaje": "Inicio de sesión exitoso",
            "usuario": {
                "id": str(usuario.id),
                "nombre": usuario.nombre,
                "correo": usuario.correo,
                "carrera": usuario.carrera,
                "habilidades": usuario.habilidades,
                "bio": usuario.bio,
                "promedio_calificacion": promedio,
                "total_resenas": len(resenas),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/tareas")
def api_crear_tarea(req: TareaRequest):
    try:
        tarea = crear_tarea_uc.ejecutar(
            creador_id=parsear_uuid(req.creador_id),
            titulo=req.titulo,
            descripcion=req.descripcion,
            requisitos=req.requisitos,
            fecha_limite_str=req.fecha_limite,
            categoria=req.categoria,
        )
        return {"mensaje": "Tarea publicada en estado Abierta.", "id": str(tarea.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/tareas")
def api_listar_tareas(usuario_id: Optional[str] = Query(default=None)):
    try:
        tareas = tareas_repo.listar_todas()
        uid = parsear_uuid(usuario_id) if usuario_id else None
        resultado = []

        for t in tareas:
            creador = usuarios_repo.obtener_por_id(t.creador_id)
            postulaciones = postulaciones_repo.obtener_por_tarea(t.id)
            prestadores = [
                p for p in postulaciones if p.rol == RolParticipacion.PRESTADOR
            ]
            aceptado = next((p for p in prestadores if p.estado == "Aceptada"), None)

            mi_estado_postulacion = None
            if uid:
                for p in prestadores:
                    if p.usuario_id == uid:
                        mi_estado_postulacion = p.estado
                        break

            es_creador = uid == t.creador_id if uid else False
            es_prestador_asignado = mi_estado_postulacion == "Aceptada"
            puede_chatear = (es_creador and aceptado is not None) or es_prestador_asignado

            ya_deje_resena = False
            if uid and t.estado == "Finalizada" and (es_creador or es_prestador_asignado):
                ya_deje_resena = (
                    resenas_repo.obtener_por_tarea_y_autor(t.id, uid) is not None
                )

            resenas_tarea = resenas_repo.listar_por_tarea(t.id)
            lista_resenas = []
            for r in resenas_tarea:
                autor = usuarios_repo.obtener_por_id(r.autor_id)
                lista_resenas.append(
                    {
                        "autor_nombre": autor.nombre if autor else "Participante",
                        "calificacion": r.calificacion,
                        "comentario": r.comentario,
                    }
                )

            resultado.append(
                {
                    "id": str(t.id),
                    "creador_id": str(t.creador_id),
                    "creador_nombre": creador.nombre if creador else "Usuario FIF",
                    "creador_carrera": creador.carrera if creador else "",
                    "titulo": t.titulo,
                    "descripcion": t.descripcion,
                    "requisitos": t.requisitos,
                    "fecha_limite": t.fecha_limite.isoformat(),
                    "categoria": t.categoria,
                    "estado": t.estado,
                    "fecha_publicacion": t.fecha_publicacion.isoformat(),
                    "total_postulantes": len(prestadores),
                    "es_creador": es_creador,
                    "mi_postulacion_estado": mi_estado_postulacion,
                    "puede_chatear": puede_chatear,
                    "puede_finalizar": es_creador and t.estado == "Asignada",
                    "puede_resenar": (
                        t.estado == "Finalizada"
                        and (es_creador or es_prestador_asignado)
                        and not ya_deje_resena
                    ),
                    "ya_deje_resena": ya_deje_resena,
                    "resenas": lista_resenas,
                }
            )

        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/tareas/{tarea_id}/postular")
def api_postularse(tarea_id: str, req: PostularRequest):
    try:
        postulacion = postularse_tarea_uc.ejecutar(
            usuario_id=parsear_uuid(req.usuario_id),
            tarea_id=parsear_uuid(tarea_id),
            mensaje_propuesta=req.mensaje_propuesta,
        )
        return {
            "mensaje": "Postulación enviada. Espera a que el creador revise tu perfil.",
            "participacion_id": str(postulacion.id),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/tareas/{tarea_id}/postulaciones")
def api_ver_postulantes(tarea_id: str, solicitante_id: str = Query(...)):
    try:
        return obtener_postulaciones_uc.ejecutar(
            solicitante_id=parsear_uuid(solicitante_id),
            tarea_id=parsear_uuid(tarea_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/api/postulaciones/{participacion_id}/responder")
def api_seleccionar_prestador(
    participacion_id: str, req: SeleccionarPrestadorRequest
):
    try:
        p = seleccionar_prestador_uc.ejecutar(
            creador_id=parsear_uuid(req.creador_id),
            postulacion_id=parsear_uuid(participacion_id),
            accion=req.accion,
        )
        return {
            "mensaje": f"Postulación marcada como {p.estado}.",
            "estado": p.estado,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/tareas/{tarea_id}/finalizar")
def api_finalizar_tarea(tarea_id: str, req: FinalizarTareaRequest):
    try:
        tarea = finalizar_tarea_uc.ejecutar(
            creador_id=parsear_uuid(req.creador_id),
            tarea_id=parsear_uuid(tarea_id),
        )
        return {
            "mensaje": "Tarea marcada como Finalizada. Se notificó al prestador asignado.",
            "estado": tarea.estado,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/tareas/{tarea_id}/resenas")
def api_crear_resena(tarea_id: str, req: ResenaRequest):
    try:
        resena = crear_resena_uc.ejecutar(
            autor_id=parsear_uuid(req.autor_id),
            tarea_id=parsear_uuid(tarea_id),
            calificacion=req.calificacion,
            comentario=req.comentario,
        )
        return {
            "mensaje": "Reseña publicada correctamente.",
            "id": str(resena.id),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/usuarios/{usuario_id}/notificaciones")
def api_notificaciones(usuario_id: str):
    try:
        uid = parsear_uuid(usuario_id)
        notifs = notificaciones_repo.listar_por_usuario(uid)
        return [
            {
                "id": str(n.id),
                "titulo": n.titulo,
                "mensaje": n.mensaje,
                "leida": n.leida,
                "fecha": n.fecha.isoformat(),
            }
            for n in notifs
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/usuarios/{usuario_id}/notificaciones/leer")
def api_leer_notificaciones(usuario_id: str):
    try:
        notificaciones_repo.marcar_todas_leidas(parsear_uuid(usuario_id))
        return {"mensaje": "Notificaciones marcadas como leídas."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/tareas/{tarea_id}/chat")
def api_obtener_chat(tarea_id: str, usuario_id: str = Query(...)):
    try:
        return gestionar_chat_uc.listar_mensajes(
            usuario_id=parsear_uuid(usuario_id),
            tarea_id=parsear_uuid(tarea_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/api/tareas/{tarea_id}/chat")
def api_enviar_mensaje_chat(tarea_id: str, req: MensajeChatRequest):
    try:
        return gestionar_chat_uc.enviar_mensaje(
            usuario_id=parsear_uuid(req.usuario_id),
            tarea_id=parsear_uuid(tarea_id),
            contenido=req.contenido,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
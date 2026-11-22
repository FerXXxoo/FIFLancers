const API_URL = "https://fiflancers.onrender.com/api";

let usuarioActual = null;
let todasLasTareas = [];
let chatTareaActivaId = null;
let intervaloChat = null;

// --- UTILIDADES ---
function escaparHTML(texto) {
    if (texto === null || texto === undefined) return "";
    return String(texto)
        .replace(/&/g, "&" + "amp;")
        .replace(/</g, "&" + "lt;")
        .replace(/>/g, "&" + "gt;")
        .replace(/"/g, "&" + "quot;")
        .replace(/'/g, "&" + "#39;");
}

function formatearFechaCorta(isoStr) {
    if (!isoStr) return "";
    return String(isoStr).replace("T", " ").slice(0, 16);
}

function formatearHora(isoStr) {
    if (!isoStr) return "";
    const partes = String(isoStr).split("T");
    if (partes.length > 1) return partes[1].slice(0, 5);
    return String(isoStr).slice(-5);
}

function vincularValidacionBoton(formId, buttonId) {
    const form = document.getElementById(formId);
    const btn = document.getElementById(buttonId);
    if (!form || !btn) return;

    const verificarCampos = () => {
        const camposRequeridos = Array.from(form.querySelectorAll("[required]"));
        const todosLlenos = camposRequeridos.every((campo) => campo.value.trim() !== "");
        btn.disabled = !todosLlenos;
    };

    form.addEventListener("input", verificarCampos);
    form.addEventListener("change", verificarCampos);
    verificarCampos();
}

function obtenerUsuarioGuardado() {
    const raw =
        localStorage.getItem("fiflancers_usuario") ||
        localStorage.getItem("usuarioActual") ||
        localStorage.getItem("usuario");
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

function guardarUsuarioSesion(usuario) {
    usuarioActual = usuario;
    const json = JSON.stringify(usuario);
    localStorage.setItem("fiflancers_usuario", json);
    localStorage.setItem("usuarioActual", json);
}

function cerrarSesion() {
    localStorage.removeItem("fiflancers_usuario");
    localStorage.removeItem("usuarioActual");
    localStorage.removeItem("usuario");
    window.location.href = "login.html";
}

function cerrarModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add("hidden");
}

// --- INICIALIZACIÓN SEGÚN PÁGINA ---
document.addEventListener("DOMContentLoaded", () => {
    const formLogin = document.getElementById("form-login");
    const formRegistro = document.getElementById("form-registro");

    if (formLogin) {
        inicializarLogin(formLogin);
        return;
    }

    if (formRegistro) {
        inicializarRegistro(formRegistro);
        return;
    }

    usuarioActual = obtenerUsuarioGuardado();
    if (!usuarioActual) {
        window.location.href = "login.html";
        return;
    }

    pintarPerfilLateral();
    actualizarContadorNotificaciones();

    const page = document.body.dataset.page || "inicio";
    if (page === "inicio") {
        inicializarInicio();
    } else if (page === "publicar") {
        inicializarPublicar();
    } else if (page === "mis-tareas") {
        inicializarMisTareas();
    } else if (page === "perfil") {
        inicializarAjustesPerfil();
    }
});

// --- LOGIN Y REGISTRO DIRECTO ---
function inicializarLogin(form) {
    vincularValidacionBoton("form-login", "btn-login");
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const correo = (
            document.getElementById("login-correo") ||
            form.querySelector("input[type='email']")
        ).value.trim();
        const password = (
            document.getElementById("login-password") ||
            form.querySelector("input[type='password']")
        ).value;
        const msg =
            document.getElementById("mensaje-login") ||
            form.querySelector(".status-msg");

        if (msg) {
            msg.style.color = "#0a66c2";
            msg.textContent = "Conectando con el servidor...";
        }

        try {
            const resp = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ correo, password }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || "No se pudo iniciar sesión.");

            guardarUsuarioSesion(data.usuario);
            window.location.href = "index.html";
        } catch (err) {
            if (msg) {
                msg.style.color = "#c92a2a";
                msg.textContent = err.message;
            }
        }
    });
}

function inicializarRegistro(form) {
    vincularValidacionBoton("form-registro", "btn-registro");
    const seccionVerif = document.getElementById("seccion-verificacion");
    const formVerif = document.getElementById("form-verificar");
    if (seccionVerif) seccionVerif.classList.add("hidden");
    if (formVerif) formVerif.classList.add("hidden");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const nombre = document.getElementById("reg-nombre").value.trim();
        const correo = document.getElementById("reg-correo").value.trim();
        const carrera = document.getElementById("reg-carrera").value;
        const habilidades = (document.getElementById("reg-habilidades")?.value || "").trim();
        const bio = (document.getElementById("reg-bio")?.value || "").trim();
        const password = document.getElementById("reg-password").value;
        const msg =
            document.getElementById("mensaje-registro") ||
            form.querySelector(".status-msg");

        if (msg) {
            msg.style.color = "#0a66c2";
            msg.textContent = "Registrando cuenta...";
        }

        try {
            const resp = await fetch(`${API_URL}/auth/registro`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    nombre,
                    correo,
                    password,
                    carrera,
                    contacto: correo,
                    habilidades: habilidades || "Python, HTML/CSS",
                    bio: bio || "Estudiante FIF - UAQ",
                }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || "No se pudo completar el registro.");

            if (data.usuario) {
                guardarUsuarioSesion(data.usuario);
            }
            if (msg) {
                msg.style.color = "#137333";
                msg.textContent = `Registro exitoso. Código simulado enviado a notificaciones: ${data.codigo_simulado}. Entrando...`;
            }
            setTimeout(() => {
                window.location.href = "index.html";
            }, 900);
        } catch (err) {
            if (msg) {
                msg.style.color = "#c92a2a";
                msg.textContent = err.message;
            }
        }
    });
}

// --- PERFIL LATERAL ---
function pintarPerfilLateral() {
    if (!usuarioActual) return;
    const iniciales = usuarioActual.nombre
        .split(" ")
        .slice(0, 2)
        .map((n) => n[0])
        .join("")
        .toUpperCase();

    const elIni = document.getElementById("perfil-iniciales");
    const elNom = document.getElementById("perfil-nombre");
    const elCar = document.getElementById("perfil-carrera");
    const elRep = document.getElementById("perfil-reputacion");
    const elCon = document.getElementById("perfil-contacto");
    const elHab = document.getElementById("perfil-habilidades");
    const elBio = document.getElementById("perfil-bio");

    const prom = usuarioActual.promedio_calificacion || usuarioActual.calificacion_promedio || 0;
    const tot = usuarioActual.total_resenas || 0;

    if (elIni) elIni.textContent = iniciales || "U";
    if (elNom) elNom.textContent = usuarioActual.nombre;
    if (elCar) elCar.textContent = usuarioActual.carrera;
    if (elRep) {
        elRep.textContent =
            tot > 0 ? `★ ${prom} (${tot} reseñas)` : "Sin reseñas aún";
    }
    if (elCon) elCon.textContent = usuarioActual.contacto || usuarioActual.correo || "-";
    if (elHab) elHab.textContent = usuarioActual.habilidades || "Sin habilidades registradas";
    if (elBio) elBio.textContent = usuarioActual.bio || "Sin descripción personal";
}

// --- PÁGINA INICIO Y RECOMENDACIONES ---
async function inicializarInicio() {
    vincularValidacionBoton("form-postular", "btn-enviar-postulacion");
    vincularValidacionBoton("form-resena", "btn-enviar-resena");
    vincularValidacionBoton("form-chat", "btn-enviar-chat");

    document.getElementById("buscador-titulo")?.addEventListener("input", aplicarFiltrosTareas);
    document.getElementById("filtro-categoria")?.addEventListener("change", aplicarFiltrosTareas);
    document.getElementById("filtro-estado")?.addEventListener("change", aplicarFiltrosTareas);

    document.getElementById("form-postular")?.addEventListener("submit", enviarPostulacion);
    document.getElementById("form-resena")?.addEventListener("submit", enviarResena);
    document.getElementById("form-chat")?.addEventListener("submit", enviarMensajeChat);

    await Promise.all([cargarTareas(), cargarRecomendacionesPerfiles()]);
}

async function cargarRecomendacionesPerfiles() {
    const contenedor = document.getElementById("lista-recomendaciones");
    if (!contenedor) return;

    try {
        const resp = await fetch(`${API_URL}/usuarios/${usuarioActual.id}/recomendados`);
        const perfiles = await resp.json();

        if (!perfiles.length) {
            contenedor.innerHTML = `<p class="task-meta">No hay sugerencias disponibles por el momento.</p>`;
            return;
        }

        contenedor.innerHTML = perfiles
            .map((p) => {
                const ini = p.nombre
                    .split(" ")
                    .slice(0, 2)
                    .map((x) => x[0])
                    .join("")
                    .toUpperCase();
                return `
                    <div class="rec-item">
                        <div class="rec-item-top">
                            <div class="rec-avatar">${escaparHTML(ini)}</div>
                            <div>
                                <div class="rec-name">${escaparHTML(p.nombre)}</div>
                                <div class="task-meta">${escaparHTML(p.carrera)}</div>
                            </div>
                        </div>
                        <div class="rec-reason">${escaparHTML(p.motivo)}</div>
                        <div class="rec-contact">Contacto: ${escaparHTML(p.contacto)}</div>
                    </div>
                `;
            })
            .join("");
    } catch {
        contenedor.innerHTML = `<p class="task-meta">No se pudieron cargar las sugerencias.</p>`;
    }
}

async function cargarTareas() {
    const contenedor = document.getElementById("lista-tareas");
    if (contenedor) {
        contenedor.innerHTML = `<div class="card"><p class="task-meta">Cargando tareas disponibles...</p></div>`;
    }
    try {
        const resp = await fetch(`${API_URL}/tareas?usuario_id=${encodeURIComponent(usuarioActual.id)}`);
        todasLasTareas = await resp.json();
        aplicarFiltrosTareas();
    } catch {
        if (contenedor) {
            contenedor.innerHTML = `<div class="card"><p style="color:#c92a2a;">Error al conectar con el servidor.</p></div>`;
        }
    }
}

function aplicarFiltrosTareas() {
    const texto = (document.getElementById("buscador-titulo")?.value || "").toLowerCase().trim();
    const categoria = document.getElementById("filtro-categoria")?.value || "Todas";
    const estado = document.getElementById("filtro-estado")?.value || "Todos";

    const filtradas = todasLasTareas.filter((t) => {
        const coincideTexto =
            t.titulo.toLowerCase().includes(texto) ||
            t.descripcion.toLowerCase().includes(texto);
        const coincideCat = categoria === "Todas" || t.categoria === categoria;
        const coincideEst = estado === "Todos" || t.estado === estado;
        return coincideTexto && coincideCat && coincideEst;
    });

    renderizarListaTareas(filtradas, "lista-tareas");
}

function limpiarFiltros() {
    const b = document.getElementById("buscador-titulo");
    const c = document.getElementById("filtro-categoria");
    const e = document.getElementById("filtro-estado");
    if (b) b.value = "";
    if (c) c.value = "Todas";
    if (e) e.value = "Todos";
    aplicarFiltrosTareas();
}

function renderizarListaTareas(lista, contenedorId) {
    const contenedor = document.getElementById(contenedorId);
    if (!contenedor) return;

    if (!lista.length) {
        contenedor.innerHTML = `<div class="card"><p class="task-meta">No se encontraron tareas con esos criterios.</p></div>`;
        return;
    }

    contenedor.innerHTML = lista
        .map((t) => {
            let badgeEstado = "badge-open";
            if (t.estado === "Asignada") badgeEstado = "badge-assigned";
            if (t.estado === "Finalizada") badgeEstado = "badge-finished";

            let botones = "";
            if (t.es_creador) {
                if (t.estado === "Abierta") {
                    botones += `<button type="button" class="btn-secondary" onclick="verPostulantes('${t.id}', '${escaparHTML(t.titulo)}')">Ver Postulantes (${t.total_postulantes})</button>`;
                }
                if (t.puede_chatear) {
                    botones += `<button type="button" class="btn-chat" onclick="abrirChat('${t.id}', '${escaparHTML(t.titulo)}')">Abrir Chat</button>`;
                }
                if (t.puede_finalizar) {
                    botones += `<button type="button" class="btn-finish" onclick="finalizarTarea('${t.id}')">Marcar Finalizada</button>`;
                }
                if (t.puede_resenar) {
                    botones += `<button type="button" class="btn-review" onclick="abrirModalResena('${t.id}', '${escaparHTML(t.titulo)}')">Calificar Prestador</button>`;
                }
            } else {
                if (t.estado === "Abierta") {
                    if (t.mi_postulacion_estado) {
                        botones += `<span class="badge badge-assigned">Postulación: ${escaparHTML(t.mi_postulacion_estado)}</span>`;
                    } else {
                        botones += `<button type="button" class="btn-primary" onclick="abrirModalPostular('${t.id}', '${escaparHTML(t.titulo)}')">Postularme</button>`;
                    }
                } else if (t.mi_postulacion_estado && t.mi_postulacion_estado !== "Aceptada") {
                    botones += `<span class="badge badge-finished">Postulación: ${escaparHTML(t.mi_postulacion_estado)}</span>`;
                }
                if (t.puede_chatear) {
                    botones += `<button type="button" class="btn-chat" onclick="abrirChat('${t.id}', '${escaparHTML(t.titulo)}')">Abrir Chat</button>`;
                }
                if (t.puede_resenar) {
                    botones += `<button type="button" class="btn-review" onclick="abrirModalResena('${t.id}', '${escaparHTML(t.titulo)}')">Calificar Creador</button>`;
                }
            }

            const bloqueResenas =
                t.resenas && t.resenas.length
                    ? `<div class="task-reviews-box">
                        <strong>Reseñas de la colaboración:</strong>
                        ${t.resenas
                            .map(
                                (r) =>
                                    `<div style="margin-top:4px;">★ ${r.calificacion}/5 — <b>${escaparHTML(r.autor_nombre)}:</b> ${escaparHTML(r.comentario)}</div>`
                            )
                            .join("")}
                       </div>`
                    : "";

            return `
                <article class="task-card">
                    <div class="task-header">
                        <div>
                            <div class="task-author">${escaparHTML(t.creador_nombre)}</div>
                            <div class="task-meta">${escaparHTML(t.creador_carrera)} • Publicada: ${escaparHTML(formatearFechaCorta(t.fecha_publicacion))}</div>
                        </div>
                        <div class="badges">
                            <span class="badge badge-category">${escaparHTML(t.categoria)}</span>
                            <span class="badge ${badgeEstado}">${escaparHTML(t.estado)}</span>
                        </div>
                    </div>
                    <h3 class="task-title">${escaparHTML(t.titulo)}</h3>
                    <p class="task-desc">${escaparHTML(t.descripcion)}</p>
                    <div class="task-specs">
                        <strong>Requisitos:</strong> ${escaparHTML(t.requisitos)}<br>
                        <strong>Entrega límite:</strong> ${escaparHTML(formatearFechaCorta(t.fecha_limite))}
                        ${t.asignado_nombre ? `<br><strong>Prestador asignado:</strong> ${escaparHTML(t.asignado_nombre)}` : ""}
                    </div>
                    ${bloqueResenas}
                    <div class="task-footer">
                        <span class="applicants-count">Postulantes: ${t.total_postulantes}</span>
                        <div class="task-actions-group">${botones}</div>
                    </div>
                </article>
            `;
        })
        .join("");
}

// --- PUBLICAR TAREA ---
function inicializarPublicar() {
    vincularValidacionBoton("form-tarea", "btn-publicar");
    const form = document.getElementById("form-tarea");
    form?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const msg = document.getElementById("mensaje-tarea");
        const payload = {
            creador_id: usuarioActual.id,
            titulo: document.getElementById("titulo").value.trim(),
            categoria: document.getElementById("categoria").value,
            fecha_limite: document.getElementById("fecha-limite").value,
            requisitos: document.getElementById("requisitos").value.trim(),
            descripcion: document.getElementById("descripcion").value.trim(),
        };

        try {
            const resp = await fetch(`${API_URL}/tareas`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || "No se pudo publicar la tarea.");

            msg.style.color = "#137333";
            msg.textContent = "Tarea publicada. Redirigiendo al inicio...";
            setTimeout(() => {
                window.location.href = "index.html";
            }, 900);
        } catch (err) {
            msg.style.color = "#c92a2a";
            msg.textContent = err.message;
        }
    });
}

// --- MIS TAREAS ---
async function inicializarMisTareas() {
    vincularValidacionBoton("form-resena", "btn-enviar-resena");
    vincularValidacionBoton("form-chat", "btn-enviar-chat");
    document.getElementById("form-resena")?.addEventListener("submit", enviarResena);
    document.getElementById("form-chat")?.addEventListener("submit", enviarMensajeChat);

    try {
        const resp = await fetch(`${API_URL}/tareas?usuario_id=${encodeURIComponent(usuarioActual.id)}`);
        todasLasTareas = await resp.json();

        const creadas = todasLasTareas.filter((t) => t.es_creador);
        const postuladas = todasLasTareas.filter(
            (t) => !t.es_creador && t.mi_postulacion_estado !== null
        );

        renderizarListaTareas(creadas, "lista-creadas");
        renderizarListaTareas(postuladas, "lista-postuladas");
    } catch {
        document.getElementById("lista-creadas").innerHTML = `<div class="card"><p style="color:#c92a2a;">Error al cargar tus tareas.</p></div>`;
    }
}

// --- AJUSTES DE PERFIL ---
async function inicializarAjustesPerfil() {
    document.getElementById("edit-nombre").value = usuarioActual.nombre || "";
    const selectCarrera = document.getElementById("edit-carrera");
    if (selectCarrera && usuarioActual.carrera) {
        const existeOpcion = Array.from(selectCarrera.options).some(
            (opt) => opt.value === usuarioActual.carrera
        );
        if (!existeOpcion) {
            const nuevaOpt = document.createElement("option");
            nuevaOpt.value = usuarioActual.carrera;
            nuevaOpt.textContent = usuarioActual.carrera;
            selectCarrera.appendChild(nuevaOpt);
        }
        selectCarrera.value = usuarioActual.carrera;
    }
    document.getElementById("edit-contacto").value =
        usuarioActual.contacto || usuarioActual.correo || "";
    document.getElementById("edit-habilidades").value = usuarioActual.habilidades || "";
    document.getElementById("edit-bio").value = usuarioActual.bio || "";

    document.getElementById("form-perfil")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const msg = document.getElementById("mensaje-perfil");
        const payload = {
            nombre: document.getElementById("edit-nombre").value.trim(),
            carrera: document.getElementById("edit-carrera").value,
            contacto: document.getElementById("edit-contacto").value.trim(),
            habilidades: document.getElementById("edit-habilidades").value.trim(),
            bio: document.getElementById("edit-bio").value.trim(),
        };

        try {
            const resp = await fetch(`${API_URL}/usuarios/${usuarioActual.id}/perfil`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || "No se pudo actualizar el perfil.");

            guardarUsuarioSesion(data.usuario);
            pintarPerfilLateral();
            msg.style.color = "#137333";
            msg.textContent = "Perfil actualizado correctamente.";
        } catch (err) {
            msg.style.color = "#c92a2a";
            msg.textContent = err.message;
        }
    });

    await cargarUsuariosSilenciadosPerfil();
}

async function cargarUsuariosSilenciadosPerfil() {
    const contenedor = document.getElementById("lista-silenciados-perfil");
    if (!contenedor) return;

    try {
        const resp = await fetch(`${API_URL}/usuarios/${usuarioActual.id}/silenciados`);
        const lista = await resp.json();
        if (!lista.length) {
            contenedor.innerHTML = `<p class="task-meta">No tienes usuarios silenciados.</p>`;
            return;
        }
        contenedor.innerHTML = lista
            .map(
                (u) => `
                <div class="applicant-card" style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>${escaparHTML(u.nombre)}</strong>
                        <div class="task-meta">${escaparHTML(u.carrera)}</div>
                    </div>
                    <button type="button" class="btn-secondary" onclick="quitarSilencio('${u.id}')">Reactivar</button>
                </div>
            `
            )
            .join("");
    } catch {
        contenedor.innerHTML = `<p class="task-meta">No se pudo cargar la lista.</p>`;
    }
}

// --- POSTULACIONES, ASIGNACIÓN Y RESEÑAS ---
function abrirModalPostular(tareaId, titulo) {
    document.getElementById("postular-tarea-id").value = tareaId;
    document.getElementById("postular-titulo-tarea").textContent = titulo;
    document.getElementById("postular-mensaje").value = "";
    document.getElementById("error-postular").textContent = "";
    document.getElementById("btn-enviar-postulacion").disabled = true;
    document.getElementById("modal-postular").classList.remove("hidden");
}

async function enviarPostulacion(e) {
    e.preventDefault();
    const tareaId = document.getElementById("postular-tarea-id").value;
    const mensajePropuesta = document.getElementById("postular-mensaje").value.trim();
    const errEl = document.getElementById("error-postular");

    try {
        const resp = await fetch(`${API_URL}/tareas/${tareaId}/postular`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                usuario_id: usuarioActual.id,
                mensaje_propuesta: mensajePropuesta,
            }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || "No se pudo enviar la postulación.");

        cerrarModal("modal-postular");
        await cargarTareas();
    } catch (err) {
        errEl.style.color = "#c92a2a";
        errEl.textContent = err.message;
    }
}

async function verPostulantes(tareaId, titulo) {
    document.getElementById("postulantes-titulo-tarea").textContent = titulo;
    const cont = document.getElementById("contenedor-postulantes");
    cont.innerHTML = `<p class="task-meta">Cargando postulantes...</p>`;
    document.getElementById("modal-postulantes").classList.remove("hidden");

    try {
        const resp = await fetch(
            `${API_URL}/tareas/${tareaId}/postulaciones?solicitante_id=${encodeURIComponent(usuarioActual.id)}`
        );
        const lista = await resp.json();
        if (!lista.length) {
            cont.innerHTML = `<p class="task-meta">Aún no hay postulantes en esta tarea.</p>`;
            return;
        }
        cont.innerHTML = lista
            .map((item) => {
                const p = item.postulante;
                const rep =
                    p.promedio_calificacion !== null
                        ? `★ ${p.promedio_calificacion} (${p.total_resenas})`
                        : "Sin reseñas";
                const acciones =
                    item.estado === "Pendiente"
                        ? `
                            <button type="button" class="btn-primary" onclick="responderPostulacion('${item.participacion_id}', 'Aceptada')">Seleccionar y Asignar</button>
                            <button type="button" class="btn-danger-sm" onclick="responderPostulacion('${item.participacion_id}', 'Rechazada')">Rechazar</button>
                          `
                        : `<span class="badge badge-assigned">${escaparHTML(item.estado)}</span>`;

                return `
                    <div class="applicant-card">
                        <div class="applicant-header">
                            <strong>${escaparHTML(p.nombre)}</strong>
                            <span class="badge badge-category">${rep}</span>
                        </div>
                        <p><b>Carrera:</b> ${escaparHTML(p.carrera)}</p>
                        <p><b>Contacto:</b> ${escaparHTML(p.contacto || p.correo || "-")}</p>
                        <p><b>Habilidades:</b> ${escaparHTML(p.habilidades || "-")}</p>
                        <p><b>Propuesta:</b> "${escaparHTML(item.mensaje_propuesta)}"</p>
                        <div class="applicant-actions">${acciones}</div>
                    </div>
                `;
            })
            .join("");
    } catch {
        cont.innerHTML = `<p style="color:#c92a2a;">Error al obtener postulantes.</p>`;
    }
}

async function responderPostulacion(participacionId, accion) {
    try {
        const resp = await fetch(`${API_URL}/postulaciones/${participacionId}/responder`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ creador_id: usuarioActual.id, accion }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || "No se pudo procesar la postulación.");

        cerrarModal("modal-postulantes");
        location.reload();
    } catch (err) {
        alert(err.message);
    }
}

async function finalizarTarea(tareaId) {
    if (!confirm("¿Confirmas que el trabajo fue entregado y deseas marcar la tarea como Finalizada?")) return;
    try {
        const resp = await fetch(`${API_URL}/tareas/${tareaId}/finalizar`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ creador_id: usuarioActual.id }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || "No se pudo finalizar.");
        location.reload();
    } catch (err) {
        alert(err.message);
    }
}

function abrirModalResena(tareaId, titulo) {
    document.getElementById("resena-tarea-id").value = tareaId;
    document.getElementById("resena-titulo-tarea").textContent = titulo;
    document.getElementById("resena-calificacion").value = "";
    document.getElementById("resena-comentario").value = "";
    document.getElementById("error-resena").textContent = "";
    document.getElementById("btn-enviar-resena").disabled = true;
    document.getElementById("modal-resena").classList.remove("hidden");
}

async function enviarResena(e) {
    e.preventDefault();
    const tareaId = document.getElementById("resena-tarea-id").value;
    const calificacion = parseInt(document.getElementById("resena-calificacion").value, 10);
    const comentario = document.getElementById("resena-comentario").value.trim();
    const errEl = document.getElementById("error-resena");

    try {
        const resp = await fetch(`${API_URL}/tareas/${tareaId}/resenas`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ autor_id: usuarioActual.id, calificacion, comentario }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || "No se pudo guardar la reseña.");

        cerrarModal("modal-resena");
        location.reload();
    } catch (err) {
        errEl.style.color = "#c92a2a";
        errEl.textContent = err.message;
    }
}

// --- CHAT PRIVADO CON HORA Y ELIMINACIÓN DE MENSAJES ---
function abrirChat(tareaId, titulo) {
    chatTareaActivaId = tareaId;
    document.getElementById("chat-titulo-tarea").textContent = `Chat: ${titulo}`;
    document.getElementById("chat-texto").value = "";
    document.getElementById("btn-enviar-chat").disabled = true;
    document.getElementById("modal-chat").classList.remove("hidden");

    cargarMensajesChat();
    if (intervaloChat) clearInterval(intervaloChat);
    intervaloChat = setInterval(cargarMensajesChat, 4000);
}

function cerrarChat() {
    cerrarModal("modal-chat");
    chatTareaActivaId = null;
    if (intervaloChat) {
        clearInterval(intervaloChat);
        intervaloChat = null;
    }
}

async function cargarMensajesChat() {
    if (!chatTareaActivaId) return;
    const box = document.getElementById("chat-mensajes");
    try {
        const resp = await fetch(
            `${API_URL}/tareas/${chatTareaActivaId}/chat?usuario_id=${encodeURIComponent(usuarioActual.id)}`
        );
        const mensajes = await resp.json();
        if (!mensajes.length) {
            box.innerHTML = `<p class="task-meta" style="text-align:center; margin-top:20px;">Aún no hay mensajes. Inicia la conversación.</p>`;
            return;
        }

        box.innerHTML = mensajes
            .map((m) => {
                const esMio = m.emisor_id === usuarioActual.id;
                const btnBorrar = esMio
                    ? `<button type="button" class="btn-del-msg" title="Eliminar mensaje" onclick="eliminarMensajeChat('${m.id}')">Eliminar</button>`
                    : "";
                return `
                    <div class="msg-bubble ${esMio ? "msg-mine" : "msg-other"}">
                        <div class="msg-top-row">
                            <span class="msg-sender">${escaparHTML(m.emisor_nombre)}</span>
                            <span class="msg-meta-right">
                                <span class="msg-time">${escaparHTML(formatearHora(m.fecha_envio))}</span>
                                ${btnBorrar}
                            </span>
                        </div>
                        <div>${escaparHTML(m.contenido)}</div>
                    </div>
                `;
            })
            .join("");
        box.scrollTop = box.scrollHeight;
    } catch {
        box.innerHTML = `<p style="color:#c92a2a;">Error al cargar mensajes.</p>`;
    }
}

async function enviarMensajeChat(e) {
    e.preventDefault();
    if (!chatTareaActivaId) return;
    const input = document.getElementById("chat-texto");
    const contenido = input.value.trim();
    if (!contenido) return;

    input.value = "";
    document.getElementById("btn-enviar-chat").disabled = true;

    try {
        await fetch(`${API_URL}/tareas/${chatTareaActivaId}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario_id: usuarioActual.id, contenido }),
        });
        await cargarMensajesChat();
    } catch {
        alert("No se pudo enviar el mensaje.");
    }
}

async function eliminarMensajeChat(mensajeId) {
    if (!chatTareaActivaId) return;
    if (!confirm("¿Eliminar este mensaje para ambos participantes?")) return;
    try {
        const resp = await fetch(
            `${API_URL}/tareas/${chatTareaActivaId}/chat/${mensajeId}?usuario_id=${encodeURIComponent(usuarioActual.id)}`,
            { method: "DELETE" }
        );
        if (!resp.ok) {
            const data = await resp.json();
            throw new Error(data.detail || "No se pudo eliminar el mensaje.");
        }
        await cargarMensajesChat();
    } catch (err) {
        alert(err.message);
    }
}

// --- NOTIFICACIONES Y SILENCIAR USUARIOS ---
async function actualizarContadorNotificaciones() {
    const badge = document.getElementById("badge-notif");
    if (!badge || !usuarioActual) return;
    try {
        const resp = await fetch(`${API_URL}/usuarios/${usuarioActual.id}/notificaciones`);
        const lista = await resp.json();
        const noLeidas = lista.filter((n) => !n.leida).length;
        if (noLeidas > 0) {
            badge.textContent = noLeidas;
            badge.classList.remove("hidden");
        } else {
            badge.classList.add("hidden");
        }
    } catch {
        badge.classList.add("hidden");
    }
}

async function abrirModalNotificaciones() {
    document.getElementById("modal-notificaciones").classList.remove("hidden");
    await cargarBandejaNotificaciones();
    await fetch(`${API_URL}/usuarios/${usuarioActual.id}/notificaciones/leer`, { method: "POST" });
    actualizarContadorNotificaciones();
}

async function cargarBandejaNotificaciones() {
    const cont = document.getElementById("contenedor-notificaciones");
    const contSil = document.getElementById("contenedor-silenciados-modal");
    cont.innerHTML = `<p class="task-meta">Cargando notificaciones...</p>`;

    try {
        const [respNotif, respSil] = await Promise.all([
            fetch(`${API_URL}/usuarios/${usuarioActual.id}/notificaciones`),
            fetch(`${API_URL}/usuarios/${usuarioActual.id}/silenciados`),
        ]);
        const notifs = await respNotif.json();
        const silenciados = await respSil.json();

        if (!notifs.length) {
            cont.innerHTML = `<p class="task-meta">No tienes notificaciones en tu bandeja.</p>`;
        } else {
            cont.innerHTML = notifs
                .map((n) => {
                    const btnSilenciar =
                        n.origen_usuario_id && n.origen_usuario_id !== usuarioActual.id
                            ? `<button type="button" class="btn-muted-sm" onclick="silenciarUsuario('${n.origen_usuario_id}', '${escaparHTML(n.origen_nombre || "este usuario")}')">Silenciar a ${escaparHTML(n.origen_nombre || "usuario")}</button>`
                            : "";

                    return `
                        <div class="applicant-card">
                            <div class="applicant-header">
                                <strong>${escaparHTML(n.titulo || "Notificación")}</strong>
                                <span class="task-meta">${escaparHTML(formatearFechaCorta(n.fecha))}</span>
                            </div>
                            <p>${escaparHTML(n.mensaje)}</p>
                            <div class="notif-item-actions">
                                ${btnSilenciar}
                                <button type="button" class="btn-danger-sm" onclick="eliminarNotificacion('${n.id}')">Eliminar</button>
                            </div>
                        </div>
                    `;
                })
                .join("");
        }

        if (contSil) {
            if (!silenciados.length) {
                contSil.innerHTML = "";
            } else {
                contSil.innerHTML = `
                    <hr class="divider">
                    <p style="font-size:13px; font-weight:700; margin-bottom:8px;">Usuarios silenciados (${silenciados.length}):</p>
                    ${silenciados
                        .map(
                            (s) => `
                            <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; font-size:13px;">
                                <span>${escaparHTML(s.nombre)}</span>
                                <button type="button" class="btn-secondary" style="padding:4px 10px; font-size:11px;" onclick="quitarSilencio('${s.id}')">Reactivar</button>
                            </div>
                        `
                        )
                        .join("")}
                `;
            }
        }
    } catch {
        cont.innerHTML = `<p style="color:#c92a2a;">Error al cargar notificaciones.</p>`;
    }
}

async function eliminarNotificacion(notifId) {
    try {
        await fetch(`${API_URL}/usuarios/${usuarioActual.id}/notificaciones/${notifId}`, {
            method: "DELETE",
        });
        await cargarBandejaNotificaciones();
        actualizarContadorNotificaciones();
    } catch {
        alert("No se pudo eliminar la notificación.");
    }
}

async function vaciarBandejaNotificaciones() {
    if (!confirm("¿Eliminar todas las notificaciones de tu bandeja?")) return;
    try {
        await fetch(`${API_URL}/usuarios/${usuarioActual.id}/notificaciones`, {
            method: "DELETE",
        });
        await cargarBandejaNotificaciones();
        actualizarContadorNotificaciones();
    } catch {
        alert("No se pudo vaciar la bandeja.");
    }
}

async function silenciarUsuario(silenciadoId, nombre) {
    if (!confirm(`¿Silenciar a ${nombre}? Ya no recibirás notificaciones de su actividad.`)) return;
    try {
        await fetch(`${API_URL}/usuarios/${usuarioActual.id}/silenciar`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ silenciado_id: silenciadoId }),
        });
        await cargarBandejaNotificaciones();
        if (document.body.dataset.page === "inicio") {
            await cargarRecomendacionesPerfiles();
        }
    } catch {
        alert("No se pudo silenciar al usuario.");
    }
}

async function quitarSilencio(silenciadoId) {
    try {
        await fetch(`${API_URL}/usuarios/${usuarioActual.id}/silenciar/${silenciadoId}`, {
            method: "DELETE",
        });
        await cargarBandejaNotificaciones();
        if (document.body.dataset.page === "perfil") {
            await cargarUsuariosSilenciadosPerfil();
        } else if (document.body.dataset.page === "inicio") {
            await cargarRecomendacionesPerfiles();
        }
    } catch {
        alert("No se pudo reactivar al usuario.");
    }
}
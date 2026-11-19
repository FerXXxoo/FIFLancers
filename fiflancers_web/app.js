const API_URL = "https://fiflancers.onrender.com/api";

let usuarioActual = null;
let todasLasTareas = [];
let chatTareaActivaId = null;
let intervaloChat = null;

// --- UTILIDADES DE VALIDACIÓN Y BLOQUEO DE BOTONES ---
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

function validarCamposNoVacios(campos) {
    for (const [nombre, valor] of Object.entries(campos)) {
        if (!valor || String(valor).trim() === "") {
            throw new Error(`El campo "${nombre}" es obligatorio y no puede quedar vacío.`);
        }
    }
}

// --- INICIALIZACIÓN POR VENTANA ---
document.addEventListener("DOMContentLoaded", () => {
    const pagina = document.body.dataset.page;
    const sesionGuardada = localStorage.getItem("fiflancers_usuario");

    if (sesionGuardada) {
        usuarioActual = JSON.parse(sesionGuardada);
    }

    if (pagina === "login" || pagina === "registro") {
        if (usuarioActual) {
            window.location.href = "index.html";
            return;
        }
    } else {
        if (!usuarioActual) {
            window.location.href = "login.html";
            return;
        }
        cargarPerfilLateral();
        cargarContadorNotificaciones();
    }

    if (pagina === "login") iniciarPaginaLogin();
    if (pagina === "registro") iniciarPaginaRegistro();
    if (pagina === "inicio") iniciarPaginaInicio();
    if (pagina === "publicar") iniciarPaginaPublicar();
    if (pagina === "mis-tareas") iniciarPaginaMisTareas();
});

function cargarPerfilLateral() {
    const elNombre = document.getElementById("perfil-nombre");
    if (!elNombre || !usuarioActual) return;

    elNombre.innerText = usuarioActual.nombre;
    document.getElementById("perfil-carrera").innerText = usuarioActual.carrera;
    document.getElementById("perfil-habilidades").innerText = usuarioActual.habilidades;
    document.getElementById("perfil-bio").innerText = usuarioActual.bio;
    document.getElementById("perfil-iniciales").innerText = usuarioActual.nombre.charAt(0).toUpperCase();

    const repEl = document.getElementById("perfil-reputacion");
    if (repEl) {
        repEl.innerText =
            usuarioActual.total_resenas > 0
                ? `★ ${usuarioActual.promedio_calificacion} (${usuarioActual.total_resenas} reseñas)`
                : "Sin reseñas aún";
    }
}

function cerrarSesion() {
    localStorage.removeItem("fiflancers_usuario");
    window.location.href = "login.html";
}

// ==========================================
// 1. VENTANA: LOGIN (login.html)
// ==========================================
function iniciarPaginaLogin() {
    vincularValidacionBoton("form-login", "btn-login");

    document.getElementById("form-login").addEventListener("submit", async (e) => {
        e.preventDefault();
        const msgDiv = document.getElementById("auth-mensaje");
        msgDiv.innerText = "";

        try {
            const correo = document.getElementById("login-correo").value;
            const password = document.getElementById("login-password").value;

            validarCamposNoVacios({
                "Correo electrónico": correo,
                "Contraseña": password,
            });

            const res = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ correo, password }),
            });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "No se pudo iniciar sesión.");
            }

            localStorage.setItem("fiflancers_usuario", JSON.stringify(data.usuario));
            window.location.href = "index.html";
        } catch (error) {
            msgDiv.style.color = "#c92a2a";
            msgDiv.innerText = "❌ " + error.message;
        }
    });
}

// ==========================================
// 2. VENTANA: REGISTRO Y VERIFICACIÓN (registro.html)
// ==========================================
function iniciarPaginaRegistro() {
    vincularValidacionBoton("form-registro", "btn-registro");
    vincularValidacionBoton("form-verificar", "btn-verificar");

    document.getElementById("form-registro").addEventListener("submit", async (e) => {
        e.preventDefault();
        const msgDiv = document.getElementById("auth-mensaje");
        msgDiv.innerText = "";

        try {
            const payload = {
                nombre: document.getElementById("reg-nombre").value,
                correo: document.getElementById("reg-correo").value,
                password: document.getElementById("reg-password").value,
                carrera: document.getElementById("reg-carrera").value,
                habilidades: document.getElementById("reg-habilidades").value,
                bio: document.getElementById("reg-bio").value,
            };

            validarCamposNoVacios({
                "Nombre completo": payload.nombre,
                "Correo electrónico": payload.correo,
                "Contraseña": payload.password,
                "Carrera": payload.carrera,
                "Habilidades": payload.habilidades,
                "Descripción": payload.bio,
            });

            if (payload.password.trim().length < 6) {
                throw new Error("La contraseña debe tener al menos 6 caracteres.");
            }

            const res = await fetch(`${API_URL}/auth/registro`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Error en el registro.");
            }

            document.getElementById("form-registro").classList.add("hidden");
            document.getElementById("form-verificar").classList.remove("hidden");
            document.getElementById("ver-correo").value = data.correo;
            document.getElementById("banner-codigo-demo").innerHTML =
                `Hemos enviado un código de verificación a <strong>${data.correo}</strong>.<br>` +
                `Código generado: <strong>${data.codigo_verificacion_demo}</strong>`;

            msgDiv.style.color = "#137333";
            msgDiv.innerText = "✅ " + data.mensaje;
        } catch (error) {
            msgDiv.style.color = "#c92a2a";
            msgDiv.innerText = "❌ " + error.message;
        }
    });

    document.getElementById("form-verificar").addEventListener("submit", async (e) => {
        e.preventDefault();
        const msgDiv = document.getElementById("auth-mensaje");
        msgDiv.innerText = "";

        try {
            const correo = document.getElementById("ver-correo").value;
            const codigo = document.getElementById("ver-codigo").value;

            validarCamposNoVacios({
                "Correo": correo,
                "Código de verificación": codigo,
            });

            const res = await fetch(`${API_URL}/auth/verificar`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ correo, codigo }),
            });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Código incorrecto.");
            }

            msgDiv.style.color = "#137333";
            msgDiv.innerText = "✅ " + data.mensaje + " Redirigiendo...";
            setTimeout(() => {
                window.location.href = "login.html";
            }, 1400);
        } catch (error) {
            msgDiv.style.color = "#c92a2a";
            msgDiv.innerText = "❌ " + error.message;
        }
    });
}

// ==========================================
// 3. VENTANA: INICIO / FEED DE TAREAS (index.html)
// ==========================================
function iniciarPaginaInicio() {
    vincularValidacionBoton("form-postular", "btn-enviar-postulacion");
    vincularValidacionBoton("form-chat", "btn-enviar-chat");
    vincularValidacionBoton("form-resena", "btn-enviar-resena");

    document.getElementById("buscador-titulo").addEventListener("input", renderizarTareasInicio);
    document.getElementById("filtro-categoria").addEventListener("change", renderizarTareasInicio);
    document.getElementById("filtro-estado").addEventListener("change", renderizarTareasInicio);

    configurarEventosGlobalesModales(() => cargarTareasInicio());
    cargarTareasInicio();
}

async function cargarTareasInicio() {
    try {
        const res = await fetch(`${API_URL}/tareas?usuario_id=${usuarioActual.id}`);
        if (!res.ok) throw new Error("No se pudieron cargar las tareas.");
        todasLasTareas = await res.json();
        renderizarTareasInicio();
    } catch (error) {
        document.getElementById("lista-tareas").innerHTML =
            `<div class="card"><p style="color:#c92a2a;">❌ ${error.message}</p></div>`;
    }
}

function limpiarFiltros() {
    document.getElementById("buscador-titulo").value = "";
    document.getElementById("filtro-categoria").value = "Todas";
    document.getElementById("filtro-estado").value = "Todos";
    renderizarTareasInicio();
}

function renderizarTareasInicio() {
    const contenedor = document.getElementById("lista-tareas");
    const textoBusqueda = document.getElementById("buscador-titulo").value.toLowerCase().trim();
    const filtroCat = document.getElementById("filtro-categoria").value;
    const filtroEst = document.getElementById("filtro-estado").value;

    const filtradas = todasLasTareas.filter((t) => {
        const coincideTitulo = t.titulo.toLowerCase().includes(textoBusqueda);
        const coincideCategoria = filtroCat === "Todas" || t.categoria === filtroCat;
        const coincideEstado = filtroEst === "Todos" || t.estado === filtroEst;
        return coincideTitulo && coincideCategoria && coincideEstado;
    });

    if (filtradas.length === 0) {
        contenedor.innerHTML = `<div class="card"><p style="color:#666;">No se encontraron tareas con esos filtros.</p></div>`;
        return;
    }

    contenedor.innerHTML = filtradas.map((t) => construirTarjetaTareaHTML(t)).join("");
}

// ==========================================
// 4. VENTANA: PUBLICAR TAREA (publicar.html)
// ==========================================
function iniciarPaginaPublicar() {
    vincularValidacionBoton("form-tarea", "btn-publicar");

    document.getElementById("form-tarea").addEventListener("submit", async (e) => {
        e.preventDefault();
        const msgDiv = document.getElementById("mensaje-tarea");
        msgDiv.innerText = "";

        try {
            const titulo = document.getElementById("titulo").value;
            const categoria = document.getElementById("categoria").value;
            const fecha_limite = document.getElementById("fecha-limite").value;
            const requisitos = document.getElementById("requisitos").value;
            const descripcion = document.getElementById("descripcion").value;

            validarCamposNoVacios({
                "Título de la tarea": titulo,
                "Categoría": categoria,
                "Fecha límite": fecha_limite,
                "Requisitos técnicos": requisitos,
                "Descripción": descripcion,
            });

            const res = await fetch(`${API_URL}/tareas`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    creador_id: usuarioActual.id,
                    titulo,
                    categoria,
                    fecha_limite,
                    requisitos,
                    descripcion,
                }),
            });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "No se pudo publicar la tarea.");
            }

            msgDiv.style.color = "#137333";
            msgDiv.innerText = "✅ " + data.mensaje + " Redirigiendo al feed principal...";
            document.getElementById("form-tarea").reset();
            document.getElementById("btn-publicar").disabled = true;

            setTimeout(() => {
                window.location.href = "index.html";
            }, 1200);
        } catch (error) {
            msgDiv.style.color = "#c92a2a";
            msgDiv.innerText = "❌ " + error.message;
        }
    });
}

// ==========================================
// 5. VENTANA: MIS TAREAS Y POSTULACIONES (mis-tareas.html)
// ==========================================
function iniciarPaginaMisTareas() {
    vincularValidacionBoton("form-chat", "btn-enviar-chat");
    vincularValidacionBoton("form-resena", "btn-enviar-resena");

    configurarEventosGlobalesModales(() => cargarMisTareas());
    cargarMisTareas();
}

async function cargarMisTareas() {
    try {
        const res = await fetch(`${API_URL}/tareas?usuario_id=${usuarioActual.id}`);
        if (!res.ok) throw new Error("Error al consultar tus tareas.");
        const tareas = await res.json();

        const creadas = tareas.filter((t) => t.es_creador);
        const postuladas = tareas.filter((t) => t.mi_postulacion_estado !== null);

        const contCreadas = document.getElementById("lista-creadas");
        const contPostuladas = document.getElementById("lista-postuladas");

        contCreadas.innerHTML = creadas.length
            ? creadas.map((t) => construirTarjetaTareaHTML(t)).join("")
            : `<div class="card"><p style="color:#666;">Aún no has publicado ninguna tarea.</p></div>`;

        contPostuladas.innerHTML = postuladas.length
            ? postuladas.map((t) => construirTarjetaTareaHTML(t)).join("")
            : `<div class="card"><p style="color:#666;">Aún no te has postulado a ninguna tarea.</p></div>`;
    } catch (error) {
        alert("❌ " + error.message);
    }
}

// ==========================================
// COMPONENTES COMPARTIDOS: TARJETAS, MODALES, CHAT Y RESEÑAS
// ==========================================
function construirTarjetaTareaHTML(t) {
    let botonesAccion = "";

    const claseEstado =
        t.estado === "Abierta"
            ? "badge-open"
            : t.estado === "Asignada"
            ? "badge-assigned"
            : "badge-finished";

    if (t.es_creador) {
        botonesAccion += `<button class="btn-secondary" style="margin-top:0;" onclick="abrirModalPostulantes('${t.id}', '${escaparComillas(t.titulo)}')">
            Ver Postulantes (${t.total_postulantes})
        </button>`;
    } else {
        if (!t.mi_postulacion_estado && t.estado === "Abierta") {
            botonesAccion += `<button class="btn-primary" onclick="abrirModalPostular('${t.id}', '${escaparComillas(t.titulo)}')">
                Postularme
            </button>`;
        } else if (t.mi_postulacion_estado) {
            botonesAccion += `<span class="badge ${t.mi_postulacion_estado === "Aceptada" ? "badge-open" : "badge-finished"}">
                Postulación: ${t.mi_postulacion_estado}
            </span>`;
        }
    }

    if (t.puede_chatear) {
        botonesAccion += `<button class="btn-chat" onclick="abrirChat('${t.id}', '${escaparComillas(t.titulo)}')">
            Abrir Chat
        </button>`;
    }

    if (t.puede_finalizar) {
        botonesAccion += `<button class="btn-finish" onclick="finalizarTarea('${t.id}')">
            Finalizar Tarea
        </button>`;
    }

    if (t.puede_resenar) {
        botonesAccion += `<button class="btn-review" onclick="abrirModalResena('${t.id}', '${escaparComillas(t.titulo)}')">
            Dejar Reseña
        </button>`;
    } else if (t.ya_deje_resena) {
        botonesAccion += `<span class="badge badge-open">Reseña enviada ✓</span>`;
    }

    const fechaFormateada = new Date(t.fecha_limite).toLocaleString("es-MX", {
        dateStyle: "medium",
        timeStyle: "short",
    });

    const bloqueResenas =
        t.resenas && t.resenas.length > 0
            ? `<div class="task-reviews-box">
                <strong>Reseñas de la colaboración:</strong>
                ${t.resenas
                    .map(
                        (r) =>
                            `<div style="margin-top:4px;">• <strong>${r.autor_nombre}</strong> (${"★".repeat(r.calificacion)}): "${r.comentario}"</div>`
                    )
                    .join("")}
               </div>`
            : "";

    return `
        <article class="task-card">
            <div class="task-header">
                <div>
                    <div class="task-author">${t.creador_nombre}</div>
                    <div class="task-meta">${t.creador_carrera}</div>
                </div>
                <div class="badges">
                    <span class="badge badge-category">${t.categoria}</span>
                    <span class="badge ${claseEstado}">${t.estado}</span>
                </div>
            </div>
            <h3 class="task-title">${t.titulo}</h3>
            <p class="task-desc">${t.descripcion}</p>
            <div class="task-specs">
                <div><strong>Requisitos:</strong> ${t.requisitos}</div>
                <div><strong>Fecha límite:</strong> ${fechaFormateada}</div>
            </div>
            ${bloqueResenas}
            <div class="task-footer">
                <span class="applicants-count">${t.total_postulantes} postulación(es)</span>
                <div class="task-actions-group">${botonesAccion}</div>
            </div>
        </article>
    `;
}

function configurarEventosGlobalesModales(callbackRecargar) {
    const formPostular = document.getElementById("form-postular");
    if (formPostular) {
        formPostular.addEventListener("submit", async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById("error-postular");
            errorDiv.innerText = "";

            try {
                const tareaId = document.getElementById("postular-tarea-id").value;
                const mensajePropuesta = document.getElementById("postular-mensaje").value;

                validarCamposNoVacios({ "Mensaje de propuesta": mensajePropuesta });

                const res = await fetch(`${API_URL}/tareas/${tareaId}/postular`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        usuario_id: usuarioActual.id,
                        mensaje_propuesta: mensajePropuesta,
                    }),
                });
                const data = await res.json();

                if (!res.ok) throw new Error(data.detail || "No se pudo enviar la postulación.");

                cerrarModal("modal-postular");
                callbackRecargar();
            } catch (error) {
                errorDiv.style.color = "#c92a2a";
                errorDiv.innerText = "❌ " + error.message;
            }
        });
    }

    const formResena = document.getElementById("form-resena");
    if (formResena) {
        formResena.addEventListener("submit", async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById("error-resena");
            errorDiv.innerText = "";

            try {
                const tareaId = document.getElementById("resena-tarea-id").value;
                const calificacion = document.getElementById("resena-calificacion").value;
                const comentario = document.getElementById("resena-comentario").value;

                validarCamposNoVacios({
                    "Calificación": calificacion,
                    "Comentario": comentario,
                });

                const res = await fetch(`${API_URL}/tareas/${tareaId}/resenas`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        autor_id: usuarioActual.id,
                        calificacion: parseInt(calificacion, 10),
                        comentario,
                    }),
                });
                const data = await res.json();

                if (!res.ok) throw new Error(data.detail || "Error al publicar reseña.");

                cerrarModal("modal-resena");
                callbackRecargar();
            } catch (error) {
                errorDiv.style.color = "#c92a2a";
                errorDiv.innerText = "❌ " + error.message;
            }
        });
    }

    const formChat = document.getElementById("form-chat");
    if (formChat) {
        formChat.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!chatTareaActivaId) return;

            try {
                const input = document.getElementById("chat-texto");
                const contenido = input.value;
                validarCamposNoVacios({ "Mensaje": contenido });

                const res = await fetch(`${API_URL}/tareas/${chatTareaActivaId}/chat`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        usuario_id: usuarioActual.id,
                        contenido,
                    }),
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "No se pudo enviar el mensaje.");

                input.value = "";
                document.getElementById("btn-enviar-chat").disabled = true;
                cargarMensajesChat();
            } catch (error) {
                alert("❌ " + error.message);
            }
        });
    }
}

async function finalizarTarea(tareaId) {
    try {
        const res = await fetch(`${API_URL}/tareas/${tareaId}/finalizar`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ creador_id: usuarioActual.id }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "No se pudo finalizar la tarea.");

        alert("✅ " + data.mensaje);
        if (document.body.dataset.page === "inicio") cargarTareasInicio();
        if (document.body.dataset.page === "mis-tareas") cargarMisTareas();
    } catch (error) {
        alert("❌ " + error.message);
    }
}

function abrirModalPostular(tareaId, titulo) {
    document.getElementById("postular-tarea-id").value = tareaId;
    document.getElementById("postular-titulo-tarea").innerText = `Tarea: ${titulo}`;
    document.getElementById("postular-mensaje").value = "";
    document.getElementById("error-postular").innerText = "";
    document.getElementById("btn-enviar-postulacion").disabled = true;
    document.getElementById("modal-postular").classList.remove("hidden");
}

function abrirModalResena(tareaId, titulo) {
    document.getElementById("resena-tarea-id").value = tareaId;
    document.getElementById("resena-titulo-tarea").innerText = `Tarea: ${titulo}`;
    document.getElementById("resena-calificacion").value = "";
    document.getElementById("resena-comentario").value = "";
    document.getElementById("error-resena").innerText = "";
    document.getElementById("btn-enviar-resena").disabled = true;
    document.getElementById("modal-resena").classList.remove("hidden");
}

async function abrirModalPostulantes(tareaId, titulo) {
    document.getElementById("postulantes-titulo-tarea").innerText = `Tarea: ${titulo}`;
    const contenedor = document.getElementById("contenedor-postulantes");
    contenedor.innerHTML = "<p>Cargando perfiles...</p>";
    document.getElementById("modal-postulantes").classList.remove("hidden");

    try {
        const res = await fetch(
            `${API_URL}/tareas/${tareaId}/postulaciones?solicitante_id=${usuarioActual.id}`
        );
        const lista = await res.json();

        if (!res.ok) throw new Error(lista.detail || "No tienes permiso para ver postulantes.");

        if (lista.length === 0) {
            contenedor.innerHTML = "<p style='color:#666;'>Aún nadie se ha postulado a esta tarea.</p>";
            return;
        }

        contenedor.innerHTML = lista
            .map((item) => {
                const p = item.postulante;
                const rep =
                    p.promedio_calificacion !== null
                        ? `★ ${p.promedio_calificacion} (${p.total_resenas} reseñas)`
                        : "Sin reseñas aún";

                const botones =
                    item.estado === "Pendiente"
                        ? `<button class="btn-primary" onclick="seleccionarPrestador('${item.participacion_id}', 'Aceptada', '${tareaId}', '${escaparComillas(titulo)}')">Asignar Prestador (BR-04)</button>
                           <button class="btn-secondary" style="margin-top:0;" onclick="seleccionarPrestador('${item.participacion_id}', 'Rechazada', '${tareaId}', '${escaparComillas(titulo)}')">Rechazar</button>`
                        : `<span class="badge ${item.estado === "Aceptada" ? "badge-open" : "badge-finished"}">Estado: ${item.estado}</span>`;

                return `
                    <div class="applicant-card">
                        <div class="applicant-header">
                            <strong>${p.nombre}</strong>
                            <span class="badge badge-category">${rep}</span>
                        </div>
                        <p><strong>Correo:</strong> ${p.correo}</p>
                        <p><strong>Carrera:</strong> ${p.carrera}</p>
                        <p><strong>Habilidades:</strong> ${p.habilidades}</p>
                        <p><strong>Perfil:</strong> ${p.bio}</p>
                        <p><strong>Propuesta:</strong> "${item.mensaje_propuesta}"</p>
                        <div class="applicant-actions">${botones}</div>
                    </div>
                `;
            })
            .join("");
    } catch (error) {
        contenedor.innerHTML = `<p style="color:#c92a2a;">❌ ${error.message}</p>`;
    }
}

async function seleccionarPrestador(participacionId, accion, tareaId, titulo) {
    try {
        const res = await fetch(`${API_URL}/postulaciones/${participacionId}/responder`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                creador_id: usuarioActual.id,
                accion,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "No se pudo asignar el prestador.");

        abrirModalPostulantes(tareaId, titulo);
        if (document.body.dataset.page === "inicio") cargarTareasInicio();
        if (document.body.dataset.page === "mis-tareas") cargarMisTareas();
    } catch (error) {
        alert("❌ " + error.message);
    }
}

async function cargarContadorNotificaciones() {
    if (!usuarioActual) return;
    try {
        const res = await fetch(`${API_URL}/usuarios/${usuarioActual.id}/notificaciones`);
        if (!res.ok) return;
        const lista = await res.json();
        const noLeidas = lista.filter((n) => !n.leida).length;
        const badge = document.getElementById("badge-notif");
        if (badge) {
            if (noLeidas > 0) {
                badge.innerText = noLeidas;
                badge.classList.remove("hidden");
            } else {
                badge.classList.add("hidden");
            }
        }
    } catch (e) {
        console.error(e);
    }
}

async function abrirModalNotificaciones() {
    const contenedor = document.getElementById("contenedor-notificaciones");
    contenedor.innerHTML = "<p>Cargando notificaciones...</p>";
    document.getElementById("modal-notificaciones").classList.remove("hidden");

    try {
        const res = await fetch(`${API_URL}/usuarios/${usuarioActual.id}/notificaciones`);
        const lista = await res.json();
        await fetch(`${API_URL}/usuarios/${usuarioActual.id}/notificaciones/leer`, { method: "POST" });
        cargarContadorNotificaciones();

        if (lista.length === 0) {
            contenedor.innerHTML = "<p style='color:#666;'>No tienes notificaciones.</p>";
            return;
        }

        contenedor.innerHTML = lista
            .map(
                (n) => `
                <div class="applicant-card" style="${n.leida ? "" : "border-left: 4px solid #0a66c2;"}">
                    <strong>${n.titulo}</strong>
                    <p>${n.mensaje}</p>
                </div>`
            )
            .join("");
    } catch (e) {
        contenedor.innerHTML = "<p>Error al cargar notificaciones.</p>";
    }
}

function abrirChat(tareaId, titulo) {
    chatTareaActivaId = tareaId;
    document.getElementById("chat-titulo-tarea").innerText = `Chat: ${titulo}`;
    document.getElementById("chat-texto").value = "";
    document.getElementById("btn-enviar-chat").disabled = true;
    document.getElementById("modal-chat").classList.remove("hidden");

    cargarMensajesChat();
    if (intervaloChat) clearInterval(intervaloChat);
    intervaloChat = setInterval(cargarMensajesChat, 3000);
}

function cerrarChat() {
    chatTareaActivaId = null;
    if (intervaloChat) {
        clearInterval(intervaloChat);
        intervaloChat = null;
    }
    cerrarModal("modal-chat");
}

async function cargarMensajesChat() {
    if (!chatTareaActivaId || !usuarioActual) return;
    try {
        const res = await fetch(
            `${API_URL}/tareas/${chatTareaActivaId}/chat?usuario_id=${usuarioActual.id}`
        );
        if (!res.ok) return;
        const mensajes = await res.json();
        const contenedor = document.getElementById("chat-mensajes");

        if (mensajes.length === 0) {
            contenedor.innerHTML = "<p style='color:#666; text-align:center;'>Aún no hay mensajes. ¡Inicia la conversación!</p>";
            return;
        }

        contenedor.innerHTML = mensajes
            .map((m) => {
                const esMio = m.emisor_id === usuarioActual.id;
                return `
                    <div class="msg-bubble ${esMio ? "msg-mine" : "msg-other"}">
                        <div class="msg-sender">${esMio ? "Tú" : m.emisor_nombre}</div>
                        <div>${m.contenido}</div>
                    </div>
                `;
            })
            .join("");

        contenedor.scrollTop = contenedor.scrollHeight;
    } catch (error) {
        console.error("Error cargando chat:", error);
    }
}

function cerrarModal(id) {
    document.getElementById(id).classList.add("hidden");
}

function escaparComillas(texto) {
    return texto.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

# FIFLancers

FIFLancers es una plataforma web desarrollada para la comunidad estudiantil de la Facultad de Informática (FIF) de la Universidad Autónoma de Querétaro (UAQ). Su objetivo es centralizar la publicación de tareas, asesorías y microproyectos académicos, permitiendo que los estudiantes encuentren colaboradores con habilidades afines, coordinen entregas mediante un chat privado y construyan reputación a través de reseñas verificadas tras completar cada trabajo.

## Equipo de Desarrollo

| Nombre | Expediente | Rol en el Proyecto |

| Delgado Brian Nicholas | 333336 | Arquitectura Backend, Casos de Uso y Despliegue |
| Toribio Dimas Briseida Monserrat | <Expediente> | Desarrollo Frontend, Documentación y Pruebas |

## Recursos y Stack Tecnológico

Para operar en entorno local y en producción, el sistema utiliza los siguientes componentes y servicios:

* **Backend:** Python 3.10+, FastAPI, Uvicorn y Pydantic para validación de esquemas de entrada.
* **Base de datos y seguridad:** SQLite (`database.db`) gestionado mediante consultas SQL parametrizadas, identificadores UUIDv4 y cifrado SHA-256 para contraseñas.
* **Frontend:** HTML5, CSS3 y JavaScript (ES6+) sin frameworks externos, consumiendo la API mediante `fetch` y gestionando la sesión activa en `localStorage`.
* **Infraestructura de despliegue:**
  * **Render:** Aloja el servicio web de la API REST (`https://fiflancers.onrender.com/api`).
  * **Netlify:** Sirve la interfaz web estática.
* **Variables de entorno:** Archivo `.env` (basado en `.env.example`) para configurar rutas locales sin exponer credenciales en el repositorio.

## Estructura del Proyecto

El repositorio está dividido en dos módulos principales (`fiflancers_api` y `fiflancers_web`) junto con la carpeta de documentación técnica (`docs`):

```text
FIFLancers/
├── fiflancers_api/
│   ├── domain/
│   │   └── entidades.py          # Entidades del dominio, enums e invariantes de negocio puras
│   ├── application/
│   │   ├── interfaces.py         # Puertos (interfaces abstractas) de repositorios y validador
│   │   └── casos_uso.py          # Casos de uso y orquestación de flujos de aplicación
│   ├── infrastructure/
│   │   └── sqlite_adapters.py    # Implementaciones SQLite de los puertos, SHA-256 y semilla
│   ├── main.py                   # Adaptador HTTP (endpoints FastAPI), esquemas Pydantic y CORS
│   └── requirements.txt          # Dependencias del servidor (fastapi, uvicorn, pydantic)
├── fiflancers_web/
│   ├── index.html                # Tablero principal de tareas, filtros y perfiles recomendados
│   ├── login.html                # Inicio de sesión y registro de estudiantes
│   ├── publicar.html             # Formulario de creación y publicación de tareas
│   ├── mis-tareas.html           # Panel de tareas publicadas y postulaciones enviadas
│   ├── perfil.html               # Edición de perfil y administración de usuarios silenciados
│   ├── style.css                 # Hoja de estilos responsiva
│   └── app.js                    # Lógica de cliente, consumo de API, chat y notificaciones
├── docs/
│   ├── arquitectura.png          # Diagrama de capas siguiendo Clean Architecture
│   └── adr/                      # Architecture Decision Records (ADRs) del proyecto
├── .env.example                  # Plantilla de configuración sin secretos
└── README.md
```

## Arquitectura del Sistema

![Diagrama de Arquitectura](docs/arquitectura.png)

El backend está estructurado bajo **Clean Architecture**, respetando la regla de dependencia: las capas internas definen las reglas y contratos del negocio sin conocer detalles de HTTP, frameworks web o motores de base de datos.

1. **Entities (`fiflancers_api/domain/entidades.py`):** Contiene las entidades `Usuario`, `Tarea`, `Postulacion`, `Mensaje`, `Notificacion`, `Resena` y el enumerado `RolParticipacion`. Cada entidad protege sus propias invariantes (formato de correo, obligatoriedad de campos, fechas límite futuras al crear una tarea, transiciones válidas de estado y calificaciones enteras entre 1 y 5) sin importar librerías externas.
2. **Use Cases (`fiflancers_api/application/casos_uso.py` e `interfaces.py`):** Define las interfaces abstractas (`IUsuarioRepository`, `ITareaRepository`, `IPostulacionRepository`, `IMensajeRepository`, `INotificacionRepository`, `IResenaRepository`, `ISilencioRepository`, `IValidadorCredenciales`) e implementa la lógica de cada operación (`RegistrarUsuario`, `IniciarSesion`, `ActualizarPerfil`, `ObtenerPerfilesRecomendados`, `CrearTarea`, `PostularseATarea`, `ObtenerPostulacionesTarea`, `SeleccionarPrestador`, `FinalizarTarea`, `CrearResena`, `GestionarChat`, `GestionarNotificaciones`).
3. **Interface Adapters (`fiflancers_api/main.py` y `fiflancers_web/app.js`):** `main.py` expone los endpoints REST, valida los datos entrantes mediante Pydantic, inyecta los repositorios en los casos de uso y traduce excepciones de negocio (`ValueError`) en respuestas HTTP (`400`, `401`, `403`). En el navegador, `app.js` transforma las respuestas JSON en vistas interactivas.
4. **Frameworks & Drivers (`fiflancers_api/infrastructure/sqlite_adapters.py`):** Implementa los repositorios concretos sobre SQLite, ejecuta la creación de tablas (`inicializar_bd`) y carga los datos iniciales de demostración (`sembrar_datos_iniciales`).

## Decisiones de Arquitectura (ADRs)

Las decisiones técnicas tomadas durante el desarrollo se encuentran documentadas en `docs/adr/`. A continuación se resumen las principales:

* **ADR-001 — Separación por capas con Clean Architecture:** Se aisló el dominio y la lógica de aplicación respecto a FastAPI y SQLite mediante interfaces de repositorio. Esto permite reemplazar la base de datos o el framework web modificando únicamente la capa de infraestructura.
* **ADR-002 — Persistencia autocontenida con SQLite y SQL puro:** Se eligió SQLite (`database.db`) con adaptadores SQL parametrizados en lugar de un ORM complejo para simplificar la portabilidad del proyecto, evitar dependencias pesadas y mantener control directo sobre las consultas y migraciones ligeras.
* **ADR-003 — Despliegue desacoplado en Render y Netlify:** Se separó el backend (API REST en Render) del frontend estático (Netlify) comunicándose mediante JSON sobre HTTPS. Esto permite actualizar la interfaz de usuario sin reiniciar el servidor y facilita pruebas locales independientes.
* **ADR-004 — Registro directo con activación inmediata y código simulado (Supera verificación bloqueante):** Originalmente las cuentas quedaban inactivas hasta validar un código externo, lo que bloqueaba correos si el flujo se interrumpía. Se decidió activar la cuenta inmediatamente tras verificar la unicidad del correo en SQLite y registrar un código simulado dentro de la bandeja interna de notificaciones.
* **ADR-005 — Moderación unilateral mediante bloqueo silencioso:** Se implementó una tabla `UsuariosSilenciados` para que cualquier estudiante pueda dejar de recibir notificaciones y sugerencias de perfiles provenientes de otro usuario sin afectar tareas que ya estén en curso.

## Reglas de Negocio y Flujos Principales

El comportamiento funcional de FIFLancers está gobernado por las siguientes reglas aplicadas en dominio y casos de uso:

* **Cuentas y credenciales:** Los correos electrónicos se normalizan a minúsculas y tienen restricción `UNIQUE` en la base de datos. Las contraseñas deben tener al menos 6 caracteres y se almacenan exclusivamente como hash SHA-256.
* **Publicación de tareas:** Una tarea nace en estado `Abierta` y exige título, descripción, requisitos técnicos, categoría y una fecha límite posterior al momento de creación. Al publicarla, el autor queda registrado con rol `Creador`.
* **Postulación y asignación única:** Un estudiante no puede postularse a una tarea propia ni enviar más de una postulación a la misma tarea. Solo se aceptan postulaciones en tareas `Abierta` cuya fecha límite no haya vencido. Únicamente el creador puede consultar los perfiles de los postulantes y aceptar a un prestador; al hacerlo, la tarea cambia a `Asignada` y las demás postulaciones pendientes pasan automáticamente a `Rechazada`.
* **Coordinación por chat privado:** Cuando una tarea pasa a `Asignada`, se habilita un chat privado exclusivo entre el creador y el prestador seleccionado. Cada mensaje registra la hora de envío y puede ser eliminado por su propio autor.
* **Cierre y evaluación mutua:** Solo el creador puede marcar una tarea `Asignada` como `Finalizada`. Una vez finalizada, tanto el creador como el prestador asignado pueden registrar una única reseña mutua (calificación de 1 a 5 estrellas y comentario), visible en el historial de la tarea y reflejada en el promedio de cada perfil.
* **Recomendaciones y notificaciones:** El sistema sugiere colaboradores afines calculando coincidencias en habilidades técnicas y carrera, omitiendo al propio usuario y a perfiles silenciados. Las acciones relevantes generan notificaciones persistentes que pueden marcarse como leídas, eliminarse individualmente o vaciarse por completo.

## Instalación y Ejecución Local

### 1. Requisitos previos
* Python 3.10 o superior
* Git
* Navegador web moderno

### 2. Clonar el repositorio y configurar entorno
```bash
git clone [https://github.com/FerXXxoo/FIFLancers.git](https://github.com/FerXXxoo/FIFLancers.git)
cd FIFLancers
cp .env.example .env
```
*(En PowerShell de Windows: `Copy-Item .env.example .env`)*

### 3. Levantar el backend (FastAPI)
```bash
cd fiflancers_api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
* La API quedará activa en `http://127.0.0.1:8000` y su documentación interactiva Swagger en `http://127.0.0.1:8000/docs`.
* En el primer arranque se crea automáticamente `database.db` con usuarios y tareas de prueba.

### 4. Ejecutar el frontend
1. Para conectar el frontend con el servidor local, abre `fiflancers_web/app.js` y ajusta la primera línea:
   ```javascript
   const API_URL = "[http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)";
   ```
   *(Por defecto apunta a `https://fiflancers.onrender.com/api` para producción).*
2. Sirve la carpeta `fiflancers_web/` mediante Live Server (VS Code) o con Python:
   ```bash
   cd ../fiflancers_web
   python -m http.server 5500
   ```
3. Abre `http://127.0.0.1:5500/login.html` en el navegador.

### Cuentas de prueba precargadas
* **Ana Estudiante:** `ana@uaq.mx` / `Ana123!`
* **Carlos Mendoza:** `carlos@uaq.mx` / `Carlos123!`
* **Valeria López:** `valeria@uaq.mx` / `Valeria123!`

## Documentación y Demostración

* **Diagrama de arquitectura:**
* <img width="4920" height="3089" alt="Diagrama_de_arquitectura_FIFLancers" src="https://github.com/user-attachments/assets/f44be1ff-e57d-4a51-b79c-6c1da8c6c505" />

* **Registros de decisiones (ADRs):** `docs/adr/`
* **Video de explicación y demostración:** <Enlace al video en YouTube o Google Drive>

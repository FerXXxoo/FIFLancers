from abc import ABC, abstractmethod
import uuid
from typing import List, Optional
from domain.entidades import (
    Usuario,
    Tarea,
    Postulacion,
    Mensaje,
    Notificacion,
    Resena,
)


class IValidadorCredenciales(ABC):
    @abstractmethod
    def hashear(self, password_plano: str) -> str:
        pass

    @abstractmethod
    def verificar(self, password_plano: str, password_hash: str) -> bool:
        pass


class IUsuarioRepository(ABC):
    @abstractmethod
    def guardar(self, usuario: Usuario) -> None:
        pass

    @abstractmethod
    def actualizar(self, usuario: Usuario) -> None:
        pass

    @abstractmethod
    def obtener_por_id(self, id: uuid.UUID) -> Optional[Usuario]:
        pass

    @abstractmethod
    def obtener_por_correo(self, correo: str) -> Optional[Usuario]:
        pass


class ITareaRepository(ABC):
    @abstractmethod
    def guardar(self, tarea: Tarea) -> None:
        pass

    @abstractmethod
    def actualizar_estado(self, tarea_id: uuid.UUID, nuevo_estado: str) -> None:
        pass

    @abstractmethod
    def obtener_por_id(self, id: uuid.UUID) -> Optional[Tarea]:
        pass

    @abstractmethod
    def listar_todas(self) -> List[Tarea]:
        pass


class IPostulacionRepository(ABC):
    @abstractmethod
    def guardar(self, postulacion: Postulacion) -> None:
        pass

    @abstractmethod
    def actualizar_estado(self, postulacion_id: uuid.UUID, nuevo_estado: str) -> None:
        pass

    @abstractmethod
    def obtener_por_id(self, postulacion_id: uuid.UUID) -> Optional[Postulacion]:
        pass

    @abstractmethod
    def obtener_por_tarea(self, tarea_id: uuid.UUID) -> List[Postulacion]:
        pass

    @abstractmethod
    def obtener_por_usuario_y_tarea(
        self, usuario_id: uuid.UUID, tarea_id: uuid.UUID
    ) -> Optional[Postulacion]:
        pass


class IMensajeRepository(ABC):
    @abstractmethod
    def guardar(self, mensaje: Mensaje) -> None:
        pass

    @abstractmethod
    def listar_por_tarea(self, tarea_id: uuid.UUID) -> List[Mensaje]:
        pass


class INotificacionRepository(ABC):
    @abstractmethod
    def guardar(self, notificacion: Notificacion) -> None:
        pass

    @abstractmethod
    def listar_por_usuario(self, usuario_id: uuid.UUID) -> List[Notificacion]:
        pass

    @abstractmethod
    def marcar_todas_leidas(self, usuario_id: uuid.UUID) -> None:
        pass


class IResenaRepository(ABC):
    @abstractmethod
    def guardar(self, resena: Resena) -> None:
        pass

    @abstractmethod
    def obtener_por_tarea_y_autor(
        self, tarea_id: uuid.UUID, autor_id: uuid.UUID
    ) -> Optional[Resena]:
        pass

    @abstractmethod
    def listar_por_receptor(self, receptor_id: uuid.UUID) -> List[Resena]:
        pass

    @abstractmethod
    def listar_por_tarea(self, tarea_id: uuid.UUID) -> List[Resena]:
        pass
from sqlalchemy.orm import Session

from src.modules.usuarios.models.rol_model import Rol
from src.modules.usuarios.models.usuario_model import Usuario


class UsuarioRepository:

    @staticmethod
    def get_rol_by_name(session: Session, nombre: str):
        return session.query(Rol).filter(
            Rol.nombre == nombre
        ).first()

    @staticmethod
    def get_user_by_username(session: Session, username: str):
        return session.query(Usuario).filter(
            Usuario.username == username
        ).first()
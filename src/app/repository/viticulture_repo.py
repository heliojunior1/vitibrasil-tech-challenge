from sqlalchemy.orm import Session
from src.app.models.viticulture import Viticulture
from src.app.domain.viticulture import ViticulturaDTO
from src.app.domain.viticulture import ViticultureCategory


class RepositorioViticulture:

    def __init__(self, db: Session):
        self.db = db

    def adicionar(self, data: ViticulturaDTO):
        novo_registro = Viticulture(**data.dict())
        self.db.add(novo_registro)
        self.db.refresh(novo_registro)
        return novo_registro

    def listar_todos(self):
        return self.db.query(Viticulture).all()
    
    def buscar_por_categoria_tipo_ano(self, categoria: ViticultureCategory, tipo: str, ano: int):
        """
        Busca registros no banco de dados com base na categoria, tipo e ano.
        """
        return (
            self.db.query(Viticulture)
            .filter(
                Viticulture.category == categoria,
                Viticulture.subcategory == tipo,
                Viticulture.year == ano
            )
            .all()
        )
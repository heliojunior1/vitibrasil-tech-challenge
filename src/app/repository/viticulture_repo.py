from sqlalchemy.orm import Session
from src.app.models.viticulture import Viticulture
from src.app.domain.viticulture import ViticulturaDTO

class RepositorioViticulture:

    def __init__(self, db: Session):
        self.db = db

    def adicionar(self, data: ViticulturaDTO):
        novo_registro = Viticulture(**data.dict())
        self.db.add(novo_registro)
        self.db.commit()
        self.db.refresh(novo_registro)
        return novo_registro

    def listar_todos(self):
        return self.db.query(Viticulture).all()
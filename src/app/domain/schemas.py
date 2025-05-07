from pydantic import BaseModel

class ViticulturaSchema(BaseModel):
    tipo: str
    valor: str

    class Config:
        orm_mode = True
import pytest
from app.scraper.viticulture_full_scraper import normalize_text

def test_normalize_text_simple():
    assert normalize_text("Vinhos Finos de Mesa") == "vinhos_finos_de_mesa"

def test_normalize_text_with_special_chars():
    assert normalize_text("Produção (Kg)") == "producao_kg"
    assert normalize_text("Valor (US$)") == "valor_us"
    assert normalize_text("Comercialização - Total") == "comercializacao_total"

def test_normalize_text_with_accentuation():
    assert normalize_text("Comercialização") == "comercializacao"
    assert normalize_text("Suco de Uva Integral") == "suco_de_uva_integral"

def test_normalize_text_empty_and_none():
    assert normalize_text("") == ""
    assert normalize_text(None) is None

def test_normalize_text_with_numbers():
    assert normalize_text("Safra 2023") == "safra_2023"

def test_normalize_text_extra_spaces():
    assert normalize_text("  Vinho   Branco  ") == "vinho_branco"

def test_normalize_text_already_normalized():
    assert normalize_text("vinhos_de_mesa") == "vinhos_de_mesa"

def test_normalize_text_mixed_case():
    assert normalize_text("Vinhos Tintos") == "vinhos_tintos"
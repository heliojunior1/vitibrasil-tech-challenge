# src/app/scraper/exceptions.py
class ScrapingError(Exception):
    """Erro base para scraping"""
    pass

class PageNotFoundError(ScrapingError):
    """Erro quando página não é encontrada"""
    pass

class TableNotFoundError(ScrapingError):
    """Erro quando tabela de dados não é encontrada"""
    pass

class InvalidOptionError(ScrapingError):
    """Erro para opção inválida"""
    pass

class YearRangeError(ScrapingError):
    """Erro para range de anos inválido"""
    pass
from sqlalchemy.orm import Session
from typing import List

from src.app.models.viticulture import Viticultura as ViticulturaModel
from src.app.domain.viticulture import ViticulturaCreate

def save_bulk(db: Session, data_entries: List[ViticulturaCreate]):
    """
    Saves a list of viticulture data entries to the database.
    This function will first delete all existing data in the viticultura_data table,
    then add the new entries.
    """
    try:
        # Delete all existing records from the table
        num_deleted = db.query(ViticulturaModel).delete()
        print(f"Deleted {num_deleted} old records from viticultura_data table.")

        # Add new records
        db_entries = []
        for entry_data in data_entries:
            # The 'dados' field from ViticulturaCreate (which is List[Dict[str, Any]])
            # will be stored in the 'dados_list_json' column of the ViticulturaModel.
            db_entry = ViticulturaModel(
                ano=entry_data.ano,
                aba=entry_data.aba,
                subopcao=entry_data.subopcao,
                dados_list_json=entry_data.dados # SQLAlchemy handles JSON conversion
            )
            db_entries.append(db_entry)
        
        db.add_all(db_entries)
        db.commit()
        print(f"Successfully saved {len(db_entries)} new records to viticultura_data table.")
        
        # Optionally, refresh the instances if needed, though usually not necessary after add_all & commit
        # for db_entry in db_entries:
        #     db.refresh(db_entry)
        return db_entries # Or return the count, or just True for success
    except Exception as e:
        db.rollback()
        print(f"Error in save_bulk: {e}")
        raise e # Re-raise the exception to be handled by the service layer

def get_all(db: Session) -> List[ViticulturaModel]:
    """
    Retrieves all viticulture data entries from the database.
    Returns a list of Viticultura SQLAlchemy model instances.
    """
    try:
        return db.query(ViticulturaModel).all()
    except Exception as e:
        print(f"Error in get_all: {e}")
        # Depending on desired error handling, you might return an empty list or raise
        return [] 

# If you need a function to get data by specific criteria, e.g., by year:
# def get_by_year(db: Session, year: int) -> List[ViticulturaModel]:
#     try:
#         return db.query(ViticulturaModel).filter(ViticulturaModel.ano == year).all()
#     except Exception as e:
#         print(f"Error in get_by_year: {e}")
#         return []
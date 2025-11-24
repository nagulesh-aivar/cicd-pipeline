# client_service/utils/pydantic_utils.py
from pydantic import BaseModel

def map_to_pydantic(model: BaseModel, data: dict) -> BaseModel:
    """
    Dynamically map a raw dict to a Pydantic model (Pydantic v2).
    Only keep keys that exist in the Pydantic model.
    """
    model_fields = model.model_fields.keys()
    filtered_data = {k: v for k, v in data.items() if k in model_fields}
    return model(**filtered_data)

from pydantic import BaseModel


class MasterResponse(BaseModel):

    filename: str

    output_file: str

    analysis: dict

    message: str
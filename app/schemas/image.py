from pydantic import BaseModel, ConfigDict, Field


class ImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique image identifier.")
    file_id: str = Field(description="ImageKit file id.")
    url: str = Field(description="Public delivery URL.")
    file_path: str = Field(description="Path of the file in the ImageKit media library.")

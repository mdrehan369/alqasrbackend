from pydantic import BaseModel, ConfigDict


class DashboardBasicStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_products: int
    active_categories: int
    low_stock_products: int
    total_catalog_value: float

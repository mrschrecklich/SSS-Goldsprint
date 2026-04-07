from pydantic_settings import BaseSettings
from pydantic import Field

class GoldsprintConfig(BaseSettings):
    """
    Configuration for the Goldsprint server and race engine.
    Values can be overridden by environment variables (e.g., GOLDSPRINT_PORT=4000).
    """
    # Server configuration
    port: int = Field(default=3000, description="Port the FastAPI server listens on")
    host: str = Field(default="0.0.0.0", description="Host the FastAPI server binds to")
    
    # Sensor configuration
    sensor_host: str = Field(default="127.0.0.1", description="Host of the physical or mock sensor")
    sensor_port: int = Field(default=5000, description="Port of the physical or mock sensor")
    
    # Race engine defaults
    default_target_dist: float = Field(default=500.0, description="Default race distance in meters")
    default_circumference: float = Field(default=2.1, description="Default wheel circumference in meters")
    false_start_threshold: int = Field(default=20, description="RPM threshold for detecting false starts")

    class Config:
        env_prefix = "GOLDSPRINT_"
        case_sensitive = False

# Global configuration instance
config = GoldsprintConfig()

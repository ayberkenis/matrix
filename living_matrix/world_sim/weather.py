"""Weather system with regional weather and transitions."""

import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class WeatherState:
    """Weather state for a region."""
    temperature: float  # 0.0 (cold) to 1.0 (hot)
    precipitation: float  # 0.0 (dry) to 1.0 (heavy rain)
    wind: float  # 0.0 (calm) to 1.0 (strong)
    cloud: float  # 0.0 (clear) to 1.0 (overcast)


class WeatherSystem:
    """Manages weather for all regions."""
    
    # Markov transition probabilities (simplified)
    TEMP_TRANSITION = 0.15  # Probability of temperature change
    PRECIP_TRANSITION = 0.20  # Probability of precipitation change
    WIND_TRANSITION = 0.25  # Probability of wind change
    CLOUD_TRANSITION = 0.20  # Probability of cloud change
    
    def __init__(self, region_ids: List[str], seed: int = 42):
        """
        Initialize weather system.
        
        Args:
            region_ids: List of region IDs to track weather for
            seed: Random seed for deterministic behavior
        """
        self.seed = seed
        random.seed(seed)
        self.region_weather: Dict[str, WeatherState] = {}
        
        # Initialize weather for each region
        for region_id in region_ids:
            self.region_weather[region_id] = WeatherState(
                temperature=random.uniform(0.3, 0.7),
                precipitation=random.uniform(0.0, 0.4),
                wind=random.uniform(0.1, 0.5),
                cloud=random.uniform(0.2, 0.6)
            )
    
    def advance(self):
        """Advance weather by one turn (slow transitions)."""
        for region_id, weather in self.region_weather.items():
            # Temperature drift
            if random.random() < self.TEMP_TRANSITION:
                weather.temperature += random.uniform(-0.1, 0.1)
                weather.temperature = max(0.0, min(1.0, weather.temperature))
            
            # Precipitation drift
            if random.random() < self.PRECIP_TRANSITION:
                weather.precipitation += random.uniform(-0.15, 0.15)
                weather.precipitation = max(0.0, min(1.0, weather.precipitation))
            
            # Wind drift
            if random.random() < self.WIND_TRANSITION:
                weather.wind += random.uniform(-0.2, 0.2)
                weather.wind = max(0.0, min(1.0, weather.wind))
            
            # Cloud drift
            if random.random() < self.CLOUD_TRANSITION:
                weather.cloud += random.uniform(-0.15, 0.15)
                weather.cloud = max(0.0, min(1.0, weather.cloud))
    
    def snapshot(self, region_id: str) -> WeatherState:
        """Get current weather snapshot for a region."""
        return self.region_weather.get(region_id)
    
    def get_global_summary(self) -> Tuple[float, float, float, float]:
        """
        Get global weather averages.
        
        Returns:
            Tuple of (avg_temp, avg_precip, avg_wind, avg_cloud)
        """
        if not self.region_weather:
            return (0.5, 0.0, 0.3, 0.4)
        
        temps = [w.temperature for w in self.region_weather.values()]
        precips = [w.precipitation for w in self.region_weather.values()]
        winds = [w.wind for w in self.region_weather.values()]
        clouds = [w.cloud for w in self.region_weather.values()]
        
        return (
            sum(temps) / len(temps),
            sum(precips) / len(precips),
            sum(winds) / len(winds),
            sum(clouds) / len(clouds)
        )
    
    def format_weather_line(self, region_id: Optional[str] = None) -> str:
        """
        Format weather as a string line.
        
        Args:
            region_id: If provided, show specific region; otherwise global average
            
        Returns:
            Formatted weather string
        """
        if region_id and region_id in self.region_weather:
            weather = self.region_weather[region_id]
        else:
            avg_temp, avg_precip, avg_wind, avg_cloud = self.get_global_summary()
            weather = WeatherState(avg_temp, avg_precip, avg_wind, avg_cloud)
        
        # Convert to descriptive terms
        cloud_desc = "clear" if weather.cloud < 0.3 else "partly cloudy" if weather.cloud < 0.7 else "overcast"
        wind_desc = "calm" if weather.wind < 0.3 else "breeze" if weather.wind < 0.6 else "strong"
        precip_desc = "none" if weather.precipitation < 0.2 else "drizzle" if weather.precipitation < 0.5 else "rain"
        temp_desc = "cold" if weather.temperature < 0.4 else "mild" if weather.temperature < 0.7 else "warm"
        
        return f"Sky: {cloud_desc} • Wind: {wind_desc} • Precip: {precip_desc} • Temp: {temp_desc}"
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "seed": self.seed,
            "region_weather": {
                rid: {
                    "temperature": w.temperature,
                    "precipitation": w.precipitation,
                    "wind": w.wind,
                    "cloud": w.cloud
                }
                for rid, w in self.region_weather.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict, region_ids: List[str]) -> "WeatherSystem":
        """Deserialize from dictionary."""
        obj = cls(region_ids=region_ids, seed=data.get("seed", 42))
        
        for rid, wdata in data.get("region_weather", {}).items():
            if rid in obj.region_weather:
                obj.region_weather[rid] = WeatherState(
                    temperature=wdata["temperature"],
                    precipitation=wdata["precipitation"],
                    wind=wdata["wind"],
                    cloud=wdata["cloud"]
                )
        
        return obj

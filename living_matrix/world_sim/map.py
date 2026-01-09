"""World map system with regions and locations."""

import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Location:
    """A location in the world."""
    id: str
    name: str
    region_id: str
    type_tag: str  # residential, market, transit, industrial, civic, edge
    crowd_density: float = 0.0  # 0.0-1.0, updated by agent system


@dataclass
class Region:
    """A region containing multiple locations."""
    id: str
    name: str
    locations: List[Location]
    tags: List[str] = None  # market, industrial, residential, garden, etc.
    food: float = 50.0  # 0-100
    materials: float = 50.0  # 0-100
    energy: float = 50.0  # 0-100
    infrastructure: float = 0.5  # 0-1, affects production stability
    tension: float = 0.2  # 0-1, increases with shortages


class WorldMap:
    """Manages world map with regions and locations."""
    
    # Fictional location name parts (no real-world references)
    LOCATION_PARTS = {
        'residential': ['Block', 'Court', 'Haven', 'Nest', 'Row', 'Lane'],
        'market': ['Market', 'Exchange', 'Bazaar', 'Post', 'Hub'],
        'transit': ['Transit', 'Crossing', 'Gate', 'Terminal', 'Bridge'],
        'industrial': ['Works', 'Yard', 'Depot', 'Forge', 'Mill'],
        'civic': ['Hall', 'Square', 'Plaza', 'Forum', 'Center'],
        'edge': ['Edge', 'Outpost', 'Fringe', 'Rim', 'Border']
    }
    
    REGION_NAMES = ['Kora', 'Vey', 'Lume', 'Nex', 'Zeph', 'Rift', 'Core', 'Apex']
    
    def __init__(self, seed: int = 42):
        """
        Initialize world map.
        
        Args:
            seed: Random seed for deterministic generation
        """
        self.seed = seed
        random.seed(seed)
        self.regions: Dict[str, Region] = {}
        self.locations: Dict[str, Location] = {}
        self._generate_map()
    
    def _generate_map(self):
        """Generate fictional regions and locations."""
        num_regions = random.randint(6, 12)
        region_names = random.sample(self.REGION_NAMES, min(num_regions, len(self.REGION_NAMES)))
        if len(region_names) < num_regions:
            extra_names = ['Vex', 'Nex', 'Zeph', 'Rift', 'Core', 'Apex', 'Kira', 'Mira', 'Tara', 'Jax']
            region_names.extend(random.sample(extra_names, num_regions - len(region_names)))
        
        location_id = 0
        region_tags_options = [
            ['market', 'residential'],
            ['industrial', 'transit'],
            ['residential', 'garden'],
            ['market', 'civic'],
            ['industrial', 'transit', 'residential'],
            ['edge', 'transit']
        ]
        
        for region_name in region_names:
            region_id = f"region_{region_name.lower()}"
            tags = random.choice(region_tags_options)
            
            # Initialize resources based on tags
            food = random.uniform(40, 80)
            materials = random.uniform(30, 70)
            energy = random.uniform(40, 80)
            infrastructure = random.uniform(0.4, 0.8)
            
            region = Region(
                id=region_id,
                name=region_name,
                locations=[],
                tags=tags,
                food=food,
                materials=materials,
                energy=energy,
                infrastructure=infrastructure,
                tension=random.uniform(0.1, 0.3)
            )
            
            # Generate locations per region
            num_locations = random.randint(4, 8)
            location_types = ['residential', 'market', 'transit', 'industrial', 'civic', 'edge']
            
            for _ in range(num_locations):
                loc_type = random.choice(location_types)
                loc_name = f"{region_name} {random.choice(self.LOCATION_PARTS[loc_type])}"
                loc_id = f"loc_{location_id}"
                
                location = Location(
                    id=loc_id,
                    name=loc_name,
                    region_id=region_id,
                    type_tag=loc_type
                )
                
                region.locations.append(location)
                self.locations[loc_id] = location
                location_id += 1
            
            self.regions[region_id] = region
    
    def get_hotspots(self, top_n: int = 5) -> List[Tuple[Location, float]]:
        """
        Get locations with highest crowd density.
        
        Args:
            top_n: Number of hotspots to return
            
        Returns:
            List of (Location, density) tuples, sorted by density
        """
        locations_with_density = [
            (loc, loc.crowd_density)
            for loc in self.locations.values()
            if loc.crowd_density > 0.0
        ]
        locations_with_density.sort(key=lambda x: x[1], reverse=True)
        return locations_with_density[:top_n]
    
    def get_location(self, location_id: str) -> Optional[Location]:
        """Get location by ID."""
        return self.locations.get(location_id)
    
    def get_location_by_name(self, name: str) -> Optional[Location]:
        """Get location by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for loc in self.locations.values():
            if name_lower in loc.name.lower():
                return loc
        return None
    
    def get_region(self, region_id: str) -> Optional[Region]:
        """Get region by ID."""
        return self.regions.get(region_id)
    
    def update_crowd_density(self, location_id: str, density: float):
        """Update crowd density for a location."""
        if location_id in self.locations:
            self.locations[location_id].crowd_density = max(0.0, min(1.0, density))
    
    def get_region_by_location_id(self, location_id: str) -> Optional[Region]:
        """Get region that contains a location."""
        location = self.locations.get(location_id)
        if location:
            return self.regions.get(location.region_id)
        return None
    
    def update_region_resources(self, region_id: str, food_delta: float = 0.0,
                                materials_delta: float = 0.0, energy_delta: float = 0.0):
        """Update region resources (clamped to [0, 100])."""
        if region_id in self.regions:
            region = self.regions[region_id]
            region.food = max(0.0, min(100.0, region.food + food_delta))
            region.materials = max(0.0, min(100.0, region.materials + materials_delta))
            region.energy = max(0.0, min(100.0, region.energy + energy_delta))
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "seed": self.seed,
            "regions": {
                rid: {
                    "id": r.id,
                    "name": r.name,
                    "tags": r.tags if r.tags else [],
                    "food": r.food,
                    "materials": r.materials,
                    "energy": r.energy,
                    "infrastructure": r.infrastructure,
                    "tension": r.tension,
                    "locations": [
                        {
                            "id": loc.id,
                            "name": loc.name,
                            "region_id": loc.region_id,
                            "type_tag": loc.type_tag,
                            "crowd_density": loc.crowd_density
                        }
                        for loc in r.locations
                    ]
                }
                for rid, r in self.regions.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorldMap":
        """Deserialize from dictionary."""
        obj = cls(seed=data.get("seed", 42))
        obj.regions.clear()
        obj.locations.clear()
        
        for rid, rdata in data.get("regions", {}).items():
            region = Region(
                id=rdata["id"],
                name=rdata["name"],
                locations=[],
                tags=rdata.get("tags", []),
                food=rdata.get("food", 50.0),
                materials=rdata.get("materials", 50.0),
                energy=rdata.get("energy", 50.0),
                infrastructure=rdata.get("infrastructure", 0.5),
                tension=rdata.get("tension", 0.2)
            )
            for loc_data in rdata["locations"]:
                location = Location(
                    id=loc_data["id"],
                    name=loc_data["name"],
                    region_id=loc_data["region_id"],
                    type_tag=loc_data["type_tag"],
                    crowd_density=loc_data.get("crowd_density", 0.0)
                )
                region.locations.append(location)
                obj.locations[location.id] = location
            obj.regions[rid] = region
        
        return obj

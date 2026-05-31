"""
Map - Province and territory management system.
Handles the 8-bit grid-based map, provinces, terrain, and ownership.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import os


class TerrainType:
    PLAINS = "plains"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    OCEAN = "ocean"
    DESERT = "desert"
    URBAN = "urban"


# Terrain movement cost multipliers
TERRAIN_MOVEMENT_COST = {
    TerrainType.PLAINS: 1.0,
    TerrainType.FOREST: 1.5,
    TerrainType.MOUNTAIN: 2.5,
    TerrainType.OCEAN: 999.0,  # Impassable on land
    TerrainType.DESERT: 1.8,
    TerrainType.URBAN: 1.2,
}

# 8-bit color palette for terrain (RGB)
TERRAIN_COLORS = {
    TerrainType.PLAINS:   (120, 180, 80),
    TerrainType.FOREST:   (34,  100, 34),
    TerrainType.MOUNTAIN: (140, 120, 100),
    TerrainType.OCEAN:    (30,  80,  180),
    TerrainType.DESERT:   (210, 180, 80),
    TerrainType.URBAN:    (160, 150, 150),
}


@dataclass
class Province:
    """Represents a single province on the map."""
    id: int
    name: str
    x: int              # Top-left pixel x on the native 256x224 map
    y: int              # Top-left pixel y
    width: int = 8      # Province tile width
    height: int = 8     # Province tile height
    terrain: str = TerrainType.PLAINS
    owner_tag: str = ""
    controller_tag: str = ""  # May differ from owner during war
    is_capital: bool = False
    population: int = 1000
    manpower: int = 100
    industry: int = 1          # Factory slots
    resources: Dict[str, int] = field(default_factory=dict)
    neighbors: List[int] = field(default_factory=list)  # Neighbor province IDs

    @property
    def color(self) -> Tuple[int, int, int]:
        return TERRAIN_COLORS.get(self.terrain, (128, 128, 128))

    @property
    def rect(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)

    def contains_point(self, px: int, py: int) -> bool:
        return (self.x <= px < self.x + self.width and
                self.y <= py < self.y + self.height)


class GameMap:
    """Manages the game map, provinces, and adjacency."""

    MAP_WIDTH = 256
    MAP_HEIGHT = 168  # Bottom portion reserved for UI

    def __init__(self):
        self.provinces: Dict[int, Province] = {}
        self._pixel_to_province: Dict[Tuple[int, int], int] = {}

    def load_default(self):
        """Load the default 8-bit world map (simplified)."""
        data_path = os.path.join(os.path.dirname(__file__), 
                                  "..", "data", "provinces.json")
        if os.path.exists(data_path):
            self._load_from_json(data_path)
        else:
            self._generate_default_map()

    def _load_from_json(self, path: str):
        with open(path, "r") as f:
            data = json.load(f)
        for p_data in data["provinces"]:
            prov = Province(**p_data)
            self.provinces[prov.id] = prov
        self._build_pixel_index()

    def _generate_default_map(self):
        """Generate a simple procedural map for demonstration."""
        prov_id = 1
        tile_w, tile_h = 8, 8
        cols = self.MAP_WIDTH // tile_w
        rows = self.MAP_HEIGHT // tile_h

        country_grid = [
            # Simplified 8-country layout (each covers multiple tiles)
            ("GER", 12, 4, 8, 6),    # Germany: col 12, row 4, 8w 6h
            ("FRA", 8,  6, 6, 5),    # France
            ("ENG", 6,  2, 4, 3),    # UK
            ("SOV", 20, 2, 12, 10),  # Soviet Union
            ("ITA", 12, 8, 4, 5),    # Italy
            ("JAP", 26, 4, 6, 6),    # Japan
            ("USA", 1,  4, 7, 8),    # USA
            ("CHI", 22, 6, 5, 6),    # China
        ]

        # Build a country map for tiles
        country_map: Dict[Tuple[int,int], str] = {}
        for tag, sc, sr, w, h in country_grid:
            for r in range(sr, sr + h):
                for c in range(sc, sc + w):
                    country_map[(c, r)] = tag

        terrain_pattern = {
            (3, 2): TerrainType.MOUNTAIN,
            (4, 2): TerrainType.MOUNTAIN,
            (22, 3): TerrainType.MOUNTAIN,
            (13, 7): TerrainType.FOREST,
            (14, 7): TerrainType.FOREST,
        }

        for row in range(rows):
            for col in range(cols):
                # Ocean border
                if col < 1 or col >= cols - 1 or row < 1 or row >= rows - 1:
                    terrain = TerrainType.OCEAN
                    owner = ""
                else:
                    terrain = terrain_pattern.get((col, row), TerrainType.PLAINS)
                    owner = country_map.get((col, row), "")
                    if not owner:
                        terrain = TerrainType.OCEAN

                prov = Province(
                    id=prov_id,
                    name=f"Province {prov_id}",
                    x=col * tile_w,
                    y=row * tile_h,
                    width=tile_w,
                    height=tile_h,
                    terrain=terrain,
                    owner_tag=owner,
                    controller_tag=owner,
                    is_capital=(col == 15 and row == 5 and owner == "GER"),
                    population=max(100, 500 - abs(col - 15) * 10),
                    manpower=50,
                    industry=1 if owner else 0,
                    resources={"manpower": 100} if owner else {},
                )
                self.provinces[prov_id] = prov
                prov_id += 1

        self._build_neighbors()
        self._build_pixel_index()

    def _build_pixel_index(self):
        """Build a fast pixel -> province lookup."""
        self._pixel_to_province.clear()
        for prov_id, prov in self.provinces.items():
            for dy in range(prov.height):
                for dx in range(prov.width):
                    self._pixel_to_province[(prov.x + dx, prov.y + dy)] = prov_id

    def _build_neighbors(self):
        """Compute adjacency between provinces."""
        for prov in self.provinces.values():
            neighbors = set()
            # Check 4 cardinal neighbors (tile-based adjacency)
            for ox, oy in [(-prov.width, 0), (prov.width, 0),
                            (0, -prov.height), (0, prov.height)]:
                neighbor_px = prov.x + ox + prov.width // 2
                neighbor_py = prov.y + oy + prov.height // 2
                nid = self._pixel_to_province.get((neighbor_px, neighbor_py))
                if nid and nid != prov.id:
                    neighbors.add(nid)
            prov.neighbors = list(neighbors)

    def get_province_at(self, px: int, py: int) -> Optional[int]:
        """Return province ID at pixel coordinates, or None."""
        return self._pixel_to_province.get((px, py))

    def get_province(self, prov_id: int) -> Optional[Province]:
        return self.provinces.get(prov_id)

    def get_provinces_by_owner(self, tag: str) -> List[Province]:
        return [p for p in self.provinces.values() if p.owner_tag == tag]

    def transfer_province(self, prov_id: int, new_owner: str):
        """Transfer a province to a new owner."""
        if prov_id in self.provinces:
            self.provinces[prov_id].owner_tag = new_owner
            self.provinces[prov_id].controller_tag = new_owner

    def get_adjacent_enemy_provinces(self, tag: str, enemy_tags: List[str]) -> List[int]:
        """Get enemy provinces adjacent to any province owned by tag."""
        owned_ids = {p.id for p in self.get_provinces_by_owner(tag)}
        result = []
        for pid in owned_ids:
            prov = self.provinces[pid]
            for nid in prov.neighbors:
                neighbor = self.provinces.get(nid)
                if neighbor and neighbor.owner_tag in enemy_tags:
                    result.append(nid)
        return list(set(result))

    def shortest_path(self, start_id: int, end_id: int,
                      passable_tags: Optional[List[str]] = None) -> List[int]:
        """BFS pathfinding between provinces. Returns list of province IDs."""
        from collections import deque
        if start_id == end_id:
            return [start_id]
        visited = {start_id}
        queue = deque([[start_id]])
        while queue:
            path = queue.popleft()
            current = path[-1]
            prov = self.provinces.get(current)
            if not prov:
                continue
            for nid in prov.neighbors:
                if nid in visited:
                    continue
                neighbor = self.provinces.get(nid)
                if not neighbor:
                    continue
                if neighbor.terrain == TerrainType.OCEAN:
                    continue
                if passable_tags and neighbor.owner_tag not in passable_tags:
                    continue
                new_path = path + [nid]
                if nid == end_id:
                    return new_path
                visited.add(nid)
                queue.append(new_path)
        return []  # No path found

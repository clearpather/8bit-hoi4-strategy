"""
Country - Nation and faction management.
Handles country data, resources, politics, and faction/alliance management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json, os


class Ideology:
    DEMOCRATIC = "democratic"
    FASCIST = "fascist"
    COMMUNIST = "communist"
    NEUTRAL = "neutral"


# 8-bit country colors (RGB)
COUNTRY_COLORS: Dict[str, Tuple[int,int,int]] = {
    "GER": (80,  80,  180),   # Blue-grey
    "FRA": (60,  120, 60),    # Green
    "ENG": (180, 60,  60),    # Red
    "SOV": (200, 40,  40),    # Bright red
    "ITA": (200, 160, 40),    # Gold
    "JAP": (200, 80,  80),    # Red-pink
    "USA": (80,  120, 200),   # Blue
    "CHI": (180, 120, 40),    # Orange-brown
}

DEFAULT_COLOR = (128, 128, 128)


@dataclass
class Technology:
    """Represents a technology node."""
    id: str
    name: str
    cost: int
    prerequisites: List[str] = field(default_factory=list)
    bonuses: Dict[str, float] = field(default_factory=dict)
    researched: bool = False


@dataclass
class Country:
    """Represents a playable nation."""
    tag: str
    name: str
    ideology: str = Ideology.NEUTRAL
    color: Tuple[int,int,int] = (128,128,128)

    # Resources
    manpower: int = 1000
    factories: int = 5
    oil: int = 0
    steel: int = 10
    food: int = 50

    # Political stats (0-100)
    stability: int = 70
    war_support: int = 30
    political_power: int = 0

    # Military
    army_experience: int = 0
    navy_experience: int = 0

    # Research
    research_slots: int = 2
    technologies: Dict[str, Technology] = field(default_factory=dict)
    current_research: List[str] = field(default_factory=list)

    # Diplomacy
    at_war_with: List[str] = field(default_factory=list)
    allies: List[str] = field(default_factory=list)
    guarantees: List[str] = field(default_factory=list)
    non_aggression_pacts: List[str] = field(default_factory=list)

    # National focuses
    national_focus: Optional[str] = None
    focus_progress: int = 0
    focus_cost: int = 70  # days

    # Victory points
    victory_points: int = 0
    capital_province_id: int = 0

    @property
    def is_major(self) -> bool:
        return self.factories >= 20

    def can_afford_tech(self, tech_id: str) -> bool:
        tech = self.technologies.get(tech_id)
        if not tech or tech.researched:
            return False
        for prereq in tech.prerequisites:
            if prereq not in self.technologies or not self.technologies[prereq].researched:
                return False
        return True

    def start_research(self, tech_id: str) -> bool:
        if (len(self.current_research) < self.research_slots and
                self.can_afford_tech(tech_id)):
            self.current_research.append(tech_id)
            return True
        return False

    def add_resource(self, resource: str, amount: int):
        if resource == "manpower":
            self.manpower = max(0, self.manpower + amount)
        elif resource == "factories":
            self.factories = max(0, self.factories + amount)
        elif resource == "oil":
            self.oil = max(0, self.oil + amount)
        elif resource == "steel":
            self.steel = max(0, self.steel + amount)
        elif resource == "food":
            self.food = max(0, self.food + amount)

    def process_monthly(self):
        """Monthly update: resources, political power, research."""
        # Political power gain
        self.political_power = min(1000, self.political_power + 3)
        # Stability drift toward center
        if self.stability > 50:
            self.stability = max(50, self.stability - 1)
        # Resource production from factories
        self.steel += self.factories // 2
        self.food = min(1000, self.food + 10)

    def process_yearly(self):
        """Yearly update: population growth, manpower."""
        self.manpower = min(10000, self.manpower + 200)

    def get_color(self) -> Tuple[int,int,int]:
        return COUNTRY_COLORS.get(self.tag, DEFAULT_COLOR)


class CountryManager:
    """Manages all countries in the game."""

    def __init__(self):
        self.countries: Dict[str, Country] = {}

    def load_default_countries(self):
        data_path = os.path.join(os.path.dirname(__file__),
                                  "..", "data", "countries.json")
        if os.path.exists(data_path):
            self._load_from_json(data_path)
        else:
            self._generate_default_countries()

    def _load_from_json(self, path: str):
        with open(path, "r") as f:
            data = json.load(f)
        for c_data in data["countries"]:
            tech_dict = {}
            for t in c_data.pop("technologies", []):
                tech = Technology(**t)
                tech_dict[tech.id] = tech
            country = Country(**c_data)
            country.technologies = tech_dict
            self.countries[country.tag] = country

    def _generate_default_countries(self):
        """Create default 8 major powers."""
        defaults = [
            ("GER", "Germany",      Ideology.FASCIST,    1000, 30, 50),
            ("FRA", "France",       Ideology.DEMOCRATIC,  800, 25, 30),
            ("ENG", "UK",           Ideology.DEMOCRATIC,  900, 40, 10),
            ("SOV", "Soviet Union", Ideology.COMMUNIST,  1500, 20, 30),
            ("ITA", "Italy",        Ideology.FASCIST,     600, 20, 20),
            ("JAP", "Japan",        Ideology.FASCIST,     700, 18, 10),
            ("USA", "USA",          Ideology.DEMOCRATIC, 2000, 50,  0),
            ("CHI", "China",        Ideology.NEUTRAL,    1200,  5,  0),
        ]
        for tag, name, ideology, mp, fac, oil in defaults:
            country = Country(
                tag=tag, name=name, ideology=ideology,
                color=COUNTRY_COLORS.get(tag, DEFAULT_COLOR),
                manpower=mp, factories=fac, oil=oil,
                steel=fac * 2, food=100,
                stability=70 if ideology == Ideology.DEMOCRATIC else 60,
                war_support=30,
            )
            self._add_default_technologies(country)
            self.countries[tag] = country

    def _add_default_technologies(self, country: Country):
        """Add basic tech tree nodes to a country."""
        techs = [
            Technology("infantry_weapons_1", "Basic Infantry Weapons", 50,
                       bonuses={"infantry_attack": 0.1}),
            Technology("infantry_weapons_2", "Improved Infantry Weapons", 100,
                       prerequisites=["infantry_weapons_1"],
                       bonuses={"infantry_attack": 0.2}),
            Technology("artillery_1", "Field Artillery", 80,
                       bonuses={"artillery_attack": 0.15}),
            Technology("industry_1", "Basic Industry", 60,
                       bonuses={"factory_output": 0.1}),
            Technology("industry_2", "Industrial Revolution", 120,
                       prerequisites=["industry_1"],
                       bonuses={"factory_output": 0.25}),
            Technology("armor_1", "Basic Armor", 150,
                       bonuses={"armor_attack": 0.2}),
            Technology("radar_1", "Radar", 100,
                       bonuses={"air_detection": 0.3}),
        ]
        for tech in techs:
            country.technologies[tech.id] = tech

    def get_country(self, tag: str) -> Optional[Country]:
        return self.countries.get(tag)

    def process_monthly(self):
        for country in self.countries.values():
            country.process_monthly()

    def process_yearly(self):
        for country in self.countries.values():
            country.process_yearly()

    def check_victory(self) -> Optional[Country]:
        """Check if a country has achieved world domination."""
        total = len(self.countries)
        for country in self.countries.values():
            if country.victory_points >= total * 50:
                return country
        return None

    def get_all_tags(self) -> List[str]:
        return list(self.countries.keys())

    def declare_war(self, attacker_tag: str, defender_tag: str) -> bool:
        attacker = self.get_country(attacker_tag)
        defender = self.get_country(defender_tag)
        if not attacker or not defender:
            return False
        if defender_tag not in attacker.at_war_with:
            attacker.at_war_with.append(defender_tag)
        if attacker_tag not in defender.at_war_with:
            defender.at_war_with.append(attacker_tag)
        return True

    def make_peace(self, tag_a: str, tag_b: str):
        a = self.get_country(tag_a)
        b = self.get_country(tag_b)
        if a and tag_b in a.at_war_with:
            a.at_war_with.remove(tag_b)
        if b and tag_a in b.at_war_with:
            b.at_war_with.remove(tag_a)

    def are_at_war(self, tag_a: str, tag_b: str) -> bool:
        a = self.get_country(tag_a)
        return a is not None and tag_b in a.at_war_with

    def are_allied(self, tag_a: str, tag_b: str) -> bool:
        a = self.get_country(tag_a)
        return a is not None and tag_b in a.allies

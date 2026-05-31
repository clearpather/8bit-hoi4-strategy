"""
Game - Core game state and main game loop logic.
Manages the overall game state, turn processing, and coordinates all systems.
"""

from enum import Enum, auto
from typing import Optional
from .map import GameMap
from .country import Country, CountryManager
from .army import ArmyManager
from .diplomacy import DiplomacyManager
from .economy import EconomyManager
from .events import EventManager
from .ai import AIManager
from .save_load import SaveLoadManager


class GamePhase(Enum):
    MAIN_MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    DIPLOMACY = auto()
    ARMY_DEPLOY = auto()
    GAME_OVER = auto()


class GameSpeed(Enum):
    PAUSED = 0
    SLOW = 1
    NORMAL = 2
    FAST = 3
    ULTRA = 4


class Game:
    """Central game state manager."""

    # Seconds of game time per real second at each speed
    SPEED_MULTIPLIERS = {
        GameSpeed.PAUSED: 0,
        GameSpeed.SLOW: 1,
        GameSpeed.NORMAL: 3,
        GameSpeed.FAST: 7,
        GameSpeed.ULTRA: 15,
    }

    def __init__(self):
        self.phase: GamePhase = GamePhase.MAIN_MENU
        self.speed: GameSpeed = GameSpeed.NORMAL
        self.game_map: Optional[GameMap] = None
        self.country_manager: Optional[CountryManager] = None
        self.army_manager: Optional[ArmyManager] = None
        self.diplomacy_manager: Optional[DiplomacyManager] = None
        self.economy_manager: Optional[EconomyManager] = None
        self.event_manager: Optional[EventManager] = None
        self.ai_manager: Optional[AIManager] = None
        self.save_load: SaveLoadManager = SaveLoadManager()

        # Game time (in days, starting Jan 1 1936)
        self.day: int = 1
        self.month: int = 1
        self.year: int = 1936
        self._time_accumulator: float = 0.0

        # Player country tag
        self.player_tag: str = "GER"

        # UI state
        self.selected_province_id: Optional[int] = None
        self.selected_unit_id: Optional[int] = None
        self.camera_x: int = 0
        self.camera_y: int = 0
        self.ui_message: str = ""

    def new_game(self):
        """Initialize a fresh game."""
        self.game_map = GameMap()
        self.game_map.load_default()
        self.country_manager = CountryManager()
        self.country_manager.load_default_countries()
        self.army_manager = ArmyManager(self.game_map, self.country_manager)
        self.army_manager.spawn_default_armies()
        self.economy_manager = EconomyManager(self.country_manager)
        self.diplomacy_manager = DiplomacyManager(self.country_manager)
        self.event_manager = EventManager(self)
        self.ai_manager = AIManager(self)
        self.phase = GamePhase.PLAYING
        self.day = 1
        self.month = 1
        self.year = 1936
        self.player_tag = "GER"
        self.ui_message = "Welcome to 8-Bit Grand Strategy!"

    def update(self, dt: float):
        """Update game state each frame."""
        if self.phase != GamePhase.PLAYING:
            return
        if self.speed == GameSpeed.PAUSED:
            return

        mult = self.SPEED_MULTIPLIERS[self.speed]
        self._time_accumulator += dt * mult

        while self._time_accumulator >= 1.0:
            self._time_accumulator -= 1.0
            self._advance_day()

    def _advance_day(self):
        """Process one game day."""
        self.day += 1
        days_in_month = self._days_in_month(self.month, self.year)
        if self.day > days_in_month:
            self.day = 1
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year += 1
                self._process_yearly()
            self._process_monthly()
        self._process_daily()

    def _process_daily(self):
        """Daily processing: movement, combat."""
        if self.army_manager:
            self.army_manager.process_movement()
            self.army_manager.process_combat()
        if self.ai_manager:
            self.ai_manager.daily_update()
        if self.event_manager:
            self.event_manager.check_events()
        self._check_victory_conditions()

    def _process_monthly(self):
        """Monthly processing: manpower, resource income."""
        if self.economy_manager:
            self.economy_manager.process_monthly()
        if self.country_manager:
            self.country_manager.process_monthly()
        if self.diplomacy_manager:
            self.diplomacy_manager.process_monthly()

    def _process_yearly(self):
        """Yearly processing: technology, national decisions."""
        if self.country_manager:
            self.country_manager.process_yearly()

    def _days_in_month(self, month: int, year: int) -> int:
        leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        days = [0,31,28+leap,31,30,31,30,31,31,30,31,30,31]
        return days[month]

    def _check_victory_conditions(self):
        """Check if any country has won."""
        if not self.country_manager:
            return
        winner = self.country_manager.check_victory()
        if winner:
            self.phase = GamePhase.GAME_OVER
            self.ui_message = f"{winner.name} has conquered the world!"

    def handle_keydown(self, key: int, mod: int):
        """Handle keyboard input."""
        import pygame
        if key == pygame.K_SPACE:
            self._toggle_pause()
        elif key == pygame.K_1:
            self.speed = GameSpeed.SLOW
        elif key == pygame.K_2:
            self.speed = GameSpeed.NORMAL
        elif key == pygame.K_3:
            self.speed = GameSpeed.FAST
        elif key == pygame.K_4:
            self.speed = GameSpeed.ULTRA
        elif key == pygame.K_s and (mod & pygame.KMOD_CTRL):
            self.save_load.save(self, "quicksave")
            self.ui_message = "Game saved!"
        elif key == pygame.K_l and (mod & pygame.KMOD_CTRL):
            self.save_load.load(self, "quicksave")
            self.ui_message = "Game loaded!"
        # Camera movement
        elif key == pygame.K_LEFT or key == pygame.K_a:
            self.camera_x = max(0, self.camera_x - 8)
        elif key == pygame.K_RIGHT or key == pygame.K_d:
            self.camera_x += 8
        elif key == pygame.K_UP or key == pygame.K_w:
            self.camera_y = max(0, self.camera_y - 8)
        elif key == pygame.K_DOWN or key == pygame.K_s:
            self.camera_y += 8

    def _toggle_pause(self):
        if self.speed == GameSpeed.PAUSED:
            self.speed = GameSpeed.NORMAL
        else:
            self.speed = GameSpeed.PAUSED

    def handle_click(self, mx: int, my: int, button: int):
        """Handle mouse click at native resolution coordinates."""
        if self.phase not in (GamePhase.PLAYING, GamePhase.ARMY_DEPLOY):
            return
        # Convert screen coords to map coords
        map_x = mx + self.camera_x
        map_y = my + self.camera_y
        if self.game_map:
            prov_id = self.game_map.get_province_at(map_x, map_y)
            if prov_id is not None:
                self._handle_province_click(prov_id, button)

    def _handle_province_click(self, prov_id: int, button: int):
        """Handle clicking on a province."""
        if button == 1:  # Left click - select
            self.selected_province_id = prov_id
            prov = self.game_map.provinces.get(prov_id)
            if prov:
                self.ui_message = f"{prov.name} | Owner: {prov.owner_tag}"
        elif button == 3:  # Right click - order movement
            if self.selected_unit_id and self.army_manager:
                self.army_manager.order_move(self.selected_unit_id, prov_id)

    @property
    def date_string(self) -> str:
        months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
        return f"{self.day:02d} {months[self.month-1]} {self.year}"

    @property
    def player_country(self) -> Optional[Country]:
        if self.country_manager:
            return self.country_manager.get_country(self.player_tag)
        return None

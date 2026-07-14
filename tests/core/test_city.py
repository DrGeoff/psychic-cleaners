"""Tests for the city grid: buildings, haunt bookkeeping, distances."""

from psychic_cleaners.core.city import Building, City
from psychic_cleaners.core.constants import (
    BLOCK_LENGTH,
    DEPOT_POS,
    GRID_HEIGHT,
    GRID_WIDTH,
    TOWER_POS,
)


def test_new_city_has_58_buildings() -> None:
    city = City.new()
    assert len(city.buildings) == GRID_WIDTH * GRID_HEIGHT - 2 == 58
    assert city.wisps == []


def test_tower_and_depot_cells_are_empty() -> None:
    city = City.new()
    assert TOWER_POS not in city.buildings
    assert DEPOT_POS not in city.buildings


def test_buildings_know_their_positions_and_start_unhaunted() -> None:
    city = City.new()
    assert city.buildings[(0, 0)] == Building(pos=(0, 0), haunted=False)
    assert city.buildings[(9, 5)] == Building(pos=(9, 5), haunted=False)


def test_distance_is_manhattan_times_block_length() -> None:
    city = City.new()
    assert city.distance((0, 0), (3, 2)) == 5 * BLOCK_LENGTH
    assert city.distance((3, 2), (0, 0)) == 5 * BLOCK_LENGTH
    assert city.distance((4, 4), (4, 4)) == 0.0


def test_haunt_bookkeeping() -> None:
    city = City.new()
    assert city.active_haunts() == 0
    city.buildings[(2, 2)].haunted = True
    city.buildings[(7, 1)].haunted = True
    assert city.active_haunts() == 2
    assert set(city.haunted_positions()) == {(2, 2), (7, 1)}
    city.clear_haunt((2, 2))
    assert city.haunted_positions() == [(7, 1)]


def test_clear_haunt_is_idempotent_and_safe() -> None:
    city = City.new()
    city.clear_haunt((2, 2))  # never haunted: no error, no change
    city.clear_haunt((2, 2))
    city.clear_haunt(TOWER_POS)  # not even a building: still no error
    assert city.active_haunts() == 0


def test_stompable_positions_are_all_buildings() -> None:
    city = City.new()
    assert set(city.stompable_positions()) == set(city.buildings)
    assert len(city.stompable_positions()) == 58

"""Ecovacs mower entity."""

from __future__ import annotations

import logging

from deebot_client.capabilities import MowerCapabilities
from deebot_client.device import Device
from deebot_client.events import StateEvent
from deebot_client.models import CleanAction, State

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityEntityDescription,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .controller import EcovacsController
from .entity import EcovacsEntity

_LOGGER = logging.getLogger(__name__)


_STATE_TO_MOWER_STATE = {
    State.IDLE: LawnMowerActivity.PAUSED,
    State.CLEANING: LawnMowerActivity.MOWING,
    State.RETURNING: LawnMowerActivity.MOWING,
    State.DOCKED: LawnMowerActivity.DOCKED,
    State.ERROR: LawnMowerActivity.ERROR,
    State.PAUSED: LawnMowerActivity.PAUSED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ecovacs mowers."""
    mowers: list[EcovacsMower] = []
    controller: EcovacsController = hass.data[DOMAIN][config_entry.entry_id]
    for device in controller.devices(MowerCapabilities):
        mowers.append(EcovacsMower(device))
    _LOGGER.debug("Adding Ecovacs Mowers to Home Assistant: %s", mowers)
    async_add_entities(mowers)


class EcovacsMower(
    EcovacsEntity[MowerCapabilities, MowerCapabilities],
    LawnMowerEntity,
):
    """Ecovacs Mower."""

    _attr_supported_features = (
        LawnMowerEntityFeature.DOCK
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.START_MOWING
    )

    entity_description = LawnMowerEntityEntityDescription(
        key="mower", translation_key="mower", name=None
    )

    def __init__(self, device: Device[MowerCapabilities]) -> None:
        """Initialize the mower."""
        capabilities = device.capabilities
        super().__init__(device, capabilities)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_status(event: StateEvent) -> None:
            self._attr_activity = _STATE_TO_MOWER_STATE[event.state]
            self.async_write_ha_state()

        self._subscribe(self._capability.state.event, on_status)

    async def _clean_command(self, action: CleanAction) -> None:
        await self._device.execute_command(
            self._capability.clean.action.command(action)
        )

    async def async_start_mowing(self) -> None:
        """Resume schedule."""
        await self._clean_command(CleanAction.START)

    async def async_pause(self) -> None:
        """Pauses the mower."""
        await self._clean_command(CleanAction.PAUSE)

    async def async_dock(self) -> None:
        """Parks the mower until next schedule."""
        await self._device.execute_command(self._capability.charge.execute())

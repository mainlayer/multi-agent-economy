"""Base agent class providing Mainlayer payment infrastructure for all agents."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAINLAYER_BASE_URL = "https://api.mainlayer.xyz"


class MainlayerError(Exception):
    """Raised when a Mainlayer API call fails."""

    def __init__(self, message: str, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class BaseAgent:
    """
    Foundation class for all economy agents.

    Each agent has:
    - A unique name and wallet address on the Mainlayer network.
    - An authenticated httpx client pointed at the Mainlayer API.
    - Helper methods for registering services and paying for them.
    """

    def __init__(self, name: str, api_key: str, agent_wallet: str) -> None:
        """
        Args:
            name:          Human-readable agent name (e.g. "Researcher").
            api_key:       Mainlayer API key used for authentication.
            agent_wallet:  Mainlayer wallet address that receives / spends funds.
        """
        self.name = name
        self.agent_wallet = agent_wallet
        self._api_key = api_key

        self.client = httpx.AsyncClient(
            base_url=MAINLAYER_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

        # Populated after setup_service() is called.
        self.resource_id: str | None = None
        self.service_price: float | None = None

        logger.info("Agent '%s' initialised (wallet=%s)", self.name, self.agent_wallet)

    # ------------------------------------------------------------------
    # Service registration
    # ------------------------------------------------------------------

    async def setup_service(
        self,
        slug: str,
        price: float,
        description: str,
    ) -> dict:
        """
        Register this agent's service as a Mainlayer resource.

        Creates (or retrieves) a resource that other agents can pay for.

        Args:
            slug:        URL-safe identifier for the resource (e.g. "research-report").
            price:       Price in USD per access (e.g. 0.10).
            description: Human-readable description shown to buyers.

        Returns:
            The full resource object returned by the Mainlayer API.

        Raises:
            MainlayerError: If the API returns a non-2xx status.
        """
        payload = {
            "slug": slug,
            "price": price,
            "description": description,
            "wallet": self.agent_wallet,
            "agent": self.name,
        }

        logger.debug("'%s' registering resource slug='%s' price=$%.4f", self.name, slug, price)

        try:
            response = await self.client.post("/resources", json=payload)
        except httpx.RequestError as exc:
            raise MainlayerError(f"Network error while registering service: {exc}") from exc

        if response.status_code not in (200, 201):
            raise MainlayerError(
                f"Failed to register service '{slug}': HTTP {response.status_code}",
                status_code=response.status_code,
                details=response.text,
            )

        data: dict = response.json()
        self.resource_id = data.get("id") or data.get("resource_id")
        self.service_price = price

        logger.info(
            "'%s' service registered: resource_id=%s price=$%.4f",
            self.name,
            self.resource_id,
            price,
        )
        return data

    # ------------------------------------------------------------------
    # Payment
    # ------------------------------------------------------------------

    async def pay_for_service(self, resource_id: str) -> dict:
        """
        Pay for another agent's Mainlayer resource.

        Args:
            resource_id: The resource ID returned by the seller's setup_service().

        Returns:
            Payment receipt dict containing at minimum:
            ``{"payment_id": str, "status": str, "access_token": str}``.

        Raises:
            MainlayerError: If the API returns a non-2xx status.
        """
        payload = {
            "resource_id": resource_id,
            "buyer_wallet": self.agent_wallet,
        }

        logger.debug("'%s' paying for resource_id=%s", self.name, resource_id)

        try:
            response = await self.client.post("/payments", json=payload)
        except httpx.RequestError as exc:
            raise MainlayerError(f"Network error while paying for service: {exc}") from exc

        if response.status_code not in (200, 201):
            raise MainlayerError(
                f"Payment failed for resource '{resource_id}': HTTP {response.status_code}",
                status_code=response.status_code,
                details=response.text,
            )

        receipt: dict = response.json()
        logger.info(
            "'%s' payment confirmed: payment_id=%s status=%s",
            self.name,
            receipt.get("payment_id"),
            receipt.get("status"),
        )
        return receipt

    # ------------------------------------------------------------------
    # Access verification
    # ------------------------------------------------------------------

    async def check_access(self, resource_id: str) -> bool:
        """
        Verify that this agent currently has paid access to a resource.

        Args:
            resource_id: The resource ID to check.

        Returns:
            True if access is granted, False otherwise.
        """
        params = {"resource_id": resource_id, "wallet": self.agent_wallet}

        try:
            response = await self.client.get("/access", params=params)
        except httpx.RequestError as exc:
            logger.warning("'%s' access check network error: %s", self.name, exc)
            return False

        if response.status_code == 200:
            data: dict = response.json()
            granted: bool = data.get("access", False)
            logger.debug("'%s' access check resource_id=%s granted=%s", self.name, resource_id, granted)
            return granted

        logger.debug(
            "'%s' access check returned HTTP %s for resource_id=%s",
            self.name,
            response.status_code,
            resource_id,
        )
        return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client. Call when the agent shuts down."""
        await self.client.aclose()

    async def __aenter__(self) -> "BaseAgent":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"wallet={self.agent_wallet!r}, "
            f"resource_id={self.resource_id!r})"
        )

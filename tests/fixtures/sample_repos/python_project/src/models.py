"""Data models for Python project."""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class User:
    """User model."""

    id: int
    name: str
    email: str
    created_at: datetime = field(default_factory=datetime.now)
    orders: List["Order"] = field(default_factory=list)

    def add_order(self, order: "Order") -> None:
        """Add an order to user."""
        self.orders.append(order)
        order.user_id = self.id

    def get_order_count(self) -> int:
        """Get total number of orders."""
        return len(self.orders)


@dataclass
class Order:
    """Order model."""

    id: int
    user_id: Optional[int] = None
    items: List[Dict[str, Any]] = field(default_factory=list)
    total: float = 0.0
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)

    def calculate_total(self) -> float:
        """Calculate order total."""
        self.total = sum(
            item.get("price", 0) * item.get("quantity", 1) for item in self.items
        )
        return self.total

    def update_status(self, status: str) -> None:
        """Update order status."""
        valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
        if status in valid_statuses:
            self.status = status


@dataclass
class Product:
    """Product model."""

    id: int
    name: str
    description: str
    price: float
    stock: int = 0

    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        return self.stock > 0

    def reduce_stock(self, quantity: int) -> bool:
        """Reduce stock by quantity."""
        if self.stock >= quantity:
            self.stock -= quantity
            return True
        return False

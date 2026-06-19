class DKPBotError(Exception):
    """Базовое исключение бота."""
    pass


class InsufficientDKPError(DKPBotError):
    def __init__(self, need: int, have: int):
        self.need = need
        self.have = have
        super().__init__(f"Недостаточно DKP: нужно {need}, есть {have}")


class AuctionAlreadyActiveError(DKPBotError):
    def __init__(self, item_name: str):
        self.item_name = item_name
        super().__init__(f"Уже идёт аукцион: «{item_name}»")


class NoActiveAuctionError(DKPBotError):
    def __init__(self):
        super().__init__("Нет активного аукциона")


class InvalidBidError(DKPBotError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)

class Response:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if not (200 <= self.status_code < 400):
            raise RuntimeError(f"HTTP error: {self.status_code}")

class AsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        return Response()

__all__ = ["AsyncClient", "Response"]

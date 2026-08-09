import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from python.local_install import resolve_stock_client


class StockDiscoveryTests(unittest.TestCase):
    def test_direct_python_prefers_read_only_stock_before_local_client(self) -> None:
        with tempfile.TemporaryDirectory() as root, patch.dict(
            os.environ, {"JFTSE_STOCK_CLIENT": ""}, clear=False
        ):
            jftse = Path(root)
            stock = jftse / ".jftse-client-linux" / "client"
            local = jftse / "FantaTennis-Local-Client" / "client"
            stock.mkdir(parents=True)
            local.mkdir(parents=True)

            self.assertEqual(resolve_stock_client(jftse), stock.resolve())


if __name__ == "__main__":
    unittest.main()

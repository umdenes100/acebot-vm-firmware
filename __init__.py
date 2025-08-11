# Expose the singleton instance with the legacy import name
from .client import Enes100

# Global instance to match student usage: from Enes100 import enes100
enes100 = Enes100()

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
import pytest

from turan.core import ImageData


@pytest.fixture
def picture():
    stream = io.BytesIO()
    Image.new("RGB", (24, 24), "#c02050").save(stream, "PNG")
    return ImageData(stream.getvalue(), "fixture.png", "image/png")

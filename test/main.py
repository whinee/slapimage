from PIL import Image
from whinesnips.utils.utils import fn

from slapimage.draw import Draw

tpl = Image.open(fn("../assets/images/test-tpl.png"))
draw = Draw(tpl)
draw.text(
    type_coords_tuple=("xyxy", 25, 25, 475, 75),
    text="left ascender inverted gpq",
    font="InterTight",
    fill="black",
    anchor="la",
    inverted=True,
    max_font_size=30,
)
draw.text(
    type_coords_tuple=("xyxy", 25, 80, 475, 130),
    text="middle middle inverted gpq",
    font="InterTight",
    fill="black",
    anchor="mm",
    inverted=True,
    max_font_size=30,
)
draw.text(
    type_coords_tuple=("xyxy", 25, 135, 475, 185),
    text="right descender inverted bdlt",
    font="InterTight",
    fill="black",
    anchor="rd",
    inverted=True,
    max_font_size=30,
)
draw.text(
    type_coords_tuple=("xyxy", 25, 190, 475, 475),
    text="""Dance to your heart's desire in tune to this waltz of malice, lest those who don't shall be damned!
Drown in grandeur and pleasure, for those who don't are misers!""",
    font="InterTight",
    fill="black",
    anchor="mmm",
    line_height=1.5,
    # inverted=True,
    max_font_size=30,
)
tpl.save(fn("test-op.png"))

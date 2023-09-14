from collections.abc import Callable
from os import path
from textwrap import wrap
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont
from whinesnips.utils.utils import half_round


def ttf(
    font: str,
    size: int = 10,
) -> FreeTypeFont:
    return ImageFont.truetype(path.join("assets/fonts", font) + ".ttf", size)


def font_size_fn(
    draw: ImageDraw,
    font: str,
    xy: tuple[int, int],
    **kwargs: dict[str, Any],
) -> Callable[..., list[int]]:
    def inner(size: int, text: str) -> list[int]:
        x1, y1, x2, y2 = draw.multiline_textbbox(
            xy=xy,
            text=text,
            font=ttf(font, size),
            **kwargs,
        )
        return [x2 - x1, y2 - y1]

    return inner


def xywh2xyxy(
    anchor: str | tuple[str, str],
    x: int,
    y: int,
    w: int,
    h: int,
) -> list[int]:
    """
    Considering the given text anchor, convert [x, y, w, h] to [x1, y1, x2, y2].

    | `x-anchor` |    `x1` |    `x2` |
    |-----------:|--------:|--------:|
    | l (left)   |       x |   x + w |
    | m (middle) | x - w/2 | x + w/2 |
    | r (right)  |   x - w |       x |

    |           `y-anchor` |    `y1` |    `y2` |
    |---------------------:|--------:|--------:|
    | a (ascender/top)     |       y |   y + h |
    | m (middle)           | y - h/2 | y + h/2 |
    | d (descender/bottom) |   y - h |       y |

    Args:
    - anchor (`str`): text anchor
    - x (`int`): text's x-coordinate
    - y (`int`): text's y-coordinate
    - w (`int`): text's width
    - h (`int`): text's height

    Returns:
    `list[int]`: [x1, y1, x2, y2]
    """

    xa: str
    ya: str
    xa, ya = anchor  # type: ignore[misc]

    match xa:
        case "l":
            x1, x2 = x, x + w
        case "m":
            x1, x2 = x - half_round(w), x + half_round(w)
        case "r":
            x1, x2 = x - w, x

    match ya:
        case "a":
            y1, y2 = y, y + h
        case "m":
            y1, y2 = y - half_round(h), y + half_round(h)
        case "d":
            y1, y2 = y - h, y

    return [x1, y1, x2, y2]


def xyxy2xywh(
    anchor: str | tuple[str, str],
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> list[int]:
    """
    Considering the given text anchor, convert [x1, y1, x2, y2] to [x, y, w, h] (text with x, y coordinate and dimensions of w, h).

    | `x-anchor` |           `x` |     `w` |
    |-----------:|--------------:|--------:|
    | l (left)   |            x1 | x2 - x1 |
    | m (middle) | (x1 + x2) / 2 | x2 - x1 |
    | r (right)  |            x2 | x2 - x1 |

    |           `y-anchor` |           `y` |     `h` |
    |---------------------:|--------------:|--------:|
    | a (ascender/top)     |            y1 | y2 - y1 |
    | m (middle)           | (y1 + y2) / 2 | y2 - y1 |
    | d (descender/bottom) |            y2 | y2 - y1 |

    Args:
    - anchor (`str`): text anchor
    - x1 (`int`): text's x-coordinate of left edge
    - y1 (`int`): text's y-coordinate of top edge
    - x2 (`int`): text's x-coordinate of right edge
    - y2 (`int`): text's y-coordinate of bottom edge

    Returns:
    `list[int]`: [x, y, w, h]
    """

    xa: str
    ya: str
    xa, ya = anchor  # type: ignore[misc]

    match xa:
        case "l":
            x = x1
        case "m":
            x = round((x1 + x2) * 0.5)
        case "r":
            x = x2

    match ya:
        case "a":
            y = y1
        case "m":
            y = round((y1 + y2) * 0.5)
        case "d":
            y = y2

    return [x, y, x2 - x1, y2 - y1]


class Draw:
    def __init__(self, img: Image) -> None:
        self.img = img
        self.draw = ImageDraw.Draw(img)

    def text(
        self,
        type_coords_tuple: tuple[str, int, int, int, int],
        text: str,
        anchor: str,
        font: str,
        max_font_size: float | int = 100,
        breaktext: Optional[bool] = None,
        line_height: float | int = 1,
        inverted: bool = False,
        **kwargs: Any,
    ) -> None:
        if breaktext is None:
            breaktext = False

        if not text:
            return

        xa: str
        ya: str
        mlva_ls: list[str]

        text = str(text).strip()
        coords_type, *coords = type_coords_tuple
        xa, ya, *mlva_ls = anchor  # type: ignore[misc] # multi line vertical anchor list
        slas: str = xa + ya  # type: ignore[misc] # single line anchor set

        if len(mlva_ls) > 1:
            raise Exception(
                "Anchor for multiline text should not exceed three characters.",
            )

        if coords_type == "xyxy":
            # left-most x-coordinate, highest y-coordinate, right-most x-coordinate, lowest y-coordinate
            x1, y1, x2, y2 = coords
            # field starting x-coordinate, field starting y-coordinate, field width, field height
            fx, fy, fw, fh = xyxy2xywh(slas, x1, y1, x2, y2)
        elif coords_type == "xywh":
            fx, fy, fw, fh = coords
            x1, y1, x2, y2 = xywh2xyxy(slas, fx, fy, fw, fh)

        tfs = font_size_fn(
            self.draw,
            font,
            (fx, fy),
        )  # true font size # type: ignore[arg-type]

        text_sls: str | list[str] = text  # text: string or list

        max_font_size = int(max_font_size)
        if ("\n" in text) or breaktext:
            if len(mlva_ls) == 0:
                mlva = "m"
            else:
                mlva = mlva_ls[0]
            while True:
                tw = 0
                tw_ls = []
                th_ls = []

                tt = text.splitlines()
                for i in tt:
                    tw += tfs(max_font_size, i)[0]
                ml = max(len(i) for i in tt)
                cpfw = round(fw / (tfs(max_font_size, text)[0] / ml))

                tt = [j for i in tt for j in wrap(i, cpfw)]
                ltt = len(tt)

                for i in tt:
                    twi, thi = tfs(max_font_size, i)
                    tw_ls.append(twi)
                    th_ls.append(thi)

                tw = max(tw_ls)
                th = round(ltt * line_height * (sum(th_ls) / ltt))
                if (tw > fw) or (th > fh):
                    max_font_size -= 1
                else:
                    text_sls = tt
                    break
        else:
            if len(mlva_ls) > 0:
                raise Exception(
                    "Anchor for single line text should not exceed two characters.",
                )
            tw, th = tfs(max_font_size, text)
            if (tw > fw) or (th > fh):
                while True:
                    max_font_size -= 1
                    tw, th = tfs(max_font_size, text)
                    if (tw <= fw) and (th <= fh):
                        break

        if inverted:
            hth = round(th / 2)  # halved text height
            lhth = th - hth  # large half of the text height
            fh += th
            it = Image.new("RGBA", (fw, fh), color=(0, 0, 0, 0))
            itd = ImageDraw.Draw(it)

            match xa:
                case "l":
                    slas = "r" + ya
                    fx = fw
                case "m":
                    fx = round(fw / 2)
                case "r":
                    slas = "l" + ya
                    fx = 0

            match ya:
                case "a":
                    fy = fh - th - lhth
                case "m":
                    fy: int = round(fh / 2)  # type: ignore[no-redef]
                case "d":
                    fy = th + lhth
        else:
            itd = self.draw

        t_kwargs = {
            "anchor": slas,
            "fill": kwargs.pop("fill"),
            "font": ttf(font=font, size=max_font_size),  # type: ignore[arg-type, misc]
            **kwargs,
        }

        if isinstance(text_sls, list):
            tholtt = th / ltt

            match mlva:
                case "a":
                    va: float = fh - th if inverted else y1  # vertical additive
                case "m":
                    va = (fh - th) / 2 if inverted else y1 + ((fh - th) / 2)
                case "d":
                    va = 0 if inverted else y1 + fh - th

            for t, ty in zip(
                text_sls,
                range(round(tholtt / 2), th, round(tholtt)),
                strict=True,
            ):
                itd.text(text=t, xy=(fx, va + ty), **t_kwargs)
        else:
            itd.text(text=text_sls, xy=(fx, fy), **t_kwargs)

        if inverted:
            it = it.rotate(180)
            self.img.paste(it, (x1, y1 - lhth, x2, y2 + hth), it)

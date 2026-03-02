import logging
from typing import List

from withoutbg import WithoutBG
from rembg import remove, new_session
from PIL import Image

logger = logging.getLogger(__name__)


def remove_background(input_images: List[Image.Image]) -> List[Image.Image]:
    model = WithoutBG.opensource()
    result = model.remove_background_batch(input_images)
    return result

def remove_background_v2(input_image: Image.Image) -> Image.Image:
    output = remove(input_image)
    return output

def remove_background_v2_batch(input_images: List[Image.Image]) -> List[Image.Image]:
    session = new_session()
    output = []
    for img in input_images:
        trans_img = remove(img, session=session)
        output.append(trans_img)
    return output

if __name__ == "__main__":
    img = Image.open("services/character_image.png")
    result = remove_background_v2(img)
    result.save("services/character_image_trans1.png")
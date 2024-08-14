from PIL import Image, ImageDraw, ImageFont
import os
import torch
import numpy as np


class AddText:
    """
    在图像上添加文字的节点
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        # 获取字体目录和所有字体文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(script_dir, "fonts")
        available_fonts = ["Custom"] + \
                          [f[:-4] for f in os.listdir(font_dir) if
                           f.endswith(".ttf") | f.endswith(".TTF") | f.endswith(".ttc")]
        available_fonts = list(set(available_fonts))  # 去重

        return {
            "required": {
                "image": ("IMAGE",),
                "text": ("STRING", {"multiline": True, "default": "A cute puppy"}),
                "x": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 1, "display": "number"}),
                "y": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 1, "display": "number"}),
                "font_size": ("INT", {"default": 38, "min": 0, "max": 100, "step": 1, "display": "number"}),
                "font_family": (available_fonts,),
                "font_color": ("STRING", {"multiline": False, "default": "#ffffff"}),
                "font_shadow_x": ("INT", {"default": 0, "min": 0, "max": 20, "step": 1, "display": "number"}),
                "font_shadow_y": ("INT", {"default": 0, "min": 0, "max": 20, "step": 1, "display": "number"}),
                "shadow_color": ("STRING", {"multiline": False, "default": "#000000"}),
            },
            "optional": {
                "custom_font_path": ("STRING", {"multiline": False, "default": "",
                                                "visible_if": {"font_family": "Custom"}}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "add_text"
    CATEGORY = "AI_Boy"

    def add_text(self, image, text, x, y, font_size, font_family, font_color, font_shadow_x, font_shadow_y,
                 shadow_color, custom_font_path=None):
        """
        在图像上添加文字
        """

        # 获取原始图像的维度信息
        orig_shape = image.shape

        # 调整维度顺序
        image = image.permute(0, 3, 1, 2)

        # 设置字体
        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(script_dir, "fonts")

        # 解析字体路径
        font_path = parse_font_path(font_family, custom_font_path, font_dir);
        font = ImageFont.truetype(font_path, font_size)

        # 解析颜色值
        font_color = parse_font_color(font_color);
        shadow_color = parse_font_color(shadow_color);

        # 将 Tensor 转换为 PIL Image
        images = []
        for i in range(image.shape[0]):
            img = torch.clamp(image[i], min=0., max=1.)
            img = (img * 255).cpu().numpy().astype(np.uint8)
            img = Image.fromarray(img.transpose(1, 2, 0)).convert("RGB")
            images.append(img)

        processed_images = []
        for img in images:
            # 获取图像的宽度和高度
            image_width, image_height = img.size
            # 检查 x, y 是否超出范围，如果超出则限制在图像范围内
            x = max(0, min(x, image_width - 1))
            y = max(0, min(y, image_height - 1))

            # 获取文字的宽度和高度
            text_width, text_height = font.getmask(text).size

            # 如果 x, y 没有设置，则默认文字在图片正下方居中
            if x == 0 and y == 0:
                # 计算文字的 x 坐标，使其水平居中
                x = (image_width - text_width) // 2
                # 计算文字的 y 坐标，使其位于图像正下方
                y = image_height - 50  # 添加 50 个像素的间距

            # 创建绘图对象
            draw = ImageDraw.Draw(img)

            # 添加文字阴影
            if font_shadow_x > 0 and font_shadow_y > 0:
                draw.text((x + font_shadow_x, y + font_shadow_y), text, font=font, fill=shadow_color)
            # 添加文字
            draw.text((x, y), text, font=font, fill=font_color)

            processed_images.append(img)

        # 将 PIL Image 转换回 Tensor
        processed_images = [np.array(img).astype(np.float32) / 255.0 for img in processed_images]
        image = torch.from_numpy(np.stack(processed_images, axis=0))

        # 恢复原始图像的维度顺序
        image = image.reshape(orig_shape)
        return (image,)


NODE_CLASS_MAPPINGS = {
    "AddText": AddText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AddText": "AddTextToImage",
}


# 解析颜色值
def parse_font_color(font_color):
    if font_color.startswith("#"):
        font_color = font_color.lstrip('#')
        try:
            font_color = tuple(int(font_color[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            raise ValueError("无效的十六进制颜色值: {}".format(font_color))
    else:
        try:
            font_color = tuple(map(int, font_color.split(',')))
            if len(font_color) != 3:
                raise ValueError("RGB 颜色值必须包含三个整数")
        except ValueError:
            raise ValueError("无效的 RGB 颜色值: {}".format(font_color))
    return font_color


# 解析字体路径
def parse_font_path(font_family, custom_font_path, font_dir):
    if font_family == "Custom":
        if not os.path.exists(custom_font_path):
            raise ValueError(f"自定义字体路径不存在: {custom_font_path}")
        font_path = custom_font_path
    else:
        font_path = os.path.join(font_dir, f"{font_family}.ttf")
        if not os.path.exists(font_path):
            font_path = os.path.join(font_dir, f"{font_family}.TTF")
        # 如果 .ttf 文件不存在，则尝试 .ttc 文件
        if not os.path.exists(font_path):
            font_path = os.path.join(font_dir, f"{font_family}.ttc")
        if not os.path.exists(font_path):
            font_path = os.path.join(font_dir, f"{font_family}.TTC")
    # 检查字体文件是否存在
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"字体文件未找到: {font_path}")
    return font_path

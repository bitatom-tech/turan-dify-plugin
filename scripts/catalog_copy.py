"""Curated English UI translations and bilingual product descriptions.

Only presentation text belongs here. API values, defaults and bindings stay intact.
"""
import re

GROUPS = {
    "设计素材": "Design Materials", "模特工具": "Model Tools",
    "场景创意": "Scene Creativity", "图案工具": "Pattern Tools", "视频类": "Video",
}

# code: English title, English description, Chinese description
PRODUCTS = {
    "white_background": ("Background Removal", "Remove backgrounds from product or portrait images to create clean assets for e-commerce and design layouts.", "去除商品或人物图片背景，快速制作适合电商展示与设计排版的干净素材。"),
    "product_selling_show": ("Product Highlights Grid", "Turn product images and selling points into a four-panel presentation for product listings and promotions.", "结合产品图片与卖点，生成四宫格展示图，让商品特色与使用场景更直观。"),
    "real_to_line_art": ("Product to Line Art", "Convert product photos into line drawings for design exploration and visual references.", "将实物照片转为线稿，便于款式分析、设计沟通与创意延展。"),
    "line_to_tile_img": ("Sketch to Product", "Visualize a product sketch with fabric and material references to explore its finished appearance.", "结合线稿、面料与材质参考，生成产品实物效果图，直观预览设计方案。"),
    "line_to_model_img": ("Sketch to Model Image", "Turn garment sketches into styled model images to preview how a design looks when worn.", "将服装线稿转为模特穿搭效果图，提前预览款式的上身表现。"),
    "hot_item_modify": ("Product Design Variations", "Create new design variations from an existing product using reference elements and creative instructions.", "以现有款式为基础，结合目标元素与创作要求，探索新的产品设计方向。"),
    "change_color": ("Garment Recoloring", "Recolor garments using a hex color or a color reference image. Provide exactly one color source.", "通过目标颜色值或颜色参考图调整服装配色，快速预览不同色款。颜色值与参考图二选一。"),
    "product_selling_analyze": ("Product Selling Point Analysis", "Analyze product images with audience and brand positioning to develop selling-point ideas.", "结合产品图片、适用人群与品牌定位，分析商品特色，辅助提炼营销卖点。"),
    "product_point_four": ("Product Detail Images", "Create product detail images that showcase fabric, construction and distinctive features.", "生成突出面料、工艺与设计亮点的产品细节图，丰富商品展示内容。"),
    "free_model_img": ("Custom Model Styling", "Create model styling images from product references and your choice of model, scene and outfit instructions.", "结合产品参考与模特、场景和穿搭要求，创作符合品牌风格的模特展示图。"),
    "change_face": ("Model Face Swap", "Replace a model's face using a reference image and customize hair, expression and accessories.", "依据人脸参考替换模特面容，并结合发型、表情与配饰要求调整人物形象。"),
    "change_clothes": ("Model Outfit Change", "Dress a model in a target garment or accessory using product references and fit instructions.", "将目标服装或配饰呈现在模特身上，结合穿戴要求制作商品上身效果图。"),
    "digital_human": ("AI Virtual Model", "Create virtual model images with your preferred age, ethnicity and presentation style.", "根据年龄、人种与展示要求生成虚拟模特形象，丰富服装与商品展示素材。"),
    "change_pose": ("Model Pose Change", "Adjust a model's pose using a reference pose and additional styling instructions.", "参考目标姿势调整模特动作，为同一套穿搭扩展不同展示角度。"),
    "model_split_buyer": ("Model Lifestyle Images", "Create lifestyle-style model images from product references for natural, everyday presentations.", "结合产品参考生成生活化的模特买家秀，呈现自然的日常穿搭效果。"),
    "series_img_split": ("Image Series Variations", "Expand a source image into a coordinated series with guided variations in pose, scene and styling.", "以原图为基础，结合姿势、场景与造型要求衍生系列图片，扩充成套展示素材。"),
    "model_commute": ("Product Styling in Scenes", "Show products on models in selected scenes to explore outfits and usage contexts.", "将产品融入指定场景与模特穿搭，展示不同风格和使用情境下的上身效果。"),
    "model_changing_underware": ("Model Underwear Change", "Create underwear presentation images using garment and model references with fit instructions.", "结合内衣产品图、模特参考与穿戴要求，生成内衣上身展示图。"),
    "poster_transfer": ("Reference Poster Transfer", "Create promotional visuals by adapting a reference poster's style to your product or model.", "参考海报风格，结合目标商品或人物生成宣传视觉图，快速延展品牌创意。"),
    "sports_transfer": ("Sports Scene Images", "Place products or models into sports-inspired scenes using visual references and presentation instructions.", "结合运动场景参考与展示要求，为商品或模特创作富有动感的场景图片。"),
    "auto_styling": ("Outfit Styling", "Explore outfit combinations from product and model references with your styling preferences.", "结合产品、模特参考与搭配偏好，探索多样化的服装穿搭方案。"),
    "showcase_style": ("Style Recreation", "Recreate a reference image's visual style for your product using detail images and creative instructions.", "参考目标图片的视觉风格，结合商品细节与创作要求，生成风格统一的展示图。"),
    "brand_main_img": ("Brand Campaign Images", "Create brand campaign visuals from product references, scene ideas and model requirements.", "结合产品参考、场景创意与模特要求，制作适合品牌传播的宣传主图。"),
    "onekey_buyer_show": ("Product Lifestyle Images", "Create lifestyle product images with your preferred models and scenes for everyday usage presentations.", "根据产品、模特与场景要求生成买家秀图片，呈现商品在日常生活中的使用效果。"),
    "flat_3d": ("Flat Lay to 3D", "Transform flat-lay product photos into images with a more dimensional presentation and adjustable viewing angle.", "将产品平铺图转为更具立体感的展示图，并按需调整展示角度与呈现效果。"),
    "partial_ai": ("Local Image Editing", "Edit specific image details using a source image, target elements and written instructions.", "结合原图、目标元素与文字要求编辑图片局部，灵活调整指定内容的细节。"),
    "seamless_pattern_extract": ("Seamless Fabric Pattern", "Extract fabric patterns into repeatable tiles for textile design and pattern exploration.", "从面料图片中提取可连续拼接的图案，为纺织设计与花型开发提供素材。"),
    "pattern_extract": ("Garment Pattern Extraction", "Extract printed motifs from garment images for pattern references and further design work.", "从服装图片中提取印花图案，便于整理图案素材与开展后续设计。"),
    "partial_ai_2": ("Local Image Editing V2", "Refine specific image content using a source image, reference images and written instructions.", "结合原图、参考图片与文字要求，对指定内容进行局部重绘，完成有针对性的创意调整。"),
    "common_product": ("Product Video Generation", "Turn product images into video with motion instructions, duration and aspect-ratio controls.", "将产品图片转为动态展示视频，结合动作描述、时长与比例要求，制作商品宣传素材。"),
}

LABELS = dict(pair.split("|", 1) for pair in """
需改色原始图|Source Image for Recoloring
原海报图|Original Poster Image
目标颜色图|Target Color Reference
原图|Source Image
参考图|Reference Image
处理要求|Processing Instructions
尺寸比例|Aspect Ratio
服装穿戴要求|Outfit Instructions
提示词|Prompt
产品主颜色图|Product Color Reference
产品&模特图|Product and Model Images
场景说明|Scene Description
模特要求|Model Requirements
适用年龄段|Target Age Group
品牌价格定位|Brand Price Positioning
用户提示词|Custom Prompt
人脸参考图|Face Reference Image
被换脸模特及其他图|Target Model and Other Images
头部配饰|Head Accessories
脸部角度、表情和眼神方向|Face Angle, Expression and Gaze
发型参考|Hairstyle Reference
原模特图|Original Model Image
目标姿势图|Target Pose Image
去除元素|Elements to Remove
人物姿势和眼神方向|Pose and Gaze
产品主图|Main Product Image
补充图|Additional Reference Image
生成视频秒数|Video Duration (seconds)
生成视频比例|Video Aspect Ratio
参考模特|Reference Model
年龄|Age
人种|Ethnicity
展示角度和优化幅度|View Angle and Adjustment Level
原产品图|Original Product Image
目标图|Target Image
服装穿戴形态参考|Outfit Fit Reference
原款式图|Original Design Image
目标元素图|Target Element Image
去除|Remove
强制保留|Must Keep
衍生方向|Variation Direction
线稿图|Sketch Image
面料描述|Fabric Description
材质&辅料图|Fabric and Trim Images
产品图|Product Image
遮罩图|Mask Image
内衣图|Underwear Image
模特图|Model Image
模特年龄段|Model Age Group
模特人种|Model Ethnicity
场景|Scene
目标场景图|Target Scene Image
指定场景描述|Specific Scene Description
场景要求|Scene Requirements
模特特征|Model Characteristics
模特数量|Number of Models
含图案原图|Pattern Source Image
产品原图|Original Product Image
细节图|Detail Image
面料名称|Fabric Name
参考图/细节和局部图|Reference and Close-up Images
原户外海报/运动场景图|Original Outdoor Poster or Sports Scene
目标物的展示形式、角度和呈现形态|Product Display, Angle and Presentation
裂变原图|Source Image for Variations
细节&平铺图|Detail and Flat-lay Images
按原图模特展示范围限定展示|Match the Original Model Framing
服装的长度和廓形|Garment Length and Silhouette
原始图|Original Image
细节&背景图|Detail and Background Images
背景色|Background Color
展示风格|Presentation Style
去除部位|Parts to Remove
普通图|Standard Image
高清图|HD Image
视频|Video
auto|Automatic
""".strip().splitlines())


def english_label(text):
    if text in LABELS:
        return LABELS[text]
    for pattern, replacement in [(r"参考图(\d+)", "Reference Image {}"), (r"图(\d+)", "Image {}"), (r"提示词(\d+)", "Prompt {}"), (r"(\d+)秒", "{} seconds")]:
        match = re.fullmatch(pattern, text)
        if match:
            return replacement.format(match[1])
    if re.search(r"[\u3400-\u9fff]", text):
        raise ValueError("Missing English label: " + text)
    return text


def field_help(field):
    """Explain the input without exposing backend implementation or example prompts."""
    if field["type"] == "file":
        return "Upload an image for " + english_label(field["label"]).lower() + ". Supports PNG, JPEG and WebP, up to 20 MiB."
    if field["name"] == "duration_seconds":
        return "Choose 6, 10, 15, 20, 25 or 30 seconds. Reference price: 6 Turan coins per second; final pricing is confirmed at submission."
    if field["name"] == "aspect_ratio":
        return "Set the output aspect ratio, such as 1:1 or 16:9. Use auto for automatic sizing."
    if field["kind"] == "color":
        return "Enter a color in #RRGGBB format, such as #8e2929."
    if field["type"] == "select":
        return "Choose an available option for " + english_label(field["label"]).lower() + "."
    return "Describe your preferences for " + english_label(field["label"]).lower() + ". Keep the default or customize it to suit your project."

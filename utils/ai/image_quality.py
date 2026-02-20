import sys
import json

def analyze_image_quality(images_data):
    """
    Analyze image quality based on metadata.
    Since we can't run PIL in this context, we analyze what Cloudinary provides:
    - Image count, dimensions, file sizes from metadata
    - Returns quality score and suggestions
    """
    warnings = []
    tips = []
    score = 100

    num_images = len(images_data)

    # Check image count
    if num_images == 0:
        score -= 50
        warnings.append({
            'type': 'no_images',
            'severity': 'critical',
            'message': 'No images uploaded. Listings with photos get 10x more views.'
        })
    elif num_images == 1:
        score -= 20
        warnings.append({
            'type': 'few_images',
            'severity': 'warning',
            'message': 'Only 1 image. Add at least 3-5 photos showing different rooms and angles.'
        })
    elif num_images < 3:
        score -= 10
        warnings.append({
            'type': 'few_images',
            'severity': 'info',
            'message': f'Only {num_images} images. Properties with 5+ photos get 3x more inquiries.'
        })

    # Analyze each image
    for i, img in enumerate(images_data):
        width = img.get('width', 0)
        height = img.get('height', 0)
        size_kb = img.get('sizeKb', 0)

        # Check resolution
        if width > 0 and height > 0:
            if width < 640 or height < 480:
                score -= 8
                warnings.append({
                    'type': 'low_resolution',
                    'severity': 'warning',
                    'imageIndex': i,
                    'message': f'Image {i + 1} is low resolution ({width}x{height}). Use at least 1280x720 for clarity.'
                })
            elif width < 800 or height < 600:
                score -= 3
                tips.append(f'Image {i + 1} could be higher resolution ({width}x{height}). 1920x1080 is ideal.')

        # Check file size (too small = likely low quality)
        if size_kb > 0 and size_kb < 50:
            score -= 5
            warnings.append({
                'type': 'tiny_file',
                'severity': 'warning',
                'imageIndex': i,
                'message': f'Image {i + 1} is very small ({size_kb}KB). It may appear blurry.'
            })

        # Check aspect ratio
        if width > 0 and height > 0:
            ratio = width / height
            if ratio < 0.5 or ratio > 3.0:
                score -= 3
                tips.append(f'Image {i + 1} has an unusual aspect ratio. Standard 16:9 or 4:3 works best.')

    # Suggest cover photo tips
    if num_images >= 3:
        tips.append('Make your first image the exterior/best room — it\'s the cover photo!')

    # Normalization
    score = max(0, min(100, score))

    if score >= 80:
        grade = 'A'
        label = 'Excellent'
    elif score >= 60:
        grade = 'B'
        label = 'Good'
    elif score >= 40:
        grade = 'C'
        label = 'Needs Improvement'
    else:
        grade = 'D'
        label = 'Poor Quality'

    return {
        'score': score,
        'grade': grade,
        'label': label,
        'warnings': warnings,
        'tips': tips,
        'imageCount': num_images
    }

if __name__ == '__main__':
    input_data = json.loads(sys.stdin.read())
    images = input_data.get('images', [])
    result = analyze_image_quality(images)
    print(json.dumps(result))

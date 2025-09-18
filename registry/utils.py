import base64
from io import BytesIO
from PIL import Image, ImageDraw
import json

def signature_data_to_image(signature_data):
    """
    Convert signature data (list of points) to an image
    """
    try:
        # Extract points from signature data
        if isinstance(signature_data, str):
            signature_data = json.loads(signature_data)
        
        if not signature_data or not isinstance(signature_data, list):
            return None
        
        # Find the bounding box of the signature
        all_x = [point['x'] for point in signature_data if 'x' in point]
        all_y = [point['y'] for point in signature_data if 'y' in point]
        
        if not all_x or not all_y:
            return None
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Create image with some padding
        padding = 10
        width = int(max_x - min_x) + 2 * padding
        height = int(max_y - min_y) + 2 * padding
        
        if width <= 0 or height <= 0:
            return None
        
        # Create a white background image
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw the signature
        for i in range(len(signature_data) - 1):
            if all(k in signature_data[i] and k in signature_data[i + 1] for k in ['x', 'y']):
                x1 = signature_data[i]['x'] - min_x + padding
                y1 = signature_data[i]['y'] - min_y + padding
                x2 = signature_data[i + 1]['x'] - min_x + padding
                y2 = signature_data[i + 1]['y'] - min_y + padding
                draw.line([(x1, y1), (x2, y2)], fill='black', width=2)
        
        return img
        
    except (ValueError, KeyError, TypeError) as e:
        print(f"Error converting signature to image: {e}")
        return None

def save_signature_image(signature_img, entry, field_name='signature_image'):
    """
    Save signature image to model field
    """
    if signature_img:
        try:
            # Convert image to bytes
            buffer = BytesIO()
            signature_img.save(buffer, format='PNG')
            
            # Save to model field
            from django.core.files.base import ContentFile
            image_file = ContentFile(buffer.getvalue())
            
            # Generate filename
            filename = f"signature_{entry.id}.png"
            
            # Save to the specified field
            getattr(entry, field_name).save(filename, image_file, save=False)
            
        except Exception as e:
            print(f"Error saving signature image: {e}")
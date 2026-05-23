import sys
try:
    from PIL import Image
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

def convert_to_transparent():
    # Load image
    img = Image.open('/Users/arjunsingh/Desktop/algo_brain/frontend/img/synap.jpg').convert('L')
    
    # Create a new RGBA image
    # We want the logo to be white, with the alpha channel driven by the original image's brightness
    rgba = Image.new('RGBA', img.size)
    
    # Put data
    img_data = img.getdata()
    new_data = []
    
    for val in img_data:
        # val is 0 (black) to 255 (white)
        # We can map the value using a slight threshold to make sure the background is fully transparent
        # and the logo is crisp.
        # Let's say if val < 10, alpha is 0.
        if val < 15:
            alpha = 0
        else:
            # boost the alpha slightly so the midtones are more solid
            alpha = min(255, int(val * 1.5))
        
        # We make the actual color pure white, and use the brightness as opacity
        new_data.append((255, 255, 255, alpha))
        
    rgba.putdata(new_data)
    rgba.save('/Users/arjunsingh/Desktop/algo_brain/frontend/react-app/public/synap.png', 'PNG')
    print("Successfully created transparent synap.png")

if __name__ == "__main__":
    convert_to_transparent()

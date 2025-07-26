#!/usr/bin/env python3
"""
Car Auction Analyzer - Icon Generator

This script generates all required PWA icons for the Car Auction Analyzer app.
It creates vector-style icons with a car silhouette, magnifying glass, and dollar sign
in various sizes required for PWA installation and app stores.

Requirements:
    - PIL/Pillow: pip install pillow

Usage:
    python generate-icons.py

This will create all icons in the 'docs/icons' directory.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

# Configuration
OUTPUT_DIR = "docs/icons"
PRIMARY_COLOR = (0, 102, 204)  # Blue (#0066cc)
SECONDARY_COLOR = (52, 199, 89)  # Green (#34c759)
ACCENT_COLOR = (255, 59, 48)  # Red (#ff3b30)
BACKGROUND_COLOR = (255, 255, 255)  # White

# Icon sizes needed for PWA
ICON_SIZES = [
    # Standard PWA icons
    {"size": 72, "name": "icon-72x72.png"},
    {"size": 96, "name": "icon-96x96.png"},
    {"size": 128, "name": "icon-128x128.png"},
    {"size": 144, "name": "icon-144x144.png"},
    {"size": 152, "name": "icon-152x152.png"},
    {"size": 192, "name": "icon-192x192.png"},
    {"size": 384, "name": "icon-384x384.png"},
    {"size": 512, "name": "icon-512x512.png"},
    # Apple specific icons
    {"size": 152, "name": "apple-icon-152.png"},
    {"size": 167, "name": "apple-icon-167.png"},
    {"size": 180, "name": "apple-icon-180.png"},
    # Apple splash screens
    {"size": 640, "name": "apple-splash-640-1136.png", "width": 640, "height": 1136},
    {"size": 750, "name": "apple-splash-750-1334.png", "width": 750, "height": 1334},
    {"size": 828, "name": "apple-splash-828-1792.png", "width": 828, "height": 1792},
    {"size": 1125, "name": "apple-splash-1125-2436.png", "width": 1125, "height": 2436},
    {"size": 1242, "name": "apple-splash-1242-2688.png", "width": 1242, "height": 2688},
    {"size": 1536, "name": "apple-splash-1536-2048.png", "width": 1536, "height": 2048},
    {"size": 1668, "name": "apple-splash-1668-2224.png", "width": 1668, "height": 2224},
    {"size": 1668, "name": "apple-splash-1668-2388.png", "width": 1668, "height": 2388},
    {"size": 2048, "name": "apple-splash-2048-2732.png", "width": 2048, "height": 2732},
]


def draw_car(draw, size, color):
    """Draw a car silhouette on the canvas."""
    scale = size / 512  # Scale factor based on 512px original design
    
    # Translate to center the car
    center_x = size * 0.5
    center_y = size * 0.55
    
    # Car body - simplified sedan shape
    car_points = [
        (center_x - 180 * scale, center_y),  # Start at left bottom
        (center_x - 180 * scale, center_y - 30 * scale),  # Left side up
        (center_x - 150 * scale, center_y - 60 * scale),  # Front windshield
        (center_x - 80 * scale, center_y - 70 * scale),  # Roof front
        (center_x + 30 * scale, center_y - 70 * scale),  # Roof
        (center_x + 100 * scale, center_y - 50 * scale),  # Rear windshield
        (center_x + 150 * scale, center_y - 30 * scale),  # Trunk
        (center_x + 180 * scale, center_y),  # Right bottom
    ]
    
    # Draw car body
    draw.polygon(car_points, fill=color)
    
    # Draw wheels
    wheel_radius = 40 * scale
    draw.ellipse(
        [
            center_x - 120 * scale - wheel_radius,
            center_y - wheel_radius,
            center_x - 120 * scale + wheel_radius,
            center_y + wheel_radius,
        ],
        fill=color,
    )
    draw.ellipse(
        [
            center_x + 120 * scale - wheel_radius,
            center_y - wheel_radius,
            center_x + 120 * scale + wheel_radius,
            center_y + wheel_radius,
        ],
        fill=color,
    )
    
    # Draw windows
    # Front window
    window_points = [
        (center_x - 140 * scale, center_y - 35 * scale),
        (center_x - 120 * scale, center_y - 60 * scale),
        (center_x - 80 * scale, center_y - 65 * scale),
        (center_x - 80 * scale, center_y - 35 * scale),
    ]
    draw.polygon(window_points, fill=BACKGROUND_COLOR)
    
    # Middle window
    window_points = [
        (center_x - 70 * scale, center_y - 65 * scale),
        (center_x + 20 * scale, center_y - 65 * scale),
        (center_x + 20 * scale, center_y - 35 * scale),
        (center_x - 70 * scale, center_y - 35 * scale),
    ]
    draw.polygon(window_points, fill=BACKGROUND_COLOR)
    
    # Rear window
    window_points = [
        (center_x + 30 * scale, center_y - 65 * scale),
        (center_x + 90 * scale, center_y - 50 * scale),
        (center_x + 90 * scale, center_y - 35 * scale),
        (center_x + 30 * scale, center_y - 35 * scale),
    ]
    draw.polygon(window_points, fill=BACKGROUND_COLOR)


def draw_magnifying_glass(draw, size, color):
    """Draw a magnifying glass on the canvas."""
    scale = size / 512
    
    # Position in the top right quadrant
    center_x = size * 0.7
    center_y = size * 0.3
    
    # Glass circle
    glass_radius = 70 * scale
    line_width = int(15 * scale)
    if line_width < 1:
        line_width = 1
        
    draw.ellipse(
        [
            center_x - glass_radius,
            center_y - glass_radius,
            center_x + glass_radius,
            center_y + glass_radius,
        ],
        outline=color,
        width=line_width,
    )
    
    # Glass handle
    handle_start_x = center_x + (50 * scale)
    handle_start_y = center_y + (50 * scale)
    handle_end_x = center_x + (100 * scale)
    handle_end_y = center_y + (100 * scale)
    
    draw.line(
        [handle_start_x, handle_start_y, handle_end_x, handle_end_y],
        fill=color,
        width=line_width,
    )


def draw_dollar_sign(draw, size, color):
    """Draw a dollar sign on the canvas."""
    scale = size / 512
    
    # Position in the top left quadrant
    center_x = size * 0.3
    center_y = size * 0.35
    
    # Try to load a font, fallback to drawing manually if not available
    try:
        # Font size proportional to icon size
        font_size = int(120 * scale)
        if font_size < 10:
            font_size = 10
            
        try:
            # Try to use Arial or a similar font
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Draw the dollar sign
        draw.text((center_x, center_y), "$", fill=color, font=font, anchor="mm")
    except Exception as e:
        print(f"Error using font, falling back to manual drawing: {e}")
        # Manual drawing of dollar sign if font fails
        line_width = max(1, int(10 * scale))
        
        # Vertical line
        draw.line(
            [center_x, center_y - 40 * scale, center_x, center_y + 40 * scale],
            fill=color,
            width=line_width,
        )
        
        # Top curve
        draw.arc(
            [
                center_x - 20 * scale,
                center_y - 40 * scale,
                center_x + 20 * scale,
                center_y,
            ],
            180,
            0,
            fill=color,
            width=line_width,
        )
        
        # Bottom curve
        draw.arc(
            [
                center_x - 20 * scale,
                center_y,
                center_x + 20 * scale,
                center_y + 40 * scale,
            ],
            0,
            180,
            fill=color,
            width=line_width,
        )


def create_icon(size, output_path, primary_color=PRIMARY_COLOR, 
                secondary_color=SECONDARY_COLOR, accent_color=ACCENT_COLOR):
    """Create an icon with the specified size and colors."""
    # For splash screens, use different width and height if specified
    width = size
    height = size
    
    if isinstance(size, dict) and "width" in size and "height" in size:
        width = size["width"]
        height = size["height"]
        size = size["size"]  # Use size for scaling elements
    
    # Create a new image with white background
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    
    # For splash screens, just draw app name and icon in the center
    if width != height:
        # Draw background
        draw.rectangle([0, 0, width, height], fill=primary_color)
        
        # Draw a smaller version of the icon in the center
        icon_size = min(width, height) * 0.4
        icon_image = create_icon(int(icon_size), None, primary_color, secondary_color, accent_color)
        
        # Paste the icon in the center
        icon_x = (width - icon_size) // 2
        icon_y = (height - icon_size) // 2
        image.paste(icon_image, (int(icon_x), int(icon_y)), icon_image)
        
        # Add app name text below the icon
        try:
            font_size = int(min(width, height) * 0.06)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()
                
            draw.text(
                (width // 2, icon_y + icon_size + font_size * 2),
                "Car Auction Analyzer",
                fill=BACKGROUND_COLOR,
                font=font,
                anchor="mm",
            )
        except Exception as e:
            print(f"Error adding text to splash screen: {e}")
    else:
        # Draw background circle
        draw.ellipse([0, 0, size, size], fill=primary_color)
        
        # Draw inner circle
        inner_radius = size / 2.2
        inner_center = size / 2
        draw.ellipse(
            [
                inner_center - inner_radius,
                inner_center - inner_radius,
                inner_center + inner_radius,
                inner_center + inner_radius,
            ],
            fill=BACKGROUND_COLOR,
        )
        
        # Draw car silhouette
        draw_car(draw, size, secondary_color)
        
        # Draw magnifying glass
        draw_magnifying_glass(draw, size, accent_color)
        
        # Draw dollar sign
        draw_dollar_sign(draw, size, primary_color)
    
    # Save the image if output path is provided
    if output_path:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path, "PNG")
        print(f"Created icon: {output_path}")
    
    return image


def generate_all_icons():
    """Generate all required icons for the PWA."""
    print("Generating Car Auction Analyzer icons...")
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate each icon size
    for icon_info in ICON_SIZES:
        size = icon_info["size"]
        name = icon_info["name"]
        
        # Check if this is a splash screen (non-square)
        if "width" in icon_info and "height" in icon_info:
            create_icon(
                {"size": size, "width": icon_info["width"], "height": icon_info["height"]},
                os.path.join(OUTPUT_DIR, name),
            )
        else:
            create_icon(size, os.path.join(OUTPUT_DIR, name))
    
    print(f"All icons generated successfully in {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_all_icons()

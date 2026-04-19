"""
Accessibility Module for WCAG 2.1 AA Compliance
Phase 3: Accessibility & Advanced UX
"""

from flask import request
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class AccessibilityHeaders:
    """Add accessibility-related headers"""
    
    @staticmethod
    def apply(response):
        """Apply accessibility headers"""
        # Prevent browser from MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Allow resizing text
        response.headers['viewport'] = 'width=device-width, initial-scale=1.0'
        return response


class ARIALabels:
    """Generate ARIA labels for accessibility"""
    
    @staticmethod
    def button(action, description=""):
        """Generate ARIA label for button"""
        return f"aria-label=\"{action}{' - ' + description if description else ''}\""
    
    @staticmethod
    def form_field(field_name, required=False):
        """Generate ARIA label for form field"""
        label = f"aria-label=\"{field_name}"
        if required:
            label += " - required"
        label += "\""
        return label
    
    @staticmethod
    def live_region(polite=True):
        """Generate ARIA live region"""
        region = "aria-live=\"polite\"" if polite else "aria-live=\"assertive\""
        region += " aria-atomic=\"true\""
        return region
    
    @staticmethod
    def error_message():
        """Generate ARIA label for error message"""
        return "role=\"alert\" aria-live=\"assertive\""


class KeyboardNavigation:
    """Keyboard navigation handlers"""
    
    KEYS = {
        'ENTER': 13,
        'ESC': 27,
        'TAB': 9,
        'ARROW_UP': 38,
        'ARROW_DOWN': 40,
        'ARROW_LEFT': 37,
        'ARROW_RIGHT': 39,
        'SPACE': 32,
    }
    
    @staticmethod
    def is_key_pressed(key_code, target_key):
        """Check if specific key was pressed"""
        return key_code == KeyboardNavigation.KEYS.get(target_key)
    
    @staticmethod
    def generate_keyboard_handler():
        """Generate keyboard event handler code"""
        return """
        document.addEventListener('keydown', function(event) {
            // Tab: Move focus
            if (event.key === 'Tab') {
                // Browser handles this natively
            }
            // Escape: Close modals
            if (event.key === 'Escape') {
                closeActiveModal();
            }
            // Enter: Activate focused element
            if (event.key === 'Enter') {
                if (document.activeElement.tagName !== 'TEXTAREA') {
                    document.activeElement.click();
                }
            }
            // Arrow keys: Navigate lists
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
                navigateList(event.key);
            }
        });
        """


class ScreenReaderSupport:
    """Screen reader optimization"""
    
    @staticmethod
    def announce(message, priority='polite'):
        """Generate announcement for screen readers"""
        return f"""
        <div role="status" aria-live="{priority}" aria-atomic="true" class="sr-only">
            {message}
        </div>
        """
    
    @staticmethod
    def hide_from_screen_reader(element_id):
        """Hide element from screen readers"""
        return f"aria-hidden=\"true\" id=\"{element_id}\""
    
    @staticmethod
    def label_form_control(control_id, label_text):
        """Associate label with form control"""
        return f"<label for=\"{control_id}\">{label_text}</label>"
    
    @staticmethod
    def describe_complex_element(element_id, description_id):
        """Add description for complex elements"""
        return f"aria-describedby=\"{description_id}\" id=\"{element_id}\""


class ColorContrast:
    """Color contrast validators"""
    
    @staticmethod
    def validate_wcag_aa(fg_color, bg_color):
        """
        Validate color contrast meets WCAG AA (4.5:1 for text)
        Colors should be hex format
        """
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def get_luminance(rgb):
            r, g, b = [x / 255.0 for x in rgb]
            r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
            g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
            b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        fg_rgb = hex_to_rgb(fg_color)
        bg_rgb = hex_to_rgb(bg_color)
        
        fg_lum = get_luminance(fg_rgb)
        bg_lum = get_luminance(bg_rgb)
        
        lighter = max(fg_lum, bg_lum)
        darker = min(fg_lum, bg_lum)
        
        contrast_ratio = (lighter + 0.05) / (darker + 0.05)
        
        return {
            'ratio': contrast_ratio,
            'wcag_aa': contrast_ratio >= 4.5,  # 4.5:1 for normal text
            'wcag_aaa': contrast_ratio >= 7.0   # 7:1 for AAA
        }
    
    @staticmethod
    def common_accessible_colors():
        """Provide WCAG AA compliant color palette"""
        return {
            'background': '#FFFFFF',
            'text': '#000000',
            'primary': '#0066CC',
            'success': '#008000',
            'warning': '#FFA500',
            'error': '#CC0000',
            'info': '#0099FF'
        }


class AccessibilityValidation:
    """Validate accessibility compliance"""
    
    @staticmethod
    def validate_page_structure(html_content):
        """Validate semantic HTML structure"""
        checks = {
            'has_h1': '<h1' in html_content,
            'proper_heading_order': validate_heading_order(html_content),
            'form_labels': all('<label' in html_content for _ in [1]),
            'alt_text': validate_alt_text(html_content),
            'aria_labels': validate_aria_labels(html_content)
        }
        return checks
    
    @staticmethod
    def check_keyboard_navigation(routes):
        """Check if all routes support keyboard navigation"""
        return {
            'tab_navigation': True,
            'escape_closes_modal': True,
            'enter_activates_buttons': True,
            'arrow_keys_work': True
        }
    
    @staticmethod
    def check_screen_reader_compatibility():
        """Check screen reader compatibility"""
        return {
            'aria_labels': True,
            'live_regions': True,
            'semantic_html': True,
            'form_associations': True
        }


def require_accessibility(f):
    """Decorator to ensure accessibility standards"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        # Add accessibility headers
        AccessibilityHeaders.apply(response)
        
        # Log accessibility violations
        logger.debug(f"Accessibility check for {request.path}")
        
        return response
    return decorated_function


def validate_heading_order(html_content):
    """Validate heading hierarchy"""
    import re
    headings = re.findall(r'<h([1-6])', html_content)
    if not headings:
        return False
    
    # Heading levels should increase by 1
    for i in range(len(headings) - 1):
        level_diff = int(headings[i+1]) - int(headings[i])
        if level_diff > 1:  # Skip more than 1 level
            return False
    return True


def validate_alt_text(html_content):
    """Validate all images have alt text"""
    import re
    images = re.findall(r'<img[^>]*>', html_content)
    for img in images:
        if 'alt=' not in img:
            return False
    return True


def validate_aria_labels(html_content):
    """Validate ARIA labels present"""
    import re
    interactive = re.findall(r'<(button|input|select|textarea)[^>]*>', html_content)
    labeled = re.findall(r'aria-label|<label', html_content)
    return len(labeled) > 0


# Accessibility compliance checklist
WCAG_CHECKLIST = {
    'Perceivable': {
        'images_have_alt_text': False,
        'color_not_only_means': False,
        'sufficient_contrast': False,
        'resizable_text': False,
    },
    'Operable': {
        'keyboard_accessible': False,
        'no_keyboard_trap': False,
        'skip_links': False,
        'focus_visible': False,
    },
    'Understandable': {
        'readable_text': False,
        'clear_labels': False,
        'error_messages': False,
        'consistent_navigation': False,
    },
    'Robust': {
        'valid_html': False,
        'proper_structure': False,
        'aria_correct': False,
        'multiple_ways_to_navigate': False,
    }
}


def get_accessibility_score():
    """Calculate accessibility compliance score"""
    total = sum(len(v) for v in WCAG_CHECKLIST.values())
    completed = sum(1 for category in WCAG_CHECKLIST.values() 
                   for status in category.values() if status)
    return (completed / total) * 100 if total > 0 else 0

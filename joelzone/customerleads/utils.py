import africastalking
from django.conf import settings
import phonenumbers

africastalking.initialize(
    settings.AFRICASTALKING_USERNAME,
    settings.AFRICASTALKING_API_KEY
)

voice = africastalking.Voice


import re

def format_phone_to_e164(phone_number):
    if not phone_number:
        return None
    
    # 1. Strip out everything that isn't a digit or a plus sign
    cleaned = re.sub(r'[^\d+]', '', str(phone_number).strip())
    
    # 2. Handle standard Ugandan local format (e.g., 0700562982 or 0772000000)
    if cleaned.startswith('0'):
        # Drop the leading '0' and attach Uganda's country code
        return f"+256{cleaned[1:]}"
    
    # 3. Handle cases where the user wrote it starting with the country code without a plus (e.g., 256700...)
    if cleaned.startswith('256') and not cleaned.startswith('+'):
        return f"+{cleaned}"
        
    # 4. If it's already properly formatted with +256
    if cleaned.startswith('+256') and len(cleaned) >= 13:
        return cleaned

    # CRITICAL: If it doesn't match a real pattern, return None (NOT just "+")
    return None
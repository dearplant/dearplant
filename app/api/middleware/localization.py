# 📄 File: app/api/middleware/localization.py
# 🧭 Purpose (Layman Explanation): 
# Automatically detects user's language preferences and provides plant care information in their preferred language (English, Spanish, French, etc.)
# 🧪 Purpose (Technical Summary): 
# Implements i18n (internationalization) middleware that detects language from headers, manages locale context, and provides translation utilities for API responses
# 🔗 Dependencies: 
# FastAPI, babel, typing, app.shared.core.config, locale detection libraries
# 🔄 Connected Modules / Calls From: 
# app.main.py middleware registration, API response formatting, error message translation

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from functools import lru_cache
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

import os

logger = logging.getLogger(__name__)

# Context variable to store current locale across request
current_locale: ContextVar[str] = ContextVar('current_locale', default='en')

class LocalizationMiddleware(BaseHTTPMiddleware):
    """
    Localization middleware for Plant Care Application supporting multiple languages.
    Handles language detection, locale management, and translation context for API responses.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Get environment from environment variable
        self.environment = os.getenv('ENVIRONMENT', 'development').lower()
        
        # Supported languages for plant care app
        self.supported_locales = [
            'en',    # English (default)
            'es',    # Spanish
            'fr',    # French
            'de',    # German
            'it',    # Italian
            'pt',    # Portuguese
            'zh',    # Chinese (Simplified)
            'ja',    # Japanese
            'ko',    # Korean
            'hi',    # Hindi
            'ar',    # Arabic
            'ru',    # Russian
            'nl',    # Dutch
            'sv',    # Swedish
        ]
        
        self.default_locale = 'en'
        self.fallback_locale = 'en'
        
        # Load translation data
        self.translations = self._load_translations()
        
        # Plant-specific language mappings
        self.plant_name_locales = self._load_plant_names()
        
        logger.info(f"Localization middleware initialized with {len(self.supported_locales)} supported locales")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process localization for incoming requests
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain
            
        Returns:
            Response with localized content
        """
        # Detect user's preferred language
        detected_locale = self._detect_locale(request)
        
        # Set locale in context
        current_locale.set(detected_locale)
        
        # Add locale info to request state
        request.state.locale = detected_locale
        request.state.supported_locales = self.supported_locales
        request.state.translation_context = self._get_translation_context(detected_locale)
        
        # Log locale detection
        user_agent = request.headers.get("user-agent", "unknown")
        logger.debug(f"Locale detected: {detected_locale} for {request.url.path} ({user_agent})")
        
        # Process request with locale context
        response = await call_next(request)
        
        # Add locale headers to response
        self._add_locale_headers(response, detected_locale)
        
        return response
    
    def _detect_locale(self, request: Request) -> str:
        """
        Detect user's preferred locale from various sources
        
        Args:
            request: HTTP request object
            
        Returns:
            Detected locale code
        """
        # Priority order for locale detection:
        # 1. URL parameter (?lang=es)
        # 2. Custom header (X-Language)
        # 3. User preference from database (if authenticated)
        # 4. Accept-Language header
        # 5. Geolocation (if available)
        # 6. Default locale
        
        # 1. Check URL parameter
        lang_param = request.query_params.get('lang')
        if lang_param and self._is_supported_locale(lang_param):
            logger.debug(f"Locale from URL parameter: {lang_param}")
            return lang_param
        
        # 2. Check custom header
        custom_lang = request.headers.get('X-Language') or request.headers.get('X-Locale')
        if custom_lang and self._is_supported_locale(custom_lang):
            logger.debug(f"Locale from custom header: {custom_lang}")
            return custom_lang
        
        # 3. Check user preference (if authenticated)
        if hasattr(request.state, 'user_id') and request.state.user_id:
            user_locale = self._get_user_locale_preference(request.state.user_id)
            if user_locale and self._is_supported_locale(user_locale):
                logger.debug(f"Locale from user preference: {user_locale}")
                return user_locale
        
        # 4. Parse Accept-Language header
        accept_language = request.headers.get('Accept-Language')
        if accept_language:
            detected = self._parse_accept_language(accept_language)
            if detected:
                logger.debug(f"Locale from Accept-Language: {detected}")
                return detected
        
        # 5. Check geolocation header (if available)
        country_code = request.headers.get('CF-IPCountry') or request.headers.get('X-Country-Code')
        if country_code:
            geo_locale = self._country_to_locale(country_code)
            if geo_locale and self._is_supported_locale(geo_locale):
                logger.debug(f"Locale from geolocation: {geo_locale} ({country_code})")
                return geo_locale
        
        # 6. Default locale
        logger.debug(f"Using default locale: {self.default_locale}")
        return self.default_locale
    
    def _parse_accept_language(self, accept_language: str) -> Optional[str]:
        """
        Parse Accept-Language header and find best match
        
        Args:
            accept_language: Accept-Language header value
            
        Returns:
            Best matching locale or None
        """
        try:
            # Parse "en-US,en;q=0.9,es;q=0.8,fr;q=0.7"
            languages = []
            
            for lang_item in accept_language.split(','):
                lang_item = lang_item.strip()
                if ';q=' in lang_item:
                    lang, quality = lang_item.split(';q=', 1)
                    quality = float(quality)
                else:
                    lang = lang_item
                    quality = 1.0
                
                # Extract primary language code
                lang = lang.split('-')[0].lower()
                languages.append((lang, quality))
            
            # Sort by quality score
            languages.sort(key=lambda x: x[1], reverse=True)
            
            # Find first supported language
            for lang, _ in languages:
                if self._is_supported_locale(lang):
                    return lang
                    
        except Exception as e:
            logger.warning(f"Failed to parse Accept-Language header: {e}")
        
        return None
    
    def _country_to_locale(self, country_code: str) -> Optional[str]:
        """
        Map country code to locale
        
        Args:
            country_code: ISO country code
            
        Returns:
            Corresponding locale or None
        """
        country_locale_map = {
            'US': 'en', 'GB': 'en', 'CA': 'en', 'AU': 'en', 'NZ': 'en', 'IE': 'en',
            'ES': 'es', 'MX': 'es', 'AR': 'es', 'CO': 'es', 'CL': 'es', 'PE': 'es',
            'FR': 'fr', 'BE': 'fr', 'CH': 'fr', 'LU': 'fr',
            'DE': 'de', 'AT': 'de',
            'IT': 'it',
            'PT': 'pt', 'BR': 'pt',
            'CN': 'zh', 'TW': 'zh', 'HK': 'zh', 'SG': 'zh',
            'JP': 'ja',
            'KR': 'ko',
            'IN': 'hi',
            'SA': 'ar', 'AE': 'ar', 'EG': 'ar', 'JO': 'ar',
            'RU': 'ru', 'BY': 'ru', 'KZ': 'ru',
            'NL': 'nl',
            'SE': 'sv', 'NO': 'sv', 'DK': 'sv',
        }
        
        return country_locale_map.get(country_code.upper())
    
    def _is_supported_locale(self, locale: str) -> bool:
        """
        Check if locale is supported
        
        Args:
            locale: Locale code to check
            
        Returns:
            True if supported
        """
        return locale.lower() in self.supported_locales
    
    def _get_user_locale_preference(self, user_id: str) -> Optional[str]:
        """
        Get user's saved locale preference from database
        
        Args:
            user_id: User identifier
            
        Returns:
            User's preferred locale or None
        """
        # TODO: Implement database lookup for user locale preference
        # This would query the user's profile settings
        # For now, return None to fall back to other detection methods
        return None
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """
        Load translation files from disk
        
        Returns:
            Dictionary of translations by locale
        """
        translations = {}
        translations_dir = Path(__file__).parent.parent.parent / "shared" / "translations"
        
        # Default translations (embedded)
        default_translations = {
            'en': {
                'errors.validation_failed': 'Validation failed',
                'errors.not_found': 'Resource not found',
                'errors.unauthorized': 'Unauthorized access',
                'errors.rate_limit_exceeded': 'Rate limit exceeded',
                'plants.watering_due': 'Watering due',
                'plants.fertilizing_due': 'Fertilizing due',
                'plants.healthy': 'Plant is healthy',
                'plants.needs_attention': 'Plant needs attention',
                'notifications.care_reminder': 'Time to care for your plants',
                'api.success': 'Operation successful',
                'api.created': 'Resource created successfully',
                'api.updated': 'Resource updated successfully',
                'api.deleted': 'Resource deleted successfully'
            },
            'es': {
                'errors.validation_failed': 'Error de validación',
                'errors.not_found': 'Recurso no encontrado',
                'errors.unauthorized': 'Acceso no autorizado',
                'errors.rate_limit_exceeded': 'Límite de velocidad excedido',
                'plants.watering_due': 'Riego pendiente',
                'plants.fertilizing_due': 'Fertilización pendiente',
                'plants.healthy': 'La planta está saludable',
                'plants.needs_attention': 'La planta necesita atención',
                'notifications.care_reminder': 'Hora de cuidar tus plantas',
                'api.success': 'Operación exitosa',
                'api.created': 'Recurso creado exitosamente',
                'api.updated': 'Recurso actualizado exitosamente',
                'api.deleted': 'Recurso eliminado exitosamente'
            },
            'fr': {
                'errors.validation_failed': 'Échec de la validation',
                'errors.not_found': 'Ressource non trouvée',
                'errors.unauthorized': 'Accès non autorisé',
                'errors.rate_limit_exceeded': 'Limite de débit dépassée',
                'plants.watering_due': 'Arrosage dû',
                'plants.fertilizing_due': 'Fertilisation due',
                'plants.healthy': 'La plante est en bonne santé',
                'plants.needs_attention': 'La plante a besoin d\'attention',
                'notifications.care_reminder': 'Il est temps de prendre soin de vos plantes',
                'api.success': 'Opération réussie',
                'api.created': 'Ressource créée avec succès',
                'api.updated': 'Ressource mise à jour avec succès',
                'api.deleted': 'Ressource supprimée avec succès'
            }
        }
        
        # Use embedded translations
        translations.update(default_translations)
        
        # Try to load additional translations from files
        if translations_dir.exists():
            try:
                for locale_file in translations_dir.glob("*.json"):
                    locale = locale_file.stem
                    if locale in self.supported_locales:
                        with open(locale_file, 'r', encoding='utf-8') as f:
                            translations[locale] = json.load(f)
                            logger.debug(f"Loaded translations for locale: {locale}")
            except Exception as e:
                logger.warning(f"Failed to load translation files: {e}")
        
        return translations
    
    def _load_plant_names(self) -> Dict[str, Dict[str, str]]:
        """
        Load plant name translations
        
        Returns:
            Dictionary of plant names by locale
        """
        # Sample plant name translations
        return {
            'en': {
                'monstera_deliciosa': 'Monstera Deliciosa',
                'snake_plant': 'Snake Plant',
                'pothos': 'Pothos',
                'peace_lily': 'Peace Lily',
                'rubber_tree': 'Rubber Tree'
            },
            'es': {
                'monstera_deliciosa': 'Monstera Deliciosa',
                'snake_plant': 'Planta Serpiente',
                'pothos': 'Potos',
                'peace_lily': 'Lirio de la Paz',
                'rubber_tree': 'Árbol del Caucho'
            },
            'fr': {
                'monstera_deliciosa': 'Monstera Deliciosa',
                'snake_plant': 'Plante Serpent',
                'pothos': 'Pothos',
                'peace_lily': 'Lys de la Paix',
                'rubber_tree': 'Arbre à Caoutchouc'
            }
        }
    
    def _get_translation_context(self, locale: str) -> Dict[str, Any]:
        """
        Get translation context for the locale
        
        Args:
            locale: Current locale
            
        Returns:
            Translation context dictionary
        """
        return {
            'locale': locale,
            'translations': self.translations.get(locale, self.translations.get(self.fallback_locale, {})),
            'plant_names': self.plant_name_locales.get(locale, self.plant_name_locales.get(self.fallback_locale, {})),
            'date_format': self._get_date_format(locale),
            'number_format': self._get_number_format(locale),
            'rtl': locale in ['ar', 'he', 'fa']  # Right-to-left languages
        }
    
    def _get_date_format(self, locale: str) -> str:
        """
        Get date format for locale
        
        Args:
            locale: Locale code
            
        Returns:
            Date format string
        """
        date_formats = {
            'en': '%m/%d/%Y',  # MM/DD/YYYY
            'es': '%d/%m/%Y',  # DD/MM/YYYY
            'fr': '%d/%m/%Y',  # DD/MM/YYYY
            'de': '%d.%m.%Y',  # DD.MM.YYYY
            'it': '%d/%m/%Y',  # DD/MM/YYYY
            'pt': '%d/%m/%Y',  # DD/MM/YYYY
            'zh': '%Y/%m/%d',  # YYYY/MM/DD
            'ja': '%Y/%m/%d',  # YYYY/MM/DD
            'ko': '%Y/%m/%d',  # YYYY/MM/DD
        }
        return date_formats.get(locale, '%Y-%m-%d')
    
    def _get_number_format(self, locale: str) -> Dict[str, str]:
        """
        Get number formatting for locale
        
        Args:
            locale: Locale code
            
        Returns:
            Number format configuration
        """
        number_formats = {
            'en': {'decimal': '.', 'thousands': ','},
            'es': {'decimal': ',', 'thousands': '.'},
            'fr': {'decimal': ',', 'thousands': ' '},
            'de': {'decimal': ',', 'thousands': '.'},
            'it': {'decimal': ',', 'thousands': '.'},
            'pt': {'decimal': ',', 'thousands': '.'},
            'zh': {'decimal': '.', 'thousands': ','},
            'ja': {'decimal': '.', 'thousands': ','},
            'ko': {'decimal': '.', 'thousands': ','},
            'hi': {'decimal': '.', 'thousands': ','},
            'ar': {'decimal': '.', 'thousands': ','},
            'ru': {'decimal': ',', 'thousands': ' '},
            'nl': {'decimal': ',', 'thousands': '.'},
            'sv': {'decimal': ',', 'thousands': ' '},
        }
        return number_formats.get(locale, {'decimal': '.', 'thousands': ','})
    
    def _add_locale_headers(self, response: Response, locale: str) -> None:
        """
        Add locale-related headers to response
        
        Args:
            response: HTTP response
            locale: Current locale
        """
        response.headers["Content-Language"] = locale
        response.headers["X-Locale"] = locale
        response.headers["X-Supported-Locales"] = ",".join(self.supported_locales)
        
        # Add cache headers for localized content
        response.headers["Vary"] = "Accept-Language, X-Language"

# Utility functions for translation
def get_current_locale() -> str:
    """
    Get the current request locale
    
    Returns:
        Current locale code
    """
    try:
        return current_locale.get()
    except LookupError:
        return 'en'  # Default fallback

def translate(key: str, locale: Optional[str] = None, **kwargs) -> str:
    """
    Translate a message key
    
    Args:
        key: Translation key (e.g., 'errors.not_found')
        locale: Target locale (uses current if None)
        **kwargs: Template variables for formatting
        
    Returns:
        Translated message
    """
    if locale is None:
        locale = get_current_locale()
    
    # Get middleware instance (simplified for this example)
    # In real implementation, this would be injected or accessed differently
    try:
        # This is a simplified approach - in production you'd want better dependency injection
        middleware = LocalizationMiddleware(None)
        translations = middleware.translations.get(locale, {})
        
        # Get translation or fallback to English
        message = translations.get(key)
        if not message and locale != 'en':
            message = middleware.translations.get('en', {}).get(key)
        
        # Final fallback to key itself
        if not message:
            message = key
        
        # Format with variables if provided
        if kwargs:
            try:
                message = message.format(**kwargs)
            except (KeyError, ValueError):
                logger.warning(f"Translation formatting failed for key: {key}")
        
        return message
        
    except Exception as e:
        logger.warning(f"Translation failed for key '{key}': {e}")
        return key

def translate_plant_name(plant_key: str, locale: Optional[str] = None) -> str:
    """
    Translate a plant name
    
    Args:
        plant_key: Plant identifier key
        locale: Target locale (uses current if None)
        
    Returns:
        Translated plant name
    """
    if locale is None:
        locale = get_current_locale()
    
    try:
        middleware = LocalizationMiddleware(None)
        plant_names = middleware.plant_name_locales.get(locale, {})
        
        # Get plant name or fallback to English
        name = plant_names.get(plant_key)
        if not name and locale != 'en':
            name = middleware.plant_name_locales.get('en', {}).get(plant_key)
        
        # Final fallback to key itself (formatted)
        if not name:
            name = plant_key.replace('_', ' ').title()
        
        return name
        
    except Exception as e:
        logger.warning(f"Plant name translation failed for '{plant_key}': {e}")
        return plant_key.replace('_', ' ').title()

def format_localized_date(date_obj, locale: Optional[str] = None) -> str:
    """
    Format date according to locale preferences
    
    Args:
        date_obj: datetime object to format
        locale: Target locale (uses current if None)
        
    Returns:
        Formatted date string
    """
    if locale is None:
        locale = get_current_locale()
    
    try:
        middleware = LocalizationMiddleware(None)
        date_format = middleware._get_date_format(locale)
        return date_obj.strftime(date_format)
    except Exception as e:
        logger.warning(f"Date formatting failed: {e}")
        return date_obj.strftime('%Y-%m-%d')

def format_localized_number(number: float, locale: Optional[str] = None) -> str:
    """
    Format number according to locale preferences
    
    Args:
        number: Number to format
        locale: Target locale (uses current if None)
        
    Returns:
        Formatted number string
    """
    if locale is None:
        locale = get_current_locale()
    
    try:
        middleware = LocalizationMiddleware(None)
        format_config = middleware._get_number_format(locale)
        
        # Simple number formatting
        formatted = f"{number:,.2f}"
        
        # Replace separators according to locale
        if format_config['decimal'] != '.' or format_config['thousands'] != ',':
            # Split into integer and decimal parts
            parts = formatted.split('.')
            integer_part = parts[0].replace(',', format_config['thousands'])
            decimal_part = parts[1] if len(parts) > 1 else '00'
            
            formatted = f"{integer_part}{format_config['decimal']}{decimal_part}"
        
        return formatted
        
    except Exception as e:
        logger.warning(f"Number formatting failed: {e}")
        return str(number)

def get_supported_locales() -> List[str]:
    """
    Get list of supported locale codes
    
    Returns:
        List of supported locale codes
    """
    middleware = LocalizationMiddleware(None)
    return middleware.supported_locales.copy()

def is_rtl_locale(locale: Optional[str] = None) -> bool:
    """
    Check if locale uses right-to-left text direction
    
    Args:
        locale: Locale to check (uses current if None)
        
    Returns:
        True if RTL locale
    """
    if locale is None:
        locale = get_current_locale()
    
    return locale in ['ar', 'he', 'fa', 'ur']

@lru_cache(maxsize=128)
def get_locale_display_name(locale: str, display_locale: Optional[str] = None) -> str:
    """
    Get display name for a locale
    
    Args:
        locale: Locale code to get name for
        display_locale: Locale to display name in (uses current if None)
        
    Returns:
        Display name for the locale
    """
    if display_locale is None:
        display_locale = get_current_locale()
    
    # Locale display names
    locale_names = {
        'en': {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'it': 'Italian', 'pt': 'Portuguese', 'zh': 'Chinese', 'ja': 'Japanese',
            'ko': 'Korean', 'hi': 'Hindi', 'ar': 'Arabic', 'ru': 'Russian',
            'nl': 'Dutch', 'sv': 'Swedish'
        },
        'es': {
            'en': 'Inglés', 'es': 'Español', 'fr': 'Francés', 'de': 'Alemán',
            'it': 'Italiano', 'pt': 'Portugués', 'zh': 'Chino', 'ja': 'Japonés',
            'ko': 'Coreano', 'hi': 'Hindi', 'ar': 'Árabe', 'ru': 'Ruso',
            'nl': 'Holandés', 'sv': 'Sueco'
        },
        'fr': {
            'en': 'Anglais', 'es': 'Espagnol', 'fr': 'Français', 'de': 'Allemand',
            'it': 'Italien', 'pt': 'Portugais', 'zh': 'Chinois', 'ja': 'Japonais',
            'ko': 'Coréen', 'hi': 'Hindi', 'ar': 'Arabe', 'ru': 'Russe',
            'nl': 'Néerlandais', 'sv': 'Suédois'
        }
    }
    
    names = locale_names.get(display_locale, locale_names.get('en', {}))
    return names.get(locale, locale.upper())

# Configuration helper
def get_localization_config() -> Dict[str, Any]:
    """
    Get localization configuration
    
    Returns:
        Localization configuration dictionary
    """
    middleware = LocalizationMiddleware(None)
    
    return {
        'supported_locales': middleware.supported_locales,
        'default_locale': middleware.default_locale,
        'fallback_locale': middleware.fallback_locale,
        'available_translations': list(middleware.translations.keys()),
        'available_plant_names': list(middleware.plant_name_locales.keys())
    }
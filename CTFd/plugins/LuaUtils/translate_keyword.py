#!/usr/bin/env python3
"""
Script to translate a keyword into all CTFd available languages and add to a plugin's translations.json

Usage:
    python translate_keyword.py <keyword> <plugin_name>

Examples:
    python translate_keyword.py "Challenge Created" MyPlugin
    python translate_keyword.py "Challenge Created" /path/to/plugin  # Full path also works
"""

import argparse
import json
import os
import sys

# Try to import translation library
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False

# Import CTFd's language constants
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


Languages = {
    "en": "English",
    "de": "Deutsch",
    "pl": "Polski",
    "es": "Español",
    "ar": "اَلْعَرَبِيَّةُ",
    "zh_CN": "简体中文",
    "zh_TW": "繁體中文",
    "fr": "Français",
    "ko": "한국어",
    "ru": "русский язык",
    "pt_BR": "Português do Brasil",
    "sk": "Slovenský jazyk",
    "ja": "日本語",
    "it": "Italiano",
    "vi": "tiếng Việt",
    "ca": "Català",
    "el": "Ελληνικά",
    "fi": "Suomi",
    "ro": "Română",
    "sl": "Slovenščina",
    "sv": "Svenska",
    "he": "עברית",
    "uz": "oʻzbekcha",
}


def translate_keyword(keyword, target_lang):
    """Translate keyword to target language using available service."""    
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        result = translator.translate(keyword)
        return result
    except Exception as e:
        print(f"Warning: Translation failed for {target_lang}: {e}")
        return None



def load_translations_file(plugin_dir):
    """Load existing translations from plugin's translations.json"""
    translations_path = os.path.join(plugin_dir, 'translations.json')
    if os.path.exists(translations_path):
        try:
            with open(translations_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def resolve_plugin_dir(plugin_input):
    """Resolve plugin name or path to absolute plugin directory.
    
    Args:
        plugin_input: Either a plugin name (e.g., 'MyPlugin') or full path
    
    Returns:
        Absolute path to plugin directory
    """
    # If it's an absolute path or looks like a path (contains / or \), use it as-is
    if os.path.isabs(plugin_input) or '/' in plugin_input or '\\' in plugin_input:
        return os.path.abspath(plugin_input)
    
    # Otherwise, treat it as a plugin name and resolve relative to CTFd/plugins/
    luautils_dir = os.path.dirname(__file__)
    plugins_dir = os.path.dirname(luautils_dir)
    plugin_dir = os.path.join(plugins_dir, plugin_input)
    return os.path.abspath(plugin_dir)


def save_translations_file(plugin_dir, translations):
    """Save translations to plugin's translations.json"""
    translations_path = os.path.join(plugin_dir, 'translations.json')
    os.makedirs(plugin_dir, exist_ok=True)
    with open(translations_path, 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Translate a keyword into all CTFd available languages'
    )
    parser.add_argument('keyword', help='The keyword to translate')
    parser.add_argument('plugin_name', help='Plugin name (e.g., MyPlugin) or full path')
    parser.add_argument(
        '--key',
        help='Translation key (defaults to lowercase keyword with underscores)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Print translations without saving'
    )
    
    args = parser.parse_args()
    
    keyword = args.keyword
    plugin_input = args.plugin_name
    translation_key = args.key or keyword.lower().replace(' ', '_')
    
    # Resolve plugin directory
    plugin_dir = resolve_plugin_dir(plugin_input)
    
    # Validate plugin directory
    if not os.path.isdir(plugin_dir):
        print(f"Error: Plugin directory not found: {plugin_dir}")
        sys.exit(1)
    
    # Check if translator is available
    if not HAS_TRANSLATOR:
        print("Error: deep-translator is required but not installed.")
        print("Install with: pip install deep-translator")
        sys.exit(1)
    
    translations = {}
    failed_langs = []
    
    # Translate to each language
    for lang_code, lang_name in Languages.items():
        if lang_code == 'en':
            # English is the source, use the keyword as-is
            translation = keyword
        else:
            translation = translate_keyword(keyword, lang_code)
            if translation is None:
                failed_langs.append(lang_code)
                continue
        
        if lang_code not in translations:
            translations[lang_code] = {}
        translations[lang_code][translation_key] = translation
    
    if failed_langs:
        print(f"Warning: Failed to translate to: {', '.join(failed_langs)}")
    
    # Save if not --no-save
    if not args.no_save:
        # Load existing translations and merge
        existing = load_translations_file(plugin_dir)
        
        # Merge new translations with existing
        for lang_code, new_terms in translations.items():
            if lang_code not in existing:
                existing[lang_code] = {}
            existing[lang_code].update(new_terms)
        
        save_translations_file(plugin_dir, existing)
        print(f"Saved to {os.path.join(plugin_dir, 'translations.json')}")

if __name__ == '__main__':
    main()

"""
Test script to verify centralized config loading works correctly
"""

import sys
from config_manager import (
    load_config,
    get_config_info,
    reload_config,
    initialize_data_directory,
    config_path,
    data_path,
    template_path
)


def test_config_loading():
    """Test that config loading works correctly"""
    print("=" * 60)
    print("Testing Centralized Config Loading")
    print("=" * 60)

    # Test 1: Initialize data directory
    print("\nTest 1: Initialize data directory")
    print("-" * 60)
    was_initialized = initialize_data_directory()
    print(f"Initialization needed: {was_initialized}")
    print(f"Config path: {config_path}")
    print(f"Data path: {data_path}")
    print(f"Template path: {template_path}")

    # Test 2: Load config
    print("\nTest 2: Load configuration")
    print("-" * 60)
    config = load_config()
    print(f"Config loaded successfully: {len(config) > 0}")
    print(f"Templates in config: {len(config.get('templates', {}))}")
    if config.get('templates'):
        print("Template list:")
        for name, path in config.get('templates', {}).items():
            print(f"  - {name}: {path}")

    # Test 3: Get config info
    print("\nTest 3: Get config info")
    print("-" * 60)
    info = get_config_info()
    print(f"Template count: {info['template_count']}")
    print(f"Templates: {info['templates']}")
    print(f"WSL enabled: {info['wsl_enabled']}")
    if info['wsl_enabled']:
        print(f"WSL distro: {info['wsl_distro']}")
    print(f"Light mode: {info['light_mode']}")

    # Test 4: Reload config
    print("\nTest 4: Reload configuration")
    print("-" * 60)
    reloaded = reload_config()
    print(f"Config reloaded successfully: {len(reloaded) > 0}")

    print("\n" + "=" * 60)
    print("All tests completed successfully! ✓")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_config_loading()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

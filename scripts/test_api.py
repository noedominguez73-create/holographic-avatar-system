"""
Script de pruebas basicas para verificar que el sistema funciona
"""
import requests
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing /health...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code == 200:
            print("  OK: Sistema saludable")
            return True
        else:
            print(f"  FAIL: Status {r.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("  FAIL: No se puede conectar al servidor")
        print("  Asegurate de ejecutar start_dev.bat primero")
        return False

def test_root():
    """Test root endpoint"""
    print("Testing /...")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        data = r.json()
        print(f"  OK: {data.get('service')} v{data.get('version')}")
        print(f"  Modos disponibles: {', '.join(data.get('modes', []))}")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_modes():
    """Test modes listing"""
    print("Testing /api/v1/modes...")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/modes", timeout=5)
        data = r.json()
        modes = data.get('modes', [])
        print(f"  OK: {len(modes)} modos encontrados")
        for mode in modes:
            status = "habilitado" if mode.get('enabled') else "deshabilitado"
            print(f"    - {mode['id']}: {mode['name']} ({status})")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_locations():
    """Test locations endpoint"""
    print("Testing /api/v1/locations...")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/locations", timeout=5)
        data = r.json()
        print(f"  OK: {len(data)} ubicaciones")
        for loc in data:
            print(f"    - {loc['name']} ({loc.get('city', 'N/A')})")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_devices():
    """Test devices endpoint"""
    print("Testing /api/v1/devices...")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/devices", timeout=5)
        data = r.json()
        print(f"  OK: {len(data)} dispositivos registrados")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_avatars():
    """Test avatars endpoint"""
    print("Testing /api/v1/content/avatars...")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/content/avatars", timeout=5)
        data = r.json()
        print(f"  OK: {len(data)} avatares")
        for avatar in data:
            print(f"    - {avatar['name']} ({avatar['avatar_type']})")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_menu():
    """Test menu endpoints"""
    print("Testing /api/v1/menu/categories...")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/menu/categories", timeout=5)
        data = r.json()
        print(f"  OK: {len(data)} categorias de menu")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_catalog():
    """Test catalog endpoints"""
    print("Testing /api/v1/catalog/products...")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/catalog/products", timeout=5)
        data = r.json()
        print(f"  OK: {len(data)} productos")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def test_processing_services():
    """Test frame processor and polar encoder"""
    services = [
        ("Frame Processor", "http://localhost:8010/health"),
        ("Polar Encoder", "http://localhost:8011/health"),
        ("Fan Driver", "http://localhost:8012/health"),
    ]

    print("\nTesting servicios de procesamiento...")
    all_ok = True
    for name, url in services:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                print(f"  OK: {name}")
            else:
                print(f"  FAIL: {name} - Status {r.status_code}")
                all_ok = False
        except:
            print(f"  WARN: {name} no disponible")
            all_ok = False
    return all_ok

def main():
    print("=" * 50)
    print("HOLOGRAPHIC AVATAR SYSTEM - TEST SUITE")
    print("=" * 50)
    print()

    tests = [
        test_health,
        test_root,
        test_modes,
        test_locations,
        test_devices,
        test_avatars,
        test_menu,
        test_catalog,
        test_processing_services,
    ]

    passed = 0
    failed = 0

    for test in tests:
        print()
        if test():
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 50)
    print(f"RESULTADOS: {passed} OK, {failed} FAIL")
    print("=" * 50)

    if failed > 0:
        print("\nPara mas detalles, revisa:")
        print("  - API Docs: http://localhost:8000/docs")
        print("  - Logs de cada servicio")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

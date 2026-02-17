"""
Script para probar conexión con ventilador holográfico
"""
import socket
import sys

def test_connection(ip: str, port: int = 5499) -> bool:
    """Probar si el ventilador está accesible"""
    print(f"Probando conexión a {ip}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, port))
        sock.close()

        if result == 0:
            print(f"  ✓ Ventilador CONECTADO en {ip}:{port}")
            return True
        else:
            print(f"  ✗ No se pudo conectar (error {result})")
            return False
    except socket.timeout:
        print(f"  ✗ Timeout - el ventilador no responde")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def scan_network(base_ip: str = "192.168"):
    """Buscar ventiladores en la red"""
    print(f"\nEscaneando red {base_ip}.x.x buscando ventiladores...")
    print("(Esto puede tardar unos minutos)\n")

    found = []

    # Probar subredes comunes
    subnets = [
        f"{base_ip}.4",    # Red AP del ventilador
        f"{base_ip}.1",    # Red doméstica común
        f"{base_ip}.0",    # Otra red común
    ]

    for subnet in subnets:
        for host in range(1, 255):
            ip = f"{subnet}.{host}"
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                result = sock.connect_ex((ip, 5499))
                sock.close()

                if result == 0:
                    print(f"  ✓ ENCONTRADO: {ip}")
                    found.append(ip)
            except:
                pass

            # Mostrar progreso
            if host % 50 == 0:
                print(f"  Escaneando {subnet}.{host}...")

    return found

def main():
    print("=" * 50)
    print("TEST DE CONEXIÓN CON VENTILADOR HOLOGRÁFICO")
    print("=" * 50)
    print()

    # IP por defecto del ventilador en modo AP
    default_ip = "192.168.4.1"

    if len(sys.argv) > 1:
        ip = sys.argv[1]
    else:
        print(f"Uso: python test_fan_connection.py [IP]")
        print(f"     Sin IP, se usa la predeterminada: {default_ip}")
        print()
        ip = default_ip

    # Test de conexión
    if test_connection(ip):
        print("\n¡El ventilador está listo para recibir contenido!")
        print(f"\nPara enviar un archivo .bin:")
        print(f'  curl -X POST "http://localhost:8012/upload/{ip}" -F "file=@tu_archivo.bin"')
    else:
        print("\nEl ventilador no está accesible.")
        print("\nVerifica:")
        print("  1. ¿El ventilador está encendido?")
        print("  2. ¿Estás conectado a la red WiFi del ventilador?")
        print("     (Busca una red llamada 'HoloFan', '3D-Fan', etc.)")
        print("  3. ¿La IP es correcta?")
        print()

        resp = input("¿Quieres escanear la red buscando ventiladores? (s/n): ")
        if resp.lower() == 's':
            found = scan_network()
            if found:
                print(f"\nVentiladores encontrados: {found}")
            else:
                print("\nNo se encontraron ventiladores en la red.")

if __name__ == "__main__":
    main()

"""
Módulo: resource.py — Pool de Recursos del Sistema

Este módulo modela los recursos físicos disponibles en el simulador.
Su objetivo es mantener un conteo consistente de CPU y RAM, evitando que
el planificador asigne más recursos de los que realmente existen.

La clase `ResourcePool` centraliza dos operaciones críticas:
- reservar recursos cuando un proceso entra a ejecución,
- devolver recursos cuando el proceso termina o libera CPU por I/O.
"""

class ResourcePool:
    """Pool de recursos del sistema simulado.

    La instancia representa la capacidad total del sistema y también el
    estado actual de disponibilidad. Esto permite decidir si un proceso
    puede ser admitido o ejecutado en un momento dado.
    """

    def __init__(self, cpu_cores: int = 1, ram_mb: int = 4096) -> None:
        # Se valida la configuración inicial para evitar un sistema imposible.
        if cpu_cores < 1:
            raise ValueError(f"cpu_cores debe ser >= 1, recibido: {cpu_cores}.")
        if ram_mb < 1:
            raise ValueError(f"ram_mb debe ser >= 1, recibido: {ram_mb}.")

        # Capacidad total instalada en el sistema simulado.
        self.total_cpu: int = cpu_cores
        self.total_ram: int = ram_mb

        # Disponibilidad actual. Estos valores cambian con cada request/release.
        self.available_cpu: int = cpu_cores
        self.available_ram: int = ram_mb

    def request(self, cpu: int, ram: int) -> bool:

        # No se aceptan valores negativos porque romperían el balance del pool.
        if cpu < 0 or ram < 0:
            raise ValueError(f"Recursos negativos no permitidos: cpu={cpu}, ram={ram}.")

        # La petición no puede superar la capacidad física instalada.
        if cpu > self.total_cpu or ram > self.total_ram:
            return False

        # Tampoco puede superar los recursos que quedan libres en este instante.
        if cpu > self.available_cpu or ram > self.available_ram:
            return False

        # Si pasa todas las validaciones, se descuenta del inventario disponible.
        self.available_cpu -= cpu
        self.available_ram -= ram
        return True

    def release(self, cpu: int, ram: int) -> bool:

        # La liberación también debe ser coherente: no se admiten negativos.
        if cpu < 0 or ram < 0:
            raise ValueError(f"Recursos negativos no permitidos: cpu={cpu}, ram={ram}.")

        # Evita que la suma de disponibles supere el total físico del sistema.
        if self.available_cpu + cpu > self.total_cpu:
            return False
        if self.available_ram + ram > self.total_ram:
            return False

        # Si la operación es coherente, restaura el inventario disponible.
        self.available_cpu += cpu
        self.available_ram += ram
        return True

    def __str__(self) -> str:

        # Se calcula el uso actual para mostrarlo de forma amigable en consola.
        cpu_used: int = self.total_cpu - self.available_cpu
        ram_used: int = self.total_ram - self.available_ram

        return (
            f"+======================================+\n"
            f"|        RECURSOS DEL SISTEMA          |\n"
            f"+======================================+\n"
            f"|  CPU: {cpu_used}/{self.total_cpu} nucleos en uso{' ' * (13 - len(f'{cpu_used}/{self.total_cpu}'))}|\n"
            f"|  RAM: {ram_used}/{self.total_ram} MB en uso{' ' * (15 - len(f'{ram_used}/{self.total_ram}'))}|\n"
            f"+======================================+"
        )

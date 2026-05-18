"""
Módulo: producer_consumer.py — IPC (Productor-Consumidor)

Demuestra concurrencia real y sincronización mediante hilos, mutex y semáforos.
"""

import threading
import time
import random
from collections import deque

# Configuración base de la demostración
BUFFER_SIZE: int = 3
ITEMS_PER_PRODUCER: int = 4

def run_demo() -> None:
    """Ejecuta la demo con 2 productores y 2 consumidores."""
    print("\n" + "=" * 65)
    print("    DEMO IPC: PROBLEMA PRODUCTOR-CONSUMIDOR")
    print("    (2 Productores, 2 Consumidores, Buffer de 3)")
    print("=" * 65)

    # Buffer compartido e inicialización de primitivas de sincronización
    buffer: deque[str] = deque()
    mutex: threading.Lock = threading.Lock()
    empty: threading.Semaphore = threading.Semaphore(BUFFER_SIZE)
    full: threading.Semaphore = threading.Semaphore(0)

    # Tracking y métricas
    produced_count: list[int] = [0]
    consumed_count: list[int] = [0]
    count_lock: threading.Lock = threading.Lock()
    total_items: int = 2 * ITEMS_PER_PRODUCER

    def producer(producer_id: int) -> None:
        """Genera datos y los inserta en el buffer de manera segura."""
        for i in range(ITEMS_PER_PRODUCER):
            # Simula tiempo de procesamiento de generación
            item: str = f"Item-P{producer_id}-{i}"
            time.sleep(random.uniform(0.1, 0.5))

            # Disminuye el contador de espacios vacíos (se bloquea si es 0)
            empty.acquire()
            
            # Sección crítica: Inserción en buffer
            mutex.acquire()
            try:
                buffer.append(item)
                with count_lock:
                    produced_count[0] += 1
                    seq = produced_count[0]
                print(
                    f"  [Productor {producer_id}] Produjo: {item:20s} "
                    f"| Buffer: {list(buffer)} "
                    f"({len(buffer)}/{BUFFER_SIZE}) "
                    f"[{seq}/{total_items}]"
                )
            finally:
                mutex.release()

            # Incrementa el contador de items disponibles
            full.release()

    def consumer(consumer_id: int) -> None:
        """Retira datos del buffer simulando carga de trabajo."""
        while True:
            # Condición de salida si ya se procesó el lote total
            with count_lock:
                if consumed_count[0] >= total_items:
                    break

            # Disminuye contador de items llenos (timeout para evitar deadlocks en fin de ciclo)
            acquired = full.acquire(timeout=1.0)
            if not acquired:
                with count_lock:
                    if consumed_count[0] >= total_items:
                        break
                continue

            # Sección crítica: Retirar elemento del buffer
            mutex.acquire()
            try:
                if buffer:
                    item = buffer.popleft()
                    with count_lock:
                        consumed_count[0] += 1
                        seq = consumed_count[0]
                    print(
                        f"  [Consumidor {consumer_id}] Consumió: {item:20s} "
                        f"| Buffer: {list(buffer)} "
                        f"({len(buffer)}/{BUFFER_SIZE}) "
                        f"[{seq}/{total_items}]"
                    )
                else:
                    # Mecanismo de seguridad ante desincronizaciones extrañas
                    empty.release()
                    mutex.release()
                    continue
            finally:
                if mutex.locked():
                    mutex.release()

            # Incrementa contador de espacios vacíos para habilitar productores
            empty.release()
            
            # Simulación de trabajo o procesamiento de I/O
            time.sleep(random.uniform(0.1, 0.3))

    print("\n  Iniciando hilos...\n")
    threads: list[threading.Thread] = []

    # Inicialización de hilos (2 Productores, 2 Consumidores)
    for pid in range(1, 3):
        t = threading.Thread(target=producer, args=(pid,), name=f"Productor-{pid}", daemon=True)
        threads.append(t)

    for cid in range(1, 3):
        t = threading.Thread(target=consumer, args=(cid,), name=f"Consumidor-{cid}", daemon=True)
        threads.append(t)

    # Inicia el proceso multi-hilo
    for t in threads:
        t.start()
        
    # Espera controlada a que todos finalicen
    for t in threads:
        t.join(timeout=30.0)

    print(f"\n  [OK] Demo completada: {consumed_count[0]} items procesados.")
    print("=" * 65)

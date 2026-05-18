"""run_headless.py — Ejecuta una simulación headless del Scheduler.

Crea varios procesos, los registra en el Scheduler y ejecuta ticks
hasta completar la simulación. Imprime el log final en consola.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.process import PCB
from src.core.resource import ResourcePool
from src.core.scheduler import Scheduler, SchedulingAlgorithm
from src.ui.logger import Logger


def run_simulation(num_processes: int = 10, algorithm: SchedulingAlgorithm = SchedulingAlgorithm.FCFS):
    logger = Logger(verbose=True)
    resources = ResourcePool(cpu_cores=1, ram_mb=4096)
    scheduler = Scheduler(resources=resources, logger=logger, algorithm=algorithm)

    # Generar procesos con llegada inmediata
    for i in range(1, num_processes + 1):
        pcb = PCB(name=f"P{i:02d}")
        pcb.arrival_time = 0
        scheduler.register_process(pcb)

    # Ejecutar hasta completar
    step = 0
    while not scheduler.is_simulation_complete():
        step += 1
        out = scheduler.execute_cycle()
        # imprimo un resumen por cada tick
        print(f"{out}")
        if step > 10000:  # safety
            print("[!] Límite de ticks alcanzado, abortando")
            break

    print("\nSimulación finalizada. Resumen de logs:\n")
    logger.show_history()


if __name__ == '__main__':
    run_simulation(num_processes=10, algorithm=SchedulingAlgorithm.FCFS)

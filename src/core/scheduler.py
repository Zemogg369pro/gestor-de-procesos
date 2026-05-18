"""
Módulo: scheduler.py — Planificador de Procesos (CPU Scheduler)

Este módulo contiene la lógica principal de planificación del simulador.
El `Scheduler` administra las colas de procesos, decide qué proceso corre
en cada tick, maneja llegadas nuevas, atiende procesos bloqueados por I/O y
libera recursos cuando un proceso termina.

El comportamiento se apoya en una simulación determinista por ticks, con un
toque de variabilidad estocástica cuando un proceso solicita I/O.
"""

import random
from collections import deque
from enum import Enum, auto

from src.core.process import PCB, ProcessState, ExitReason
from src.core.resource import ResourcePool
from src.ui.logger import Logger

# Constantes de simulación I/O estocástica.
# Se usan para decidir cuándo un proceso puede abandonar la CPU por I/O y
# cuántos ticks permanecerá bloqueado antes de volver a READY.
IO_PROBABILITY: float = 0.10
IO_WAIT_MIN: int = 2
IO_WAIT_MAX: int = 5

class SchedulingAlgorithm(Enum):
    """Algoritmos de planificación soportados por el simulador."""
    FCFS = auto()
    SJF = auto()

class Scheduler:
    """Planificador de procesos del SO simulado.

    La clase coordina la vida de los procesos desde su llegada hasta su
    terminación. También actúa como árbitro entre CPU, RAM, colas de listos
    y colas de espera.
    """

    def __init__(
        self,
        resources: ResourcePool,
        logger: Logger,
        algorithm: SchedulingAlgorithm = SchedulingAlgorithm.FCFS,
    ) -> None:
        # Estructuras principales de planificación.
        # `ready_queue` contiene procesos listos para usar CPU.
        # `waiting_queue` contiene procesos bloqueados por I/O.
        # `all_processes` conserva el conjunto total para poder saber cuándo
        # la simulación finalizó.
        self.ready_queue: deque[PCB] = deque()
        self.waiting_queue: list[PCB] = []
        self.all_processes: list[PCB] = []
        
        # Dependencias externas del simulador.
        # `resources` representa CPU y RAM físicas disponibles.
        # `logger` registra eventos relevantes para depuración o UI.
        self.resources: ResourcePool = resources
        self.algorithm: SchedulingAlgorithm = algorithm
        self.current_process: PCB | None = None
        self.clock: int = 0
        self.logger: Logger = logger

    def register_process(self, pcb: PCB) -> None:
        """Añade un proceso en estado NEW a la lista general del sistema.

        Registrar no significa admitir todavía. Solo guarda el proceso en el
        inventario global para que luego pueda entrar al sistema cuando su
        `arrival_time` lo permita.
        """
        self.all_processes.append(pcb)
        self.logger.log(
            f"REGISTRADO: PID {pcb.pid} ({pcb.name}) | "
            f"Burst={pcb.cpu_burst} | RAM={pcb.mem_mb}MB | "
            f"Llegada=t{pcb.arrival_time}",
            self.clock,
        )

    def admit_process(self, pcb: PCB) -> bool:
        """Transfiere un proceso de NEW a READY si hay RAM suficiente.

        La admisión reserva memoria para garantizar que el proceso pueda ser
        ejecutado sin exceder la capacidad del sistema.
        """

        # Un proceso solo puede ser admitido si todavía no ha cambiado de estado.
        if pcb.state != ProcessState.NEW:
            self.logger.log(f"ERROR: PID {pcb.pid} no esta en NEW ({pcb.state.name}).", self.clock)
            return False

        # La admisión reserva RAM antes de mover el proceso a READY.
        if not self.resources.request(cpu=0, ram=pcb.mem_mb):
            self.logger.log(
                f"RECHAZADO: PID {pcb.pid} ({pcb.name}) necesita "
                f"{pcb.mem_mb} MB, disponible: {self.resources.available_ram} MB.",
                self.clock,
            )
            return False

        # Si la memoria está disponible, el proceso entra a la cola de listos.
        pcb.transition(ProcessState.READY)
        self.ready_queue.append(pcb)

        self.logger.log(
            f"ADMITIDO: PID {pcb.pid} ({pcb.name}) -> READY | "
            f"Burst={pcb.cpu_burst} | RAM={pcb.mem_mb}MB",
            self.clock,
        )
        return True

    def _handle_arrivals(self) -> None:
        """Admite procesos cuyo `arrival_time` ya alcanzó el reloj actual."""

        # Se seleccionan los procesos que ya llegaron y siguen esperando ser admitidos.
        pending = [
            p for p in self.all_processes
            if p.state == ProcessState.NEW and p.arrival_time <= self.clock
        ]
        # Se ordena por llegada para mantener un comportamiento determinista.
        pending.sort(key=lambda p: p.arrival_time)
        for pcb in pending:
            self.admit_process(pcb)

    def _handle_waiting(self) -> None:
        """Decrementa el tiempo de espera de I/O y reactiva procesos cuando termina.

        Cada tick reduce el contador de espera. Cuando llega a cero, el proceso
        abandona WAITING y vuelve a READY para competir nuevamente por CPU.
        """
        completed_io = []
        for pcb in self.waiting_queue:
            pcb.io_wait_time -= 1
            if pcb.io_wait_time <= 0:
                completed_io.append(pcb)

        # Los procesos que terminaron I/O regresan a la cola de listos.
        for pcb in completed_io:
            self.waiting_queue.remove(pcb)
            pcb.transition(ProcessState.READY)
            self.ready_queue.append(pcb)
            self.logger.log(f"I/O COMPLETO: PID {pcb.pid} ({pcb.name}) -> READY", self.clock)

    def _select_next(self) -> PCB | None:
        """Selecciona el siguiente proceso de la cola de listos según el algoritmo.

        FCFS toma el primero en entrar.
        SJF elige el proceso con menor tiempo restante de CPU.
        """
        if not self.ready_queue:
            return None

        # El `match` permite decidir el despacho según la política configurada.
        match self.algorithm:
            case SchedulingAlgorithm.FCFS:
                return self.ready_queue.popleft()
            case SchedulingAlgorithm.SJF:
                # Encuentra el trabajo más corto sin desalojar al que ya está ejecutándose.
                shortest = min(self.ready_queue, key=lambda p: p.time_remaining)
                self.ready_queue.remove(shortest)
                return shortest

        return self.ready_queue.popleft()

    def _execute_tick(self, pcb: PCB) -> bool:
        """
        Avanza la ejecución del proceso actual en un tick.
        Simula solicitudes aleatorias de I/O (paso a WAITING).
        """
        # Un tick de CPU consume una unidad del tiempo restante del proceso.
        pcb.time_remaining -= 1
        self.logger.log(
            f"TICK: PID {pcb.pid} ({pcb.name}) | "
            f"Restante: {pcb.time_remaining}/{pcb.cpu_burst}",
            self.clock,
        )

        # Mientras el proceso aún no termine, puede solicitar I/O de forma aleatoria.
        if pcb.time_remaining > 0 and random.random() < IO_PROBABILITY:
            io_ticks: int = random.randint(IO_WAIT_MIN, IO_WAIT_MAX)
            pcb.io_wait_time = io_ticks
            pcb.transition(ProcessState.WAITING)
            
            # El proceso sale de CPU, pero mantiene su RAM reservada.
            self.resources.release(cpu=1, ram=0)
            self.waiting_queue.append(pcb)
            self.current_process = None

            self.logger.log(
                f"I/O REQUEST: PID {pcb.pid} ({pcb.name}) -> WAITING ({io_ticks} ticks)",
                self.clock,
            )
            return True
        return False

    def execute_cycle(self) -> str:
        """Ejecuta un ciclo completo del planificador.

        Un ciclo equivale a un tick de simulación. En cada tick se procesan
        llegadas, se avanza la espera por I/O y, si la CPU está libre, se
        selecciona un nuevo proceso para ejecutarse.
        """

        # El reloj avanza primero para que todos los eventos se evalúen en el nuevo tick.
        self.clock += 1
        self._handle_arrivals()
        self._handle_waiting()

        # Si la CPU está libre, el planificador intenta despachar un proceso.
        if self.current_process is None:
            next_pcb = self._select_next()
            if next_pcb is None:
                self.logger.log("IDLE: Cola vacia, CPU ociosa.", self.clock)
                return f"[Tick {self.clock}] CPU ociosa -- cola vacia."

            # Reserva CPU antes de mover el proceso a RUNNING.
            if not self.resources.request(cpu=1, ram=0):
                self.ready_queue.appendleft(next_pcb)
                return f"[Tick {self.clock}] No hay CPU disponible."

            next_pcb.transition(ProcessState.RUNNING)
            self.current_process = next_pcb
            self.logger.log(
                f"DISPATCH: PID {next_pcb.pid} ({next_pcb.name}) -> RUNNING "
                f"[{self.algorithm.name}]",
                self.clock,
            )

        assert self.current_process is not None
        # Ejecuta un tick real sobre el proceso que ocupa la CPU.
        io_requested = self._execute_tick(self.current_process)

        if io_requested:
            return f"[Tick {self.clock}] Proceso solicito I/O -> WAITING."

        # Si terminó su ráfaga, el proceso pasa a TERMINATED y se liberan recursos.
        if self.current_process.time_remaining <= 0:
            finished = self.current_process
            finished.transition(ProcessState.TERMINATED)
            finished.exit_reason = ExitReason.NORMAL
            
            # Se devuelven CPU y RAM al pool para que otros procesos puedan usarlos.
            self.resources.release(cpu=1, ram=finished.mem_mb)
            self.logger.log(
                f"TERMINADO: PID {finished.pid} ({finished.name}) completo.",
                self.clock,
            )
            self.current_process = None
            return f"[Tick {self.clock}] PID {finished.pid} TERMINADO."

        return f"[Tick {self.clock}] PID {self.current_process.pid} ejecutando."

    def is_simulation_complete(self) -> bool:
        """Retorna `True` si todos los procesos han terminado.

        Se usa como condición de parada principal del simulador.
        """
        if not self.all_processes:
            return True
        # La simulación termina cuando todos los procesos alcanzaron el estado final.
        return all(p.state == ProcessState.TERMINATED for p in self.all_processes)

    def set_algorithm(self, algorithm: SchedulingAlgorithm) -> None:
        """Cambia el algoritmo de planificación en uso.

        Esto permite alternar la política de despacho sin reconstruir todo el
        simulador, útil para comparar FCFS contra SJF en la misma ejecución.
        """
        self.algorithm = algorithm
        self.logger.log(f"ALGORITMO: {algorithm.name}", self.clock)

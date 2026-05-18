"""
Módulo: process.py — Bloque de Control de Proceso (PCB)

Este módulo concentra la representación de un proceso dentro del simulador.
Incluye:
- los estados posibles de un proceso,
- el motivo por el que puede terminar,
- la tabla estricta de transiciones válidas entre estados,
- y la clase `PCB`, que modela los datos y reglas del proceso.

La idea principal es que la lógica de estado no quede dispersa por el
resto del sistema: el propio PCB valida si una transición es legal y
mantiene su información coherente durante toda su vida útil.
"""

import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import ClassVar

class ProcessState(Enum):
    """Estados del ciclo de vida de un proceso en el simulador."""
    NEW = auto()
    READY = auto()
    RUNNING = auto()
    WAITING = auto()
    TERMINATED = auto()

class ExitReason(Enum):
    """Motivos posibles por los que un proceso puede terminar."""
    NORMAL = auto()
    ERROR = auto()
    DEADLOCK = auto()

# Matriz estricta de control de transiciones de estados de procesos (FSM).
#
# Cada clave representa el estado actual del proceso y cada valor contiene
# el conjunto de estados a los que sí se puede pasar. Si una transición no
# aparece aquí, se considera inválida.
VALID_TRANSITIONS: dict[ProcessState, frozenset[ProcessState]] = {
    # Un proceso nuevo solo puede pasar a la cola de listos.
    ProcessState.NEW: frozenset({ProcessState.READY}),
    # Desde READY solo se permite empezar a ejecutar.
    ProcessState.READY: frozenset({ProcessState.RUNNING}),
    # Mientras se ejecuta puede volver a READY por desalojo,
    # pasar a WAITING si solicita I/O o terminar definitivamente.
    ProcessState.RUNNING: frozenset({
        ProcessState.READY,
        ProcessState.WAITING,
        ProcessState.TERMINATED,
    }),
    # Cuando espera recursos o E/S, solo puede volver a READY.
    ProcessState.WAITING: frozenset({ProcessState.READY}),
    # TERMINATED es un estado final: no admite salidas.
    ProcessState.TERMINATED: frozenset(),
}

# Parámetros por defecto para la generación automática en modo batch.
# Se usan cuando el usuario no proporciona valores concretos y se quiere
# crear una simulación con procesos aleatorios pero válidos.
BURST_MIN: int = 3
BURST_MAX: int = 15
MEM_MIN: int = 64
MEM_MAX: int = 512
ARRIVAL_MIN: int = 0
ARRIVAL_MAX: int = 20

@dataclass
class PCB:
    """Bloque de Control de Proceso (Process Control Block).

    Un PCB reúne la información mínima que necesita el simulador para
    administrar un proceso: identificación, estado, memoria, tiempo de CPU
    pendiente y datos auxiliares de ejecución.

    La clase también encapsula reglas importantes:
    - asignación automática de PID,
    - generación aleatoria de atributos en modo batch,
    - validación de valores mínimos,
    - y control de transiciones válidas entre estados.
    """

    # Contador compartido por toda la clase para autogenerar PIDs únicos.
    # Cada instancia nueva toma el valor actual y luego incrementa el contador.
    _next_pid: ClassVar[int] = 1

    # Nombre visible del proceso en reportes, logs o interfaz gráfica.
    name: str = "Proceso"
    # Ráfaga total de CPU que el proceso necesita para completar su ejecución.
    cpu_burst: int = -1
    # Memoria requerida por el proceso, expresada en megabytes.
    mem_mb: int = -1
    # Momento de llegada del proceso al sistema, en ticks de simulación.
    arrival_time: int = -1

    # PID asignado automáticamente durante __post_init__.
    pid: int = field(init=False)
    # Estado actual del proceso. Empieza en NEW y evoluciona por transiciones válidas.
    state: ProcessState = field(init=False, default=ProcessState.NEW)
    # Tiempo de CPU que todavía falta por consumir.
    time_remaining: int = field(init=False)
    # Tiempo de espera por E/S. Se usa solo cuando el proceso está en WAITING.
    io_wait_time: int = field(init=False, default=0)
    # Razón final por la que el proceso terminó, si ya fue finalizado.
    exit_reason: ExitReason | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        # Se ejecuta inmediatamente después del __init__ generado por dataclass.
        # Aquí se completan los campos derivados y se validan los datos de entrada.

        # Asignación secuencial de PID. En el simulador se asume una ejecución
        # simple; por eso este contador funciona como un generador global de IDs.
        self.pid = PCB._next_pid
        PCB._next_pid += 1

        # Si el usuario no especifica un valor, se genera uno aleatorio dentro
        # de un rango razonable para que el proceso siga siendo válido.
        if self.cpu_burst == -1:
            self.cpu_burst = random.randint(BURST_MIN, BURST_MAX)
        if self.mem_mb == -1:
            self.mem_mb = random.randint(MEM_MIN, MEM_MAX)
        if self.arrival_time == -1:
            self.arrival_time = random.randint(ARRIVAL_MIN, ARRIVAL_MAX)

        # Validaciones básicas de integridad.
        # Se aplican después de la posible generación automática para asegurar
        # que el PCB nunca quede en un estado incoherente.
        if self.cpu_burst < 1:
            raise ValueError(f"cpu_burst debe ser >= 1, recibido: {self.cpu_burst}.")
        if self.mem_mb < 1:
            raise ValueError(f"mem_mb debe ser >= 1, recibido: {self.mem_mb}.")
        if self.arrival_time < 0:
            raise ValueError(f"arrival_time debe ser >= 0, recibido: {self.arrival_time}.")

        # Al iniciar, el tiempo restante de ejecución coincide con la ráfaga total.
        # A medida que el simulador consuma CPU, este valor irá disminuyendo.
        self.time_remaining = self.cpu_burst

    def transition(self, new_state: ProcessState) -> None:
        allowed: frozenset[ProcessState] = VALID_TRANSITIONS.get(self.state, frozenset())

        # Si el estado destino no está permitido, la transición se rechaza.
        # Esto ayuda a detectar errores del planificador o de la lógica de E/S.
        if new_state not in allowed:
            raise ValueError(
                f"Transicion INVALIDA: {self.state.name} -> {new_state.name} "
                f"para PID={self.pid}."
            )

        # Solo cuando la transición es válida se actualiza el estado real.
        self.state = new_state

    def __str__(self) -> str:
        # Se muestran solo los datos opcionales que realmente aplican al estado actual.
        exit_info: str = f" | Razón: {self.exit_reason.name}" if self.exit_reason else ""
        io_info: str = f" | I/O: {self.io_wait_time} ticks" if self.state == ProcessState.WAITING and self.io_wait_time > 0 else ""

        return (
            f"[PID {self.pid:>3}] {self.name:<15} | "
            f"Estado: {self.state.name:<10} | "
            f"CPU: {self.time_remaining}/{self.cpu_burst} ticks | "
            f"RAM: {self.mem_mb} MB | "
            f"Llegada: t={self.arrival_time}{io_info}{exit_info}"
        )

    @classmethod
    def reset_pid_counter(cls) -> None:
        cls._next_pid = 1

#contador de la clase para autogenerar PIDs
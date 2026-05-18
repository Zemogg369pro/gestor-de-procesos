"""
main.py — Interfaz Gráfica del Simulador de Gestor de Procesos (Modo Batch)

Proporciona la GUI principal mediante Tkinter para configurar y
ejecutar una simulación automática por lotes del sistema operativo.
"""

import sys
import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox

# Habilita resolución de imports desde el directorio raíz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.process import PCB, ProcessState
from src.core.resource import ResourcePool
from src.core.scheduler import Scheduler, SchedulingAlgorithm
from src.ui.logger import Logger
from src.ipc.producer_consumer import run_demo as ipc_demo

class SimulatorGUI:
    """Interfaz gráfica principal del Simulador de SO."""

    TICK_SPEED_MS: int = 500

    def __init__(self, root: tk.Tk) -> None:
        self.root: tk.Tk = root
        self.root.title("Simulador de SO — Modo Batch Automático")
        self.root.geometry("1050x720")
        self.root.resizable(False, False)

        # Inicialización de subsistemas del Kernel virtual
        self.logger: Logger = Logger(verbose=True)
        self.resources: ResourcePool = ResourcePool(cpu_cores=1, ram_mb=4096)
        self.scheduler: Scheduler = Scheduler(
            resources=self.resources,
            logger=self.logger,
            algorithm=SchedulingAlgorithm.FCFS,
        )

        # Variables de estado y control de ciclo Tkinter
        self._simulation_running: bool = False
        self._after_id: str | None = None

        self._build_ui()
        self.update_ui()

    def _build_ui(self) -> None:
        """Construye los elementos de la interfaz."""
        
        # --- Panel de Configuración de Lote ---
        self.frame_config = tk.LabelFrame(
            self.root, text="1. Configuración de la Simulación", padx=10, pady=10
        )
        self.frame_config.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(self.frame_config, text="Número de Procesos:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.entry_num_processes = tk.Entry(self.frame_config, width=8, font=("Arial", 10))
        self.entry_num_processes.insert(0, "10")
        self.entry_num_processes.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.frame_config, text="Algoritmo:", font=("Arial", 10)).grid(row=0, column=2, padx=(20, 5), pady=5, sticky=tk.W)
        self.algo_var = tk.StringVar(value="FCFS")
        self.combo_algo = ttk.Combobox(
            self.frame_config, textvariable=self.algo_var, state="readonly", width=10, font=("Arial", 10)
        )
        self.combo_algo['values'] = ("FCFS", "SJF")
        self.combo_algo.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(self.frame_config, text="Velocidad (ms/tick):", font=("Arial", 10)).grid(row=0, column=4, padx=(20, 5), pady=5, sticky=tk.W)
        self.speed_var = tk.IntVar(value=500)
        self.speed_slider = tk.Scale(
            self.frame_config, from_=100, to=1500, orient=tk.HORIZONTAL, variable=self.speed_var, length=150, showvalue=True
        )
        self.speed_slider.grid(row=0, column=5, padx=5, pady=5)

        # --- Panel de Controles y Acciones ---
        self.frame_control = tk.LabelFrame(self.root, text="2. Panel de Control", padx=10, pady=10)
        self.frame_control.pack(fill=tk.X, padx=10, pady=5)

        self.btn_start = tk.Button(
            self.frame_control, text="▶  Iniciar Simulación", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=22, command=self.on_start_simulation
        )
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_reset = tk.Button(
            self.frame_control, text="↻ Reiniciar", bg="#FF9800", fg="white", font=("Arial", 10, "bold"), command=self.on_reset_simulation
        )
        self.btn_reset.pack(side=tk.LEFT, padx=5)

        self.btn_ipc = tk.Button(self.frame_control, text="Demo IPC", font=("Arial", 10), command=self.on_run_ipc)
        self.btn_ipc.pack(side=tk.LEFT, padx=(15, 5))

        self.btn_logs = tk.Button(self.frame_control, text="Logs", font=("Arial", 10), command=self.on_view_logs)
        self.btn_logs.pack(side=tk.LEFT, padx=5)

        self.lbl_clock = tk.Label(self.frame_control, text="Reloj: 0", font=("Arial", 14, "bold"))
        self.lbl_clock.pack(side=tk.RIGHT, padx=10)

        self.lbl_status = tk.Label(self.frame_control, text="● DETENIDO", fg="red", font=("Arial", 10, "bold"))
        self.lbl_status.pack(side=tk.RIGHT, padx=10)

        # --- Panel de Monitoreo de Estado ---
        self.frame_monitor = tk.LabelFrame(self.root, text="3. Monitoreo del Sistema (Colas y Estados)", padx=10, pady=10)
        self.frame_monitor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Columna de Hardware y Stats
        self.frame_col1 = tk.Frame(self.frame_monitor)
        self.frame_col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.lbl_cpu = tk.Label(self.frame_col1, text="CPU Disponible: 1 / 1", font=("Arial", 10))
        self.lbl_cpu.pack(anchor=tk.W, pady=2)

        self.lbl_ram = tk.Label(self.frame_col1, text="RAM Disponible: 4096 / 4096 MB", font=("Arial", 10))
        self.lbl_ram.pack(anchor=tk.W, pady=2)

        self.lbl_counters = tk.Label(self.frame_col1, text="NEW: 0 | READY: 0 | WAITING: 0 | TERMINATED: 0", font=("Arial", 9), fg="#555555")
        self.lbl_counters.pack(anchor=tk.W, pady=2)

        tk.Label(self.frame_col1, text="\nProceso en Ejecución:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.lbl_running = tk.Label(self.frame_col1, text="[ Ninguno ]", font=("Consolas", 11), fg="blue")
        self.lbl_running.pack(anchor=tk.W, pady=5)

        tk.Label(self.frame_col1, text="Progreso de la Simulación:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 2))
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.frame_col1, variable=self.progress_var, maximum=100, length=250)
        self.progress_bar.pack(anchor=tk.W, pady=2)
        self.lbl_progress = tk.Label(self.frame_col1, text="0 / 0 procesos completados", font=("Arial", 9))
        self.lbl_progress.pack(anchor=tk.W, pady=2)

        # Columna de Cola Ready
        self.frame_col2 = tk.Frame(self.frame_monitor)
        self.frame_col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(self.frame_col2, text="Cola de Listos (READY):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.listbox_ready = tk.Listbox(self.frame_col2, height=12, width=40, font=("Consolas", 9))
        self.listbox_ready.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        self.scroll_ready = tk.Scrollbar(self.frame_col2, orient="vertical", command=self.listbox_ready.yview)
        self.scroll_ready.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.listbox_ready.config(yscrollcommand=self.scroll_ready.set)

        # Columna de Cola Waiting
        self.frame_col3 = tk.Frame(self.frame_monitor)
        self.frame_col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(self.frame_col3, text="En Espera I/O (WAITING):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.listbox_waiting = tk.Listbox(self.frame_col3, height=12, width=40, font=("Consolas", 9))
        self.listbox_waiting.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        self.scroll_waiting = tk.Scrollbar(self.frame_col3, orient="vertical", command=self.listbox_waiting.yview)
        self.scroll_waiting.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.listbox_waiting.config(yscrollcommand=self.scroll_waiting.set)

        # --- Panel de Procesos Terminados ---
        self.frame_terminated = tk.LabelFrame(self.root, text="4. Procesos Terminados", padx=10, pady=5)
        self.frame_terminated.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.listbox_terminated = tk.Listbox(self.frame_terminated, height=4, width=120, font=("Consolas", 9))
        self.listbox_terminated.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=2)
        self.scroll_terminated = tk.Scrollbar(self.frame_terminated, orient="vertical", command=self.listbox_terminated.yview)
        self.scroll_terminated.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
        self.listbox_terminated.config(yscrollcommand=self.scroll_terminated.set)

    def on_start_simulation(self) -> None:
        """Inicia, pausa o reanuda la simulación automática."""
        
        # Funcionalidad de Pausado Dinámico
        if self._simulation_running:
            self._simulation_running = False
            if self._after_id is not None:
                self.root.after_cancel(self._after_id)
                self._after_id = None
            self.btn_start.config(text="▶  Reanudar Simulación", bg="#4CAF50")
            self.lbl_status.config(text="● PAUSADO", fg="#FF9800")
            self.entry_num_processes.config(state=tk.NORMAL)
            self.combo_algo.config(state="readonly")
            return

        # Generación de procesos si es la primera ejecución
        if not self.scheduler.all_processes:
            try:
                num_procs: int = int(self.entry_num_processes.get())
                if num_procs < 1 or num_procs > 100:
                    messagebox.showerror("Error", "Ingrese un número entre 1 y 100.")
                    return
            except ValueError:
                messagebox.showerror("Error", "Ingrese un valor numérico válido.")
                return

            # Configura algoritmo según el UI Combobox
            seleccion: str = self.algo_var.get()
            if seleccion == "FCFS":
                self.scheduler.set_algorithm(SchedulingAlgorithm.FCFS)
            elif seleccion == "SJF":
                self.scheduler.set_algorithm(SchedulingAlgorithm.SJF)

            # Instanciación e ingreso masivo en estado NEW
            for i in range(1, num_procs + 1):
                pcb = PCB(name=f"P{i:02d}")
                self.scheduler.register_process(pcb)

            self.logger.log(f"BATCH: Generados {num_procs} procesos.", self.scheduler.clock)

        # Bloquea opciones de configuración mientras se corre
        self.entry_num_processes.config(state=tk.DISABLED)
        self.combo_algo.config(state=tk.DISABLED)

        # Actualiza visuales de arranque
        self._simulation_running = True
        self.btn_start.config(text="⏸  Pausar Simulación", bg="#F44336")
        self.lbl_status.config(text="● EJECUTANDO", fg="#4CAF50")
        self.update_ui()

        # Inicia loop de simulación no bloqueante (Event Loop Pattern)
        self._after_id = self.root.after(self.speed_var.get(), self._auto_tick)

    def _auto_tick(self) -> None:
        """Avanza la simulación un tick y programa el siguiente."""
        if not self._simulation_running:
            return

        # Core OS Dispatch logic
        self.scheduler.execute_cycle()
        self.update_ui()

        # Verifica clausura y termina simulación
        if self.scheduler.is_simulation_complete():
            self._simulation_running = False
            self.btn_start.config(text="✓  Simulación Completada", bg="#607D8B", state=tk.DISABLED)
            self.lbl_status.config(text="● COMPLETADO", fg="#2196F3")

            total: int = len(self.scheduler.all_processes)
            total_burst: int = sum(p.cpu_burst for p in self.scheduler.all_processes)
            self.logger.log(
                f"SIMULACIÓN COMPLETA: {total} procesos en {self.scheduler.clock} ticks. "
                f"Burst acumulado: {total_burst} ticks.",
                self.scheduler.clock,
            )
            messagebox.showinfo(
                "Simulación Completa",
                f"Todos los {total} procesos han terminado.\n"
                f"Ticks totales: {self.scheduler.clock}\n"
                f"Algoritmo: {self.scheduler.algorithm.name}",
            )
            return

        # Programa el siguiente salto iterativo basado en slider
        self._after_id = self.root.after(self.speed_var.get(), self._auto_tick)

    def on_reset_simulation(self) -> None:
        """Restablece el estado del kernel y purga elementos de la interfaz."""
        self._simulation_running = False
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

        # Reset global de Singletons
        PCB.reset_pid_counter()

        # Re-instanciación del hardware y OS base
        self.logger = Logger(verbose=True)
        self.resources = ResourcePool(cpu_cores=1, ram_mb=4096)
        self.scheduler = Scheduler(
            resources=self.resources,
            logger=self.logger,
            algorithm=SchedulingAlgorithm.FCFS,
        )

        # Habilita inputs nuevamente
        self.entry_num_processes.config(state=tk.NORMAL)
        self.combo_algo.config(state="readonly")
        self.btn_start.config(text="▶  Iniciar Simulación", bg="#4CAF50", state=tk.NORMAL)
        self.lbl_status.config(text="● DETENIDO", fg="red")
        self.algo_var.set("FCFS")

        self.update_ui()

    def on_view_logs(self) -> None:
        """Renderiza una ventana Toplevel con historial del Kernel."""
        top = tk.Toplevel(self.root)
        top.title("Historial de Logs del Sistema")
        top.geometry("750x450")

        text_area = tk.Text(top, font=("Consolas", 10), bg="#1e1e1e", fg="#00ff00")
        text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        if not self.logger.entries:
            text_area.insert(tk.END, "No hay eventos registrados aún.\n")
        else:
            for entry in self.logger.entries:
                text_area.insert(tk.END, f"{entry}\n")

        text_area.see(tk.END)
        text_area.config(state=tk.DISABLED)

    def on_run_ipc(self) -> None:
        """Inicia una ventana con la ejecución del script Productor-Consumidor multi-hilo."""
        top = tk.Toplevel(self.root)
        top.title("Demo IPC: Productor - Consumidor (Hilos)")
        top.geometry("600x400")

        text_area = tk.Text(top, font=("Consolas", 10), bg="#2d2d2d", fg="#ffffff")
        text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Cola IPC para sincronizar texto de un hilo secundario hacia el hilo de Tkinter
        msg_queue: queue.Queue[str | None] = queue.Queue()

        class RedirectText:
            """Adaptador de stream stdOut hacia una Queue thread-safe."""
            def __init__(self, q: queue.Queue) -> None:
                self.q = q
            def write(self, string: str) -> None:
                self.q.put(string)
            def flush(self) -> None:
                pass

        def poll_queue() -> None:
            """Desencola los logs escritos y renderiza el texto en GUI."""
            while not msg_queue.empty():
                try:
                    msg = msg_queue.get_nowait()
                    if msg is None:
                        text_area.config(state=tk.DISABLED)
                        return
                    text_area.insert(tk.END, msg)
                    text_area.see(tk.END)
                except queue.Empty:
                    break
            if top.winfo_exists():
                top.after(50, poll_queue)

        def run_demo_thread() -> None:
            """Hilo Wrapper para llamar a IPC sin congelar interfaz principal."""
            old_stdout = sys.stdout
            sys.stdout = RedirectText(msg_queue)
            try:
                ipc_demo()
                print("\n[+] Demo finalizada exitosamente.")
            except Exception as e:
                print(f"\n[!] Error en demo: {e}")
            finally:
                sys.stdout = old_stdout
                msg_queue.put(None)

        poll_queue()
        threading.Thread(target=run_demo_thread, daemon=True).start()

    def update_ui(self) -> None:
        """Actualiza asincronamente los componentes visuales iterando sobre las estructuras del OS."""
        self.lbl_clock.config(text=f"Reloj: {self.scheduler.clock}")

        # Render métricas de Hardware
        res: ResourcePool = self.scheduler.resources
        self.lbl_cpu.config(text=f"CPU Disponible: {res.available_cpu} / {res.total_cpu}")
        self.lbl_ram.config(text=f"RAM Disponible: {res.available_ram} / {res.total_ram} MB")

        # Render Estados contadores
        count_new: int = sum(1 for p in self.scheduler.all_processes if p.state == ProcessState.NEW)
        count_ready: int = len(self.scheduler.ready_queue)
        count_waiting: int = len(self.scheduler.waiting_queue)
        count_terminated: int = sum(1 for p in self.scheduler.all_processes if p.state == ProcessState.TERMINATED)
        
        self.lbl_counters.config(
            text=f"NEW: {count_new} | READY: {count_ready} | WAITING: {count_waiting} | TERMINATED: {count_terminated}"
        )

        # Contexto de RUNNING
        current: PCB | None = self.scheduler.current_process
        if current:
            texto_running: str = f"PID {current.pid} ({current.name})\nRestante: {current.time_remaining}/{current.cpu_burst} ticks"
            self.lbl_running.config(text=texto_running, fg="dark green")
        else:
            self.lbl_running.config(text="[ Ninguno - CPU Ociosa ]", fg="red")

        # Refresca las ListBoxes re-calculando sus elementos
        self.listbox_ready.delete(0, tk.END)
        for p in self.scheduler.ready_queue:
            self.listbox_ready.insert(tk.END, f"PID {p.pid:2} | Burst: {p.time_remaining:2}/{p.cpu_burst:2} | RAM: {p.mem_mb:4}MB | {p.name}")

        self.listbox_waiting.delete(0, tk.END)
        for p in self.scheduler.waiting_queue:
            self.listbox_waiting.insert(tk.END, f"PID {p.pid:2} | I/O: {p.io_wait_time:2} ticks | Burst: {p.time_remaining:2}/{p.cpu_burst:2} | {p.name}")

        self.listbox_terminated.delete(0, tk.END)
        terminated_list: list[PCB] = [p for p in self.scheduler.all_processes if p.state == ProcessState.TERMINATED]
        for p in terminated_list:
            reason: str = p.exit_reason.name if p.exit_reason else "?"
            self.listbox_terminated.insert(tk.END, f"PID {p.pid:2} | {p.name:6} | Burst: {p.cpu_burst:2} ticks | RAM: {p.mem_mb:4}MB | Razón: {reason}")

        # Cálculos porcentuales progressbar
        total: int = len(self.scheduler.all_processes)
        if total > 0:
            progress: float = (count_terminated / total) * 100
            self.progress_var.set(progress)
            self.lbl_progress.config(text=f"{count_terminated} / {total} procesos completados")
        else:
            self.progress_var.set(0)
            self.lbl_progress.config(text="0 / 0 procesos completados")

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulatorGUI(root)
    root.mainloop()

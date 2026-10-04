import sys
import os
import time
import subprocess
import platform
import psutil
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QLabel, QMessageBox, QMenu, QLineEdit, QHBoxLayout,
    QFormLayout, QGroupBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap

def bytes2human(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return f"{value:.1f} {s}B"
    return f"{n} B"

def get_cpu_model():
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    return line.split(":")[1].strip()
    except:
        pass
    return platform.processor() or "Unknown CPU"

def get_gpu_name():
    try:
        out = subprocess.check_output("lspci | grep -i vga", shell=True, text=True)
        parts = out.split(":", 2)
        if len(parts) > 2:
            return parts[2].strip()
    except:
        pass
    return "Unknown or No Dedicated GPU"

class TaskManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dave's System Information")
        self.resize(900, 700)

        # Initialize Data
        self.num_cores = psutil.cpu_count(logical=True)
        self.cpu_history = {i: [0] * 60 for i in range(self.num_cores)}
        self.mem_history = [0] * 60
        
        self.disk_read_history = [0] * 60
        self.disk_write_history = [0] * 60
        self.last_disk_io = psutil.disk_io_counters()

        self.net_recv_history = [0] * 60
        self.net_sent_history = [0] * 60
        self.last_net_io = psutil.net_io_counters()

        self.boot_time = psutil.boot_time()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Setup all tabs
        self.setup_overview_tab()
        self.setup_processes_tab()
        self.setup_performance_tab()
        self.setup_disk_tab()
        self.setup_network_tab()

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.update_data()
        self.timer.start(2000)

    # --- 1. SETUP OVERVIEW TAB ---
    def setup_overview_tab(self):
        self.overview_tab = QWidget()
        main_layout = QVBoxLayout(self.overview_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Wrap everything in a Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content_widget = QWidget()
        self.overview_layout = QVBoxLayout(content_widget)
        
        # 1. System Overview
        group = QGroupBox("System Overview")
        form = QFormLayout()
        
        self.lbl_os = QLabel(f"{platform.system()} {platform.release()}")
        self.lbl_kernel = QLabel(platform.version())
        self.lbl_cpu = QLabel(get_cpu_model())
        self.lbl_gpu = QLabel(get_gpu_name())
        self.lbl_ram = QLabel(bytes2human(psutil.virtual_memory().total))
        self.lbl_uptime = QLabel("Calculating...")
        
        form.addRow("Operating System:", self.lbl_os)
        form.addRow("Kernel Version:", self.lbl_kernel)
        form.addRow("Processor (CPU):", self.lbl_cpu)
        form.addRow("Graphics (GPU):", self.lbl_gpu)
        form.addRow("Total Physical RAM:", self.lbl_ram)
        form.addRow("System Uptime:", self.lbl_uptime)
        
        group.setLayout(form)
        self.overview_layout.addWidget(group)

        # 2. Logo
        self.logo_label = QLabel()
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS # When built by PyInstaller
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        logo_path = os.path.join(base_path, "logo.jpg")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Make the logo big
            pixmap = pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
            self.logo_label.setAlignment(Qt.AlignCenter)
            self.overview_layout.addWidget(self.logo_label)
            
        # 3. Mission Statement
        mission_text = (
            "<div style='text-align: center;'>"
            "<h2 style='color: #3498db; margin-bottom: 10px;'>Dave's Linux Software Solutions</h2>"
            "<p style='font-size: 16px; line-height: 1.6; max-width: 800px; margin: 0 auto;'>"
            "Welcome to Dave's Linux Software Solutions, where we build open-source tools, "
            "custom desktop integrations, and specialized automated systems with one simple mission:<br><br>"
            "<b><i>\"Let's make Linux friendly.\"</i></b><br><br>"
            "Whether you are a long-time user setting up a private home server or a beginner tailoring "
            "a desktop environment for gaming and daily workflows, our software bridges the gap between "
            "deep technical capability and smooth, accessible user experiences.<br><br>"
            "From optimizing system tools to creating intelligent automation pipelines, we create "
            "dependable solutions designed to make using your favorite Linux distributions "
            "straightforward, intuitive, and efficient."
            "</p></div>"
        )
        self.mission_label = QLabel(mission_text)
        self.mission_label.setWordWrap(True)
        self.mission_label.setAlignment(Qt.AlignCenter)
        self.mission_label.setContentsMargins(20, 20, 20, 40)
        
        self.overview_layout.addWidget(self.mission_label)
        self.overview_layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        self.tabs.addTab(self.overview_tab, "Overview")

    # --- 2. SETUP PROCESSES TAB ---
    def setup_processes_tab(self):
        self.processes_tab = QWidget()
        self.processes_layout = QVBoxLayout(self.processes_tab)

        # Search Bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by Name or PID...")
        self.search_input.textChanged.connect(self.update_processes)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        self.processes_layout.addLayout(search_layout)

        self.process_table = QTableWidget(0, 5)
        self.process_table.setHorizontalHeaderLabels(["PID", "Name", "User", "CPU %", "Memory %"])
        self.process_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.process_table.horizontalHeader().setStretchLastSection(True)
        self.process_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.process_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.process_table.itemDoubleClicked.connect(self.on_process_double_clicked)
        self.process_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.process_table.customContextMenuRequested.connect(self.show_context_menu)

        self.processes_layout.addWidget(self.process_table)
        self.tabs.addTab(self.processes_tab, "Processes")

    # --- 3. SETUP PERFORMANCE TAB ---
    def setup_performance_tab(self):
        self.performance_tab = QWidget()
        self.performance_layout = QVBoxLayout(self.performance_tab)

        # Memory Graph
        self.mem_graph = pg.PlotWidget(title="Global Memory Usage (%)")
        self.mem_graph.setYRange(0, 100)
        self.mem_graph.showGrid(x=True, y=True)
        self.mem_graph.setMouseEnabled(x=False, y=False)
        self.mem_graph.setMenuEnabled(False)
        self.mem_graph.setFixedHeight(150)
        self.mem_curve = self.mem_graph.plot(pen=pg.mkPen(color=(150, 50, 250), width=2))
        self.performance_layout.addWidget(self.mem_graph)

        # Scrollable area for CPU cores
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QGridLayout(self.scroll_widget)
        
        self.cpu_graphs = []
        self.cpu_curves = []
        self.cpu_labels = []

        cols = 2
        for i in range(self.num_cores):
            container = QWidget()
            layout = QVBoxLayout(container)
            
            label = QLabel(f"Core {i} - 0% - Temp: N/A")
            font = label.font()
            font.setBold(True)
            label.setFont(font)
            layout.addWidget(label)
            
            graph = pg.PlotWidget()
            graph.setYRange(0, 100)
            graph.showGrid(x=True, y=True)
            graph.setMouseEnabled(x=False, y=False)
            graph.setMenuEnabled(False)
            graph.setFixedHeight(100)
            
            hue = (i * 137.5) % 360
            color = pg.hsvColor(hue / 360.0, 0.8, 0.9)
            curve = graph.plot(pen=pg.mkPen(color=color, width=1.5))
            
            layout.addWidget(graph)
            
            self.cpu_graphs.append(graph)
            self.cpu_curves.append(curve)
            self.cpu_labels.append(label)
            
            row = i // cols
            col = i % cols
            self.scroll_layout.addWidget(container, row, col)

        self.scroll_area.setWidget(self.scroll_widget)
        self.performance_layout.addWidget(self.scroll_area)

        self.tabs.addTab(self.performance_tab, "Performance")

    # --- 4. SETUP DISK TAB ---
    def setup_disk_tab(self):
        self.disk_tab = QWidget()
        self.disk_layout = QVBoxLayout(self.disk_tab)

        self.disk_table = QTableWidget(0, 7)
        self.disk_table.setHorizontalHeaderLabels([
            "Device", "Mount Point", "FS Type", "Total", "Used", "Free", "Use %"
        ])
        self.disk_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.disk_table.horizontalHeader().setStretchLastSection(True)
        self.disk_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.disk_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.disk_layout.addWidget(self.disk_table)

        self.disk_graph = pg.PlotWidget(title="Global Disk I/O Activity (MB/s)")
        self.disk_graph.showGrid(x=True, y=True)
        self.disk_graph.setMouseEnabled(x=False, y=False)
        self.disk_graph.setMenuEnabled(False)
        self.disk_graph.addLegend()
        self.disk_read_curve = self.disk_graph.plot(pen=pg.mkPen(color=(50, 200, 50), width=2), name="Read (MB/s)")
        self.disk_write_curve = self.disk_graph.plot(pen=pg.mkPen(color=(250, 50, 50), width=2), name="Write (MB/s)")
        self.disk_layout.addWidget(self.disk_graph)

        self.tabs.addTab(self.disk_tab, "Disk")

    # --- 5. SETUP NETWORK TAB ---
    def setup_network_tab(self):
        self.net_tab = QWidget()
        self.net_layout = QVBoxLayout(self.net_tab)

        self.net_table = QTableWidget(0, 5)
        self.net_table.setHorizontalHeaderLabels([
            "Interface", "Bytes Sent", "Bytes Recv", "Packets Sent", "Packets Recv"
        ])
        self.net_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.net_table.horizontalHeader().setStretchLastSection(True)
        self.net_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.net_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.net_layout.addWidget(self.net_table)

        self.net_graph = pg.PlotWidget(title="Global Network Traffic (KB/s)")
        self.net_graph.showGrid(x=True, y=True)
        self.net_graph.setMouseEnabled(x=False, y=False)
        self.net_graph.setMenuEnabled(False)
        self.net_graph.addLegend()
        self.net_sent_curve = self.net_graph.plot(pen=pg.mkPen(color=(50, 150, 250), width=2), name="Upload (KB/s)")
        self.net_recv_curve = self.net_graph.plot(pen=pg.mkPen(color=(250, 150, 50), width=2), name="Download (KB/s)")
        self.net_layout.addWidget(self.net_graph)

        self.tabs.addTab(self.net_tab, "Network")

    # --- UPDATE LOGIC ---
    def update_data(self):
        self.update_overview()
        self.update_processes()
        self.update_performance()
        self.update_disk()
        self.update_network()

    def update_overview(self):
        uptime_seconds = time.time() - self.boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        self.lbl_uptime.setText(f"{days} days, {hours} hours, {minutes} minutes")

    def get_core_temps(self):
        temps_dict = {}
        if not hasattr(psutil, "sensors_temperatures"): return temps_dict
        try:
            sensors = psutil.sensors_temperatures()
            for name, entries in sensors.items():
                for entry in entries:
                    if entry.label.startswith("Core"):
                        try:
                            core_idx = int(entry.label.split()[1])
                            temps_dict[core_idx] = entry.current
                        except: pass
                    elif "Tdie" in entry.label or "Tctl" in entry.label or "Package" in entry.label:
                        temps_dict['global'] = entry.current
        except: pass
        return temps_dict

    def update_performance(self):
        cpu_percents = psutil.cpu_percent(interval=None, percpu=True)
        mem = psutil.virtual_memory().percent
        temps = self.get_core_temps()
        global_temp = temps.get('global', 'N/A')

        for i in range(self.num_cores):
            self.cpu_history[i] = self.cpu_history[i][1:] + [cpu_percents[i]]
            self.cpu_curves[i].setData(self.cpu_history[i])
            t = temps.get(i, global_temp)
            temp_str = f"{t}°C" if t != 'N/A' else "N/A"
            self.cpu_labels[i].setText(f"Core {i} - {cpu_percents[i]:.1f}% - Temp: {temp_str}")

        self.mem_history = self.mem_history[1:] + [mem]
        self.mem_curve.setData(self.mem_history)

    def update_disk(self):
        try:
            partitions = psutil.disk_partitions(all=False)
            self.disk_table.setRowCount(len(partitions))
            for row, p in enumerate(partitions):
                try: usage = psutil.disk_usage(p.mountpoint)
                except: continue
                def make_item(val): return QTableWidgetItem(str(val))
                self.disk_table.setItem(row, 0, make_item(p.device))
                self.disk_table.setItem(row, 1, make_item(p.mountpoint))
                self.disk_table.setItem(row, 2, make_item(p.fstype))
                self.disk_table.setItem(row, 3, make_item(bytes2human(usage.total)))
                self.disk_table.setItem(row, 4, make_item(bytes2human(usage.used)))
                self.disk_table.setItem(row, 5, make_item(bytes2human(usage.free)))
                self.disk_table.setItem(row, 6, make_item(f"{usage.percent}%"))
        except: pass

        try:
            current_io = psutil.disk_io_counters()
            if current_io and self.last_disk_io:
                read_bps = (current_io.read_bytes - self.last_disk_io.read_bytes) / 2.0
                write_bps = (current_io.write_bytes - self.last_disk_io.write_bytes) / 2.0
                read_mbs = read_bps / (1024 * 1024)
                write_mbs = write_bps / (1024 * 1024)
                self.disk_read_history = self.disk_read_history[1:] + [read_mbs]
                self.disk_write_history = self.disk_write_history[1:] + [write_mbs]
                self.disk_read_curve.setData(self.disk_read_history)
                self.disk_write_curve.setData(self.disk_write_history)
            self.last_disk_io = current_io
        except: pass

    def update_network(self):
        try:
            net_io = psutil.net_io_counters(pernic=True)
            self.net_table.setRowCount(len(net_io))
            for row, (nic, stats) in enumerate(net_io.items()):
                def make_item(val): return QTableWidgetItem(str(val))
                self.net_table.setItem(row, 0, make_item(nic))
                self.net_table.setItem(row, 1, make_item(bytes2human(stats.bytes_sent)))
                self.net_table.setItem(row, 2, make_item(bytes2human(stats.bytes_recv)))
                self.net_table.setItem(row, 3, make_item(stats.packets_sent))
                self.net_table.setItem(row, 4, make_item(stats.packets_recv))
        except: pass

        try:
            current_net = psutil.net_io_counters()
            if current_net and self.last_net_io:
                sent_bps = (current_net.bytes_sent - self.last_net_io.bytes_sent) / 2.0
                recv_bps = (current_net.bytes_recv - self.last_net_io.bytes_recv) / 2.0
                sent_kbs = sent_bps / 1024
                recv_kbs = recv_bps / 1024
                self.net_sent_history = self.net_sent_history[1:] + [sent_kbs]
                self.net_recv_history = self.net_recv_history[1:] + [recv_kbs]
                self.net_sent_curve.setData(self.net_sent_history)
                self.net_recv_curve.setData(self.net_recv_history)
            self.last_net_io = current_net
        except: pass

    def update_processes(self):
        scroll_pos = self.process_table.verticalScrollBar().value()
        selected_rows = [item.row() for item in self.process_table.selectedItems()]
        selected_pid = None
        if selected_rows:
            pid_item = self.process_table.item(selected_rows[0], 0)
            if pid_item: selected_pid = pid_item.text()

        self.process_table.setSortingEnabled(False)
        search_query = self.search_input.text().lower()
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent']):
            try:
                pinfo = proc.info
                if search_query:
                    if search_query not in str(pinfo['name']).lower() and search_query not in str(pinfo['pid']):
                        continue
                pinfo['cpu_percent'] = proc.cpu_percent(interval=None) 
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): pass
        
        self.process_table.setRowCount(len(processes))
        new_selection_row = -1

        for row, proc in enumerate(processes):
            def make_item(val, is_number=False):
                item = QTableWidgetItem()
                if is_number: item.setData(Qt.ItemDataRole.DisplayRole, val)
                else: item.setText(str(val))
                return item

            pid_str = str(proc['pid'])
            if pid_str == selected_pid: new_selection_row = row

            self.process_table.setItem(row, 0, make_item(proc['pid'], is_number=True))
            self.process_table.setItem(row, 1, make_item(proc['name']))
            self.process_table.setItem(row, 2, make_item(proc['username']))
            cpu_val = proc.get('cpu_percent', 0.0)
            self.process_table.setItem(row, 3, make_item(round(cpu_val, 1) if cpu_val else 0.0, is_number=True))
            mem_val = proc.get('memory_percent', 0.0)
            self.process_table.setItem(row, 4, make_item(round(mem_val, 1) if mem_val else 0.0, is_number=True))
            
        self.process_table.setSortingEnabled(True)
        if new_selection_row != -1: self.process_table.selectRow(new_selection_row)
        self.process_table.verticalScrollBar().setValue(scroll_pos)

    # Process Management
    def show_context_menu(self, position):
        row = self.process_table.rowAt(position.y())
        if row < 0: return
        pid_item = self.process_table.item(row, 0)
        name_item = self.process_table.item(row, 1)
        if not pid_item or not name_item: return
        pid = int(pid_item.text())
        name = name_item.text()

        menu = QMenu()
        kill_action = menu.addAction(f"End Task: {name} (PID: {pid})")
        action = menu.exec_(self.process_table.viewport().mapToGlobal(position))
        if action == kill_action: self.kill_process(pid, name)

    def on_process_double_clicked(self, item):
        row = item.row()
        pid_item = self.process_table.item(row, 0)
        name_item = self.process_table.item(row, 1)
        if not pid_item or not name_item: return
        pid = int(pid_item.text())
        name = name_item.text()
        self.kill_process(pid, name)

    def kill_process(self, pid, name):
        reply = QMessageBox.question(
            self, 'Confirm End Task',
            f"Are you sure you want to kill '{name}' (PID: {pid})?\n\nKilling a process may cause data loss or system instability.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                p = psutil.Process(pid)
                p.terminate()
            except psutil.NoSuchProcess:
                QMessageBox.warning(self, 'Error', f"Process {pid} no longer exists.")
            except psutil.AccessDenied:
                QMessageBox.critical(self, 'Error', f"Access denied. You may need root privileges to kill {name}.")
            except Exception as e:
                QMessageBox.critical(self, 'Error', f"Could not kill process: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TaskManager()
    window.show()
    sys.exit(app.exec_())

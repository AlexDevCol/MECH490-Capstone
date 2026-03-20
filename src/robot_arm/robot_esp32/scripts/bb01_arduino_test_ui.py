#!/usr/bin/env python3
"""
BB01 Arduino Test UI (Tkinter + pyserial)

Human-facing joint inputs are degrees. On the wire, joint values are radians.

TX:  cmd,j1_rad,...,j6_rad,gripper_deg (newline-terminated)
RX:  fb,j1_rad,...,j6_rad,gripper_deg (newline-terminated);
     plus bb01_test_ready once after ESP setup (firmware banner).
"""

from __future__ import annotations

import math
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import serial
from serial.tools import list_ports

NUM_JOINTS = 6
DEFAULT_BAUD = 115200


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("BB01 Arduino Test UI")
        self.root.geometry("920x720")

        self.ser: serial.Serial | None = None
        self.read_running = False
        self.read_thread: threading.Thread | None = None

        self.joint_vars = [tk.StringVar(value="0.0") for _ in range(NUM_JOINTS)]
        self.fb_deg_vars = [tk.StringVar(value="--") for _ in range(NUM_JOINTS)]
        self.fb_rad_vars = [tk.StringVar(value="--") for _ in range(NUM_JOINTS)]
        self.fb_gripper_var = tk.StringVar(value="--")
        self.status_var = tk.StringVar(value="Disconnected")

        # UI state: Serial log accordion.
        self.serial_log_visible = False
        self.log_frame: ttk.LabelFrame | None = None
        self.serial_toggle_btn: ttk.Button | None = None

        self._build()
        self.refresh_ports()

    def _apply_style(self) -> None:
        """Apply a cohesive light theme (Tkinter/ttk only)."""
        try:
            style = ttk.Style(self.root)
            # 'clam' gives better color control than 'default' on Windows.
            style.theme_use("clam")
        except tk.TclError:
            return

        # Palette (light, but still high-contrast).
        bg_main = "#F3F4F6"   # light grey background
        panel = "#FFFFFF"     # panels
        panel2 = "#EEF2F7"   # inputs / secondary surfaces
        border = "#D1D5DB"   # subtle borders
        fg = "#111827"        # near-black text
        fg_muted = "#6B7280"  # muted labels
        accent = "#F97316"   # orange accents
        accent2 = "#F59E0B"  # secondary orange
        danger = "#EF4444"   # errors

        # Expose a few palette values for later widget configuration.
        self.accent = accent
        self.fg = fg
        self.panel = panel
        self.panel2 = panel2
        self.bg_main = bg_main

        self.root.configure(background=bg_main)

        # ttk base widgets.
        style.configure("TFrame", background=bg_main)
        style.configure("TLabel", background=bg_main, foreground=fg)
        style.configure("TLabelframe", background=panel, bordercolor=border, padding=6)
        style.configure(
            "TLabelframe.Label",
            background=panel,
            foreground=fg,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "TEntry",
            fieldbackground=panel2,
            foreground=fg,
            insertcolor=fg,
            bordercolor=border,
        )
        style.configure(
            "TCombobox",
            fieldbackground=panel2,
            foreground=fg,
            bordercolor=border,
        )

        # Default button tuning (darker grey buttons).
        btn_bg = "#E5E7EB"
        btn_fg = "#111827"
        btn_active = "#D1D5DB"
        btn_disabled = "#F3F4F6"
        style.configure(
            "TButton",
            padding=(12, 8),
            font=("Segoe UI", 10),
            background=btn_bg,
            foreground=btn_fg,
            bordercolor=border,
        )
        style.map(
            "TButton",
            background=[
                ("active", btn_active),
                ("disabled", btn_disabled),
            ],
            foreground=[
                ("active", btn_fg),
                ("disabled", fg_muted),
            ],
        )

        # Accent button (used for the main Send action).
        style.configure(
            "AccentLarge.TButton",
            background=accent,
            foreground="white",
            padding=(18, 12),
            font=("Segoe UI", 12, "bold"),
        )
        style.map(
            "AccentLarge.TButton",
            background=[("active", "#EA580C")],
            foreground=[("active", "white")],
        )

        # Accordion toggle styling.
        style.configure(
            "Ghost.TButton",
            background=panel,
            foreground=fg_muted,
            padding=(10, 6),
            font=("Segoe UI", 10, "bold"),
            bordercolor=border,
        )
        style.map(
            "Ghost.TButton",
            background=[("active", panel2)],
            foreground=[("active", fg)],
        )

        # Add log widget styling (ScrolledText uses tk.Text under the hood).
        # We apply these later once the widget exists.

    def _build(self):
        self._apply_style()

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        conn = ttk.LabelFrame(main, text="Serial", padding=8)
        conn.pack(fill="x", pady=(0, 6))

        self.port_var = tk.StringVar(value="COM3")
        ttk.Label(conn, text="Port").grid(row=0, column=0, padx=4)
        self.port_combo = ttk.Combobox(
            conn, textvariable=self.port_var, width=20, state="readonly"
        )
        self.port_combo.grid(row=0, column=1, padx=4)
        ttk.Button(conn, text="Refresh", command=self.refresh_ports).grid(
            row=0, column=2, padx=4
        )
        self.baud_var = tk.StringVar(value=str(DEFAULT_BAUD))
        ttk.Label(conn, text="Baud").grid(row=0, column=3, padx=8)
        ttk.Entry(conn, textvariable=self.baud_var, width=10).grid(
            row=0, column=4, padx=4
        )
        self.btn_connect = ttk.Button(conn, text="Connect", command=self.connect)
        self.btn_connect.grid(row=0, column=5, padx=6)
        self.btn_disconnect = ttk.Button(
            conn, text="Disconnect", command=self.disconnect, state="disabled"
        )
        self.btn_disconnect.grid(row=0, column=6, padx=4)
        ttk.Label(conn, textvariable=self.status_var).grid(
            row=0, column=7, padx=10, sticky="w"
        )

        tip = (
            "Tip: ESP32 often lists two COM ports — use the one that shows "
            "bb01_test_ready then fb,... every ~200ms. Wait >2s after connect "
            "(firmware delay). Close Arduino Serial Monitor while using this UI."
        )
        ttk.Label(conn, text=tip, wraplength=860, justify="left").grid(
            row=1, column=0, columnspan=8, sticky="w", padx=4, pady=(6, 2)
        )

        cmd = ttk.LabelFrame(main, text="Commands (human: degrees)", padding=8)
        cmd.pack(fill="x", pady=(0, 10))
        for i in range(NUM_JOINTS):
            ttk.Label(cmd, text=f"J{i + 1} deg").grid(
                row=i, column=0, sticky="w", padx=4, pady=2
            )
            ttk.Entry(cmd, textvariable=self.joint_vars[i], width=12).grid(
                row=i, column=1, padx=4, pady=2, sticky="w"
            )

        ttk.Label(cmd, text="Gripper deg").grid(
            row=0, column=2, sticky="w", padx=(20, 4)
        )
        self.gripper_scale = ttk.Scale(cmd, from_=0, to=180, orient="horizontal")
        self.gripper_scale.set(90)
        self.gripper_scale.grid(row=0, column=3, sticky="ew", padx=4)
        self.gripper_label = tk.StringVar(value="90")
        self.gripper_scale.configure(
            command=lambda v: self.gripper_label.set(str(int(float(v))))
        )
        ttk.Label(cmd, textvariable=self.gripper_label).grid(
            row=0, column=4, padx=4, sticky="w"
        )
        p = ttk.Frame(cmd)
        p.grid(row=1, column=2, columnspan=3, sticky="w", padx=(20, 4))
        ttk.Button(p, text="Open", command=lambda: self._set_gripper(180)).pack(
            side="left", padx=3
        )
        ttk.Button(p, text="Neutral", command=lambda: self._set_gripper(90)).pack(
            side="left", padx=3
        )
        ttk.Button(p, text="Close", command=lambda: self._set_gripper(0)).pack(
            side="left", padx=3
        )
        self.btn_send = ttk.Button(
            cmd, text="Send", command=self.send, state="disabled", style="AccentLarge.TButton"
        )
        self.btn_send.grid(row=6, column=0, columnspan=5, pady=(12, 8), sticky="ew")
        cmd.columnconfigure(3, weight=1)
        cmd.columnconfigure(1, weight=1)

        fb = ttk.LabelFrame(main, text="Feedback (from fb,... lines)", padding=8)
        fb.pack(fill="x", pady=(0, 10))
        ttk.Label(fb, text="Joint").grid(row=0, column=0, padx=6, sticky="w")
        ttk.Label(fb, text="Deg").grid(row=0, column=1, padx=6, sticky="w")
        ttk.Label(fb, text="Rad").grid(row=0, column=2, padx=6, sticky="w")
        for i in range(NUM_JOINTS):
            ttk.Label(fb, text=f"J{i + 1}").grid(
                row=i + 1, column=0, padx=6, sticky="w"
            )
            ttk.Label(fb, textvariable=self.fb_deg_vars[i]).grid(
                row=i + 1, column=1, padx=6, sticky="w"
            )
            ttk.Label(fb, textvariable=self.fb_rad_vars[i]).grid(
                row=i + 1, column=2, padx=6, sticky="w"
            )
        ttk.Label(fb, text="Gripper deg").grid(
            row=1, column=3, padx=(30, 6), sticky="w"
        )
        ttk.Label(fb, textvariable=self.fb_gripper_var).grid(
            row=1, column=4, padx=6, sticky="w"
        )

        # Serial log accordion (toggleable).
        serial_header = ttk.Frame(main)
        serial_header.pack(fill="x", pady=(0, 6))

        toggle_text = (
            "Serial Monitor (hide)" if self.serial_log_visible else "Serial Monitor (show)"
        )
        self.serial_toggle_btn = ttk.Button(
            serial_header,
            text=toggle_text,
            command=self.toggle_serial_monitor,
            style="Ghost.TButton",
        )
        self.serial_toggle_btn.pack(side="left")

        serial_hint = ttk.Label(
            serial_header,
            text="RX/TX details",
            foreground=getattr(self, "fg_muted", "#6B7280"),
        )
        serial_hint.pack(side="left", padx=(10, 0))

        logf = ttk.LabelFrame(main, text="Serial log", padding=8)
        self.log_frame = logf
        logf.pack(fill="both", expand=True)
        if not self.serial_log_visible:
            logf.pack_forget()

        self.log = ScrolledText(logf, state="disabled", height=10)
        self.log.pack(fill="both", expand=True)

        # Apply styling to the underlying tk.Text.
        self.log.configure(
            background="#FFFFFF",
            foreground=getattr(self, "fg", "#111827"),
            insertbackground=getattr(self, "accent", "#F97316"),
            selectbackground="#FFE1C2",
            relief="flat",
            borderwidth=0,
        )
        # Slightly reduce glare: disable default scrollbar step-by-step colors.

    def _set_gripper(self, value: int):
        self.gripper_scale.set(value)
        self.gripper_label.set(str(value))

    def toggle_serial_monitor(self) -> None:
        """Accordion toggle for the Serial log panel."""
        if not self.log_frame or not self.serial_toggle_btn:
            return

        if self.serial_log_visible:
            self.log_frame.pack_forget()
            self.serial_log_visible = False
            self.serial_toggle_btn.configure(text="Serial Monitor (show)")
        else:
            self.log_frame.pack(fill="both", expand=True)
            self.serial_log_visible = True
            self.serial_toggle_btn.configure(text="Serial Monitor (hide)")

    def refresh_ports(self):
        ports = [p.device for p in list_ports.comports()]
        self.port_combo["values"] = ports
        if ports:
            # Prefer COM3 by default (requested), otherwise pick the first detected port.
            if "COM3" in ports:
                self.port_var.set("COM3")
            else:
                self.port_var.set(ports[0])
        else:
            self.port_var.set("COM3")

    def _append_log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def connect(self):
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("Error", "Select a serial port")
            return
        try:
            baud = int(self.baud_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Baud must be an integer")
            return
        try:
            self.ser = serial.Serial(
                port=port, baudrate=baud, timeout=0.1, write_timeout=2
            )
        except Exception as e:
            messagebox.showerror("Connect failed", str(e))
            return
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass

        self.read_running = True
        self.read_thread = threading.Thread(target=self._reader, daemon=True)
        self.read_thread.start()
        self.btn_connect.configure(state="disabled")
        self.btn_disconnect.configure(state="normal")
        self.btn_send.configure(state="normal")
        self.status_var.set(f"Connected {port} @ {baud}")
        self._append_log(f"[INFO] Connected {port} @ {baud}")
        self._append_log(
            "[INFO] Expect bb01_test_ready then repeating fb,... (~200ms). "
            "If log stays empty, try another COM port from the list."
        )

    def disconnect(self):
        self.read_running = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        self.btn_connect.configure(state="normal")
        self.btn_disconnect.configure(state="disabled")
        self.btn_send.configure(state="disabled")
        self.status_var.set("Disconnected")
        self._append_log("[INFO] Disconnected")

    def send(self):
        if not self.ser:
            return
        try:
            degs = [float(v.get().strip()) for v in self.joint_vars]
        except ValueError:
            messagebox.showerror("Error", "Joint values must be numeric")
            return
        if any(d < -90.0 or d > 90.0 for d in degs):
            messagebox.showerror(
                "Error", "Joint degree inputs must be within [-90, 90]"
            )
            return
        rads = [math.radians(d) for d in degs]
        gr = int(float(self.gripper_scale.get()))
        msg = "cmd," + ",".join(f"{r:.6f}" for r in rads) + f",{gr}\n"
        try:
            self.ser.write(msg.encode("ascii"))
            self.ser.flush()
        except Exception as e:
            messagebox.showerror("Write failed", str(e))
            return
        self._append_log(
            "[TX] "
            + msg.strip()
            + "  # deg="
            + ",".join(f"{d:.2f}" for d in degs)
            + f" gripper={gr}"
        )

    def _reader(self):
        while self.read_running:
            try:
                line = (
                    self.ser.readline().decode("ascii", errors="replace").strip()
                    if self.ser
                    else ""
                )
            except Exception as e:
                self.root.after(0, lambda e=e: self._append_log(f"[ERR] {e}"))
                break
            if line:
                self.root.after(0, lambda l=line: self._handle_line(l))

    def _handle_line(self, line: str):
        stripped = line.strip()
        self._append_log("[RX] " + stripped)

        if stripped == "bb01_test_ready":
            self._append_log("[INFO] Firmware serial banner OK (skipping fb parse).")
            return

        parts = [p.strip() for p in stripped.split(",")]
        if parts:
            parts[0] = parts[0].lstrip("\ufeff").strip()

        tag = parts[0] if parts else ""
        if len(parts) != 8 or tag != "fb":
            self._append_log(
                f"[RX skip] expected 'fb' + 7 commas (8 fields); "
                f"got {len(parts)} fields, first={tag!r}"
            )
            return

        try:
            rads = [float(parts[i + 1]) for i in range(NUM_JOINTS)]
            gr = int(float(parts[7]))
        except ValueError:
            self._append_log("[RX skip] non-numeric value in fb line")
            return

        for i, r in enumerate(rads):
            self.fb_rad_vars[i].set(f"{r:.6f}")
            self.fb_deg_vars[i].set(f"{math.degrees(r):.2f}")
        self.fb_gripper_var.set(str(gr))


def main():
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.disconnect(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()

"""Tkinter restaurant floorplan. Pixels are NEVER map-frame Goal coordinates.

ROS callbacks are serviced by Tk.after() on the GUI thread. The GUI publishes
only logical T03 requests and explicit staff confirmations.
"""
import argparse
import json
import uuid
from pathlib import Path


def floorplan_scale(width, height, design_width=806, design_height=460):
    """Scale UI-only canvas coordinates; never change Nav2 map poses."""
    if min(width, height, design_width, design_height) <= 0:
        raise ValueError("UI_CANVAS_DIMENSIONS_MUST_BE_POSITIVE")
    return min(1.10, width / design_width, height / design_height)

STATES_KO = {
    "IDLE": "IDLE · 출발 대기",
    "TO_TABLE": "TO_TABLE · 테이블 이동",
    "WAIT_LOADING": "WAIT_LOADING · 식기 적재 대기",
    "AI_CHECK": "AI_CHECK · 적재 안정성 확인",
    "NEEDS_CONFIRMATION": "NEEDS_CONFIRMATION · 직원 확인 필요",
    "TO_RETURN": "TO_RETURN · 반납점 이동",
    "WAIT_UNLOADING": "WAIT_UNLOADING · 식기 반납 대기",
    "TO_HOME": "TO_HOME · 대기점 복귀",
    "COMPLETED": "COMPLETED · 회수 완료",
    "ERROR": "ERROR · 오류",
    "CANCELED": "CANCELED · 취소",
}


def read_layout(path):
    import yaml
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("frame") != "ui_pixels":
        raise ValueError("UI_LAYOUT_MUST_USE_PIXEL_FRAME")
    tables = doc.get("tables")
    if not isinstance(tables, dict) or set(tables) != {
            "T01", "T02", "T03", "T04", "T05", "T06"}:
        raise ValueError("UI_LAYOUT_EXACTLY_SIX_TABLES")
    for table_id, spec in tables.items():
        if (not isinstance(spec, dict)
                or not isinstance(spec.get("rect"), list)
                or len(spec["rect"]) != 4
                or not all(isinstance(n, int) for n in spec["rect"])
                or spec.get("enabled") is not (table_id == "T03")):
            raise ValueError("UI_LAYOUT_INVALID_TABLE_" + table_id)
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser(description="SmartDish Tkinter UI")
    parser.add_argument("--ai-available", choices=("true", "false"), default="false")
    parser.add_argument("--layout", default=None)
    args, ros_args = parser.parse_known_args(argv)

    import tkinter as tk
    from tkinter import messagebox
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
    from std_msgs.msg import String
    from ament_index_python.packages import get_package_share_directory

    if args.layout:
        layout_path = Path(args.layout)
    else:
        layout_path = Path(get_package_share_directory("smartdish_service")) / "config/ui_layout.yaml"
    layout = read_layout(layout_path)

    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST, depth=10,
        reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE
    )

    class UiNode(Node):
        def __init__(self):
            super().__init__("smartdish_ui")
            self.request_pub = self.create_publisher(String, "/collection/request", qos)
            self.staff_pub = self.create_publisher(String, "/collection/staff_confirm", qos)
            self.callback = None
            self.create_subscription(String, "/collection/status", self.on_status, qos)

        def on_status(self, msg):
            try:
                obj = json.loads(msg.data)
                if isinstance(obj, dict) and self.callback:
                    self.callback(obj)
            except (ValueError, TypeError):
                self.get_logger().warning("SMARTDISH_D_BAD_STATUS_JSON")

        def send(self, publisher, data):
            msg = String()
            msg.data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            publisher.publish(msg)

    class App:
        BG = "#f3f6f9"
        INK = "#192e49"
        MUTED = "#6c7e91"
        TEAL = "#0d8494"
        PANEL = "#ffffff"

        def __init__(self, node):
            self.node = node
            self.node.callback = self.on_status
            self.root = tk.Tk()
            self.root.title("SmartDish — 테이블 선택형 식기 회수")
            self.root.geometry("1210x740")
            self.root.minsize(1024, 680)
            self.root.configure(bg=self.BG)
            self.root.protocol("WM_DELETE_WINDOW", self.close)
            self.selected = None
            self.active_request = None
            self.active_state = "IDLE"
            self.ai_available = args.ai_available == "true"
            self.ai_var = tk.BooleanVar(value=False)
            self.table_wait = tk.StringVar(value="10")
            self.dropoff_wait = tk.StringVar(value="5")
            self.status_var = tk.StringVar(value=STATES_KO["IDLE"])
            self.selected_var = tk.StringVar(value="선택 전 · T03을 누르세요")
            self.remaining_var = tk.StringVar(value="—")
            self.reason_var = tk.StringVar(value="")
            self._build()
            self.root.after(60, self.poll_ros)

        def _label(self, parent, text, size=13, color=None, bold=False, **kw):
            return tk.Label(
                parent, text=text, fg=color or self.INK,
                bg=kw.pop("bg", self.PANEL), anchor=kw.pop("anchor", "w"),
                font=("DejaVu Sans", size, "bold" if bold else "normal"), **kw)

        def _build(self):
            heading = tk.Frame(self.root, bg=self.BG)
            heading.pack(fill="x", padx=25, pady=(15, 12))
            self._label(heading, "WHAT / USER INTERFACE", size=11,
                        color=self.TEAL, bold=True, bg=self.BG).pack(anchor="w")
            self._label(heading, "매장 배치를 보고 직접 테이블을 선택합니다.",
                        size=23, bold=True, bg=self.BG).pack(anchor="w", pady=(5, 0))
            self._label(heading, "T03 단일 활성 · ROS 2 수신 결과로 상태 갱신 · AI OFF 기본",
                        color=self.MUTED, bg=self.BG).pack(anchor="w", pady=(5, 0))

            content = tk.Frame(self.root, bg=self.BG)
            content.pack(fill="both", expand=True, padx=25)
            # Pack reserves space in order: the controls must come first.
            right = tk.Frame(content, bg=self.PANEL, width=345,
                             highlightbackground="#d6e1eb", highlightthickness=1)
            right.pack(side="right", fill="y")
            right.pack_propagate(False)
            left = tk.Frame(content, bg=self.PANEL, highlightbackground="#d6e1eb",
                            highlightthickness=1)
            left.pack(side="left", fill="both", expand=True, padx=(0, 12))

            self._label(left, "매장 평면도  ·  테이블 선택", size=17, bold=True).pack(
                anchor="w", padx=16, pady=(12, 0))
            # Pixel artwork must not reserve the entire source-image width.
            self.canvas = tk.Canvas(left, width=1, height=1, bg=self.PANEL,
                                    bd=0, highlightthickness=0)
            self.canvas.pack(fill="both", expand=True, padx=12, pady=(4, 8))
            self._floorplan_scale = 1.0
            self._draw_map()
            self.canvas.bind("<Configure>", self._resize_floorplan)
            self._label(right, "현재 로봇 상태", size=12, color=self.MUTED).pack(
                anchor="w", padx=18, pady=(20, 0))
            self._label(right, "", size=16, bold=True,
                        textvariable=self.status_var, wraplength=305).pack(
                anchor="w", padx=18, pady=(1, 15))
            self._label(right, "선택 테이블", color=self.MUTED).pack(anchor="w", padx=18)
            self._label(right, "", size=15, bold=True, textvariable=self.selected_var).pack(
                anchor="w", padx=18, pady=(1, 12))

            # One column: full Korean label above each full-width Spinbox.
            timing = tk.Frame(right, bg=self.PANEL)
            timing.pack(fill="x", padx=18)
            timing.grid_columnconfigure(0, weight=1)
            self._label(timing, "적재 대기 (1~120초)", color=self.MUTED).grid(
                row=0, column=0, sticky="w")
            self.loading_spin = tk.Spinbox(
                timing, from_=1, to=120, textvariable=self.table_wait,
                width=7, font=("DejaVu Sans", 13), justify="center")
            self.loading_spin.grid(row=1, column=0, sticky="ew", pady=(4, 12))
            self._label(timing, "반납 대기 (1~60초)", color=self.MUTED).grid(
                row=2, column=0, sticky="w")
            self.dropoff_spin = tk.Spinbox(
                timing, from_=1, to=60, textvariable=self.dropoff_wait,
                width=7, font=("DejaVu Sans", 13), justify="center")
            self.dropoff_spin.grid(row=3, column=0, sticky="ew", pady=(4, 8))
            self._label(right, "남은 대기 시간 (초)", color=self.MUTED).pack(
                anchor="w", padx=18, pady=(9, 0))
            self._label(right, "", size=16, bold=True, textvariable=self.remaining_var).pack(
                anchor="w", padx=18)
            self.start_button = tk.Button(
                right, text="선택 테이블로 회수 시작", command=self.start,
                fg="white", bg=self.TEAL, activebackground="#086d79",
                font=("DejaVu Sans", 13, "bold"), height=2, bd=0)
            self.start_button.pack(fill="x", padx=18, pady=(18, 8))
            ai_text = "AI 검사: 준비됨 (선택)" if self.ai_available else "AI 검사: OFF (준비 중)"
            self.ai_button = tk.Checkbutton(
                right, text=ai_text, variable=self.ai_var, onvalue=True, offvalue=False,
                state="normal" if self.ai_available else "disabled",
                bg="#eaf0f3", anchor="w", font=("DejaVu Sans", 11))
            self.ai_button.pack(fill="x", padx=18, pady=4)
            self.confirm_frame = tk.Frame(right, bg=self.PANEL)
            tk.Button(self.confirm_frame, text="직원 승인 · 계속", command=lambda:
                      self.confirm("APPROVE_CONTINUE"), bg="#cde9de").pack(
                      side="left", padx=3)
            tk.Button(self.confirm_frame, text="중단", command=lambda:
                      self.confirm("ABORT"), bg="#f7d4d4").pack(
                      side="left", padx=3)
            self._label(right, "", textvariable=self.reason_var, size=10,
                        color="#b44c4c", wraplength=305).pack(
                anchor="w", padx=18, pady=9)
            bottom = tk.Frame(self.root, bg="#e5f2f4")
            bottom.pack(fill="x", padx=25, pady=(8, 12))
            self._label(bottom,
                        "T03 클릭  →  table_id=T03  →  A: table_poses.yaml  →  실제 Nav2 결과  →  UI",
                        size=10, color="#006c78", bg="#e5f2f4").pack(padx=8, pady=5)

        def _resize_floorplan(self, event):
            """Fit UI-only artwork; keep the 345px controls reserved."""
            new_scale = floorplan_scale(
                event.width, event.height,
                layout["canvas"]["width"], layout["canvas"]["height"])
            factor = new_scale / self._floorplan_scale
            self.canvas.scale("all", 0, 0, factor, factor)
            self._floorplan_scale = new_scale

        def _draw_map(self):
            c = self.canvas
            tables = layout["tables"]
            c.create_rectangle(18, 12, 790, 58, fill="#cda977", outline="")
            c.create_text(404, 35, text="조리대 / 주방", font=("DejaVu Sans", 13, "bold"),
                          fill=self.INK)
            for tid, spec in tables.items():
                x1, y1, x2, y2 = spec["rect"]
                for y in (y1 - 20, y2 + 14):
                    for x in (x1 + 36, x2 - 36):
                        c.create_oval(x-12, y-6, x+12, y+6, fill="#b1c2cc", outline="")
                fill = "#d8e8ef" if tid != "T03" else "#ffe0ad"
                outline = "#85aabf" if tid != "T03" else "#d18a37"
                rect = c.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=2)
                label = c.create_text((x1+x2)//2, (y1+y2)//2, text=tid,
                                      fill=self.INK, font=("DejaVu Sans", 19, "bold"))
                if spec["enabled"]:
                    c.tag_bind(rect, "<Button-1>", lambda event: self.select_t03())
                    c.tag_bind(label, "<Button-1>", lambda event: self.select_t03())
                    c.tag_bind(rect, "<Enter>", lambda event: c.configure(cursor="hand2"))
                    c.tag_bind(rect, "<Leave>", lambda event: c.configure(cursor=""))
                    c.create_text((x1+x2)//2, y2+28, text="선택 가능",
                                  fill="#9c611d", font=("DejaVu Sans", 9, "bold"))
                else:
                    c.create_text((x1+x2)//2, y2+28, text="준비 중",
                                  fill="#8c9aa8", font=("DejaVu Sans", 8))
                if tid == "T03":
                    self.t03_rect = rect
            for key, color, text in [
                ("HOME", "#d9f0eb", "HOME / 대기점"),
                ("DISH_RETURN", "#eee9f7", "DISH_RETURN / 반납"),
            ]:
                x1, y1, x2, y2 = layout["areas"][key]
                c.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
                c.create_text((x1+x2)//2, (y1+y2)//2, text=text,
                              font=("DejaVu Sans", 13, "bold"),
                              fill="#006c78" if key == "HOME" else "#77629e")

        def select_t03(self):
            if self.active_state in {
                    "TO_TABLE", "WAIT_LOADING", "AI_CHECK", "NEEDS_CONFIRMATION",
                    "TO_RETURN", "WAIT_UNLOADING", "TO_HOME"}:
                return
            self.selected = "T03"
            self.selected_var.set("T03 · 우측 중앙 구역")
            self.canvas.itemconfigure(self.t03_rect, fill="#f9a64d", outline="#e38f35")

        @staticmethod
        def _seconds(raw, upper):
            try:
                val = int(raw)
                if str(val) != raw.strip() or not 1 <= val <= upper:
                    raise ValueError()
                return val
            except (ValueError, AttributeError):
                raise ValueError(f"대기시간은 1~{upper}의 정수여야 합니다.")

        def start(self):
            if self.selected != "T03":
                messagebox.showwarning("선택 필요", "매장 평면도에서 T03을 클릭하세요.")
                return
            try:
                wait = self._seconds(self.table_wait.get(), 120)
                dropoff = self._seconds(self.dropoff_wait.get(), 60)
            except ValueError as exc:
                messagebox.showerror("입력 오류", str(exc))
                return
            if self.node.request_pub.get_subscription_count() == 0:
                self.reason_var.set("Mission Manager 연결 안 됨 · 요청 미발행")
                return
            self.active_request = "REQ-" + uuid.uuid4().hex[:12]
            self.active_state = "TO_TABLE"
            self.reason_var.set("")
            self.start_button.configure(state="disabled")
            self.node.send(self.node.request_pub, {
                "request_id": self.active_request,
                "table_id": "T03", "table_wait_s": wait,
                "dropoff_wait_s": dropoff, "ai_enabled": bool(self.ai_var.get())
            })

        def on_status(self, data):
            if data.get("request_id") != self.active_request:
                return  # Reject events from a previous/other request.
            state = data.get("state")
            if state not in STATES_KO:
                return
            self.active_state = state
            self.status_var.set(STATES_KO[state])
            remaining = data.get("remaining_s")
            self.remaining_var.set(f"{remaining}초" if isinstance(remaining, int) else "—")
            self.reason_var.set(str(data.get("reason") or ""))
            if state == "NEEDS_CONFIRMATION":
                self.confirm_frame.pack(anchor="w", padx=18, pady=(5, 0))
            else:
                self.confirm_frame.pack_forget()
            if state in {"COMPLETED", "ERROR", "CANCELED"}:
                self.start_button.configure(state="normal")

        def confirm(self, action):
            if self.active_state != "NEEDS_CONFIRMATION" or not self.active_request:
                return
            self.node.send(self.node.staff_pub, {
                "request_id": self.active_request, "action": action})
            self.confirm_frame.pack_forget()

        def poll_ros(self):
            if not self.root.winfo_exists():
                return
            rclpy.spin_once(self.node, timeout_sec=0.0)
            self.root.after(60, self.poll_ros)

        def close(self):
            self.root.destroy()

        def run(self):
            self.root.after_idle(lambda: print("SMARTDISH_D_UI_READY", flush=True))
            self.root.mainloop()

    rclpy.init(args=ros_args)
    node = UiNode()
    try:
        App(node).run()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

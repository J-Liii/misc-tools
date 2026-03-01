"""
日程管理 — 三级导航
  Level 1  月历（显示任务数，黑色左对齐）
  Level 2  日视图（清单形式展示任务，可勾选完成）
  Level 3  时段详情（唯一可添加任务的地方）
睡眠时间仅展示，不可添加任务。
"""

import tkinter as tk
from tkinter import font as tkfont
import json, os, sys, uuid, calendar
from datetime import datetime, date, timedelta

# ── 路径 ──────────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "schedule_data.json")

# ── 时段配置 ───────────────────────────────────────────────────────────────────
PERIODS = [
    {"key": "0", "name": "Day 1", "time": "09:00 – 14:00"},
    {"key": "1", "name": "Day 2", "time": "14:00 – 20:00"},
    {"key": "2", "name": "Day 3", "time": "20:00 – 01:00"},
]
SLEEP = {"key": "3", "name": "睡眠时间", "time": "01:00 – 09:00"}

BAND_W  = [3, 3, 3, 1]
TOTAL_W = sum(BAND_W)

WD_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTH_CN  = ["", "一月", "二月", "三月", "四月", "五月", "六月",
             "七月", "八月", "九月", "十月", "十一月", "十二月"]

C = {
    "bg":          "#FFFFFF",
    "bg_off":      "#F5F5F5",
    "grid":        "#E8E8E8",
    "grid_hdr":    "#CCCCCC",
    "text":        "#1A1A1A",
    "dim":         "#999999",
    "weekend":     "#CC2200",
    "today_dot":   "#1A1A1A",
    "today_fg":    "#FFFFFF",
    "active_band": "#F0F4FF",
    "sleep":       "#1A237E",
    "sleep_txt":   "#9FA8DA",
    "done":        "#888888",
    "ph":          "#BBBBBB",
    "sep":         "#EEEEEE",
    "pill_done":   "#CBEDF6",   # 已完成任务按钮颜色
    "pill_idle":   "#EFEFEF",   # 未完成任务按钮颜色
}


# ── 工具函数 ───────────────────────────────────────────────────────────────────
def current_period() -> int:
    m = datetime.now().hour * 60 + datetime.now().minute
    if 9*60  <= m < 14*60:  return 0
    if 14*60 <= m < 20*60:  return 1
    if m >= 20*60 or m < 60: return 2
    return 3

def logical_today() -> date:
    now = datetime.now()
    return (now - timedelta(days=1)).date() if now.hour < 1 else now.date()

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 主应用 ─────────────────────────────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("日程管理")
        self.root.geometry("1100x760")
        self.root.minsize(860, 580)
        self.root.configure(bg=C["bg"])

        self.data = load_data()
        today = logical_today()
        self.view_year  = today.year
        self.view_month = today.month
        self._sel_date   = None
        self._sel_period = None
        self._cur_frame  = None

        self._fonts()
        self._build_all()
        self._to_cal()
        self._tick()

    # ── 字体 ──────────────────────────────────────────────────────────────────
    def _fonts(self):
        def F(**kw): return tkfont.Font(family="微软雅黑", **kw)
        self.f_h1     = F(size=20, weight="bold")
        self.f_bold   = F(size=11, weight="bold")
        self.f_normal = F(size=10)
        self.f_strike = F(size=10, overstrike=True)
        self.f_small  = F(size=9)
        self.f_tiny   = F(size=7)
        self.f_arrow  = tkfont.Font(family="Arial", size=22, weight="bold")

    # ── 页面切换 ──────────────────────────────────────────────────────────────
    def _show(self, frame: tk.Frame):
        if self._cur_frame:
            self._cur_frame.pack_forget()
        frame.pack(fill=tk.BOTH, expand=True)
        self._cur_frame = frame

    def _build_all(self):
        self.pg_cal    = tk.Frame(self.root, bg=C["bg"])
        self.pg_day    = tk.Frame(self.root, bg=C["bg"])
        self.pg_period = tk.Frame(self.root, bg=C["bg"])
        self._build_cal_page()
        self._build_day_page()
        self._build_period_page()

    # ── 圆角矩形绘制辅助 ──────────────────────────────────────────────────────
    def _rrect(self, cv, x, y, w, h, r, fill):
        """在 Canvas 上绘制填充圆角矩形（无描边）。"""
        x2, y2 = x + w, y + h
        cv.create_rectangle(x + r, y,      x2 - r, y2,     fill=fill, outline="")
        cv.create_rectangle(x,     y + r,  x2,     y2 - r, fill=fill, outline="")
        cv.create_oval(x,      y,      x  + 2*r, y  + 2*r, fill=fill, outline="")
        cv.create_oval(x2-2*r, y,      x2,       y  + 2*r, fill=fill, outline="")
        cv.create_oval(x,      y2-2*r, x  + 2*r, y2,       fill=fill, outline="")
        cv.create_oval(x2-2*r, y2-2*r, x2,       y2,       fill=fill, outline="")

    # ── 胶囊形待办按钮 ────────────────────────────────────────────────────────
    def _pill_btn(self, parent, todo: dict, toggle_cmd, delete_cmd):
        """渲染一个胶囊形状的待办事项按钮。点击切换完成状态。"""
        done     = todo["done"]
        pill_bg  = C["pill_done"] if done else C["pill_idle"]
        fg_col   = C["done"]  if done else C["text"]
        font     = self.f_strike if done else self.f_normal
        H, R     = 40, 14

        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill=tk.X, pady=3)

        cv = tk.Canvas(row, height=H, bg=C["bg"], highlightthickness=0,
                       cursor="hand2")
        cv.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def redraw(_=None):
            cv.delete("all")
            w = cv.winfo_width()
            if w < 10:
                return
            self._rrect(cv, 0, 0, w, H, R, pill_bg)
            cv.create_text(R + 8, H // 2, text=todo["text"],
                           anchor="w", font=font, fill=fg_col)

        cv.bind("<Configure>", redraw)
        cv.bind("<Button-1>",  lambda e: toggle_cmd())

        tk.Button(row, text="×", bg=C["bg"], fg="#C0C0C0",
                  relief=tk.FLAT, font=self.f_small, cursor="hand2",
                  activebackground=C["bg"], activeforeground=C["dim"],
                  command=delete_cmd
                  ).pack(side=tk.RIGHT, padx=(6, 0))

    # ════════════════════════════════════════════════════════════════════════════
    # PAGE 1 — 月历
    # ════════════════════════════════════════════════════════════════════════════
    def _build_cal_page(self):
        p = self.pg_cal

        nav = tk.Frame(p, bg=C["bg"], height=68)
        nav.pack(fill=tk.X)
        nav.pack_propagate(False)
        tk.Frame(p, bg=C["grid_hdr"], height=1).pack(fill=tk.X)

        tk.Button(nav, text="‹", command=self._prev_month,
                  bg=C["bg"], fg=C["text"], relief=tk.FLAT,
                  font=self.f_arrow, padx=20, cursor="hand2"
                  ).pack(side=tk.LEFT)

        self._cal_title = tk.Label(nav, text="", bg=C["bg"],
                                   fg=C["text"], font=self.f_h1)
        self._cal_title.pack(side=tk.LEFT, expand=True)

        tk.Button(nav, text="Today", command=self._go_today,
                  bg=C["bg"], fg=C["dim"], relief=tk.FLAT,
                  font=self.f_small, padx=12, cursor="hand2"
                  ).pack(side=tk.LEFT, padx=6)

        tk.Button(nav, text="›", command=self._next_month,
                  bg=C["bg"], fg=C["text"], relief=tk.FLAT,
                  font=self.f_arrow, padx=20, cursor="hand2"
                  ).pack(side=tk.RIGHT)

        wd_row = tk.Frame(p, bg=C["bg"])
        wd_row.pack(fill=tk.X)
        for i, wd in enumerate(WD_LABELS):
            clr = C["weekend"] if i >= 5 else C["dim"]
            tk.Label(wd_row, text=wd, bg=C["bg"], fg=clr,
                     font=self.f_tiny, anchor="center", pady=5
                     ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Frame(p, bg=C["grid_hdr"], height=1).pack(fill=tk.X)

        self._cv = tk.Canvas(p, bg=C["bg"], highlightthickness=0)
        self._cv.pack(fill=tk.BOTH, expand=True)
        self._cv.bind("<Configure>", lambda _: self._draw_cal())
        self._cv.bind("<Button-1>",  self._cal_click)
        self._cell_map = []

    def _draw_cal(self):
        cv = self._cv
        cv.delete("all")
        self._cell_map = []

        W = max(cv.winfo_width(),  860)
        H = max(cv.winfo_height(), 500)
        y, m  = self.view_year, self.view_month
        today = logical_today()
        act_p = current_period()

        self._cal_title.config(text=f"{y}年   {MONTH_CN[m]}")

        first  = date(y, m, 1)
        start  = first - timedelta(days=first.weekday())
        n_rows = len(calendar.monthcalendar(y, m))
        cw, ch = W / 7, H / n_rows

        for ri in range(n_rows):
            for ci in range(7):
                cell_date = start + timedelta(days=ri * 7 + ci)
                x1 = ci * cw;      y1 = ri * ch
                x2 = x1 + cw - 1; y2 = y1 + ch - 1
                in_month = (cell_date.month == m)
                ap = act_p if cell_date == today else -1
                self._draw_cell(x1, y1, x2, y2, cell_date, in_month, ap)
                if in_month:
                    self._cell_map.append((cell_date, x1, y1, x2, y2))

    def _draw_cell(self, x1, y1, x2, y2, d: date, in_month: bool, act_period: int):
        cv       = self._cv
        date_str = d.strftime("%Y-%m-%d")
        day_data = self.data.get(date_str, {})
        is_today = (d == logical_today())
        is_wkend = (d.weekday() >= 5)

        bg = C["bg"] if in_month else C["bg_off"]
        cv.create_rectangle(x1, y1, x2, y2, fill=bg, outline="")
        cv.create_line(x2, y1, x2, y2 + 1, fill=C["grid"])
        cv.create_line(x1, y2, x2,     y2,  fill=C["grid"])

        # 日期数字
        dh = min(20, (y2 - y1) * 0.20)
        if is_today:
            r  = min(dh * 0.50, 10)
            cx, cy = x1 + r + 6, y1 + r + 3
            cv.create_oval(cx-r, cy-r, cx+r, cy+r, fill=C["today_dot"], outline="")
            cv.create_text(cx, cy, text=str(d.day), font=self.f_tiny, fill=C["today_fg"])
        else:
            nc = (C["weekend"] if is_wkend else C["text"]) if in_month else C["dim"]
            cv.create_text(x1 + 12, y1 + dh * 0.6, text=str(d.day),
                           font=self.f_tiny, fill=nc)

        if not in_month:
            return

        # 四条色带
        bt, by = y1 + dh + 1, y1 + dh + 1
        bh_total = y2 - bt
        for i, bw in enumerate(BAND_W):
            h   = bh_total * bw / TOTAL_W
            bx1, bx2 = x1 + 1, x2 - 1
            by1, by2 = by, by + h

            if i == 3:
                cv.create_rectangle(bx1, by1, bx2, by2, fill=C["sleep"], outline="")
            else:
                fill = C["active_band"] if i == act_period else bg
                cv.create_rectangle(bx1, by1, bx2, by2, fill=fill, outline="")
                if i > 0:
                    cv.create_line(bx1, by1, bx2, by1, fill=C["sep"])

                todos = day_data.get(str(i), [])
                if todos and h >= 8:
                    done  = sum(1 for t in todos if t.get("done"))
                    total = len(todos)
                    # ① 任务数：黑色、左对齐、较大字体
                    cv.create_text(bx1 + 5, (by1 + by2) / 2,
                                   text=f"{done}/{total}",
                                   anchor="w", font=self.f_small, fill=C["text"])
            by += h

    def _cal_click(self, ev):
        for d, x1, y1, x2, y2 in self._cell_map:
            if x1 <= ev.x <= x2 and y1 <= ev.y <= y2:
                self._to_day(d); return

    def _to_cal(self):
        self._show(self.pg_cal)
        self._draw_cal()

    def _prev_month(self):
        if self.view_month == 1: self.view_year -= 1; self.view_month = 12
        else: self.view_month -= 1
        self._draw_cal()

    def _next_month(self):
        if self.view_month == 12: self.view_year += 1; self.view_month = 1
        else: self.view_month += 1
        self._draw_cal()

    def _go_today(self):
        t = logical_today()
        self.view_year, self.view_month = t.year, t.month
        self._draw_cal()

    # ════════════════════════════════════════════════════════════════════════════
    # PAGE 2 — 日视图（清单，可勾选）
    # ════════════════════════════════════════════════════════════════════════════
    def _build_day_page(self):
        p = self.pg_day

        hdr = tk.Frame(p, bg=C["bg"], height=56)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Frame(p, bg=C["grid_hdr"], height=1).pack(fill=tk.X)

        tk.Button(hdr, text="‹  日历", command=self._to_cal,
                  bg=C["bg"], fg=C["dim"], relief=tk.FLAT,
                  font=self.f_normal, padx=16, cursor="hand2"
                  ).pack(side=tk.LEFT, pady=10)

        self._day_title = tk.Label(hdr, text="", bg=C["bg"],
                                   fg=C["text"], font=self.f_bold)
        self._day_title.pack(side=tk.LEFT, expand=True)

        # ② 日视图内容区改为可滚动
        outer = tk.Frame(p, bg=C["bg"])
        outer.pack(fill=tk.BOTH, expand=True)

        cv  = tk.Canvas(outer, bg=C["bg"], highlightthickness=0)
        sb  = tk.Scrollbar(outer, orient="vertical", command=cv.yview)
        self._day_sf = tk.Frame(cv, bg=C["bg"])
        self._day_sf.bind("<Configure>",
                          lambda _: cv.configure(scrollregion=cv.bbox("all")))
        cw_id = cv.create_window((0, 0), window=self._day_sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.bind("<Configure>", lambda e: cv.itemconfig(cw_id, width=e.width))
        cv.bind("<Enter>", lambda _, c=cv: self.root.bind_all(
            "<MouseWheel>",
            lambda ev: c.yview_scroll(-1 * (ev.delta // 120), "units")))
        cv.bind("<Leave>", lambda _: self.root.unbind_all("<MouseWheel>"))
        cv.pack(side=tk.LEFT,  fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _to_day(self, d: date):
        self._sel_date = d
        self._show(self.pg_day)
        self._render_day()

    def _render_day(self):
        d     = self._sel_date
        today = logical_today()
        wd    = "一二三四五六日"[d.weekday()]
        suf   = "  今天" if d == today else ""
        self._day_title.config(text=f"{d.strftime('%Y年%m月%d日')}  周{wd}{suf}")

        sf = self._day_sf
        for w in sf.winfo_children():
            w.destroy()

        ds     = d.strftime("%Y-%m-%d")
        dd     = self.data.get(ds, {})
        active = current_period() if d == today else -1

        for i, p in enumerate(PERIODS):
            todos  = dd.get(str(i), [])
            is_act = (i == active)

            # 时段标题行（整行可点击 → Level 3）
            def _go(_, pi=i): self._to_period(self._sel_date, pi)

            hdr_row = tk.Frame(sf, bg=C["bg"], cursor="hand2")
            hdr_row.pack(fill=tk.X, padx=24, pady=(18, 6))
            hdr_row.bind("<Button-1>", _go)

            for text, fg, font in [
                (p["name"],      C["text"], self.f_bold),
                (f"  {p['time']}", C["dim"],  self.f_small),
            ] + ([("  Now", C["dim"], self.f_tiny)] if is_act else []):
                lbl = tk.Label(hdr_row, text=text, bg=C["bg"],
                               fg=fg, font=font, cursor="hand2")
                lbl.pack(side=tk.LEFT)
                lbl.bind("<Button-1>", _go)

            # ② 任务清单（胶囊按钮）
            task_area = tk.Frame(sf, bg=C["bg"])
            task_area.pack(fill=tk.X, padx=24, pady=(0, 6))

            if not todos:
                tk.Label(task_area, text="暂无待办事项", bg=C["bg"],
                         fg="#CCCCCC", font=self.f_small, anchor="w"
                         ).pack(anchor="w", pady=4)
            else:
                for todo in todos:
                    self._pill_btn(
                        task_area, todo,
                        toggle_cmd=lambda t=todo["id"], pi=i:
                            self._toggle_in_day(ds, pi, t),
                        delete_cmd=lambda t=todo["id"], pi=i:
                            self._delete_in_day(ds, pi, t),
                    )

            tk.Frame(sf, bg=C["grid"], height=1).pack(fill=tk.X)

        # 睡眠时段（深蓝，固定高度，不可添加任务）
        sleep_sec = tk.Frame(sf, bg=C["sleep"], height=100)
        sleep_sec.pack(fill=tk.X)
        sleep_sec.pack_propagate(False)
        inner = tk.Frame(sleep_sec, bg=C["sleep"])
        inner.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(inner, text=SLEEP["name"], bg=C["sleep"],
                 fg="white", font=self.f_bold).pack()
        tk.Label(inner, text=SLEEP["time"], bg=C["sleep"],
                 fg=C["sleep_txt"], font=self.f_small).pack(pady=(4, 0))

        tk.Frame(sf, bg=C["bg"], height=20).pack()

    def _toggle_in_day(self, ds: str, pi: int, tid: str):
        for t in self._ensure(ds)[str(pi)]:
            if t["id"] == tid:
                t["done"] = not t["done"]
                break
        save_data(self.data)
        self._render_day()

    def _delete_in_day(self, ds: str, pi: int, tid: str):
        d = self._ensure(ds)
        d[str(pi)] = [t for t in d[str(pi)] if t["id"] != tid]
        save_data(self.data)
        self._render_day()

    # ════════════════════════════════════════════════════════════════════════════
    # PAGE 3 — 时段详情（唯一可添加任务的地方）
    # ════════════════════════════════════════════════════════════════════════════
    def _build_period_page(self):
        p = self.pg_period

        hdr = tk.Frame(p, bg=C["bg"], height=56)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Frame(p, bg=C["grid_hdr"], height=1).pack(fill=tk.X)

        tk.Button(hdr, text="‹  返回", command=self._back_to_day,
                  bg=C["bg"], fg=C["dim"], relief=tk.FLAT,
                  font=self.f_normal, padx=16, cursor="hand2"
                  ).pack(side=tk.LEFT, pady=10)

        self._pd_title = tk.Label(hdr, text="", bg=C["bg"],
                                  fg=C["text"], font=self.f_bold)
        self._pd_title.pack(side=tk.LEFT, expand=True)

        self._pd_date = tk.Label(hdr, text="", bg=C["bg"],
                                 fg=C["dim"], font=self.f_small)
        self._pd_date.pack(side=tk.RIGHT, padx=20)

        # 底部输入框（先 BOTTOM，让列表填中间）
        inp_wrap = tk.Frame(p, bg=C["bg"])
        tk.Frame(inp_wrap, bg=C["grid_hdr"], height=1).pack(fill=tk.X)
        inp_inner = tk.Frame(inp_wrap, bg=C["bg"])
        inp_inner.pack(fill=tk.X, padx=28, pady=14)

        self._entry = tk.Entry(inp_inner, font=self.f_normal,
                               relief=tk.FLAT, bg=C["bg"],
                               insertbackground=C["text"], fg=C["ph"])
        self._PH = "输入待办事项，按回车添加…"
        self._entry.insert(0, self._PH)
        self._entry.bind("<FocusIn>",  self._ph_clear)
        self._entry.bind("<FocusOut>", self._ph_restore)
        self._entry.bind("<Return>",   lambda _: self._add_todo())
        self._entry.pack(fill=tk.X, ipady=8)
        tk.Frame(inp_inner, bg=C["grid_hdr"], height=1).pack(fill=tk.X)
        inp_wrap.pack(fill=tk.X, side=tk.BOTTOM)

        # 可滚动的待办列表
        outer = tk.Frame(p, bg=C["bg"])
        outer.pack(fill=tk.BOTH, expand=True)

        cv  = tk.Canvas(outer, bg=C["bg"], highlightthickness=0)
        sb  = tk.Scrollbar(outer, orient="vertical", command=cv.yview)
        self._pd_sf = tk.Frame(cv, bg=C["bg"])
        self._pd_sf.bind("<Configure>",
                         lambda _: cv.configure(scrollregion=cv.bbox("all")))
        cw_id = cv.create_window((0, 0), window=self._pd_sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.bind("<Configure>", lambda e: cv.itemconfig(cw_id, width=e.width))
        cv.bind("<Enter>", lambda _, c=cv: self.root.bind_all(
            "<MouseWheel>",
            lambda ev: c.yview_scroll(-1 * (ev.delta // 120), "units")))
        cv.bind("<Leave>", lambda _: self.root.unbind_all("<MouseWheel>"))
        cv.pack(side=tk.LEFT,  fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _ph_clear(self, _):
        if self._entry.get() == self._PH:
            self._entry.delete(0, tk.END)
            self._entry.config(fg=C["text"])

    def _ph_restore(self, _):
        if not self._entry.get():
            self._entry.insert(0, self._PH)
            self._entry.config(fg=C["ph"])

    def _to_period(self, d: date, pi: int):
        self._sel_date   = d
        self._sel_period = pi
        self._show(self.pg_period)
        p  = PERIODS[pi]
        wd = "一二三四五六日"[d.weekday()]
        self._pd_title.config(text=f"{p['name']}   {p['time']}")
        self._pd_date.config(text=f"{d.strftime('%Y年%m月%d日')}  周{wd}")
        self._ph_restore(None)
        self._render_todos()

    def _back_to_day(self):
        self._to_day(self._sel_date)

    # ③ Level 3 的任务列表也用胶囊按钮
    def _render_todos(self):
        sf = self._pd_sf
        for w in sf.winfo_children():
            w.destroy()

        ds    = self._sel_date.strftime("%Y-%m-%d")
        todos = self.data.get(ds, {}).get(str(self._sel_period), [])

        if not todos:
            tk.Label(sf, text="暂无待办事项", bg=C["bg"],
                     fg="#CCCCCC", font=self.f_normal).pack(pady=40)
            return

        tf = tk.Frame(sf, bg=C["bg"])
        tf.pack(fill=tk.X, padx=24, pady=8)

        for todo in todos:
            self._pill_btn(
                tf, todo,
                toggle_cmd=lambda t=todo["id"]: self._toggle(t),
                delete_cmd=lambda t=todo["id"]: self._delete(t),
            )

        tk.Frame(sf, bg=C["bg"], height=16).pack()

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def _ensure(self, ds: str) -> dict:
        if ds not in self.data:
            self.data[ds] = {str(i): [] for i in range(4)}
        return self.data[ds]

    def _add_todo(self):
        txt = self._entry.get().strip()
        if not txt or txt == self._PH:
            return
        ds = self._sel_date.strftime("%Y-%m-%d")
        self._ensure(ds)[str(self._sel_period)].append(
            {"id": str(uuid.uuid4()), "text": txt, "done": False})
        save_data(self.data)
        self._entry.delete(0, tk.END)
        self._entry.config(fg=C["text"])
        self._render_todos()

    def _toggle(self, tid: str):
        ds = self._sel_date.strftime("%Y-%m-%d")
        for t in self._ensure(ds)[str(self._sel_period)]:
            if t["id"] == tid:
                t["done"] = not t["done"]
                break
        save_data(self.data)
        self._render_todos()

    def _delete(self, tid: str):
        ds = self._sel_date.strftime("%Y-%m-%d")
        d  = self._ensure(ds)
        d[str(self._sel_period)] = [t for t in d[str(self._sel_period)]
                                    if t["id"] != tid]
        save_data(self.data)
        self._render_todos()

    # ── 自动刷新 ──────────────────────────────────────────────────────────────
    def _tick(self):
        if self._cur_frame == self.pg_cal:
            self._draw_cal()
        self.root.after(60_000, self._tick)


# ── 入口 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()

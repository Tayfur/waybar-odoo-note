import gi
import os
import threading
import time
import json
import datetime
import html
from odoo_api import OdooClient

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

STATE_FILE = os.path.expanduser("~/.cache/odoo_timer.json")
STATUS_FILE = os.path.expanduser("~/.cache/odoo_status.json")

def format_hrs_to_hm(hrs):
    """Converts decimal hours (0.25) to string format (00:15)"""
    try:
        total_seconds = int(float(hrs) * 3600)
        mins, _ = divmod(total_seconds, 60)
        h, m = divmod(mins, 60)
        return f"{h:02d}:{m:02d}"
    except:
        return "00:00"

class OdooHyprModal(Gtk.Window):
    def __init__(self):
        super().__init__(title="Odoo Workspace")
        self.set_wmclass("OdooModal", "OdooModal")
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(900, 600)
        self.set_keep_above(True)
        self.set_name("MainWindow")

        self.apply_css()
        self.odoo = OdooClient()
        self.is_connected = False
        self.is_loading_projects = False
        
        self.projects_data = {} 
        self.tasks_data = {} 
        self.last_att_status = False
        self.current_check_in_time_dt = None
        self.past_att_hours_today = 0.0
        
        self.timer_state = self.load_timer_state()
        self.timer_running = self.timer_state.get("running", False)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.vbox)

        self.create_header()
        self.create_body()

        self.lbl_status.set_text("🔄 Connecting to Odoo...")
        threading.Thread(target=self._master_startup_thread, daemon=True).start()
        
        GLib.timeout_add_seconds(1, self.ui_update_loop)

    def load_timer_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f: return json.load(f)
            except: pass
        return {"running": False, "start_time": 0, "accumulated": 0, "project": "", "project_id": 0, "task": "", "task_id": 0}

    def save_timer_state(self):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        self.timer_state["running"] = self.timer_running
        with open(STATE_FILE, 'w') as f: json.dump(self.timer_state, f)

    def apply_css(self):
        cp = Gtk.CssProvider()
        try:
            cp.load_from_path(os.path.join(os.path.dirname(__file__), 'style.css'))
            Gtk.StyleContext().add_provider_for_screen(Gdk.Screen.get_default(), cp, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except: pass

    def create_header(self):
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0); hb.set_name("HeaderBox")
        cb = Gtk.Button(label="✖"); cb.set_name("CloseBtn"); cb.connect("clicked", lambda w: Gtk.main_quit())
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tb.pack_start(Gtk.Label(label="💼"), False, False, 0)
        tl = Gtk.Label(label="ODOO WORKSPACE"); tl.set_name("HeaderTitle")
        tb.pack_start(tl, False, False, 0)
        hb.pack_start(tb, False, False, 10); sp = Gtk.Box(); hb.pack_start(sp, True, True, 0); hb.pack_start(cb, False, False, 10)
        self.vbox.pack_start(hb, False, False, 0)

    def create_body(self):
        bb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=25); bb.set_border_width(25); bb.set_name("OdooContainer")
        lc = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.lbl_status = Gtk.Label(label="Initializing..."); self.lbl_status.set_name("StatusLabel"); self.lbl_status.set_halign(Gtk.Align.START)
        lc.pack_start(self.lbl_status, False, False, 0)

        tf = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); tf.set_name("CardBox")
        tf.pack_start(Gtk.Label(label="⏱ TRACKER"), False, False, 0)
        self.project_combo = Gtk.ComboBoxText(); self.project_combo.append_text("Loading Projects..."); self.project_combo.set_active(0)
        self.project_combo.set_sensitive(False); self.project_handler_id = self.project_combo.connect("changed", self.on_project_changed)
        tf.pack_start(self.project_combo, False, False, 0)
        self.task_combo = Gtk.ComboBoxText(); self.task_combo.append_text("Waiting..."); self.task_combo.set_active(0)
        self.task_combo.set_sensitive(False); self.task_combo.connect("changed", self.on_task_changed)
        tf.pack_start(self.task_combo, False, False, 0)
        self.entry_desc = Gtk.Entry(); self.entry_desc.set_placeholder_text("Description...")
        tf.pack_start(self.entry_desc, False, False, 5)
        self.lbl_timer = Gtk.Label(label="00:00:00"); self.lbl_timer.set_name("TimerLabel")
        tf.pack_start(self.lbl_timer, False, False, 5)
        btb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15); btb.set_halign(Gtk.Align.CENTER)
        self.btn_timer_toggle = Gtk.Button(label="▶ START"); self.btn_timer_toggle.set_name("ActionBtn"); self.btn_timer_toggle.connect("clicked", self.toggle_timer)
        self.btn_timer_stop = Gtk.Button(label="⏹ SUBMIT"); self.btn_timer_stop.set_name("ActionBtnDanger"); self.btn_timer_stop.connect("clicked", self.stop_timer)
        btb.pack_start(self.btn_timer_toggle, False, False, 0); btb.pack_start(self.btn_timer_stop, False, False, 0)
        tf.pack_start(btb, False, False, 5); self.lbl_ts_result = Gtk.Label(label=""); tf.pack_start(self.lbl_ts_result, False, False, 0); lc.pack_start(tf, False, False, 0)

        af = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); af.set_name("CardBox")
        af.pack_start(Gtk.Label(label="🏢 ATTENDANCE"), False, False, 0)
        self.lbl_att_status = Gtk.Label(label="Status: Syncing..."); self.lbl_att_status.set_name("AttStatusLabel")
        af.pack_start(self.lbl_att_status, False, False, 5)
        self.btn_attendance = Gtk.Button(label="Check In"); self.btn_attendance.set_name("CheckBtn"); self.btn_attendance.connect("clicked", self.toggle_attendance)
        af.pack_start(self.btn_attendance, False, False, 0); lc.pack_start(af, False, False, 0)
        
        rc = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15); rc.set_name("HistoryCardBox")
        ht = Gtk.Label(label="📊 TODAY'S LOGS"); ht.set_halign(Gtk.Align.START); ht.set_name("SectionTitle")
        self.btn_refresh = Gtk.Button(label="🔄"); self.btn_refresh.set_name("ActionBtn"); self.btn_refresh.connect("clicked", lambda w: self._refresh_data())
        htb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL); htb.pack_start(ht, True, True, 0); htb.pack_start(self.btn_refresh, False, False, 0)
        rc.pack_start(htb, False, False, 0)
        scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.history_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5); scroll.add(self.history_vbox)
        rc.pack_start(scroll, True, True, 0); bb.pack_start(lc, False, False, 0); bb.pack_start(rc, True, True, 0)
        self.vbox.pack_start(bb, True, True, 0)

    def ui_update_loop(self):
        now = time.time()
        # 1. Timer UI (HH:MM:SS format)
        if self.timer_running:
            total_sec = self.timer_state["accumulated"] + (now - self.timer_state["start_time"])
            m, s = divmod(int(total_sec), 60); h, m = divmod(m, 60)
            self.lbl_timer.set_text(f"{h:02d}:{m:02d}:{s:02d}")
        
        # 2. Waybar Update (HH:MM format)
        total_att_hrs = self.past_att_hours_today
        if self.last_att_status and self.current_check_in_time_dt:
            diff = (datetime.datetime.now(datetime.UTC) - self.current_check_in_time_dt).total_seconds()
            total_att_hrs += max(0, diff / 3600.0)
        
        att_hm = format_hrs_to_hm(total_att_hrs)
        
        parts = []
        if self.timer_running:
            proj = self.timer_state.get("project","Unk")[:8]; task = self.timer_state.get("task","Unk")[:8]
            elapsed_hrs = (self.timer_state["accumulated"] + (now - self.timer_state["start_time"])) / 3600.0
            parts.append(f"{proj}-{task} {format_hrs_to_hm(elapsed_hrs)}")
        
        parts.append(f"{'🟢' if self.last_att_status else '⚪'} {att_hm}")
        display_text = f"💼 {html.escape(' | '.join(parts))}"
        
        try:
            status = {"display_text": display_text, "timer": {"running": self.timer_running}, "attendance": {"checked_in": self.last_att_status}}
            with open(STATUS_FILE, 'w') as f: json.dump(status, f)
            os.system("pkill -RTMIN+1 waybar || true")
        except: pass
        return True

    def _master_startup_thread(self):
        if not self.odoo.connect()[0]:
            GLib.idle_add(self.lbl_status.set_text, "🔴 Offline")
            return
        self.is_connected = True
        GLib.idle_add(self.lbl_status.set_text, "🟢 Connected")
        self._refresh_data_sync()
        ok, data = self.odoo.get_projects()
        if ok: GLib.idle_add(self._populate_projects, data)
        GLib.idle_add(self.lbl_status.set_text, "🟢 Ready")

    def _refresh_data(self):
        if self.is_connected: threading.Thread(target=self._refresh_data_sync, daemon=True).start()

    def _refresh_data_sync(self):
        ts_ok, ts_data = self.odoo.get_today_timesheets()
        att_ok, att_data = self.odoo.get_today_attendances()
        GLib.idle_add(self._update_history_ui, ts_ok, ts_data, att_ok, att_data)

    def _update_history_ui(self, ts_ok, ts_data, att_ok, att_data):
        for child in self.history_vbox.get_children(): self.history_vbox.remove(child)
        self.past_att_hours_today = 0.0; self.last_att_status = False; self.current_check_in_time_dt = None
        
        self.history_vbox.pack_start(Gtk.Label(label="🕔 ATTENDANCES"), False, False, 0)
        if att_ok and att_data:
            for a in att_data:
                if not a.get('check_out'):
                    self.last_att_status = True
                    try: self.current_check_in_time_dt = datetime.datetime.strptime(a.get('check_in'), '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
                    except: pass
                else: self.past_att_hours_today += a.get('worked_hours', 0.0)
                cin = a.get('check_in', '').split(' ')[1][:5]; cout = a.get('check_out', '').split(' ')[1][:5] if a.get('check_out') else 'Now'
                r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL); r.set_name("HistoryListRow")
                r.pack_start(Gtk.Label(label=f"{cin} → {cout}"), True, True, 0)
                r.pack_start(Gtk.Label(label=format_hrs_to_hm(a.get('worked_hours', 0))), False, False, 0)
                self.history_vbox.pack_start(r, False, False, 0)
        
        self.history_vbox.pack_start(Gtk.Label(label="📋 TIMESHEETS"), False, False, 10)
        if ts_ok and ts_data:
            for t in ts_data:
                p_n = t.get('project_id')[1] if isinstance(t.get('project_id'), list) else 'Unk'
                t_n = t.get('task_id')[1] if isinstance(t.get('task_id'), list) else '---'
                r = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); r.set_name("HistoryListRow")
                top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                top.pack_start(Gtk.Label(label=f"{p_n}/{t_n}"), True, True, 0)
                top.pack_start(Gtk.Label(label=format_hrs_to_hm(t.get('unit_amount', 0))), False, False, 0)
                r.pack_start(top, False, False, 0); self.history_vbox.pack_start(r, False, False, 0)
        self.history_vbox.show_all()
        self.lbl_att_status.set_text("🟢 Working" if self.last_att_status else "⚪ Off Duty")
        self.btn_attendance.set_label("🚪 CHECK OUT" if self.last_att_status else "🏢 CHECK IN")

    def _populate_projects(self, projects):
        self.is_loading_projects = True; self.project_combo.handler_block(self.project_handler_id)
        self.project_combo.remove_all(); self.projects_data = {}
        self.project_combo.append_text("-- Select Project --"); self.project_combo.set_sensitive(True)
        saved_pid = self.timer_state.get("project_id", 0); active_idx = 0
        for i, p in enumerate(projects):
            n, pid = p.get('name', 'Unk'), p.get('id', 0); self.projects_data[n] = pid
            self.project_combo.append_text(n)
            if pid == saved_pid: active_idx = i + 1
        self.project_combo.set_active(active_idx); self.project_combo.handler_unblock(self.project_handler_id); self.is_loading_projects = False
        if active_idx > 0: self._trigger_task_fetch(saved_pid)

    def on_project_changed(self, combo):
        if self.is_loading_projects: return
        text = combo.get_active_text()
        if text in self.projects_data:
            pid = self.projects_data[text]; self.timer_state.update({"project": text, "project_id": pid}); self.save_timer_state()
            self._trigger_task_fetch(pid)

    def _trigger_task_fetch(self, pid):
        GLib.idle_add(self.lbl_status.set_text, "🔄 Loading Tasks...")
        self.task_combo.set_sensitive(False); self.task_combo.remove_all(); self.task_combo.append_text("Fetching Tasks...")
        threading.Thread(target=self._fetch_tasks_worker, args=(pid,), daemon=True).start()

    def _fetch_tasks_worker(self, pid):
        ok, data = self.odoo.get_tasks(pid)
        if ok: GLib.idle_add(self._populate_tasks, data)
        GLib.idle_add(self.lbl_status.set_text, "🟢 Ready")

    def _populate_tasks(self, tasks):
        self.task_combo.remove_all(); self.tasks_data = {}
        self.task_combo.append_text("-- Task --"); self.task_combo.set_sensitive(True)
        saved_tid = self.timer_state.get("task_id", 0); active_idx = 0
        for i, t in enumerate(tasks):
            n, tid = t.get('name', 'Unk'), t.get('id', 0); self.tasks_data[n] = tid
            self.task_combo.append_text(n)
            if tid == saved_tid: active_idx = i + 1
        self.task_combo.set_active(active_idx)

    def on_task_changed(self, combo):
        text = combo.get_active_text()
        if text in self.tasks_data:
            self.timer_state.update({"task": text, "task_id": self.tasks_data[text]}); self.save_timer_state()

    def toggle_attendance(self, w):
        if not self.is_connected: return
        self.btn_attendance.set_sensitive(False); threading.Thread(target=self._toggle_att_worker, daemon=True).start()

    def _toggle_att_worker(self):
        self.odoo.toggle_attendance(); self._refresh_data_sync()
        GLib.idle_add(self.btn_attendance.set_sensitive, True)

    def toggle_timer(self, w):
        if self.timer_running:
            self.timer_running = False; self.btn_timer_toggle.set_label("▶ RESUME")
            self.timer_state["accumulated"] += (time.time() - self.timer_state["start_time"]); self.save_timer_state()
        else:
            self.timer_running = True; self.btn_timer_toggle.set_label("⏸ PAUSE")
            self.timer_state["start_time"] = time.time(); self.save_timer_state()

    def stop_timer(self, w):
        if not self.timer_running and self.timer_state["accumulated"] == 0: return
        total = (self.timer_state["accumulated"] + (time.time() - self.timer_state["start_time"] if self.timer_running else 0)) / 3600.0
        self.timer_running = False; pid, tid = self.timer_state["project_id"], self.timer_state["task_id"]
        if pid and tid:
            self.lbl_ts_result.set_text("📤 Submitting..."); self.btn_timer_stop.set_sensitive(False)
            threading.Thread(target=self._submit_ts_worker, args=(pid, tid, total, self.entry_desc.get_text()), daemon=True).start()
        self.timer_state.update({"running": False, "start_time": 0, "accumulated": 0}); self.save_timer_state()
        self.lbl_timer.set_text("00:00:00"); self.btn_timer_toggle.set_label("▶ START")

    def _submit_ts_worker(self, pid, tid, hrs, desc):
        self.odoo.create_timesheet_entry(pid, tid, max(hrs, 0.01), desc or "Desktop Entry")
        GLib.idle_add(self.lbl_ts_result.set_text, "✅ Saved"); GLib.idle_add(self.entry_desc.set_text, ""); self._refresh_data_sync()
        GLib.idle_add(self.btn_timer_stop.set_sensitive, True)

if __name__ == "__main__":
    win = OdooHyprModal(); win.connect("destroy", Gtk.main_quit); win.show_all(); Gtk.main()

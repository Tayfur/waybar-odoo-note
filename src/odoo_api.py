import xmlrpc.client
import os
import datetime
from dotenv import load_dotenv

# Load .env from the same directory as this script
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

ODOO_URL = os.getenv("ODOO_URL", "https://viingo.odoo.com")
ODOO_DB = os.getenv("ODOO_DB", "viingo")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "")

class OdooClient:
    def __init__(self):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.username = ODOO_USERNAME
        self.password = ODOO_PASSWORD
        self.uid = None
        self.models = None

    def connect(self):
        try:
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.url))
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                self.models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
                return True, "Connected"
            return False, "Authentication failed"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_attendance_status(self):
        if not self.uid:
            return False, "Not connected"
        try:
            employee_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'hr.employee', 'search',
                [[['user_id', '=', self.uid]]]
            )
            if not employee_ids:
                 return False, "Employee record not found"
                 
            employee = self.models.execute_kw(self.db, self.uid, self.password,
                'hr.employee', 'read',
                [employee_ids[0]],
                {'fields': ['attendance_state']}
            )
            
            state = employee[0].get('attendance_state')
            if state == 'checked_in':
                return True, "Checked In"
            else:
                return False, "Checked Out"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def toggle_attendance(self):
        if not self.uid:
            return False, "Not connected"
        try:
            # Get employee ID
            employee_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'hr.employee', 'search', [[['user_id', '=', self.uid]]]
            )
            if not employee_ids:
                 return False, "Employee record not found"
            
            emp_id = employee_ids[0]
            
            # Check current status
            checked_in, _ = self.get_attendance_status()
            now_utc = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')
            
            if not checked_in:
                # Perform Check-In (create a record)
                self.models.execute_kw(self.db, self.uid, self.password,
                    'hr.attendance', 'create', [{
                        'employee_id': emp_id,
                        'check_in': now_utc
                    }]
                )
                return True, "Check-in successful"
            else:
                # Perform Check-Out (update existing record)
                open_att_ids = self.models.execute_kw(self.db, self.uid, self.password,
                    'hr.attendance', 'search', [[['employee_id', '=', emp_id], ['check_out', '=', False]]],
                    {'order': 'check_in desc', 'limit': 1}
                )
                if open_att_ids:
                    self.models.execute_kw(self.db, self.uid, self.password,
                        'hr.attendance', 'write', [open_att_ids, {
                            'check_out': now_utc
                        }]
                    )
                    return True, "Check-out successful"
                return False, "No open attendance found"
        except Exception as e:
            return False, f"Attendance Action Error: {str(e)}"

    def get_projects(self):
        if not self.uid:
            return False, []
        try:
            project_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'project.project', 'search',
                [[['active', '=', True]]],
                {'limit': 20}
            )
            if not project_ids:
                return True, []
                
            projects = self.models.execute_kw(self.db, self.uid, self.password,
                'project.project', 'read',
                [project_ids],
                {'fields': ['name']}
            )
            return True, projects
        except Exception as e:
            return False, str(e)
            
    def get_tasks(self, project_id):
        if not self.uid or not project_id:
            return False, []
        try:
            task_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'project.task', 'search',
                [[['project_id', '=', project_id], ['is_closed', '=', False]]],
                {'limit': 50}
            )
            if not task_ids:
                return True, []
                
            tasks = self.models.execute_kw(self.db, self.uid, self.password,
                'project.task', 'read',
                [task_ids],
                {'fields': ['name']}
            )
            return True, tasks
        except Exception as e:
            return False, str(e)

    def create_timesheet_entry(self, project_id, task_id, duration_hours, description="Worked on task"):
        if not self.uid:
            return False, "Not connected"
        try:
            employee_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'hr.employee', 'search',
                [[['user_id', '=', self.uid]]]
            )
            if not employee_ids:
                 return False, "Employee record not found"

            timesheet_data = {
                'project_id': project_id,
                'task_id': task_id,
                'employee_id': employee_ids[0],
                'name': description,
                'unit_amount': duration_hours
            }
            
            result = self.models.execute_kw(self.db, self.uid, self.password,
                'account.analytic.line', 'create',
                [timesheet_data]
            )
            return True, "Timesheet saved successfully"
        except Exception as e:
            return False, f"Failed to save timesheet: {str(e)}"

    def get_today_timesheets(self):
        if not self.uid:
            return False, []
        try:
            employee_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'hr.employee', 'search',
                [[['user_id', '=', self.uid]]]
            )
            if not employee_ids:
                 return False, []
                 
            today_str = datetime.date.today().strftime('%Y-%m-%d')
            
            ts_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'account.analytic.line', 'search',
                [[['employee_id', '=', employee_ids[0]], ['date', '=', today_str]]],
                {'order': 'id desc', 'limit': 15}
            )
            if not ts_ids:
                return True, []
                
            timesheets = self.models.execute_kw(self.db, self.uid, self.password,
                'account.analytic.line', 'read',
                [ts_ids],
                {'fields': ['name', 'unit_amount', 'project_id', 'task_id']}
            )
            return True, timesheets
        except Exception as e:
            return False, str(e)

    def get_today_attendances(self):
        if not self.uid:
            return False, []
        try:
            employee_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'hr.employee', 'search',
                [[['user_id', '=', self.uid]]]
            )
            if not employee_ids:
                 return False, []
                 
            today_str = datetime.date.today().strftime('%Y-%m-%d')
            
            att_ids = self.models.execute_kw(self.db, self.uid, self.password,
                'hr.attendance', 'search',
                [[['employee_id', '=', employee_ids[0]], ['check_in', '>=', today_str + ' 00:00:00']]],
                {'order': 'check_in desc'}
            )
            if not att_ids:
                return True, []
                
            attendances = self.models.execute_kw(self.db, self.uid, self.password,
                'hr.attendance', 'read',
                [att_ids],
                {'fields': ['check_in', 'check_out', 'worked_hours']}
            )
            return True, attendances
        except Exception as e:
            return False, str(e)

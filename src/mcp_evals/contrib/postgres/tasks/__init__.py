"""Postgres evaluation tasks."""

from .create_payment_index.task import CreatePaymentIndexTask
from .department_summary_view.task import DepartmentSummaryViewTask
from .update_employee_info.task import UpdateEmployeeInfoTask

__all__ = [
    "CreatePaymentIndexTask",
    "DepartmentSummaryViewTask",
    "UpdateEmployeeInfoTask",
]

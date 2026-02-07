"""Postgres evaluation tasks."""

from .baseball_player_analysis.task import BaseballPlayerAnalysisTask
from .consistency_enforcement.task import ConsistencyEnforcementTask
from .create_payment_index.task import CreatePaymentIndexTask
from .customer_analysis_fix.task import CustomerAnalysisFixTask
from .customer_analytics_optimization.task import CustomerAnalyticsOptimizationTask
from .customer_data_migration.task import CustomerDataMigrationTask
from .database_security_policies.task import DatabaseSecurityPoliciesTask
from .department_summary_view.task import DepartmentSummaryViewTask
from .employee_demographics_report.task import EmployeeDemographicsReportTask
from .employee_hierarchy_management.task import EmployeeHierarchyManagementTask
from .employee_performance_analysis.task import EmployeePerformanceAnalysisTask
from .employee_project_tracking.task import EmployeeProjectTrackingTask
from .employee_retention_analysis.task import EmployeeRetentionAnalysisTask
from .executive_dashboard_automation.task import ExecutiveDashboardAutomationTask
from .film_inventory_management.task import FilmInventoryManagementTask
from .management_structure_analysis.task import ManagementStructureAnalysisTask
from .participant_report_optimization.task import ParticipantReportOptimizationTask
from .sales_and_music_charts.task import SalesAndMusicChartsTask
from .team_roster_management.task import TeamRosterManagementTask
from .transactional_inventory_transfer.task import TransactionalInventoryTransferTask
from .update_employee_info.task import UpdateEmployeeInfoTask

__all__ = [
    "BaseballPlayerAnalysisTask",
    "ConsistencyEnforcementTask",
    "CreatePaymentIndexTask",
    "CustomerAnalysisFixTask",
    "CustomerAnalyticsOptimizationTask",
    "CustomerDataMigrationTask",
    "DatabaseSecurityPoliciesTask",
    "DepartmentSummaryViewTask",
    "EmployeeDemographicsReportTask",
    "EmployeeHierarchyManagementTask",
    "EmployeePerformanceAnalysisTask",
    "EmployeeProjectTrackingTask",
    "EmployeeRetentionAnalysisTask",
    "ExecutiveDashboardAutomationTask",
    "FilmInventoryManagementTask",
    "ManagementStructureAnalysisTask",
    "ParticipantReportOptimizationTask",
    "SalesAndMusicChartsTask",
    "TeamRosterManagementTask",
    "TransactionalInventoryTransferTask",
    "UpdateEmployeeInfoTask",
]

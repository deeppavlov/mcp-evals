"""Postgres evaluation tasks."""

from .baseball_player_analysis.task import BaseballPlayerAnalysisTask
from .consistency_enforcement.task import ConsistencyEnforcementTask
from .customer_analysis_fix.task import CustomerAnalysisFixTask
from .customer_analytics_optimization.task import CustomerAnalyticsOptimizationTask
from .customer_data_migration.task import CustomerDataMigrationTask
from .database_security_policies.task import DatabaseSecurityPoliciesTask
from .dba_vector_analysis.task import DbaVectorAnalysisTask
from .employee_demographics_report.task import EmployeeDemographicsReportTask
from .employee_hierarchy_management.task import EmployeeHierarchyManagementTask
from .employee_performance_analysis.task import EmployeePerformanceAnalysisTask
from .employee_project_tracking.task import EmployeeProjectTrackingTask
from .employee_retention_analysis.task import EmployeeRetentionAnalysisTask
from .executive_dashboard_automation.task import ExecutiveDashboardAutomationTask
from .film_inventory_management.task import FilmInventoryManagementTask
from .management_structure_analysis.task import ManagementStructureAnalysisTask
from .participant_report_optimization.task import ParticipantReportOptimizationTask
from .rls_business_access.task import RlsBusinessAccessTask
from .sales_and_music_charts.task import SalesAndMusicChartsTask
from .team_roster_management.task import TeamRosterManagementTask
from .transactional_inventory_transfer.task import TransactionalInventoryTransferTask

__all__ = [
    "BaseballPlayerAnalysisTask",
    "ConsistencyEnforcementTask",
    "CreatePaymentIndexTask",
    "CustomerAnalysisFixTask",
    "CustomerAnalyticsOptimizationTask",
    "CustomerDataMigrationTask",
    "DatabaseSecurityPoliciesTask",
    "DbaVectorAnalysisTask",
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
    "RlsBusinessAccessTask",
    "SalesAndMusicChartsTask",
    "TeamRosterManagementTask",
    "TransactionalInventoryTransferTask",
    "UpdateEmployeeInfoTask",
]

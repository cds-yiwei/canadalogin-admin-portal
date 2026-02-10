class Permission:
    USER_READ = "user.read"
    USER_APPROVE = "user.approve"
    DASHBOARD_VIEW = "dashboard.view"
    TICKET_MANAGE = "ticket.manage"
    AUDIT_VIEW = "audit.view"


ALL_PERMISSIONS = {
    Permission.USER_READ,
    Permission.USER_APPROVE,
    Permission.DASHBOARD_VIEW,
    Permission.TICKET_MANAGE,
    Permission.AUDIT_VIEW,
}

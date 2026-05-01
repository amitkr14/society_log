from rest_framework import permissions

class IsAdminOrGuardCreateOnly(permissions.BasePermission):
    """
    Custom permission for Visitor Logs:
    - Admins can do anything (GET, POST, PUT, DELETE).
    - Security Guards can only View (GET) and Create (POST).
    """
    
    def has_permission(self, request, view):
        # 1. Block anyone who isn't logged in with a valid token/session
        if not request.user or not request.user.is_authenticated:
            return False

        # 2. If the user is in the 'Admins' group, grant full access
        if request.user.groups.filter(name='Admins').exists():
            return True

        # 3. If the user is in the 'Security Guards' group, restrict actions
        if request.user.groups.filter(name='Security Guards').exists():
            # SAFE_METHODS are GET, HEAD, OPTIONS (just looking at data)
            # We also explicitly allow POST (creating a new check-in)
            if request.method in permissions.SAFE_METHODS or request.method == 'POST':
                return True
                
            # If a guard tries to send a DELETE or PUT (edit) request, block it
            return False

        # 4. If they belong to no group, deny access by default
        return False
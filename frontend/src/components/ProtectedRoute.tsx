import { Navigate } from "react-router-dom";
import { useAuth } from "../store/auth";
import type { Role } from "../types";

export function ProtectedRoute({
  children,
  allowedRoles,
}: {
  children: React.ReactNode;
  allowedRoles?: Role[];
}) {
  const { token, user } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  if (allowedRoles) {
    // Wait for /auth/me to resolve before checking role.
    if (!user) return null;
    if (!allowedRoles.includes(user.role)) return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

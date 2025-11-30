import { Navigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

type Props = {
    children: React.ReactNode; // Content to protect
    roles?: string[];
    allowAny?: boolean;
};

export default function ProtectedRoute({ children, roles = [], allowAny = false }: Props) {
    const { user, loading } = useAuth();

    if (loading) return <p className="muted">Loading...</p>;
    if (!user) return <Navigate to="/login" replace />;

    if (!allowAny && roles.length) {
        const userRoles = new Set((user.roles || []).map((r) => r.toLowerCase()));
        const allowed = roles.some((r) => userRoles.has(r.toLowerCase()));
        if (!allowed) return <Navigate to="/search" replace />;
    }
    return <>{children}</>;
}

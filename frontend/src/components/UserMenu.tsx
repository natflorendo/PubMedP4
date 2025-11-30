import { useAuth } from "../AuthContext";

export default function UserMenu() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <div className="user-menu">
      <div>{user.name}</div>
      
      <div className="muted">{user.roles?.join(", ")}</div>
    </div>
  );
}

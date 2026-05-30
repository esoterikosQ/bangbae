import { Outlet } from 'react-router-dom';
import NavBar from './NavBar';

export default function Layout() {
  return (
    <div className="min-h-screen pb-20">
      <div className="mx-auto max-w-lg px-4">
        <Outlet />
      </div>
      <NavBar />
    </div>
  );
}

import { NavLink, useNavigate } from 'react-router-dom';

const tabs = [
  { to: '/', icon: '📊', label: '대시보드' },
  { to: '/transactions', icon: '💳', label: '거래' },
  { to: '/add', icon: '➕', label: '입력' },
  { to: '/budgets', icon: '🎯', label: '예산' },
  { to: '/categories', icon: '🏷️', label: '분류' },
];

export default function NavBar() {
  const navigate = useNavigate();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-800 bg-slate-950/95 backdrop-blur-sm">
      <div className="mx-auto flex max-w-lg">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === '/'}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-0.5 py-2.5 text-xs transition-colors ${
                isActive
                  ? 'text-emerald-400'
                  : 'text-slate-500 hover:text-slate-300'
              }`
            }
          >
            <span className="text-lg">{tab.icon}</span>
            <span className="font-medium">{tab.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

// src/components/layout/Sidebar.tsx
import React, { useState, useEffect } from 'react'
import { Home, BarChart2, Users, Activity } from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'

const navigation = [
  { name: 'Overview', icon: Home, path: '/dashboard' },
  { name: 'Analytics', icon: BarChart2, path: '/dashboard' },
  { name: 'Users', icon: Users, path: '/dashboard' },
  { name: 'User Activity', icon: Activity, path: '/user-activity' },
]

const Sidebar = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [selected, setSelected] = useState(navigation[0].name)

  useEffect(() => {
    const currentPath = location.pathname
    const currentNav = navigation.find(nav => nav.path === currentPath)
    if (currentNav) {
      setSelected(currentNav.name)
    }
  }, [location])
  
  const handleNavigation = (item: typeof navigation[0]) => {
    setSelected(item.name)
    navigate(item.path)
  }
  
  return (
    <aside className="fixed top-16 left-0 w-64 h-[calc(100vh-4rem)] bg-white border-r border-gray-200">
      <nav className="h-full py-4">
        <div className="px-3 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = selected === item.name
            
            return (
              <button
                key={item.name}
                onClick={() => handleNavigation(item)}
                className={`
                  flex items-center w-full px-3 py-2 text-sm rounded-md
                  ${isActive 
                    ? 'bg-gray-100 text-gray-900 font-medium' 
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}
                `}
              >
                <Icon 
                  size={18} 
                  className="mr-3 flex-shrink-0" 
                />
                {item.name}
              </button>
            )
          })}
        </div>
      </nav>
    </aside>
  )
}

export default Sidebar
// src/components/layout/dub_Sidebar.tsx
import React, { useState } from 'react'
import { Home, BarChart2, Users, LineChart } from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'

const navigation = [
  { name: 'Overview', icon: Home, path: '/' },
  { name: 'Analytics', icon: BarChart2, path: '/analytics' },
  { name: 'User Activity', icon: LineChart, path: '/user-activity' },
  { name: 'Users', icon: Users, path: '/users' },
]

const Sidebar = () => {
  const navigate = useNavigate()
  const location = useLocation()
  
  const isActive = (path: string) => {
    if (path === '/' && location.pathname === '/') return true
    if (path !== '/' && location.pathname.startsWith(path)) return true
    return false
  }
  
  return (
    <aside className="fixed top-16 left-0 w-64 h-[calc(100vh-4rem)] bg-white border-r border-gray-200">
      <nav className="h-full py-4">
        <div className="px-3 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon
            const active = isActive(item.path)
            
            return (
              <button
                key={item.name}
                onClick={() => navigate(item.path)}
                className={`
                  flex items-center w-full px-3 py-2 text-sm rounded-md transition-colors
                  ${active 
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